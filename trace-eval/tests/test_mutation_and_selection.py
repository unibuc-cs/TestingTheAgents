"""Tests for mutations, change-set extraction, metrics and strategies (small end-to-end run)."""

import random

import pytest

from traceeval.catalog import load_catalog
from traceeval.experiment.check import check
from traceeval.experiment.evaluate import evaluate, make_oracle
from traceeval.experiment.history import History
from traceeval.experiment.metrics import apfd, apfdc
from traceeval.experiment.runner import record_baseline, record_mutants
from traceeval.experiment.sutloader import copy_sut
from traceeval.mutation import MUTATIONS, get_mutation, materialize_variant
from traceeval.mutation.changeset import _python_components, _yaml_code_lines
from traceeval.selection import SelectionContext, get_strategy
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
        if name == "adaptive_bayes":  # a test that passed on the original app and now fails ends the run
            assert not log.steps[-1][1] and log.stop_reason == "regression"
            assert len(set(log.executed)) == len(log.executed)  # no test runs twice
    df = evaluate(work, strategies=["observed", "adaptive_bayes"], budgets=(0.2, 1.0), seeds=1)
    assert set(df.strategy) == {"observed", "adaptive_bayes"}
    # the prototype: the same change checked live (here on recorded answers), from this history
    log = check("skill_publish_drop_link_validation", work, 0.3, "replay")
    assert log.stop_reason == "regression" and log.p_broken > 0.9
