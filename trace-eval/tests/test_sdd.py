"""Spec layer: clause checkers and end-to-end verdicts on the demo PRs."""

import json
from pathlib import Path

import pytest

from traceeval.catalog import load_catalog
from traceeval.spec import load_specs
from traceeval.spec.model import Clause
from traceeval.spec.product import ProductModel
from traceeval.spec.prs import PRS, prs_for
from traceeval.spec.runner import agent_brief, evaluate_pr, record_baseline


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    workdir = tmp_path_factory.mktemp("sdd")
    catalog = {c.id: c for c in load_catalog()}
    sut_dir, runs, deps = record_baseline(workdir, catalog)
    return workdir, catalog, runs, deps, sut_dir


def _verdicts(world, spec_id):
    workdir, catalog, runs, deps, _ = world
    spec = next(s for s in load_specs() if s.id == spec_id)
    return {pr.id: evaluate_pr(spec, pr, workdir, catalog, runs, deps) for pr in prs_for(spec_id)}


def test_specs_load_and_every_pr_has_a_spec():
    ids = {s.id for s in load_specs()}
    assert ids == {"FS-0101", "FS-0102", "FS-0103", "FS-0104", "FS-0105"}
    assert {p.spec_id for p in PRS} <= ids
    assert len({p.id for p in PRS}) == len(PRS)


def test_fs0101_verdicts_and_proof(world):
    ev = _verdicts(world, "FS-0101")
    assert {k: v["verdict"] for k, v in ev.items()} == {
        "FS-0101/pr_correct": "accepted",
        "FS-0101/pr_no_lower_bound": "rejected",
        "FS-0101/pr_off_by_one": "rejected",
        "FS-0101/pr_branchy": "accepted with gaps",
        "FS-0101/pr_in_adapter": "rejected",
        "FS-0101/pr_unwired": "rejected",
    }
    rule, monitor = "function_contract:review_age_ok", "always_on_calls:publish_page+schedule_publish"
    by = {c["clause_id"]: c for c in ev["FS-0101/pr_correct"]["clauses"]}
    assert by[rule]["rung"] == "L5" and by[rule]["status"] == "pass" and by[rule]["required"] == "L5"
    wrong = {c["clause_id"]: c for c in ev["FS-0101/pr_no_lower_bound"]["clauses"]}
    assert wrong[rule]["status"] == "fail" and any("age_days': -1" in d for d in wrong[rule]["details"])
    placed = {c["clause_id"]: c for c in ev["FS-0101/pr_in_adapter"]["clauses"]}
    assert placed["function_in_layer:review_age_ok"]["status"] == "fail" and placed[monitor]["status"] == "pass"
    branchy = {c["clause_id"]: c for c in ev["FS-0101/pr_branchy"]["clauses"]}
    assert ev["FS-0101/pr_branchy"]["verdict"] == "accepted with gaps"
    assert branchy[rule]["status"] == "gap" and branchy[rule]["rung"] == "L2" and branchy[rule]["required"] == "L5"


def test_fs0105_finds_the_latent_defect_and_accepts_the_fix(world):
    ev = _verdicts(world, "FS-0105")
    assert ev["FS-0105/current"]["verdict"] == "rejected"
    assert ev["FS-0105/pr_fix"]["verdict"] == "accepted"
    assert ev["FS-0105/pr_partial_fix"]["verdict"] == "rejected"
    partial = {c["clause_id"]: c for c in ev["FS-0105/pr_partial_fix"]["clauses"]}
    assert any("unpublish_page" in d for d in partial["property_over_set:tool"]["details"])
    assert ev["FS-0105/pr_fix"]["change"]["files"] == ["services/workflow.py", "tools/publish_tools.py"]


def test_fs0102_and_fs0103_verdicts(world):
    ev = _verdicts(world, "FS-0102")
    assert ev["FS-0102/current"]["verdict"] == "rejected"  # a made-up token passes today
    assert ev["FS-0102/pr_correct"]["verdict"] == "accepted"
    placed = {c["clause_id"]: c for c in ev["FS-0102/pr_in_dispatcher"]["clauses"]}
    assert [k for k, c in placed.items() if c["status"] == "fail"] == [
        "function_in_layer:approver_for",
        "forbid_name_in:users",
    ]
    ev = _verdicts(world, "FS-0103")
    assert ev["FS-0103/pr_correct"]["verdict"] == "accepted"
    stale = {c["clause_id"]: c for c in ev["FS-0103/pr_gate_ignores_version"]["clauses"]}
    assert [k for k, c in stale.items() if c["status"] == "fail"] == ["function_contract:links_clean"]
    assert stale["function_contract:links_clean"]["rung"] == "L5" and "solver counterexample" in " ".join(
        stale["function_contract:links_clean"]["details"]
    )


