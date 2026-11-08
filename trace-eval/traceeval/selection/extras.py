"""Optional baselines (not part of the default comparison; select with ``--strategies all``).

observed_diverse  observed selection with "additional"-greedy breadth over distinct behaviours
history_ml        predictive test selection: logistic regression on affinity/cost/risk features,
                  trained on the outcomes of the *other* changes (needs scikit-learn)
"""

import math
from collections import defaultdict

from .base import Strategy, affinity, line_hit, matches, weighted_affinity
from .strategies import CostAware, register


@register
class ObservedDiverse(Strategy):
    """The tests ``observed`` would select, grouped by behaviour (agents, tools, faulty or not) and taken one
    group at a time, so that the budget covers many behaviours before it repeats one."""

    name = "observed_diverse"

    def order(self, ctx):
        groups: dict[tuple, list[str]] = defaultdict(list)
        for t in ctx.tests():
            if weighted_affinity(ctx.change, ctx.history.baseline[t].dep_frequency) <= 0:
                continue
            run0 = ctx.history.baseline[t].runs[0]
            sig = (
                tuple(run0.get("agents", [])),
                tuple(sorted(set(run0.get("tools", [])))),
                ctx.catalog[t].fault_profile != "healthy",
            )
            groups[sig].append(t)
        for sig in groups:
            groups[sig].sort(key=lambda t: (-ctx.catalog[t].severity, ctx.cost(t)))
        order = []
        while any(groups.values()):  # round-robin over behaviour signatures, riskiest group first
            for sig in sorted(
                groups, key=lambda s: -max(ctx.catalog[t].severity for t in groups[s]) if groups[s] else 0
            ):
                if groups[sig]:
                    order.append(groups[sig].pop(0))
        return order


def _features(ctx, t, change):
    """Feature vector of test ``t`` for ``change``: static impact evidence by kind, cost, risk, shape of the test."""
    case, st = ctx.catalog[t], ctx.history.baseline[t]
    freq = st.dep_frequency
    deps = set(freq)
    kinds = defaultdict(int)
    for c in change.components:
        if matches(c, deps):
            kinds[c.kind] += 1
    return [
        1.0,
        math.log1p(weighted_affinity(change, freq)),
        float(affinity(change, case.declared_components())),
        float(line_hit(change, deps)),
        kinds["code"],
        kinds["tool"],
        kinds["skill"],
        kinds["skill-prose"],
        kinds["agent"],
        kinds["agent-prompt"],
        kinds["config"],
        math.log(ctx.cost(t)),
        case.severity,
        float(case.fault_profile != "healthy"),
        float(case.dataset is not None),
        float(len(change.components)),
    ]


@register
class HistoryML(Strategy):
    name = "history_ml"

    def order(self, ctx):
        from sklearn.linear_model import LogisticRegression

        # one training row per (training change, test): did the test reveal the change?
        X, y = [], []
        for v in ctx.train_variants:
            change = ctx.history.changesets.get(v)
            if change is None:
                continue
            revealing = ctx.history.revealing_tests(v)
            X.extend(_features(ctx, t, change) for t in ctx.tests())
            y.extend(1 if t in revealing else 0 for t in ctx.tests())
        if not (X and 0 < sum(y) < len(y)):  # nothing to learn from (no data, or a single class)
            return CostAware().order(ctx)
        model = LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced").fit(X, y)
        probs = model.predict_proba([_features(ctx, t, ctx.change) for t in ctx.tests()])[:, 1]
        scored = [(-(p * ctx.catalog[t].severity) / ctx.cost(t), t) for p, t in zip(probs, ctx.tests(), strict=True)]
        return [t for _, t in sorted(scored)]
