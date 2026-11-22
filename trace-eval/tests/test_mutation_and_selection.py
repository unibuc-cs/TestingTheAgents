"""Tests for mutations, change-set extraction, metrics and strategies (small end-to-end run)."""

import ast
import math
import random
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from traceeval.catalog import load_catalog, load_features, load_properties
from traceeval.catalog.loader import EvalCase
from traceeval.experiment.check import check
from traceeval.experiment.coverage import (
    _crosses,
    _registered_tools,
    affected_error_paths,
    affected_features,
    affected_properties,
    coverage_floor,
    error_paths,
    suite_coverage,
)
from traceeval.experiment.coverage import (
    tests_per_component as per_component,
)
from traceeval.experiment.culprits import day_map, halving_runs, suspects
from traceeval.experiment.evaluate import evaluate, make_oracle
from traceeval.experiment.executor import read_jsonl, write_jsonl
from traceeval.experiment.history import History
from traceeval.experiment.history import TestStats as RunStats  # not under a name pytest would collect
from traceeval.experiment.manifest import baseline_copy, drift, load_manifest, tree_digest
from traceeval.experiment.metrics import apfd, apfdc, evaluate_log
from traceeval.experiment.replay_first import Replays, cassette_path, replay_first
from traceeval.experiment.report import write_report
from traceeval.experiment.runner import record_baseline, record_mutants
from traceeval.experiment.stopping import group_of, threshold
from traceeval.experiment.sutloader import copy_sut
from traceeval.mutation import MUTATIONS, compute_changeset, get_mutation, materialize_variant
from traceeval.mutation.changeset import ChangedComponent, ChangeSet, _flatten, _python_components, _yaml_code_lines
from traceeval.mutation.generator import generate, kind_of, sample, split
from traceeval.mutation.operators import PatchError
from traceeval.selection import CORE, SelectionContext, Strategy, get_strategy
from traceeval.selection.adapted import fit_logistic, kmeans, run_signals, sigmoid
from traceeval.selection.adaptive_bayes import AdaptiveBayes
from traceeval.selection.base import ExecutionLog, matches, weighted_affinity
from traceeval.sut import SUT_ROOT

COMMENT_ONLY = {"benign_code_comment_docstring", "benign_config_comments_reordered"}


def test_every_mutation_applies_and_changes_something(tmp_path):
    for m in MUTATIONS:
        _, cs = materialize_variant(m, tmp_path / "v")
        if m.id in COMMENT_ONLY:  # comments and formatting reach no strategy
            assert not (cs.files or cs.components or cs.diff), m.id
        else:
            assert cs.files and cs.components, m.id


def test_changeset_leaves_out_comments(tmp_path):
    _, cs = materialize_variant(get_mutation("benign_code_comment_docstring"), tmp_path / "v")
    assert cs.is_provably_benign()
    _, cs = materialize_variant(get_mutation("code_retry_drop_idempotency"), tmp_path / "v")
    assert not cs.is_provably_benign()
    assert any(c.id == "code:harness/retry.py::with_retry" for c in cs.components)
    assert any(c.kind == "line" for c in cs.components)
    _, cs = materialize_variant(get_mutation("config_retries_0"), tmp_path / "v")
    assert "retries: 0" in cs.diff and "transient" not in cs.diff  # the trailing YAML comment is cut off


def test_commenting_the_code_does_not_change_the_changeset(tmp_path):
    commented = copy_sut(tmp_path / "commented", SUT_ROOT)
    retry = commented / "harness" / "retry.py"
    retry.write_text(
        "# A new comment at the top.\n"
        + retry.read_text().replace(
            "    key = idempotency_key(operation) if (is_write and idempotency_enabled) else None\n",
            "    # A new comment above the line.\n"
            "    key = idempotency_key(operation) if (is_write and idempotency_enabled) else None  # a trailing one\n",
        )
    )
    m = get_mutation("code_retry_drop_idempotency")
    _, plain = materialize_variant(m, tmp_path / "v1")
    _, again = materialize_variant(m, tmp_path / "v2", baseline=commented)
    assert again.diff == plain.diff
    assert [(c.kind, c.detail) for c in again.components] == [(c.kind, c.detail) for c in plain.components]
    assert [c.id for c in again.components if c.kind != "line"] == [c.id for c in plain.components if c.kind != "line"]
    # line components still name real lines of the file: the two new comment lines sit above the change
    plain_lines = [int(c.id.rsplit(":", 1)[1]) for c in plain.components if c.kind == "line"]
    assert [int(c.id.rsplit(":", 1)[1]) for c in again.components if c.kind == "line"] == [n + 2 for n in plain_lines]


def test_yaml_comments_are_cut_but_a_hash_inside_a_scalar_stays():
    text = 'a: 1  # note\n# a whole-line comment\nb: "x # y"\nc: |\n  # part of the prompt\n  text\n'
    assert [t for _, t in _yaml_code_lines(text)] == ["a: 1", 'b: "x # y"', "c: |", "  # part of the prompt", "  text"]


def test_a_changed_class_attribute_is_a_change():
    old = "class Settings:\n    max_tokens: int = 512\n\n    def f(self):\n        return self.max_tokens\n"
    comps = _python_components("x.py", old, old.replace("512", "256"))
    assert "code:x.py" in {c.id for c in comps} and any(c.kind == "line" for c in comps)


