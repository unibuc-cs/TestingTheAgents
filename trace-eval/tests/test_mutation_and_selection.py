"""Tests for mutations, change-set extraction, metrics and strategies (small end-to-end run)."""

import ast
import random

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
    error_paths,
    suite_coverage,
)
from traceeval.experiment.coverage import (
    tests_per_component as per_component,
)
from traceeval.experiment.evaluate import evaluate, make_oracle
from traceeval.experiment.executor import read_jsonl, write_jsonl
from traceeval.experiment.history import History
from traceeval.experiment.history import TestStats as RunStats  # not under a name pytest would collect
from traceeval.experiment.metrics import apfd, apfdc, evaluate_log
from traceeval.experiment.replay_first import Replays, cassette_path, replay_first
from traceeval.experiment.report import write_report
from traceeval.experiment.runner import record_baseline, record_mutants
from traceeval.experiment.sutloader import copy_sut
from traceeval.mutation import MUTATIONS, get_mutation, materialize_variant
from traceeval.mutation.changeset import ChangedComponent, ChangeSet, _flatten, _python_components, _yaml_code_lines
from traceeval.selection import CORE, SelectionContext, Strategy, get_strategy
from traceeval.selection.adapted import fit_logistic, kmeans, run_signals, sigmoid
from traceeval.selection.base import ExecutionLog
from traceeval.sut import SUT_ROOT

COMMENT_ONLY = {"benign_code_comment_docstring", "benign_config_comments_reordered"}


def test_every_mutation_applies_and_changes_something(tmp_path):
    for m in MUTATIONS:
        _, cs = materialize_variant(m, tmp_path / "v")
        if m.id in COMMENT_ONLY:  # comments and formatting reach no selector
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


def _tiny_recording():
    """Four tests and one changed copy, built by hand: ``red`` fails on the original app, ``b`` fails on the changed
    copy in every run, and ``c`` in one run of three."""

    def run(test, passed):
        outcome = "PASS" if passed else "AGENT_FAILURE"
        return {"test_id": test, "passed": passed, "classification": outcome, "tokens": 100, "latency_ms": 1.0}

    def stats(test, *outcomes):
        s = RunStats(test)
        for passed in outcomes:
            s.add(run(test, passed))
        return s

    h = History()
    h.baseline = {t: stats(t, t != "red") for t in ("red", "a", "b", "c")}
    h.variants["v"] = {"red": stats("red", False), "b": stats("b", False), "c": stats("c", True, True, False)}
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
    log = run("unchanged", 1000)  # a copy nothing was recorded on behaves like the original app: every test passes
    assert log.executed == ["a", "b", "c"] and log.stop_reason == "exhausted"
    log = run("unchanged", 200)  # the budget keeps c out: no verdict
    assert log.executed == ["a", "b"] and log.stop_reason == "budget"
    # a failure of a test that passes by majority on the changed copy is a false alarm; a red test's failure is not
    one_off = ExecutionLog("x", steps=[("c", False, 100.0)], stop_reason="regression")
    row = evaluate_log(one_off, "v", h, catalog, 1000)
    assert row["false_alarm"] and not row["detected"]
    assert not evaluate_log(ExecutionLog("x", steps=[("red", False, 100.0)]), "v", h, catalog, 1000)["false_alarm"]


def test_training_leaves_out_the_changes_a_batch_shares():
    h = History()
    h.variants = {v: {} for v in ("a", "b", "c", "batch_ab", "batch_bc")}
    h.mutation_meta = {"batch_ab": {"members": ["a", "b"]}, "batch_bc": {"members": ["b", "c"]}, "a": {"members": []}}
    assert h.training_variants("a") == ["b", "c", "batch_bc"]  # not the batch a is a member of
    assert h.training_variants("batch_ab") == ["c"]  # not its members, nor the batch that shares one
    assert h.training_variants("unrecorded_batch", members=["c"]) == ["a", "b", "batch_ab"]
    assert {"history_ml", "observed_diverse"} <= set(CORE)


@pytest.mark.slow
def test_small_end_to_end_experiment(tmp_path, capsys):
    work = tmp_path / "exp"
    record_baseline(work, reps=1)
    record_mutants(work, mutation_ids=["skill_publish_drop_link_validation", "benign_skill_prose_reflow"], reps=1)
    h = History.load(work)
    assert h.revealing_tests("skill_publish_drop_link_validation")
    assert not h.revealing_tests("benign_skill_prose_reflow")
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
    report = write_report(work).read_text(encoding="utf-8")
    assert "## 7. Replay-first" in report and (work / "results" / "figures" / "replay_first.png").exists()
    # the prototype: the same change checked live (here on recorded answers), from this history: replay first,
    # then the method over the tests that diverge
    log = check("skill_publish_drop_link_validation", work, 0.3, "replay")
    assert log.stop_reason == "regression" and log.p_broken > 0.9
    assert not set(log.executed) & replays.replayed("skill_publish_drop_link_validation")
    out = capsys.readouterr().out
    assert "replay: " in out and "coverage: " in out and "invoked: " in out
    # a replayed failure of a test that passes on the original app ends a run before any test runs (here one is
    # written into the replay by hand: neither change of this recording has one)
    rows = read_jsonl(work / "history" / "replay_first.jsonl")
    ok = (r for r in rows if r["variant"] == "benign_skill_prose_reflow" and r["replayed"] and r["test_id"] not in red)
    next(ok)["passed"] = False
    write_jsonl(work / "history" / "replay_first.jsonl", rows)
    one = evaluate(work, ["ir_tfidf"], (1.0,), 1, ["benign_skill_prose_reflow"], replay_first=True).iloc[0]
    assert one.stop_reason == "regression" and one.cost_fraction == 0 and one.tests_run == 0 and one.false_alarm


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
