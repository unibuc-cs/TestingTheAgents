"""Common interface of selection / prioritization / stopping strategies.

A strategy receives a ``SelectionContext`` (change set, catalog, baseline history, budget) and either
- returns a prioritized list of test ids (``order``), which the evaluator executes greedily within the
  budget, or
- drives execution itself through an oracle (``run``), choosing the next test from the outcomes so far
  and deciding when to stop (adaptive strategies).

Strategies never see variant outcomes other than through the oracle, and never see mutation labels."""

from collections.abc import Callable
from dataclasses import dataclass, field

from traceeval.catalog import EvalCase
from traceeval.mutation.changeset import ChangedComponent, ChangeSet

Oracle = Callable[[str], tuple[bool, float]]  # test_id -> (passed, cost)


@dataclass
class SelectionContext:
    change: ChangeSet
    catalog: dict[str, EvalCase]
    history: object  # traceeval.experiment.history.History (baseline facts only)
    budget: float  # tokens
    rng: object
    train_variants: list[str] = field(default_factory=list)  # variants usable for learning (never the one under test)
    options: dict = field(default_factory=dict)

    def tests(self) -> list[str]:
        return [t for t in self.history.test_ids() if t in self.catalog]

    def cost(self, t: str) -> float:
        return max(1.0, self.history.cost(t))


@dataclass
class ExecutionLog:
    strategy: str
    steps: list[tuple[str, bool, float]] = field(default_factory=list)  # (test_id, passed, cost)
    stop_reason: str = "budget"
    diagnostics: dict = field(default_factory=dict)

    @property
    def cost(self) -> float:
        return sum(c for _, _, c in self.steps)

    @property
    def executed(self) -> list[str]:
        return [t for t, _, _ in self.steps]


# ---------------------------------------------------------------------------- dependency matching
def matches(component: ChangedComponent, deps: set[str]) -> bool:
    """Does a changed component touch a test whose (declared or observed) dependencies are ``deps``?"""
    cid, base = component.id, component.base
    if cid in deps or base in deps:
        return True
    if cid.startswith("code:") and "::" not in cid and "#" not in cid:
        return any(d.startswith(cid + "::") for d in deps)  # module-level change in a used file
    if cid.startswith("code:") and "#text" in cid:
        file_id = cid.split("#", 1)[0]
        return any(d.startswith(file_id + "::") for d in deps)
    return False


def affinity(change: ChangeSet, deps: set[str], semantic_only: bool = True) -> int:
    """Number of changed components touching ``deps`` (line-level hits count once per file)."""
    n, line_files = 0, set()
    for c in change.components:
        if not (c.semantic or not semantic_only) or not matches(c, deps):
            continue
        if c.kind == "line":
            line_files.add(c.file)
        else:
            n += 1
    return n + len(line_files)


def line_hit(change: ChangeSet, deps: set[str], semantic_only: bool = True) -> bool:
    """Did the test execute at least one changed line (finest-grained evidence of impact)?"""
    return any(c.kind == "line" and (c.semantic or not semantic_only) and c.id in deps for c in change.components)


def code_components(change: ChangeSet) -> list[ChangedComponent]:
    return [c for c in change.components if c.kind in ("code", "tool")]


def weighted_affinity(change: ChangeSet, dep_freq: dict[str, float], semantic_only: bool = True) -> float:
    """Affinity weighted by how often the component was exercised in the test's baseline runs."""
    total = 0.0
    deps = set(dep_freq)
    line_files: dict[str, float] = {}
    for c in change.components:
        if not (c.semantic or not semantic_only) or not matches(c, deps):
            continue
        if c.kind == "line":
            line_files[c.file] = max(line_files.get(c.file, 0.0), dep_freq.get(c.id, 1.0))
            continue
        hits = [
            dep_freq[d]
            for d in deps
            if d == c.id
            or d == c.base
            or (c.id.startswith("code:") and "::" not in c.id and d.startswith(c.id.split("#")[0] + "::"))
        ]
        total += max(hits) if hits else 1.0
    return total + sum(line_files.values())


class Strategy:
    name = "base"
    adaptive = False
    stochastic = False  # order depends on ctx.rng (then it is cached per seed, not per variant)

    def order(self, ctx: SelectionContext) -> list[str]:
        raise NotImplementedError

    def cached_order(self, ctx: SelectionContext) -> list[str]:
        """The prioritized order depends on the change and the history only (plus the seed for
        stochastic strategies), so it is cached across budgets by the evaluator."""
        cache = ctx.options.get("order_cache")
        if cache is None:
            return self.order(ctx)
        key = (self.name, ctx.change.variant, ctx.options.get("seed") if self.stochastic else None)
        if key not in cache:
            cache[key] = self.order(ctx)
        return list(cache[key])

    def run(self, ctx: SelectionContext, oracle: Oracle) -> ExecutionLog:
        """Default: greedy execution of ``order`` within the budget (skip tests that do not fit)."""
        log = ExecutionLog(self.name)
        remaining = ctx.budget
        for t in self.cached_order(ctx):
            est = ctx.cost(t)
            if est > remaining:
                continue
            passed, cost = oracle(t)
            log.steps.append((t, passed, cost))
            remaining -= cost
            if remaining <= 0:
                break
        log.stop_reason = "exhausted" if remaining > 0 else "budget"
        return log
