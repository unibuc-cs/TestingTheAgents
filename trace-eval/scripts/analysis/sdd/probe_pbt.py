"""Probe 2: why the property test misses FS-0103's 'gate ignores version' defect, and what a domain-shaped
strategy does with the same budget."""

import probe_fns
from hypothesis import strategies as st
from hypothesis.errors import NoSuchExample

from traceeval.spec.checks.contracts import _find
from traceeval.spec.context import evaluate

ASSUME = "page_version >= 1 and broken >= 0"
ENSURES = "result == (check_version == page_version and broken == 0)"
NAMES = ["check_version", "page_version", "broken"]
fn = probe_fns.f_gate_ignores_version


def trial(strat, budget, label):
    stats = {"calls": 0, "in_domain": 0, "broken0": 0}

    def violates(values):
        env = dict(zip(NAMES, values, strict=True))
        stats["calls"] += 1
        if not evaluate(ASSUME, dict(env)):
            return False
        stats["in_domain"] += 1
        stats["broken0"] += env["broken"] == 0
        env["result"] = fn(**env)
        return not evaluate(ENSURES, env)

    try:
        cx = _find(strat, violates, budget)
        print(f"{label}: counterexample {cx} after {stats}")
    except NoSuchExample:
        print(f"{label}: NO counterexample; {stats}")


# as the checker builds it: three unconstrained integers, out-of-domain draws spend the budget
naive = st.tuples(st.integers(), st.integers(), st.integers())
for budget in (200, 300, 1000, 5000):
    trial(naive, budget, f"checker strategy, budget {budget}")

# the domain written into the strategy instead of filtered afterwards
shaped = st.tuples(st.integers(), st.integers(min_value=1), st.integers(min_value=0))
for budget in (20, 200):
    trial(shaped, budget, f"domain-shaped strategy, budget {budget}")

# a boundary-value table a unit test would use
table = [(c, p, b) for p in (1, 2) for c in (p - 1, p, p + 1) for b in (0, 1)]
bad = [t for t in table if fn(*t) != (t[0] == t[1] and t[2] == 0)]
print(f"boundary table of {len(table)} cases: {len(bad)} counterexamples, first {bad[:1]}")
