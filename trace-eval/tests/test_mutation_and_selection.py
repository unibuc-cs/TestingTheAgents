"""Tests for mutations, change-set extraction, metrics and strategies (small end-to-end run)."""

import random

import pytest

from traceeval.catalog import load_catalog
from traceeval.experiment.evaluate import evaluate, make_oracle
from traceeval.experiment.history import History
from traceeval.experiment.metrics import apfd, apfdc
from traceeval.experiment.runner import record_baseline, record_mutants
from traceeval.mutation import MUTATIONS, get_mutation, materialize_variant
from traceeval.selection import SelectionContext, get_strategy


def test_every_mutation_applies_and_changes_something(tmp_path):
    for m in MUTATIONS:
        _, cs = materialize_variant(m, tmp_path / "v")
        assert cs.files, m.id
        assert cs.components, m.id


def test_changeset_flags_ast_equivalent_edits(tmp_path):
    _, cs = materialize_variant(get_mutation("benign_code_comment_docstring"), tmp_path / "v")
    assert cs.is_provably_benign()
    _, cs = materialize_variant(get_mutation("code_retry_disabled"), tmp_path / "v")
    assert not cs.is_provably_benign()
    assert any(c.id == "code:harness/retry.py::with_retry" for c in cs.components)
    assert any(c.kind == "line" for c in cs.components)


def test_changeset_is_order_sensitive_for_intents(tmp_path):
    _, cs = materialize_variant(get_mutation("prompt_translation_intents_reordered"), tmp_path / "v")
    assert "agent:translation.intents" in cs.ids()


def test_apfd_metrics():
    order = ["a", "b", "c", "d"]
    assert apfd(order, {"a"}) == pytest.approx(1 - 1 / 4 + 1 / 8)
    assert apfd(order, {"d"}) == pytest.approx(1 - 4 / 4 + 1 / 8)
    cost = {t: 1.0 for t in order}
    sev = {t: 1.0 for t in order}
    assert apfdc(order, {"a"}, cost, sev) > apfdc(order, {"d"}, cost, sev)


@pytest.mark.slow
def test_small_end_to_end_experiment(tmp_path):
    work = tmp_path / "exp"
    record_baseline(work, reps=1)
    record_mutants(work, mutation_ids=["skill_publish_drop_link_validation", "benign_skill_prose_reflow"], reps=1)
    h = History.load(work)
    assert h.revealing_tests("skill_publish_drop_link_validation")
    assert not h.revealing_tests("benign_skill_prose_reflow")
    catalog = {c.id: c for c in load_catalog()}
    for name in ("declared", "observed", "cost_aware", "ir_tfidf", "adaptive_bayes"):
        ctx = SelectionContext(
            h.changesets["skill_publish_drop_link_validation"],
            catalog,
            h,
            h.total_cost() * 0.3,
            random.Random(0),
            train_variants=["benign_skill_prose_reflow"],
        )
        log = get_strategy(name).run(ctx, make_oracle(h, "skill_publish_drop_link_validation", random.Random(0)))
        assert any(not ok for _, ok, _ in log.steps), name
    df = evaluate(work, strategies=["observed", "adaptive_bayes"], budgets=(0.2, 1.0), seeds=1)
    assert set(df.strategy) == {"observed", "adaptive_bayes"}