def test_brief_is_a_small_fraction_of_the_repo(world):
    _, catalog, runs, deps, sut_dir = world
    model = ProductModel(sut_dir, runs, deps)
    spec = next(s for s in load_specs() if s.id == "FS-0101")
    brief = agent_brief(spec, model, catalog)
    assert "services/workflow.py" in brief["read"] and "tools/publish_tools.py" in brief["read"]
    assert brief["context_tokens"] < 0.25 * brief["repo_tokens"]


def test_setting_and_placement_checks_are_static(world):
    from traceeval.spec.checks import placement, settings
    from traceeval.spec.context import CheckContext

    _, catalog, runs, deps, sut_dir = world
    ctx = CheckContext(sut=None, model=ProductModel(sut_dir, runs, deps), catalog=catalog)
    bad = Clause("x", "setting", data={"key": "runtime.retries", "type": "integer", "min": 3})
    assert settings.check(bad, ctx).status == "fail"
    rule = Clause("y", "placement", data={"rules": [{"forbid_import": {"module": "datetime", "in": ["tools"]}}]})
    assert placement.check(rule, ctx).status == "pass"
    assert ctx.cost["runs"] == 0


def test_cli_writes_report(tmp_path):
    from traceeval.cli import main

    main(["sdd", "--workdir", str(tmp_path / "w"), "--specs", "FS-0102", "--out", str(tmp_path / "out")])
    report = Path(tmp_path / "out" / "report.md").read_text()
    assert "FS-0102/current" in report and "**accepted**" in report


def test_catalog_expansion_and_validation(world):
    from traceeval.spec.model import expand_clause, load_catalog, validate_spec

    catalog = load_catalog()
    c = expand_clause({"use": "setting_in_range", "with": {"key": "runtime.retries", "min": 1, "max": 5}}, catalog)
    assert c.id == "setting_in_range:runtime.retries" and c.kind == "setting" and c.require == "L4"
    assert c.data == {"key": "runtime.retries", "type": "integer", "min": 1, "max": 5}  # optional slot dropped
    with pytest.raises(ValueError):
        expand_clause({"use": "setting_in_range", "with": {"key": "runtime.retries"}}, catalog)  # missing slots
    _, catalog_cases, runs, deps, sut_dir = world
    model = ProductModel(sut_dir, runs, deps)
    spec = next(s for s in load_specs() if s.id == "FS-0101")
    notes = validate_spec(spec, model)
    assert all(level == "note" for level, _ in notes) and len(notes) == 2  # the request introduces a key and a function
    bad = expand_clause({"use": "always_on_calls", "with": {"tools": ["no_such_tool"], "where": "1 +"}}, catalog)
    spec.clauses.append(bad)
    levels = [level for level, _ in validate_spec(spec, model)]
    assert levels.count("error") == 2


def test_draft_from_request_with_a_fake_model_and_by_replay(world, tmp_path):
    """The drafting flow: prompt built from catalog + product model, answer expanded and validated, draft written;
    the draft loads as a spec and accepts the correct PR."""
    from traceeval.spec.draft import build_messages, draft, product_slice
    from traceeval.spec.model import load_catalog, load_spec

    workdir, catalog, runs, deps, sut_dir = world
    model = ProductModel(sut_dir, runs, deps)
    example = Path("docs/sdd/draft_example")
    answer = json.loads((example / "answer.json").read_text())["content"]

    class FakeCompletions:
        def create(self, **kwargs):
            system = kwargs["messages"][0]
            assert system["role"] == "system" and "## Catalog of clause templates" in system["content"]
            message = type("M", (), {"content": answer})()
            return type("R", (), {"choices": [type("C", (), {"message": message})()]})()

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    class Settings:
        model = "fake"

    live = draft(
        example / "request.md",
        "FS-0101",
        tmp_path / "live.draft.yaml",
        model,
        catalog,
        client=FakeClient(),
        settings=Settings(),
        save_response=tmp_path / "saved.json",
    )
    replayed = draft(
        example / "request.md",
        "FS-0101",
        tmp_path / "replay.draft.yaml",
        model,
        catalog,
        replay=tmp_path / "saved.json",
    )
    assert live["problems"] == [] and replayed["problems"] == []
    assert [c.id for c in live["spec"].clauses] == [c.id for c in replayed["spec"].clauses]
    assert all(line.startswith("note:") for line in live["validation"])  # only "the request introduces" notes
    slice_text = product_slice(model, catalog)
    assert "publish_page: write" in slice_text and "## Configuration keys" in slice_text
    assert len(build_messages("x", load_catalog(), slice_text)) == 2

    spec = load_spec(tmp_path / "live.draft.yaml")
    pr = next(p for p in PRS if p.id == "FS-0101/pr_correct")
    ev = evaluate_pr(spec, pr, workdir, catalog, runs, deps)
    assert ev["verdict"] == "accepted"