def test_changeset_is_order_sensitive_for_intents(tmp_path):
    _, cs = materialize_variant(get_mutation("benign_translation_intents_reordered"), tmp_path / "v")
    assert "agent:translation.intents" in cs.ids()


def test_a_run_covers_a_workflow_when_it_delegates_to_exactly_its_chain():
    def run(*targets):
        return {"routes": [("orchestrator", t) for t in targets]}

    w4 = ["authoring", "translation", "publishing"]
    assert _crosses(run("authoring", "translation", "translation", "publishing"), w4)  # one step per language
    assert not _crosses(run("authoring", "assets", "brand", "translation", "publishing"), w4)  # W1 contains W4's chain
    assert not _crosses(run("authoring", "translation"), w4)


def test_every_part_of_a_feature_exists_in_the_app():
    tools = _registered_tools(SUT_ROOT) | {"route_to_agent"}
    skills = {d.name for d in (SUT_ROOT / "skills").iterdir() if d.is_dir()}
    agents = {f.stem for f in (SUT_ROOT / "agents").glob("*.yaml")}
    config = set(_flatten(yaml.safe_load((SUT_ROOT / "config" / "runtime.yaml").read_text(encoding="utf-8"))))
    for f in load_features().values():
        assert f.tools and set(f.tools) <= tools, f.id
        for part in f.parts:
            kind, name = part.split(":", 1)
            if kind == "code":
                file, _, function = name.partition("::")
                tree = ast.parse((SUT_ROOT / file).read_text(encoding="utf-8"))
                defined = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
                assert not function or set(function.split(".")) <= defined, part
            else:
                assert name in {"skill": skills, "agent": agents, "config": config}[kind], part


def test_a_change_affects_the_features_and_the_refusals_it_touches():
    def change(*ids):
        return ChangeSet("v", components=[ChangedComponent(i, i.split(":", 1)[0], "") for i in ids])

    assert affected_features(change("config:publishing.allow_scheduling")) == {"schedule"}
    assert {"routing", "planning", "approval"} <= affected_features(change("skill:routing#prose"))
    assert "brand" in affected_features(change("code:services/brand.py::check_page"))  # a function of a part's file
    assert affected_features(change("code:harness/retry.py::with_retry")) == set()  # shared by every feature
    paths = {(p.file, p.function, p.code) for p in error_paths()}
    assert ("tools/publish_tools.py", "schedule_publish", "validation_error") in paths  # a raise
    assert ("harness/dispatcher.py", "Dispatcher.call", "approval_required") in paths  # an error result written out
    assert not {code for _, _, code in paths} & {"tool_crash", "control_tool"}  # neither is a refusal
    hit = affected_error_paths(change("code:services/governance.py::export_user_data"))
    assert {p.code for p in hit} == {"approval_required", "not_found"}


def test_adapted_baselines_helpers():
    # k-means starts deterministically and finds the three obvious groups
    X = np.array([[0, 0], [0, 1], [10, 10], [10, 11], [20, 20]], dtype=float)
    labels, _ = kmeans(X, 3)
    assert labels[0] == labels[1] and labels[2] == labels[3] and len(set(labels.tolist())) == 3
    # the logistic regression separates a toy set, and a warm start lands on the same weights
    Xl = np.hstack([np.ones((6, 1)), np.array([[-2.0], [-1.0], [-0.5], [0.5], [1.0], [2.0]])])
    y = np.array([0, 0, 0, 1, 1, 1], dtype=float)
    w = fit_logistic(Xl, y)
    p = 1 / (1 + np.exp(-(Xl @ w)))
    assert (p[:3] < 0.5).all() and (p[3:] > 0.5).all()
    assert np.allclose(fit_logistic(Xl, y, w=w), w)
    # a penalty that silences the feature leaves a free intercept at the share of ones, and at a half once the two
    # classes are weighed alike
    rare = np.array([0, 0, 0, 0, 0, 1], dtype=float)
    w = fit_logistic(Xl, rare, l2=1e9, iters=50, free_intercept=True)
    assert abs(w[1]) < 1e-3 and sigmoid(w[0]) == pytest.approx(1 / 6, abs=1e-3)
    balance = np.where(rare > 0, 3.0, 0.6)
    w = fit_logistic(Xl, rare, l2=1e9, iters=50, sample_weight=balance, free_intercept=True)
    assert sigmoid(w[0]) == pytest.approx(0.5, abs=1e-3)
    # the signals of a run: its shape, read from a history record
    run = {"steps": 3, "tools": ["get_page", "get_page", "publish_page"], "agents": ["orchestrator", "publishing"]}
    turns, calls, distinct, top_share, *_ = run_signals({**run, "tokens": 100, "completion_tokens": 10})
    assert (turns, calls, distinct) == (3, 3, 2) and top_share == pytest.approx(2 / 3)


def test_apfd_metrics():
    order = ["a", "b", "c", "d"]
    assert apfd(order, {"a"}) == pytest.approx(1 - 1 / 4 + 1 / 8)
    assert apfd(order, {"d"}) == pytest.approx(1 - 4 / 4 + 1 / 8)
    # a change is one fault, found by the first of its revealing tests: a second one further down adds nothing
    assert apfd(order, {"b", "d"}) == apfd(order, {"b"})
    assert apfd(order, {"z"}) == pytest.approx(1 - 5 / 4 + 1 / 8)  # never found
    cost = {"a": 1.0, "b": 3.0, "c": 1.0, "d": 5.0}
    assert apfdc(order, {"a"}, cost) > apfdc(order, {"d"}, cost)
    assert apfdc(order, {"b", "d"}, cost) == pytest.approx((10 - 1 - 1.5) / 10)  # the cost left when b finds it
    assert apfdc(order, {"z"}, cost) == 0.0


