"""Common interface of selection / prioritization / stopping strategies.

A strategy receives a ``SelectionContext`` (change set, catalog, baseline history, budget) and either
- returns a prioritized list of test ids (``order``), which the evaluator executes greedily within the
  budget, or
- drives execution itself through an oracle (``run``), choosing the next test from the outcomes so far
  and deciding when to stop (adaptive strategies).

Every run follows the same two rules, so that strategies are compared like for like:
- a test the model already fails on the original app is not run (``ctx.runnable``): it cannot reveal a change;
- the run ends at the first failure, with the stop reason "regression": a test that passed on the original app
  now fails.
With replay-first (``experiment/replay_first.py``) ``ctx.runnable`` also leaves out the tests that replay to the
end on the changed copy: their outcome is known before any test runs, so a strategy orders the others only, and a
test costs what is left of it after the requests that replay (``ctx.cost``).

Strategies see the outcomes of the variant under evaluation only through the oracle (those of the other
variants, ``train_variants``, they may learn from), and never see mutation labels."""

from collections.abc import Callable
from dataclasses import dataclass, field

from traceeval.catalog import EvalCase
from traceeval.mutation.changeset import ChangedComponent, ChangeSet

Oracle = Callable[[str], tuple[bool, float]]  # test_id -> (passed, cost)


@dataclass
class SelectionContext:
    """What a strategy is given for one changed copy: the change set, the catalog, the baseline recording, the
    budget and a seed. The outcomes on that copy reach it only through the oracle."""

    # the change set of the changed copy under evaluation: its components, files and code diff
    change: ChangeSet
    # test id -> its case; the suite is the recording's tests that the catalog still has
    catalog: dict[str, EvalCase]
    history: object  # traceeval.experiment.history.History (baseline facts only)
    budget: float  # tokens
    rng: object  # random.Random of this replay seed (used by stochastic strategies)
    train_variants: list[str] = field(default_factory=list)  # variants usable for learning (never the one under test)
    options: dict = field(default_factory=dict)  # "seed" and the evaluator's "order_cache"; strategies' scratch space
    # Replay-first (experiment/replay_first.py), empty otherwise. ``replayed``: the tests whose outcome on the
    # changed copy is already known, because every request they make there is one the original app made.
    # ``prefix``: for the other tests, the tokens of the requests that replay before the change reaches the model.
    replayed: frozenset = frozenset()
    prefix: dict[str, float] = field(default_factory=dict)
    # The tests the recording has no valid run of on this changed copy (``History.missing``): the evaluation
    # cannot answer for them, so they are not run. Empty in a live check, where every test can be run.
    missing: frozenset = frozenset()

    def tests(self) -> list[str]:
        """The suite: the recorded tests that the catalog still has, in the order of the recording."""
        return [t for t in self.history.test_ids() if t in self.catalog]

    def cost(self, t: str) -> float:
        """Expected cost in tokens, the test's mean over its baseline runs; at least 1, as scores divide by it. With
        replay-first, the part of the test that replays costs nothing and is taken off."""
        return max(1.0, self.history.cost(t) - self.prefix.get(t, 0.0))

    def runnable(self, t: str) -> bool:
        """Whether running ``t`` can tell anything: it passes on the original app, and the replay has not already
        given its outcome on the changed copy. A test the model already fails on the original app fails on the
        changed copy too, whatever the change, so no strategy runs it. Nor is a test the recording has no valid
        run of on this copy."""
        return t not in self.replayed and t not in self.missing and self.history.baseline_pass_rate(t) >= 0.5


@dataclass
class ExecutionLog:
    """What a strategy did on one changed copy: the tests it ran, in order, with outcome and cost, why it stopped,
    and the adaptive method's final probability that something is broken."""

    strategy: str
    steps: list[tuple[str, bool, float]] = field(default_factory=list)  # (test_id, passed, cost)
    # regression (a test failed: the run ends there) | exhausted (every test of its order ran and passed) |
    # budget (the budget kept a test out) | clean | uninformative | no_components (the adaptive method's own)
    stop_reason: str = "budget"
    p_broken: float | None = None  # the adaptive method's final P(the change broke something)
    # ... and the same probability before each test it ran, in order: what its clean verdict compares with a
    # threshold, and what a threshold is set on (``experiment/stopping.py``)
    trace: list[float] = field(default_factory=list)
    # the adaptive method's final P(this component is broken), per changed component, most likely first: for a
    # batch of changes, which of them the outcomes point at
    blame: list[tuple[str, float]] = field(default_factory=list)

    @property
    def cost(self) -> float:
        """Tokens spent on the tests run."""
        return sum(c for _, _, c in self.steps)

    @property
    def executed(self) -> list[str]:
        """The tests run, in order."""
        return [t for t, _, _ in self.steps]


