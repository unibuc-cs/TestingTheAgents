"""Spec layer: clause checkers and end-to-end verdicts on the demo PRs."""

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
        "FS-0101/pr_in_adapter": "rejected",
        "FS-0101/pr_unwired": "rejected",
    }
    by = {c["clause_id"]: c for c in ev["FS-0101/pr_correct"]["clauses"]}
    assert by["age-rule"]["rung"] == "L5" and by["age-rule"]["status"] == "pass"
    wrong = {c["clause_id"]: c for c in ev["FS-0101/pr_no_lower_bound"]["clauses"]}
    assert wrong["age-rule"]["status"] == "fail" and any("age_days': -1" in d for d in wrong["age-rule"]["details"])
    placed = {c["clause_id"]: c for c in ev["FS-0101/pr_in_adapter"]["clauses"]}
    assert placed["lives-in-service"]["status"] == "fail" and placed["no-stale-go-live"]["status"] == "pass"


def test_fs0105_finds_the_latent_defect_and_accepts_the_fix(world):
    ev = _verdicts(world, "FS-0105")
    assert ev["FS-0105/current"]["verdict"] == "rejected"
    assert ev["FS-0105/pr_fix"]["verdict"] == "accepted"
    assert ev["FS-0105/pr_partial_fix"]["verdict"] == "rejected"
    partial = {c["clause_id"]: c for c in ev["FS-0105/pr_partial_fix"]["clauses"]}
    assert any("unpublish_page" in d for d in partial["once-per-write"]["details"])
    assert ev["FS-0105/pr_fix"]["change"]["files"] == ["services/workflow.py", "tools/publish_tools.py"]


def test_fs0102_and_fs0103_verdicts(world):
    ev = _verdicts(world, "FS-0102")
    assert ev["FS-0102/current"]["verdict"] == "rejected"  # a made-up token passes today
    assert ev["FS-0102/pr_correct"]["verdict"] == "accepted"
    placed = {c["clause_id"]: c for c in ev["FS-0102/pr_in_dispatcher"]["clauses"]}
    assert [k for k, c in placed.items() if c["status"] == "fail"] == ["one-gate"]
    ev = _verdicts(world, "FS-0103")
    assert ev["FS-0103/pr_correct"]["verdict"] == "accepted"
    stale = {c["clause_id"]: c for c in ev["FS-0103/pr_gate_ignores_version"]["clauses"]}
    assert [k for k, c in stale.items() if c["status"] == "fail"] == ["clean-check-rule"]
    assert stale["clean-check-rule"]["rung"] == "L5" and "solver counterexample" in " ".join(
        stale["clean-check-rule"]["details"]
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