def _stats(test, *outcomes):
    """The recorded runs of one test, one per outcome (True: it passed)."""
    s = RunStats(test)
    for passed in outcomes:
        outcome = "PASS" if passed else "AGENT_FAILURE"
        s.add({"test_id": test, "passed": passed, "classification": outcome, "tokens": 100, "latency_ms": 1.0})
    return s


def _tiny_recording():
    """Four tests and one changed copy, built by hand: ``red`` fails on the original app, ``b`` fails on the changed
    copy in every run, ``c`` in one run of three, and ``a`` has no run there."""
    h = History()
    h.baseline = {t: _stats(t, t != "red") for t in ("red", "a", "b", "c")}
    h.variants["v"] = {"red": _stats("red", False), "b": _stats("b", False), "c": _stats("c", True, True, False)}
    catalog = {t: EvalCase(id=t, name=t, agent="orchestrator", request=t) for t in h.baseline}
    return h, catalog


def test_every_run_leaves_out_the_red_tests_and_ends_at_the_first_failure():
    h, catalog = _tiny_recording()

    class InOrder(Strategy):
        name = "in_order"

        def order(self, ctx):
            return ["red", "a", "b", "c"]

    def run(variant, budget):
        ctx = SelectionContext(ChangeSet("v"), catalog, h, budget, random.Random(0))
        return InOrder().run(ctx, make_oracle(h, variant, random.Random(0)))

    log = run("v", 1000)  # red is never run; b fails and the run ends there, c unrun
    assert log.executed == ["a", "b"] and log.stop_reason == "regression"
    row = evaluate_log(log, "v", h, catalog, 1000)
    assert row["detected"] and not row["false_alarm"] and row["stop_correct"] and row["cost"] == 200
    log = run("unrecorded", 1000)  # asked about a copy with no runs, the oracle answers as the original app
    assert log.executed == ["a", "b", "c"] and log.stop_reason == "exhausted"
    log = run("unrecorded", 200)  # the budget keeps c out: no verdict
    assert log.executed == ["a", "b"] and log.stop_reason == "budget"
    # a failure of a test that passes by majority on the changed copy is a false alarm; a red test's failure is not
    one_off = ExecutionLog("x", steps=[("c", False, 100.0)], stop_reason="regression")
    row = evaluate_log(one_off, "v", h, catalog, 1000)
    assert row["false_alarm"] and not row["detected"]
    assert not evaluate_log(ExecutionLog("x", steps=[("red", False, 100.0)]), "v", h, catalog, 1000)["false_alarm"]


def test_a_missing_pair_is_not_run_and_the_empty_change_takes_its_failures_out():
    h, catalog = _tiny_recording()
    # "a" has no run on the changed copy: the pair is missing, so no strategy is given the test and it reveals nothing
    assert h.missing("v") == {"a"} and h.summary()["missing_pairs"] == 1
    ctx = SelectionContext(ChangeSet("v"), catalog, h, 1000, random.Random(0), missing=h.missing("v"))
    assert [t for t in h.baseline if ctx.runnable(t)] == ["b", "c"]
    assert h.revealing_tests("v") == {"b"} and h.unchanged_flips() == []
    # the empty change: "b" also fails when the original app is run the way the changed copies are, so its failure
    # on the changed copy is the way of running, not the change
    h.unchanged = {"b": _stats("b", False, False, True), "c": _stats("c", True)}
    assert h.unchanged_flips() == ["b"] and h.revealing_tests("v") == set()


def _edited(folder, rel: str, old: str, new: str):
    """A copy of the app in ``folder`` with one piece of text replaced in the file ``rel``."""
    path = copy_sut(folder) / rel
    text = path.read_text()
    assert text.count(old) == 1, old
    path.write_text(text.replace(old, new))
    return folder


