"""Baseline strategies and the strategy registry.

    full        whole suite in catalogue order (reference)
    random      random permutation
    declared    change-based selection on hand-written dependencies (classic RTS on metadata)
    ir_tfidf    text similarity between the diff and each test (IR-based prioritization, REPiR-style)
    observed    change-based selection on dependencies observed in baseline traces, risk x affinity / cost
    cost_aware  whole-suite ranking by risk x change-affinity x failure-history / expected tokens

The proposed method lives in ``adaptive_bayes.py``, two published methods reproduced as baselines in
``reproduced.py``, and two optional baselines in ``extras.py``.
"""

import math
import re
from collections import defaultdict

from .base import Strategy, affinity, line_hit, weighted_affinity

STRATEGIES: dict[str, Strategy] = {}  # name -> instance, filled by @register
CORE = [
    "full",
    "random",
    "declared",
    "ir_tfidf",
    "observed",
    "cost_aware",
    "casper_slices",
    "risk_aware_ts",
    "adaptive_bayes",
]


def register(cls):
    STRATEGIES[cls.name] = cls()
    return cls


def get_strategy(name: str) -> Strategy:
    return STRATEGIES[name]


def tokens(text: str) -> list[str]:
    """Lower-cased identifier-like words of at least three characters (snake_case and kebab-case kept whole)."""
    return [w for w in re.findall(r"[a-zA-Z_][a-zA-Z0-9_\-]+", text.lower()) if len(w) > 2]


def change_text(change) -> str:
    """Everything textual we know about a change: file names, component ids and the diff of the code
    (comments, docstrings and blank lines are never part of a change set)."""
    return " ".join(change.files) + " " + " ".join(c.id for c in change.components) + " " + change.diff


@register
class Full(Strategy):
    name = "full"

    def order(self, ctx):
        return list(ctx.tests())


@register
class Random(Strategy):
    name = "random"
    stochastic = True

    def order(self, ctx):
        tests = list(ctx.tests())
        ctx.rng.shuffle(tests)
        return tests


@register
class Declared(Strategy):
    """Select tests whose hand-written dependencies mention a changed component; order by risk, then cost."""

    name = "declared"

    def order(self, ctx):
        scored = []
        for t in ctx.tests():
            a = affinity(ctx.change, ctx.catalog[t].declared_components())
            if a > 0:
                scored.append((-ctx.catalog[t].severity, -a, ctx.cost(t), t))
        return [t for *_, t in sorted(scored)]


def tfidf_relevance(ctx) -> dict[str, float]:
    """TF-IDF cosine similarity between the change text and each test's text (0..1). The words' weights come
    from the test suite: a word that many tests share counts little."""
    docs = {t: tokens(ctx.catalog[t].text()) for t in ctx.tests()}
    df = defaultdict(int)
    for toks in docs.values():
        for w in set(toks):
            df[w] += 1
    n = len(docs)

    def vec(toks):  # sublinear tf x smoothed idf
        tf = defaultdict(int)
        for w in toks:
            tf[w] += 1
        return {w: (1 + math.log(c)) * math.log((n + 1) / (df.get(w, 0) + 1)) for w, c in tf.items()}

    q = vec(tokens(change_text(ctx.change)))
    qn = math.sqrt(sum(v * v for v in q.values())) or 1.0
    out = {}
    for t, toks in docs.items():
        d = vec(toks)
        dn = math.sqrt(sum(v * v for v in d.values())) or 1.0
        out[t] = sum(q[w] * d[w] for w in q if w in d) / (qn * dn)
    return out


@register
class IRTfidf(Strategy):
    """Rank every test by TF-IDF cosine similarity between the change text and the test text."""

    name = "ir_tfidf"

    def order(self, ctx):
        rel = tfidf_relevance(ctx)
        return sorted(rel, key=lambda t: (-rel[t], ctx.cost(t), t))


@register
class Observed(Strategy):
    """Select tests whose baseline traces exercised a changed component (agents, skills, tools, config
    reads, code functions/lines); order by affinity x risk / cost."""

    name = "observed"

    def order(self, ctx):
        scored = []
        for t in ctx.tests():
            a = weighted_affinity(ctx.change, ctx.history.baseline[t].dep_frequency)
            if a > 0:
                scored.append((-(a * ctx.catalog[t].severity) / ctx.cost(t), t))
        return [t for _, t in sorted(scored)]


@register
class CostAware(Strategy):
    """Rank the whole suite by Risk x (0.05 + ChangeAffinity) x (1 + FailureHistory) / ExpectedTokens:
    affected tests float to the top, cheap ones first; unaffected tests follow so the budget is used."""

    name = "cost_aware"

    def order(self, ctx):
        scored = []
        for t in ctx.tests():
            st = ctx.history.baseline[t]
            a = weighted_affinity(ctx.change, st.dep_frequency)
            if line_hit(ctx.change, st.deps):
                a += 1.0  # executed a changed line: strongest static evidence
            # 0.05 keeps unaffected tests in the ranking; 2 - pass_rate is the failure history (1 if the test
            # always passed at baseline, up to 2)
            score = ctx.catalog[t].severity * (0.05 + a) * (2.0 - st.pass_rate) / ctx.cost(t)
            scored.append((-score, t))
        return [t for _, t in sorted(scored)]