# ---------------------------------------------------------------------------- dependency matching
def _module_prefix(cid: str) -> str | None:
    """For a module-level code change (``code:<file>``), the prefix of the code dependencies it touches; None
    for any other component. A module's own level runs at import, before any test, so no test has its lines:
    the change touches the tests that ran a function of the file. A package's ``__init__.py`` runs before every
    module of the package (it is where the tool modules are imported, and so registered): a change there touches
    the tests that ran any code under the package."""
    if not cid.startswith("code:") or "::" in cid or "#" in cid:
        return None
    if cid.removeprefix("code:").rsplit("/", 1)[-1] == "__init__.py":
        return cid[: -len("__init__.py")]  # code:tools/__init__.py -> code:tools/
    return cid + "::"


def matches(component: ChangedComponent, deps: set[str]) -> bool:
    """Does a changed component touch a test whose (declared or observed) dependencies are ``deps``?"""
    # Dependencies are recorded at the coarser level (skill:x, agent:x), so a change to skill:x#procedure or
    # agent:x.tools touches every test that used skill x or ran agent x. A tool's schema is the one sub-part
    # recorded as such: tool:x#schema for every test in which an agent was offered x, tool:x for those that
    # called it.
    cid, base = component.id, component.base
    if cid in deps or base in deps:
        return True
    prefix = _module_prefix(cid)
    return prefix is not None and any(d.startswith(prefix) for d in deps)


def affinity(change: ChangeSet, deps: set[str]) -> int:
    """Number of changed components touching ``deps``. Line-level hits count once per file, so a long hunk
    does not outweigh a changed skill or config key."""
    n, line_files = 0, set()
    for c in change.components:
        if not matches(c, deps):
            continue
        if c.kind == "line":
            line_files.add(c.file)
        else:
            n += 1
    return n + len(line_files)


def line_hit(change: ChangeSet, deps: set[str]) -> bool:
    """Did the test execute at least one changed line (finest-grained evidence of impact)?"""
    return any(c.kind == "line" and c.id in deps for c in change.components)


def weighted_affinity(change: ChangeSet, dep_freq: dict[str, float]) -> float:
    """Affinity weighted by how often the component was exercised in the test's baseline runs."""
    total = 0.0
    deps = set(dep_freq)
    line_files: dict[str, float] = {}
    for c in change.components:
        if not matches(c, deps):
            continue
        # a changed line counts once per file, at the frequency of the most-run of that file's changed lines
        if c.kind == "line":
            line_files[c.file] = max(line_files.get(c.file, 0.0), dep_freq.get(c.id, 1.0))
            continue
        # the frequency of the dependency that made it match (the same three cases as ``matches``): the
        # component itself, its base, or code of a module (or package) changed at module level
        prefix = _module_prefix(c.id)
        total += max(dep_freq[d] for d in deps if d in (c.id, c.base) or (prefix and d.startswith(prefix)))
    return total + sum(line_files.values())


class Strategy:
    """Base class: subclasses implement ``order``; adaptive ones override ``run`` as well."""

    name = "base"
    stochastic = False  # order depends on ctx.rng (then it is cached per seed, not per variant)

    def order(self, ctx: SelectionContext) -> list[str]:
        """The prioritized test ids for this change; the evaluator runs them greedily within the budget."""
        raise NotImplementedError

    def cached_order(self, ctx: SelectionContext) -> list[str]:
        """The prioritized order depends on the change and the history only (plus the seed for
        stochastic strategies), so it is cached across budgets by the evaluator."""
        cache = ctx.options.get("order_cache")
        if cache is None:
            return self.order(ctx)
        # a stochastic order (random) depends on the seed as well; any other is the same for every seed
        key = (self.name, ctx.change.variant, ctx.options.get("seed") if self.stochastic else None)
        if key not in cache:
            cache[key] = self.order(ctx)
        return list(cache[key])

    def run(self, ctx: SelectionContext, oracle: Oracle) -> ExecutionLog:
        """Default: the order run greedily within the budget, under the two rules of the module docstring. A test
        that does not fit the remaining budget is skipped, not the end of the run."""
        log = ExecutionLog(self.name)
        # rule 1: the tests the model already fails on the original app are left out of the order
        order = [t for t in self.cached_order(ctx) if ctx.runnable(t)]
        remaining, kept_out = ctx.budget, False  # kept_out: the budget, not the order, left a test unrun
        for i, t in enumerate(order):
            if ctx.cost(t) > remaining:
                kept_out = True
                continue
            passed, cost = oracle(t)
            log.steps.append((t, passed, cost))
            remaining -= cost
            # rule 2: the first failure ends the run
            if not passed:
                log.stop_reason = "regression"
                return log
            if remaining <= 0:  # the budget is spent: tests further down the order stay unrun
                kept_out = kept_out or i < len(order) - 1
                break
        # no test failed: either the whole order ran, or the budget cut it short and the run has no verdict
        log.stop_reason = "budget" if kept_out else "exhausted"
        return log
