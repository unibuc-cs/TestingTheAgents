"""Replay phase: evaluate strategies offline against the recorded history.

For every (variant, strategy, budget, seed): build the selection context from the *baseline* history
and the variant's change set, let the strategy pick tests, and answer each execution request from the
recorded runs of that variant (outcome and cost of a randomly chosen repetition). Adaptive strategies
interact with the oracle sequentially; all others are executed greedily in their prioritized order."""

import random
from pathlib import Path

import pandas as pd

from traceeval.catalog import load_catalog
from traceeval.selection import CORE, STRATEGIES, SelectionContext, get_strategy

from .history import History
from .metrics import apfd, apfdc, evaluate_log

DEFAULT_BUDGETS = (0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0)


def _resolve(strategies):
    """None -> the core comparison; ["all"] -> every registered strategy."""
    if not strategies:
        return list(CORE)
    if list(strategies) == ["all"]:
        return list(STRATEGIES)
    return list(strategies)


def make_oracle(history: History, variant: str, rng: random.Random):
    def oracle(test_id: str):
        stats = history.variants.get(variant, {}).get(test_id)
        runs = stats.runs if stats and stats.runs else history.baseline[test_id].runs
        rec = rng.choice(runs)
        return bool(rec["passed"]), float(rec["tokens"])

    return oracle


def evaluate(
    workdir: Path,
    strategies: list[str] | None = None,
    budgets=DEFAULT_BUDGETS,
    seeds: int = 5,
    variants: list[str] | None = None,
) -> pd.DataFrame:
    workdir = Path(workdir)
    history = History.load(workdir)
    catalog = {c.id: c for c in load_catalog()}
    strategies = _resolve(strategies)
    variants = variants or sorted(history.variants)
    rows = []
    shared = {"order_cache": {}}
    for variant in variants:
        change = history.changesets[variant]
        train = [v for v in variants if v != variant]
        for name in strategies:
            strat = get_strategy(name)
            for b in budgets:
                budget = b * history.total_cost()
                for seed in range(seeds):
                    rng = random.Random(1000 * seed + sum(map(ord, variant)))
                    opts = dict(shared, seed=seed)
                    ctx = SelectionContext(change, catalog, history, budget, rng, train_variants=train, options=opts)
                    log = strat.run(ctx, make_oracle(history, variant, rng))
                    row = evaluate_log(log, variant, history, catalog, budget)
                    row.update(
                        {
                            "seed": seed,
                            "budget": b,
                            "category": history.mutation_meta.get(variant, {}).get("category", "?"),
                            "expected_regression": history.mutation_meta.get(variant, {}).get("expected_regression"),
                        }
                    )
                    rows.append(row)
    df = pd.DataFrame(rows)
    (workdir / "results").mkdir(exist_ok=True, parents=True)
    df.to_csv(workdir / "results" / "replay.csv", index=False)
    return df


def evaluate_prioritization(
    workdir: Path, strategies: list[str] | None = None, seeds: int = 3, variants: list[str] | None = None
) -> pd.DataFrame:
    """APFD / APFD_c of each strategy's complete prioritized order (selection + prioritization view)."""
    workdir = Path(workdir)
    history = History.load(workdir)
    catalog = {c.id: c for c in load_catalog()}
    strategies = _resolve(strategies)
    variants = variants or sorted(history.variants)
    cost = {t: history.cost(t) for t in history.test_ids()}
    sev = {t: catalog[t].severity for t in history.test_ids()}
    rows = []
    shared = {"order_cache": {}}
    for variant in variants:
        revealing = history.revealing_tests(variant)
        if not revealing:
            continue
        change = history.changesets[variant]
        train = [v for v in variants if v != variant]
        for name in strategies:
            strat = get_strategy(name)
            for seed in range(seeds):
                rng = random.Random(seed)
                ctx = SelectionContext(
                    change, catalog, history, float("inf"), rng, train_variants=train, options=dict(shared, seed=seed)
                )
                order = strat.order(ctx)
                seen = set(order)
                full_order = order + [t for t in history.test_ids() if t not in seen]
                rows.append(
                    {
                        "variant": variant,
                        "strategy": name,
                        "seed": seed,
                        "category": history.mutation_meta.get(variant, {}).get("category", "?"),
                        "selected": len(order),
                        "apfd": apfd(full_order, revealing),
                        "apfdc": apfdc(full_order, revealing, cost, sev),
                        "selected_cost_fraction": sum(cost[t] for t in order) / history.total_cost(),
                        "selection_recall": len(revealing & seen) / len(revealing),
                    }
                )
    df = pd.DataFrame(rows)
    df.to_csv(workdir / "results" / "prioritization.csv", index=False)
    return df
