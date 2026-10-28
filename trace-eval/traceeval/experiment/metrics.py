"""Metrics for a replayed execution against the ground-truth fault matrix of one variant."""


def apfd(order: list[str], revealing: set[str]) -> float | None:
    """Average Percentage of Faults Detected. Each revealing test is treated as one fault; the suite
    contains ``order`` (the complete prioritized suite). Returns None when nothing is revealing."""
    n, m = len(order), len(revealing)
    if n == 0 or m == 0:
        return None
    pos = {t: i + 1 for i, t in enumerate(order)}
    tf = [pos[t] for t in revealing if t in pos]
    if len(tf) < m:
        tf += [n + 1] * (m - len(tf))  # not in the suite: counts as never detected
    return 1.0 - sum(tf) / (n * m) + 1.0 / (2 * n)


def apfdc(order: list[str], revealing: set[str], cost: dict[str, float], severity: dict[str, float]) -> float | None:
    """Cost-cognizant APFD (Elbaum et al. 2001): cumulative severity detected against cumulative cost."""
    m = len(revealing)
    if not order or m == 0:
        return None
    total_cost = sum(cost[t] for t in order)
    total_sev = sum(severity.get(t, 1.0) for t in revealing)
    pos = {t: i for i, t in enumerate(order)}
    cum = []
    acc = 0.0
    for t in order:
        acc += cost[t]
        cum.append(acc)
    num = 0.0
    for t in revealing:
        if t not in pos:
            continue
        i = pos[t]
        num += severity.get(t, 1.0) * ((total_cost - cum[i]) + 0.5 * cost[t])
    return num / (total_cost * total_sev)


def evaluate_log(log, variant: str, history, catalog, budget: float) -> dict:
    revealing = history.revealing_tests(variant)
    is_regression = len(revealing) > 0
    executed = log.executed
    full_cost = history.total_cost()
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
            else:
                false_alarms.add(t)
    safety_revealing = {t for t in revealing if catalog[t].is_safety}
    out = {
        "variant": variant,
        "strategy": log.strategy,
        "budget_fraction": budget / full_cost if full_cost else None,
        "is_regression": is_regression,
        "n_revealing": len(revealing),
        "detected": bool(true_fails),
        "recall": (len(true_fails) / len(revealing)) if is_regression else None,
        "tests_run": len(executed),
        "cost": log.cost,
        "cost_fraction": log.cost / full_cost if full_cost else None,
        "cost_to_detect": first_detect_cost,
        "cost_to_detect_fraction": (first_detect_cost / full_cost) if first_detect_cost is not None else None,
        "false_alarm": bool(false_alarms),
        "safety_recall": (len(true_fails & safety_revealing) / len(safety_revealing)) if safety_revealing else None,
        "stop_reason": log.stop_reason,
        "stop_correct": (
            (log.stop_reason == "clean" and not is_regression)
            or (log.stop_reason == "regression" and is_regression)
            or (log.stop_reason in ("budget", "exhausted", "uninformative") and bool(true_fails) == is_regression)
        )
        if log.stop_reason != "no_components"
        else (not is_regression),
    }
    return out