def test_what_the_model_is_sent_is_in_the_change_set(tmp_path):
    """Edits that leave the harness as it is and change a prompt each have a component, one the tests' recorded
    dependencies match."""
    skill, described = "skills/publishing-workflow/SKILL.md", "Publish, schedule or unpublish a page safely"
    edits = {
        # the arguments of a step in another order: the step is shown with them in that order
        "skill:publishing-workflow#procedure": (
            skill,
            "args: {page_id: $page_id, reviewer_id: $approver}",
            "args: {reviewer_id: $approver, page_id: $page_id}",
        ),
        # a front-matter value spaced another way and a re-wrapped paragraph: the file goes into the prompt as written
        "skill:publishing-workflow#meta": (skill, f"description: {described}", f"description:  {described}"),
        "skill:publishing-workflow#prose": (
            skill,
            "check the permission for the requested action, then (for\npublishing",
            "check the permission for the requested action,\nthen (for publishing",
        ),
        # what an agent is told about a tool it is offered
        "tool:schedule_publish#schema": (
            "tools/publish_tools.py",
            '"Schedule a page to be published at a given time."',
            '"Publish a page, now or at a given time."',
        ),
    }
    for component, (rel, old, new) in edits.items():
        assert component in compute_changeset(SUT_ROOT, _edited(tmp_path / "edit", rel, old, new)).ids(), component
    # a comment inside the procedure block is not sent: the steps are written from the parsed YAML
    step = "args: {page_id: $page_id, reviewer_id: $approver}"
    commented = _edited(tmp_path / "edit", skill, step, step + "  # a note")
    assert compute_changeset(SUT_ROOT, commented).is_provably_benign()
    # nor is the order of a step's own keys: a step is read by their names
    reordered = _edited(tmp_path / "edit", skill, "- id: fetch\n  call: get_page\n", "- call: get_page\n  id: fetch\n")
    assert compute_changeset(SUT_ROOT, reordered).is_provably_benign()
    # a new agent: no test depends on it, yet the orchestrator now routes every request among one more specialist
    added = copy_sut(tmp_path / "edit")
    (added / "agents" / "legal.yaml").write_text("name: legal\ndescription: Legal holds.\ntriggers: [legal]\n")
    roster = {c.id: c for c in compute_changeset(SUT_ROOT, added).components}["agent:orchestrator.specialists"]
    assert roster.detail == "added: agent:legal" and matches(roster, {"agent:orchestrator"})
    # the schema reaches the tests whose agents were offered the tool; the adapter's body only those that called it
    schema = ChangedComponent("tool:schedule_publish#schema", "tool-schema", "tools/publish_tools.py")
    adapter = ChangedComponent("tool:schedule_publish", "tool", "tools/publish_tools.py")
    offered = {"tool:schedule_publish#schema"}
    assert matches(schema, offered) and matches(schema, {"tool:schedule_publish"}) and not matches(adapter, offered)
    # a package's __init__ runs before every module of the package (it is where the tools are registered)
    init = ChangedComponent("code:tools/__init__.py", "code", "tools/__init__.py")
    ran = {"code:tools/site_tools.py::audit_site": 0.5}
    assert matches(init, set(ran)) and not matches(init, {"code:services/site.py::audit"})
    assert weighted_affinity(ChangeSet("v", components=[init]), ran) == 0.5


