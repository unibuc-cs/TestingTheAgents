"""Replay phase: evaluate strategies offline against the recorded history.

For every (variant, strategy, budget, seed): build the selection context from the *baseline* history
and the variant's change set, let the strategy pick tests, and answer each execution request from the
recorded runs of that variant (outcome and cost of a randomly chosen repetition). Adaptive strategies
interact with the oracle sequentially; all others are executed greedily in their prioritized order.
Every run ends at its first failure and leaves out the tests that fail on the original app
(``selection/base.py``). The seeds draw the recorded run that answers each test and drive the strategies that
draw at random: they are not a sample, the changes are.

The same evaluation is made a second time replay-first (``replay_first.py``), when the recording has been
replayed: a test that replays to the end on the changed copy is not run, a replayed failure ends the run before
any test runs, and a diverged test is charged the tokens after its divergence point. That is an upper bound: after
that point a run still sends requests the original app made, which a check answers from the cassette too. When the
recording counted their tokens, ``new_cost_fraction`` gives the same tests charged for the new requests only."""

import random
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

import pandas as pd

from traceeval.catalog import load_catalog, load_properties
from traceeval.selection import CORE, STRATEGIES, SelectionContext, get_strategy
from traceeval.selection.base import ExecutionLog
from traceeval.selection.strategies import REPLAY_FIRST

from .coverage import affected_properties, affected_workflows
from .history import History
from .metrics import apfd, apfdc, evaluate_log
from .replay_first import Replays

DEFAULT_BUDGETS = (0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0)


def _resolve(strategies, replay_first: bool = False):
    """None -> the default comparison (with two more orders when replay-first); ["all"] -> every registered
    strategy."""
    if not strategies:
        return list(REPLAY_FIRST if replay_first else CORE)
    if list(strategies) == ["all"]:
        return list(STRATEGIES)
    return list(strategies)


def make_oracle(history: History, variant: str, rng: random.Random, prefix: dict[str, float] | None = None):
    """Answer "run this test" from the recorded runs of the variant: the outcome and cost of one recorded
    repetition, drawn at random. The run it drew is kept in ``oracle.records``, by test, for a strategy that reads
    more of a run than its outcome (its tool calls, its length), as it could of a run it had just made.

    With replay-first, ``prefix`` gives the tokens of each diverged test's requests that replay from the cassette:
    they are taken off the cost, since the model is asked from the divergence point on only."""
    prefix = prefix or {}

    def oracle(test_id: str):
        stats = history.variants.get(variant, {}).get(test_id)
        # A run the environment broke is never drawn. A pair with no valid run at all is missing (History.missing):
        # ``ctx.runnable`` keeps it from every strategy, so the baseline's runs below answer only a caller that
        # asks all the same, with the outcome History.variant_pass_rate gives the pair.
        base = history.baseline[test_id]
        runs = stats.valid_runs if stats and stats.valid_runs else (base.valid_runs or base.runs)
        rec = rng.choice(runs)
        oracle.records[test_id] = rec
        return bool(rec["passed"]), max(0.0, float(rec["tokens"]) - prefix.get(test_id, 0.0))

    oracle.records = {}
    return oracle


def new_tokens(runs) -> float:
    """Over some recorded runs of a changed copy: the tokens of the requests the original app never made, which is
    what a run costs when every request the cassette knows is answered from it, those after the divergence point
    included (``traceeval check`` runs so). ``Compare`` counts the known requests' tokens while a copy is
    recorded; NaN when one of the runs was recorded without that count."""
    known = [(r.get("cassette") or {}).get("known_tokens") for r in runs]
    if any(k is None for k in known):
        return float("nan")
    return float(sum(max(0.0, r["tokens"] - k) for r, k in zip(runs, known, strict=True)))


def _load(workdir: Path) -> History:
    """The recording, for an evaluation: nothing in it changes from here on, so the tests that reveal each change
    are worked out once (the strategies that learn from the other changes ask for them at every run)."""
    history = History.load(workdir)
    reveal = history.revealing_tests
    history.revealing_tests = lru_cache(maxsize=None)(
        lambda variant, threshold=0.5: frozenset(reveal(variant, threshold))
    )
    return history


