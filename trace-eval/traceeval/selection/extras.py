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
        """Round-robin over the behaviour groups of the tests observed would select, riskiest group first."""
        # the tests observed would select, grouped by behaviour: first run's agents and tools, faulty or not
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
        # within a group, riskiest first, then cheapest
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
    # the changed components the observed dependencies match, counted by kind
    kinds = defaultdict(int)
    for c in change.components:
        if matches(c, deps):
            kinds[c.kind] += 1
    return [
        # a constant column
        1.0,
        # the impact evidence: observed affinity (compressed), declared affinity, a changed line run
        math.log1p(weighted_affinity(change, freq)),
        float(affinity(change, case.declared_components())),
        float(line_hit(change, deps)),
        # the matched components by kind
        kinds["code"],
        kinds["tool"],
        kinds["skill"],
        kinds["skill-prose"],
        kinds["agent"],
        kinds["agent-prompt"],
        kinds["config"],
        # cost, risk and the shape of the test, then the size of the change
        math.log(ctx.cost(t)),
        case.severity,
        float(case.fault_profile != "healthy"),
        float(case.dataset is not None),
        float(len(change.components)),
    ]


@register
class HistoryML(Strategy):
    """Predictive test selection (Machalica et al.): a logistic regression trained on the other recorded changes
    gives every test a probability of revealing this change; the suite is ranked by that probability x risk / cost.
    With nothing to learn from, the cost_aware order."""

    name = "history_ml"

    def order(self, ctx):
        # imported here so that the module loads without scikit-learn; only this optional baseline needs it
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
        # revealing tests are rare, so the classes are balanced
        model = LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced").fit(X, y)
        # P(reveal) of each test for the change under evaluation, from the same features
        probs = model.predict_proba([_features(ctx, t, ctx.change) for t in ctx.tests()])[:, 1]
        # probability x risk per token, highest first
        scored = [(-(p * ctx.catalog[t].severity) / ctx.cost(t), t) for p, t in zip(probs, ctx.tests(), strict=True)]
        return [t for _, t in sorted(scored)]