def test_a_recording_knows_the_app_it_was_made_on(tmp_path):
    """The digest of the app ignores the kind of line ending and nothing else; a recording whose copy of the app
    is not traceeval/sut as it is now is refused by the check."""
    app = copy_sut(tmp_path / "app")
    retry = app / "harness" / "retry.py"
    retry.write_bytes(retry.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert tree_digest(app) == tree_digest(SUT_ROOT)
    retry.write_text("# a comment moves every line below it\n" + retry.read_text())
    assert tree_digest(app) != tree_digest(SUT_ROOT)
    work = tmp_path / "recording"
    copy_sut(baseline_copy(work), app)  # a recording made on that app
    assert set(drift(work)) == {"app"}
    with pytest.raises(SystemExit, match="differs from the app"):
        check("code_retry_drop_idempotency", work, 0.2, "replay")
    copy_sut(baseline_copy(work))  # and one made on today's
    assert drift(work) == {}


def test_training_leaves_out_the_changes_a_batch_shares():
    h = History()
    h.variants = {v: {} for v in ("a", "b", "c", "batch_ab", "batch_bc")}
    h.mutation_meta = {"batch_ab": {"members": ["a", "b"]}, "batch_bc": {"members": ["b", "c"]}, "a": {"members": []}}
    assert h.training_variants("a") == ["b", "c", "batch_bc"]  # not the batch a is a member of
    assert h.training_variants("batch_ab") == ["c"]  # not its members, nor the batch that shares one
    assert h.training_variants("unrecorded_batch", members=["c"]) == ["a", "b", "batch_ab"]
    assert {"history_ml", "observed_diverse"} <= set(CORE)


def _floor_recording():
    """Five tests and a change to two functions, f and g, with a mandatory property whose source is f: ``both`` runs
    f and g but costs more than ``only_f`` and ``only_g`` together, ``check_p`` checks the property, ``red`` fails
    on the original app, and ``known_g`` is a test whose outcome is already known."""
    f, g = "code:tools/x.py::f", "code:tools/x.py::g"

    def stats(test, deps, tokens, passed=True):
        s = RunStats(test)
        outcome = "PASS" if passed else "AGENT_FAILURE"
        s.add({"test_id": test, "passed": passed, "classification": outcome, "tokens": tokens, "latency_ms": 1.0,
               "deps": deps})  # fmt: skip
        return s

    h = History()
    tests = {"both": ([f, g], 300), "only_f": ([f], 100), "only_g": ([g], 100), "check_p": ([], 20)}
    h.baseline = {t: stats(t, deps, tokens) for t, (deps, tokens) in tests.items()}
    h.baseline["red"] = stats("red", [f, g], 10, passed=False)
    h.baseline["known_g"] = stats("known_g", [g], 50)
    catalog = {t: EvalCase(id=t, name=t, agent="orchestrator", request=t) for t in h.baseline}
    catalog["check_p"].properties = ["p"]
    props = {"p": SimpleNamespace(id="p", sources=[f], mandatory=True)}
    change = ChangeSet("v", components=[ChangedComponent(c, "code", "tools/x.py") for c in (f, g)])
    return h, catalog, props, change


def test_the_coverage_floor_is_the_cheapest_cover_of_what_a_change_touches():
    h, catalog, props, change = _floor_recording()
    candidates = ["both", "only_f", "only_g", "check_p", "red"]
    # per token: the property's test first, then the two cheap tests rather than the one that runs both functions;
    # the red test covers nothing
    assert coverage_floor(change, h, catalog, props, candidates, cost=h.cost) == ["check_p", "only_f", "only_g"]
    # a test whose outcome is known covers for free
    assert coverage_floor(change, h, catalog, props, candidates, ["known_g"], h.cost) == ["check_p", "only_f"]
    # counted in tests, not tokens: one test runs both functions
    assert coverage_floor(change, h, catalog, props, candidates) == ["both", "check_p"]


def test_with_the_floor_a_clean_verdict_waits_for_the_floor(monkeypatch):
    h, catalog, props, change = _floor_recording()
    monkeypatch.setattr("traceeval.catalog.load_properties", lambda: props)
    ctx = SelectionContext(change, catalog, h, 1e9, random.Random(0), replayed=frozenset({"known_g"}))
    # a constant so high that the method would call the change clean before any test: the floor runs first
    method = AdaptiveBayes(eps_clean=0.99, cover_floor=True)
    log = method.run(ctx, lambda t: (True, h.cost(t)))
    assert log.executed == ["check_p", "only_f"] and log.stop_reason == "clean"
    # a floor test that fails is a regression, and ends the run
    log = method.run(ctx, lambda t: (t != "check_p", h.cost(t)))
    assert log.executed == ["check_p"] and log.stop_reason == "regression"


def test_the_suspects_of_a_batch_failure_are_the_members_whose_own_replay_reaches_the_test():
    rows = {
        "reaches": {"T": {"replayed": False, "passed": False}},  # diverges on T: the change reaches it
        "fails": {"T": {"replayed": True, "passed": False}},  # T replays to the end and fails
        "leaves": {"T": {"replayed": True, "passed": True}},  # T replays to the end and passes: not a suspect
    }
    assert suspects(rows, "T") == ["reaches", "fails"]
    assert suspects({"leaves": rows["leaves"]}, "T") == []  # no suspect: only the members together fail T
    assert [halving_runs(n) for n in (0, 1, 2, 3, 4, 5, 8)] == [0, 0, 1, 2, 2, 3, 3]


def test_the_day_map_says_what_each_member_reaches_and_which_members_need_no_model():
    passed, diverges = {"replayed": True, "passed": True}, {"replayed": False, "passed": None}
    failed = {"replayed": True, "passed": False}
    rows = {
        "a": {"T1": diverges, "T2": passed, "T3": passed},  # reaches T1
        "b": {"T1": diverges, "T2": diverges, "T3": passed},  # reaches T1 and T2
        "c": {"T1": passed, "T2": passed, "T3": passed},  # reaches nothing: settled with no model
        "d": {"T1": passed, "T2": passed, "T3": failed},  # breaks T3, which passes on the original app
        "e": {"T1": passed, "T2": failed, "T3": passed},  # fails T2 in the replay, but T2 fails there anyway
    }
    day = day_map(rows, {"T1": True, "T2": False, "T3": True})
    assert day["reached"] == {"a": ["T1"], "b": ["T1", "T2"], "c": [], "d": [], "e": []}
    assert day["broken"] == {"a": [], "b": [], "c": [], "d": ["T3"], "e": []}
    assert day["settled"] == ["c", "e"]
    # the members that reach or break each test: T1 two, T3 the one that breaks it; e's failure of T2, a test that
    # fails on the original app anyway, says nothing of e
    assert day["owners"] == {"T1": ["a", "b"], "T2": ["b"], "T3": ["d"]}


def test_a_stop_threshold_is_a_low_value_of_the_past_regressions():
    values = [i / 100 for i in range(1, 66)]  # 65 past regressions, the value of each at its first revealing test
    # on average over the sets of past regressions: the k-th smallest, k = floor(alpha (n + 1)); none when k = 0
    assert [threshold(values, alpha) for alpha in (0.01, 0.05, 0.1, 0.2)] == [-math.inf, 0.03, 0.06, 0.13]
    # for nine such sets in ten: a lower one
    assert [threshold(values, alpha, 0.9) for alpha in (0.05, 0.1, 0.2)] == [0.01, 0.04, 0.09]
    assert threshold([], 0.5) == -math.inf and threshold([0.3, 0.4, 0.5], 0.5) == 0.4

    def group(*kinds):
        return group_of(ChangeSet("x", components=[ChangedComponent(f"{k}:x", k, "f", "") for k in kinds]))

    # the group of a change, from the kinds of its components: a skill's steps come first, and the text the
    # model reads (prose, a prompt, a tool's description) is apart from the rest
    assert group("skill", "skill-prose", "agent") == "a skill's steps" and group("code", "line") == "code"
    assert group("skill-prose", "agent") == group("code", "tool", "tool-schema") == "text the model reads"
    assert group("agent", "config") == "an agent's tools and skills" and group("config") == "the configuration"
    assert group("fixture") == "the starting data" and group() == "code"


@pytest.mark.slow
def test_small_end_to_end_experiment(tmp_path, capsys):
    work = tmp_path / "exp"
    record_baseline(work, reps=1)
    changes = ["skill_publish_drop_link_validation", "benign_skill_prose_reflow"]
    record_mutants(work, mutation_ids=["unchanged", *changes], reps=1)
    h = History.load(work)
    assert h.revealing_tests("skill_publish_drop_link_validation")
    assert not h.revealing_tests("benign_skill_prose_reflow")
    # the empty change is no change to evaluate: the original app, run as the changed copies are, ends as in the
    # baseline, and every request it sends is one the baseline sent, answered the same
    assert sorted(h.variants) == sorted(changes) and set(h.unchanged) == set(h.baseline)
    assert h.unchanged_flips() == [] and not any(h.missing(v) for v in changes)
    asked = [r["cassette"] for stats in h.unchanged.values() for r in stats.runs]
    assert all(c["requests"] == c["known"] > 0 and c["differ"] == 0 for c in asked)
    # so a cache of the baseline's answers would have paid for none of a run's tokens, the judge's included
    runs = [r for stats in h.unchanged.values() for r in stats.runs]
    assert all(r["cassette"]["known_tokens"] == r["tokens"] > 0 for r in runs)
    # the manifest says what the recording was made from and with, and nothing has moved since
    manifest = load_manifest(work)
    assert manifest["app"] == tree_digest(SUT_ROOT) and manifest["model"] and manifest["catalog"]
    assert (manifest["baseline"]["reps"], manifest["changes"]["workers"]) == (1, 1) and drift(work) == {}
    catalog = {c.id: c for c in load_catalog()}
    red = {t for t in h.baseline if h.baseline_pass_rate(t) < 0.5}
    # every strategy that uses the change or the traces, and the bandit's variant, which the default comparison omits
    for name in [s for s in CORE if s not in ("full", "random")] + ["risk_aware_ts_per_token"]:
        ctx = SelectionContext(
            h.changesets["skill_publish_drop_link_validation"],
            catalog,
            h,
            h.total_cost() * 0.5,
            random.Random(0),
            train_variants=["benign_skill_prose_reflow"],
        )
        oracle = make_oracle(h, "skill_publish_drop_link_validation", random.Random(0))
        log = get_strategy(name).run(ctx, oracle)
        assert len(set(log.executed)) == len(log.executed), name  # no test runs twice
        assert not red & set(log.executed), name  # nor a test the model fails on the original app
        # a test that passed on the original app and now fails ends the run, whatever the strategy
        assert [ok for _, ok, _ in log.steps].count(False) == 1 and not log.steps[-1][1], name
        assert log.stop_reason == "regression", name
        assert set(oracle.records) == set(log.executed), name  # the runs it was answered with, for their signals
    df = evaluate(work, strategies=["observed", "adaptive_bayes"], budgets=(0.2, 1.0), seeds=1)
    assert set(df.strategy) == {"observed", "adaptive_bayes"}
    # a held-out evaluation: one change evaluated, the strategies that learn given the other one only
    held = evaluate(work, ["history_ml", "adaptive_bayes"], (1.0,), 1, variants=changes[:1], train=changes[1:])
    assert set(held.variant) == set(changes[:1]) and held.detected.all()
    # shared out among two processes, the changes get the rows one process gives them
    two = evaluate(work, strategies=["observed", "adaptive_bayes"], budgets=(0.2, 1.0), seeds=1, jobs=2)
    assert two.equals(df)  # and results/replay.csv is again the file the report reads
    # coverage: the suite by dimension, and each run's change coverage (no ground truth needed)
    props = load_properties()
    rows = {r["dimension"]: r for r in suite_coverage(h, catalog, props, SUT_ROOT)}
    dims = {"agent", "feature", "skill", "tool", "tool error path", "configuration", "setting value", "property"}
    assert dims | {"workflow", "execution path", "risk"} <= set(rows)
    # the other value of every on/off setting, and the values the cases set (CFG-*)
    assert "publishing.allow_scheduling=false" not in rows["setting value"]["not covered"]
    assert "runtime.idempotency_keys=false" in rows["setting value"]["not covered"]  # no case runs with it
    assert (
        rows["feature"]["observed"] > 0
        and 0 < rows["tool error path"]["observed"] < rows["tool error path"]["components"]
    )
    assert rows["property"]["not covered"] == [] and rows["skill"]["observed"] > 0
    # every workflow a test names counts as declared, and a recorded run delegates to exactly W3's chain (brand, then
    # publishing); only the workflows no test names may be listed as not covered
    named = {c.workflow for c in catalog.values() if c.workflow}
    assert rows["workflow"]["declared"] == len(named) and rows["workflow"]["observed"] >= 1
    assert not named & set(rows["workflow"]["not covered"])
    # per component: the tests that declare it and the tests that invoke it
    per = per_component(h, catalog, SUT_ROOT)
    assert set(per) == {"agent", "skill", "tool", "feature"}
    invoked = {n: o for dim in ("agent", "skill") for n, _, o in per[dim]}
    assert 0 < invoked["orchestrator"] == invoked["routing"]  # the orchestrator always reads its routing skill
    columns = {"component_coverage", "affected_property_coverage", "mandatory_covered", "affected_workflow_coverage"}
    columns |= {"affected_feature_coverage", "error_path_coverage"}
    assert columns <= set(df.columns)
    benign = h.changesets["benign_skill_prose_reflow"]
    assert any(props[p].mandatory for p in affected_properties(benign, h, catalog, props))
    # step 5: with the whole suite affordable, a run without a regression tests every affected mandatory property
    full = df[(df.variant == "benign_skill_prose_reflow") & (df.strategy == "adaptive_bayes") & (df.budget == 1.0)]
    assert (full.stop_reason != "regression").all() and full.mandatory_covered.all()
    # replay-first: the baseline kept the model's answers as the recording's cassette, and every copy of the app
    # is replayed against it, without a model
    assert cassette_path(work).exists()
    replay_first(work, workers=1)
    replays = Replays.load(work)
    assert replays.replayed("baseline") == frozenset(h.baseline)  # the original app replays to the end
    for variant in ("skill_publish_drop_link_validation", "benign_skill_prose_reflow"):
        diverged = set(replays.diverged(variant))
        assert 0 < len(diverged) < len(h.baseline)  # the publishing skill reaches some of the tests only
        # a revealing test never replays to a pass: it diverges, or it fails in the replay
        assert h.revealing_tests(variant) <= diverged | set(replays.new_failures(variant))
    rf = evaluate(work, strategies=["ir_tfidf", "adaptive_bayes"], budgets=(1.0,), seeds=1, replay_first=True)
    assert rf[rf.variant == "skill_publish_drop_link_validation"].detected.all()
    # with no budget to stop it, an order of the whole suite runs every test the benign change reaches and no other:
    # a clean verdict with nothing left untested, paid from each test's divergence point on
    clean = rf[(rf.variant == "benign_skill_prose_reflow") & (rf.strategy == "ir_tfidf")].iloc[0]
    reached = [t for t in replays.diverged("benign_skill_prose_reflow") if t not in red]
    assert clean.stop_reason == "exhausted" and clean.tests_run == len(reached)
    assert 0 < clean.cost_fraction < clean.whole_cost_fraction < 1
    # charged for the requests the original app never made only, the same tests cost no more: after its divergence
    # point a run may still send requests the cassette knows
    assert 0 < clean.new_cost_fraction <= clean.cost_fraction
    report = write_report(work).read_text(encoding="utf-8")
    assert "## 7. Replay-first" in report and (work / "results" / "figures" / "replay_first.png").exists()
    assert "from the cache too" in report and "charged for their new requests only" in report
    assert "- The empty change" in report and "request by request" in report
    # the prototype: the same change checked live (here on recorded answers), from this history: replay first,
    # then the method over the tests that diverge
    log = check("skill_publish_drop_link_validation", work, 0.3, "replay")
    assert log.stop_reason == "regression" and log.p_broken > 0.9
    assert not set(log.executed) & replays.replayed("skill_publish_drop_link_validation")
    out = capsys.readouterr().out
    assert "replay: " in out and "coverage: " in out and "invoked: " in out and "(again)" not in out
    # with ``confirm`` the test that fails is run again before its failure counts; on recorded answers it fails
    # again, so the verdict and the tests are the same, and the second run is paid for
    twice = check("skill_publish_drop_link_validation", work, 0.3, "replay", confirm=True)
    assert (twice.stop_reason, twice.executed) == ("regression", log.executed) and twice.cost > log.cost
    assert capsys.readouterr().out.count("(again)") == 1
    # with a target miss rate the clean threshold is set on the recording's other changes. One other change is
    # too few to set any: the check says so and runs every test the benign change reaches
    sure = check("benign_skill_prose_reflow", work, 1.0, "replay", miss_rate=0.2)
    assert sure.stop_reason == "exhausted" and set(sure.executed) == set(reached)
    assert len(sure.trace) == len(sure.steps) and sure.trace == sorted(sure.trace, reverse=True)
    out = capsys.readouterr().out
    assert "no threshold for a miss rate of 20%" in out and "every test the change reaches ran and passed" in out
    # a replayed failure of a test that passes on the original app ends a run before any test runs (here one is
    # written into the replay by hand: neither change of this recording has one)
    rows = read_jsonl(work / "history" / "replay_first.jsonl")
    ok = (r for r in rows if r["variant"] == "benign_skill_prose_reflow" and r["replayed"] and r["test_id"] not in red)
    next(ok)["passed"] = False
    write_jsonl(work / "history" / "replay_first.jsonl", rows)
    one = evaluate(work, ["ir_tfidf"], (1.0,), 1, ["benign_skill_prose_reflow"], replay_first=True).iloc[0]
    assert one.stop_reason == "regression" and one.cost_fraction == 0 and one.tests_run == 0 and one.false_alarm
    # the benign change recorded again for the tests it reaches only: the others have no run, the replay gives their
    # outcome, and every test ends as it did when the whole suite was recorded
    benign, whole = "benign_skill_prose_reflow", History.load(work)
    comment = "g_comment_links_1"  # a generated change: a comment, which no test's requests can show
    record_mutants(work, mutation_ids=[benign, comment], reps=1, reached_only=True)
    runs, lean = read_jsonl(work / "history" / "variants" / f"{benign}.jsonl"), History.load(work)
    asked = {r["test_id"] for r in runs if not r.get("stand_in")}  # the runs that went to the model
    assert asked == set(replays.diverged(benign)) and len(runs) == len(lean.variants[benign]) == 180
    assert not lean.missing(benign) and not lean.revealing_tests(benign)
    assert all(lean.variant_pass_rate(benign, t) == whole.variant_pass_rate(benign, t) for t in whole.baseline)
    # the generated change: every test replays, so none is run; its copy is not kept, what its diff touched is
    assert all(st.runs[0]["stand_in"] for st in lean.variants[comment].values()) and len(lean.variants[comment]) == 180
    assert lean.mutation_meta[comment]["expected_regression"] is None and not lean.changesets[comment].components
    assert not (work / "variants" / comment / "sut").exists() and not lean.revealing_tests(comment)
    assert not Replays.load(work).diverged(comment)
    assert "no label" in write_report(work).read_text(encoding="utf-8")


def test_generated_changes_apply_and_leave_an_app_that_loads(tmp_path):
    """Every generated change applies to the app it was generated from and leaves files that still parse; the ids
    are unique, tell the kind and fit a Windows path; a sample has the change set its kind should give."""
    changes = generate()
    kinds = {kind_of(m.id) for m in changes}
    skills, others = "stepdel stepswap whennot guarddel ruledel rewrap", "tooldrop setting argswap tooldesc condnot"
    text = "promptdel agentdesc paramdesc"  # more edits to text the model reads
    assert kinds == {*skills.split(), *others.split(), *text.split(), "comment", "fixture"}
    assert len(changes) > 300 and max(len(m.id) for m in changes) <= 40
    assert all(m.expected_regression is None for m in changes)  # no label: the recording decides
    assert get_mutation(changes[0].id).id == changes[0].id
    # the sample is fixed by the ids and the seed, and holds at most so many of each kind
    drawn = sample(changes, 2)
    assert [m.id for m in drawn] == [m.id for m in sample(changes, 2)] != [m.id for m in sample(changes, 2, seed=1)]
    assert {kind_of(m.id) for m in drawn} == kinds and len(drawn) == 2 * len(kinds)
    # the two halves of a held-out evaluation: disjoint, each kind in both, the same whatever the order of the ids
    ids = [m.id for m in changes]
    learn, held_out = split(ids)
    assert not set(learn) & set(held_out) and len(learn) + len(held_out) == len(ids)
    assert {kind_of(i) for i in learn} == {kind_of(i) for i in held_out} == kinds
    assert abs(len(learn) - len(held_out)) <= len(kinds) and split(ids[::-1])[1] == held_out[::-1]
    # each change applied to one copy of the app, checked, and taken back
    copy = copy_sut(tmp_path / "app")
    for m in changes:
        files = {edit[1] for edit in m.edits if edit[0] == "lines"} or {"fixtures/base.json"}
        saved = {rel: (copy / rel).read_text() for rel in files}
        m.apply(copy)
        for rel in files:
            text = (copy / rel).read_text()
            assert text != saved[rel], m.id
            if rel.endswith(".py"):
                ast.parse(text)
            elif rel.endswith("SKILL.md"):
                steps = yaml.safe_load(text.split("```yaml\n", 1)[1].split("```", 1)[0]) or []
                assert all(isinstance(step, dict) for step in steps), m.id
            else:
                assert yaml.safe_load(text), m.id  # the agent definitions, the settings and the fixture (JSON is YAML)
        if m in drawn:
            ids = compute_changeset(SUT_ROOT, copy).ids()
            if kind_of(m.id) == "comment":
                assert not ids, m.id  # a comment is no change
            else:
                expected = {"fixture": "fixture:", "setting": "config:", "tooldrop": "agent:", "tooldesc": "tool:"}
                expected |= {"promptdel": "agent:", "agentdesc": "agent:", "paramdesc": "tool:"}
                prefix = expected.get(kind_of(m.id), "skill:" if m.category in ("skill", "benign") else "code:")
                assert any(i.startswith(prefix) for i in ids), (m.id, ids)
        for rel, text in saved.items():
            (copy / rel).write_text(text)
    assert compute_changeset(SUT_ROOT, copy).is_provably_benign()  # every change was taken back
    # a change generated from one version of the app does not apply to another: the line no longer reads the same
    (copy / "config" / "runtime.yaml").write_text(
        "# a new first line\n" + (copy / "config" / "runtime.yaml").read_text()
    )
    with pytest.raises(PatchError):
        next(m for m in changes if kind_of(m.id) == "setting").apply(copy)


def test_batches_compose_changes_that_edit_disjoint_files(tmp_path):
    """A batch applies several catalog changes to one copy; its members must not edit the same file, or the second
    edit's anchor could be gone, and the batch is a regression exactly when one of its members is."""
    from traceeval.mutation.catalog import BATCHES

    assert BATCHES, "no batches"
    for b in BATCHES:
        assert b.category == "batch" and b.members
        files_per_member = []
        for mid in b.members:
            _, cs = materialize_variant(get_mutation(mid), tmp_path / "m")
            files_per_member.append(set(cs.files))
        for i, fa in enumerate(files_per_member):
            for fb in files_per_member[i + 1 :]:
                assert not (fa & fb), (b.id, fa & fb)
        assert b.expected_regression == any(get_mutation(m).expected_regression for m in b.members)
        _, cs = materialize_variant(b, tmp_path / "b")  # every edit's anchor is still there in order
        assert set(cs.files) == set().union(*files_per_member), b.id
        assert get_mutation(b.id) is b