def _learns_from(history: History, variant: str, train: list[str] | None) -> list[str]:
    """The recorded changes a strategy may learn from when ``variant`` is under test: every other one that shares
    no change with it (``History.training_variants``) and, when ``train`` is given, is in that list. A held-out
    evaluation passes the half of the generated changes set aside for learning (``generator.split``)."""
    allowed = history.training_variants(variant)
    return allowed if train is None else [v for v in allowed if v in set(train)]


def _rows(job: tuple) -> list[dict]:
    """The rows of ``evaluate`` for some of the changes: (recording, strategies, budgets, seeds, the changes,
    replay-first or not, the changes to learn from). The rows of one change do not depend on any other change
    being evaluated, so the changes can be shared out among processes."""
    workdir, strategies, budgets, seeds, variants, replay_first, train = job
    history = _load(workdir)
    catalog = {c.id: c for c in load_catalog()}
    props = load_properties()
    replays = Replays.load(workdir) if replay_first else None
    if replay_first and replays is None:
        raise SystemExit(f"{workdir} has not been replayed: run traceeval replay-first --workdir {workdir}")
    strategies = _resolve(strategies, replay_first)
    full = history.total_cost()
    rows = []
    # a strategy's prioritized order depends on the change (and the seed) only, so it is shared across budgets
    shared = {"order_cache": {}}
    for variant in variants:
        change = history.changesets[variant]
        # for the change coverage columns: both depend on the change only, so they are computed once per variant
        affected = affected_properties(change, history, catalog, props)
        affected_wf = affected_workflows(change, history, catalog)
        # learning may use every recorded change but this one and those that share a change with it (a batch's members)
        learn = _learns_from(history, variant, train)
        # the tests the recording cannot answer for on this copy: no strategy is given them to run
        missing = history.missing(variant)
        # Replay-first: what the replay of this copy gave, before any test runs. ``replayed``: the tests whose
        # outcome is known; ``prefix``: per diverged test, the tokens that replay before the divergence; ``found``:
        # the tests that pass on the original app and replay to a failure, which is a regression for no tokens.
        replayed, prefix, found = frozenset(), {}, []
        if replays and variant not in replays.rows:
            raise SystemExit(f"{variant} is not in the replay of {workdir}: run traceeval replay-first again")
        if replays:
            replayed, prefix = replays.replayed(variant), replays.prefix(variant)
            found = [t for t in replays.new_failures(variant) if history.baseline_pass_rate(t) >= 0.5]
        # the replayed tests that pass on the original app have checked what they check, as if they had been run
        known = frozenset(t for t in replayed if history.baseline_pass_rate(t) >= 0.5)
        for name in strategies:
            strat = get_strategy(name)
            for b in budgets:
                # a nominal budget is a share of the full suite's tokens
                budget = b * full
                for seed in range(seeds):
                    # from the seed and the variant name, not hash() (salted per process)
                    rng = random.Random(1000 * seed + sum(map(ord, variant)))
                    # the same generator drives the strategy's choices and the oracle's draws
                    opts = dict(shared, seed=seed)
                    oracle = make_oracle(history, variant, rng, prefix)
                    if found:  # the replay already shows the regression: no strategy has anything to choose
                        log = ExecutionLog(name, steps=[(t, False, 0.0) for t in found], stop_reason="regression")
                    else:
                        ctx = SelectionContext(
                            change, catalog, history, budget, rng, learn, opts, replayed, prefix, missing
                        )
                        log = strat.run(ctx, oracle)
                    row = evaluate_log(log, variant, history, catalog, budget, props, affected, affected_wf, known)
                    # the change's label, for the report's ground truth table; the strategy never sees it
                    row.update(
                        {
                            "seed": seed,
                            "budget": b,
                            "category": history.mutation_meta.get(variant, {}).get("category", "?"),
                            "expected_regression": history.mutation_meta.get(variant, {}).get("expected_regression"),
                        }
                    )
                    if replays:
                        # what the same tests cost run whole, without the replayed part taken off; and what they
                        # cost when the cassette also answers the requests it knows after the divergence point
                        drawn = list(oracle.records.values())
                        row["whole_cost_fraction"] = sum(r["tokens"] for r in drawn) / full
                        row["new_cost_fraction"] = new_tokens(drawn) / full
                        if found:  # nothing ran: the failures were read off the replay
                            row["tests_run"], row["time_fraction"] = 0, 0.0
                    rows.append(row)
    return rows


