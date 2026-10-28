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
    name = "observed_diverse"

    def order(self, ctx):
        groups: dict[tuple, list[str]] = defaultdict(list)
        for t in ctx.tests():
            if weighted_affinity(ctx.change, ctx.history.baseline[t].dep_frequency()) <= 0:
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
    case, st = ctx.catalog[t], ctx.history.baseline[t]
    freq = st.dep_frequency()
    deps = set(freq)
    kinds = defaultdict(int)
    nonsem = 0
    for c in change.components:
        if not c.semantic:
            nonsem += 1
        elif matches(c, deps):
            kinds[c.kind] += 1
    return [
        1.0,
        math.log1p(weighted_affinity(change, freq)),
        float(affinity(change, case.declared_components(), semantic_only=False)),
        float(line_hit(change, deps)),
        kinds["code"],
        kinds["tool"],
        kinds["skill"],
        kinds["skill-prose"],
        kinds["agent"],
        kinds["agent-prompt"],
        kinds["config"],
        float(nonsem),
        math.log(ctx.cost(t)),
        case.severity,
        float(case.fault_profile != "healthy"),
        float(case.dataset is not None),
        float(len(change.components)),
    ]


@register
class HistoryML(Strategy):
    name = "history_ml"

    def _features_for(self, ctx, variant, change):
        cache = ctx.options.setdefault("ml_features", {})
        if (variant,) not in cache:
            cache[(variant,)] = [_features(ctx, t, change) for t in ctx.tests()]
        return cache[(variant,)]

    def order(self, ctx):
        from sklearn.linear_model import LogisticRegression

        models = ctx.options.setdefault("ml_models", {})
        key = (ctx.change.variant, tuple(sorted(ctx.train_variants)))
        if key not in models:
            X, y = [], []
            for v in ctx.train_variants:
                change = ctx.history.changesets.get(v)
                if change is None:
                    continue
                revealing = ctx.history.revealing_tests(v)
                X.extend(self._features_for(ctx, v, change))
                y.extend(1 if t in revealing else 0 for t in ctx.tests())
            models[key] = None
            if X and 0 < sum(y) < len(y):
                models[key] = LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced").fit(X, y)
        if models[key] is None:
            return CostAware().order(ctx)
        probs = models[key].predict_proba(self._features_for(ctx, ctx.change.variant, ctx.change))[:, 1]
        scored = [(-(p * ctx.catalog[t].severity) / ctx.cost(t), t) for p, t in zip(probs, ctx.tests(), strict=True)]
        return [t for _, t in sorted(scored)]
