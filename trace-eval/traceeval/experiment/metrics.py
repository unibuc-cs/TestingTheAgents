"""Metrics for a replayed execution against the ground-truth fault matrix of one variant."""


def apfd(order: list[str], revealing: set[str]) -> float | None:
    """Average Percentage of Faults Detected of ``order`` (the complete prioritized suite) for one change. The
    change is one fault, found by the first of its revealing tests in the order. Returns None when nothing is
    revealing."""
    n = len(order)
    if n == 0 or not revealing:
        return None
    # the 1-based position of the first revealing test; none in the order counts as never detected
    first = next((i + 1 for i, t in enumerate(order) if t in revealing), n + 1)
    # Rothermel et al.'s formula with one fault: 1 - (its detection position) / n + 1 / (2 n)
    return 1.0 - first / n + 1.0 / (2 * n)


def apfdc(order: list[str], revealing: set[str], cost: dict[str, float]) -> float | None:
    """Cost-cognizant APFD (Elbaum et al. 2001) for one change, taken as one fault: the share of the order's cost
    left unspent when the first revealing test finds it, plus half of that test's own cost. With a single fault
    its severity cancels out."""
    if not order or not revealing:
        return None
    total = sum(cost[t] for t in order)
    spent = 0.0
    for t in order:
        if t in revealing:
            return (total - spent - 0.5 * cost[t]) / total
        spent += cost[t]
    return 0.0  # no revealing test in the order: the fault is never found


def evaluate_log(
    log, variant: str, history, catalog, budget: float, props=None, affected=None, affected_wf=None, known=()
) -> dict:
    """One row of replay.csv: what a strategy's execution log detected, at what cost, and how it stopped.
    A failure of a revealing test is a detection. A failure of a test that passes on the original app and does not
    reveal the change (a run that differs from its test's majority) is a false alarm: the run stops on it with a
    regression verdict the ground truth does not back. Given the catalog of properties (``props``), the row also
    gets the change coverage of the executed tests (``coverage.change_coverage``), which needs no ground truth;
    ``affected`` and ``affected_wf`` are the change's affected properties and workflows when the caller already
    has them. ``known`` names the tests whose outcome on the changed copy was known without running them
    (replay-first): for the coverage columns they count as run."""
    # the ground truth: the change is a regression when at least one test reveals it
    revealing = history.revealing_tests(variant)
    is_regression = len(revealing) > 0
    executed = log.executed
    # for coverage: the tests run, and those whose outcome was known beforehand
    covering = executed + sorted(set(known) - set(executed))
    full_cost = history.total_cost()
    # walk the executed tests in order: a failing revealing test is a detection, and the tokens spent up to the
    # first one are the cost to detect; a failure of any other test that passes on the original app is a false alarm
    first_detect_cost = None
    acc = 0.0
    true_fails, false_alarms = set(), set()
    for t, passed, cost in log.steps:
        acc += cost
        if not passed:
            if t in revealing:
                true_fails.add(t)
                if first_detect_cost is None:
                    first_detect_cost = acc
            elif history.baseline_pass_rate(t) >= 0.5:
                false_alarms.add(t)
    # a change one of whose revealing tests checks a safety property is a critical regression
    safety_revealing = {t for t in revealing if catalog[t].is_safety}
    # the properties the change breaks (those of its revealing tests), and those the strategy ran a test of
    broken = {p for t in revealing for p in catalog[t].properties}
    exercised = {p for t in covering for p in catalog[t].properties}
    out = {
        "variant": variant,
        "strategy": log.strategy,
        # the nominal budget, as a share of the full suite's tokens
        "budget_fraction": budget / full_cost if full_cost else None,
        "is_regression": is_regression,
        "n_revealing": len(revealing),
        # one failing revealing test is enough; recall is the share of the revealing tests that failed in this run
        "detected": bool(true_fails),
        "recall": (len(true_fails) / len(revealing)) if is_regression else None,
        "tests_run": len(executed),
        # tokens actually spent, and those spent up to the first detection
        "cost": log.cost,
        "cost_fraction": log.cost / full_cost if full_cost else None,
        "cost_to_detect": first_detect_cost,
        "cost_to_detect_fraction": (first_detect_cost / full_cost) if first_detect_cost is not None else None,
        # run time: the executed tests' mean time on the original app, as a share of the whole suite's
        "time_fraction": sum(history.seconds(t) for t in executed) / history.total_seconds(),
        # a failure of a test that passes on the original app and does not reveal the change
        "false_alarm": bool(false_alarms),
        # set only for a change that breaks a safety property (one of its revealing tests checks one)
        "safety_recall": (len(true_fails & safety_revealing) / len(safety_revealing)) if safety_revealing else None,
        # the share of the properties the change breaks that an executed test checks
        "property_coverage": (len(broken & exercised) / len(broken)) if broken else None,
        # regression | exhausted | budget | clean | uninformative | no_components (selection/base.py)
        "stop_reason": log.stop_reason,
        # did the strategy end with the right conclusion? "clean"/"regression" are explicit verdicts; any other
        # stop is judged by whether it found a true failure (a run that ran everything it selected and found none
        # is right on a change no test reveals); with no components, "clean" is implied
        "stop_correct": (
            (log.stop_reason == "clean" and not is_regression)
            or (log.stop_reason == "regression" and is_regression)
            or (log.stop_reason in ("budget", "exhausted", "uninformative") and bool(true_fails) == is_regression)
        )
        if log.stop_reason != "no_components"
        else (not is_regression),
    }
    # the change coverage columns (coverage.py): what the executed tests cover of the change, without the ground truth
    if props is not None:
        from .coverage import change_coverage

        out.update(
            change_coverage(history.changesets[variant], covering, history, catalog, props, affected, affected_wf)
        )
    return out