def evaluate(
    workdir: Path,
    strategies: list[str] | None = None,
    budgets=DEFAULT_BUDGETS,
    seeds: int = 5,
    variants: list[str] | None = None,
    replay_first: bool = False,
    train: list[str] | None = None,
    jobs: int = 1,
) -> pd.DataFrame:
    """The replay: one row of results/replay.csv per (change, strategy, budget, seed). The strategy sees the change
    set and the baseline facts, picks tests, and the oracle answers from the recorded runs of the changed copy.
    ``variants`` names the changes to evaluate (all by default) and ``train`` those a strategy may learn from (all
    the others by default). With ``jobs`` > 1 the changes are shared out among that many processes, each of which
    loads the recording: worth it for several hundred changes.

    With ``replay_first`` the rows go to results/replay_first.csv, and each run starts from what the replay of the
    changed copy already gave (``history/replay_first.jsonl``)."""
    workdir = Path(workdir)
    variants = variants or sorted(path.stem for path in (workdir / "history" / "variants").glob("*.jsonl"))
    shares = [variants[i::jobs] for i in range(max(1, jobs))]
    todo = [(workdir, strategies, budgets, seeds, share, replay_first, train) for share in shares if share]
    if len(todo) > 1:
        with ProcessPoolExecutor(max_workers=len(todo)) as pool:
            shared_out = list(pool.map(_rows, todo))
    else:
        shared_out = [_rows(job) for job in todo]
    # one table, in the order of the changes whichever process evaluated each (the sort keeps a change's rows in order)
    place = {variant: i for i, variant in enumerate(variants)}
    df = pd.DataFrame(sorted((row for rows in shared_out for row in rows), key=lambda row: place[row["variant"]]))
    (workdir / "results").mkdir(exist_ok=True, parents=True)
    df.to_csv(workdir / "results" / ("replay_first.csv" if replay_first else "replay.csv"), index=False)
    return df


def evaluate_prioritization(
    workdir: Path,
    strategies: list[str] | None = None,
    seeds: int = 5,
    variants: list[str] | None = None,
    train: list[str] | None = None,
) -> pd.DataFrame:
    """APFD / APFD_c of each strategy's complete prioritized order (selection + prioritization view). An order that
    is drawn at random is scored over ``seeds`` draws per change; any other order is the same every time and is
    scored once."""
    workdir = Path(workdir)
    history = _load(workdir)
    catalog = {c.id: c for c in load_catalog()}
    strategies = _resolve(strategies)
    variants = variants or sorted(history.variants)
    # the suite an order is scored on: the tests that pass on the original app, since no strategy runs the others
    suite = [t for t in history.test_ids() if history.baseline_pass_rate(t) >= 0.5]
    # per test: its mean cost on the original app, for APFD_c
    cost = {t: history.cost(t) for t in suite}
    rows = []
    shared = {"order_cache": {}}
    for variant in variants:
        # APFD is undefined for a change no test reveals
        revealing = history.revealing_tests(variant)
        if not revealing:
            continue
        change = history.changesets[variant]
        learn = _learns_from(history, variant, train)
        for name in strategies:
            strat = get_strategy(name)
            for seed in range(seeds if strat.stochastic else 1):
                # from the seed and the variant name, as in ``evaluate``: another draw for every change
                rng = random.Random(1000 * seed + sum(map(ord, variant)))
                # an unlimited budget: what is measured is the order, not what the strategy would run within a budget
                ctx = SelectionContext(
                    change, catalog, history, float("inf"), rng, train_variants=learn, options=dict(shared, seed=seed)
                )
                order = [t for t in strat.order(ctx) if t in cost]
                seen = set(order)
                # the tests the strategy left out follow, in suite order, so that every revealing test has a position
                full_order = order + [t for t in suite if t not in seen]
                rows.append(
                    {
                        "variant": variant,
                        "strategy": name,
                        "seed": seed,
                        "category": history.mutation_meta.get(variant, {}).get("category", "?"),
                        # how many tests the strategy's order holds: a selecting strategy orders a subset only
                        "selected": len(order),
                        "apfd": apfd(full_order, revealing),
                        "apfdc": apfdc(full_order, revealing, cost),
                        # what that subset costs, and the share of the revealing tests inside it
                        "selected_cost_fraction": sum(cost[t] for t in order) / history.total_cost(),
                        "selection_recall": len(revealing & seen) / len(revealing),
                    }
                )
    df = pd.DataFrame(rows)
    df.to_csv(workdir / "results" / "prioritization.csv", index=False)
    return df
