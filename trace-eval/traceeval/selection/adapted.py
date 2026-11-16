"""Two methods from the literature, adapted to this testbed as baselines; ``docs/related_work.md`` ranks them the
closest competitors.

    casper_slices            CASPER (Muse, Briand, Lu, Gallaba, arXiv 2608.00378): cut the suite into slices of
                             tests that behave alike on the original app, run a few representatives of every slice
                             on the changed app, and rank the slices by how much the representatives' behaviour
                             moved.
    risk_aware_ts            Risk-Aware Adaptive Evaluation (Maji, Chowdhury, arXiv 2609.38914): a contextual
                             Thompson-sampling bandit that runs, one test at a time, the test whose sampled failure
                             probability times its impact is highest.
    risk_aware_ts_per_token  the same bandit with its score divided by the test's cost, as a budget in tokens
                             suggests. It runs when named, not in the default comparison: it does worse.

None looks at the diff: comparing with them isolates what change-awareness adds. They are adaptations, not
reproductions: each class's docstring says where the testbed differs from the paper's setting and what was done
about it. Like every strategy they follow the two rules of ``base.py``: a test that fails on the original app is
not run, and the run ends at the first failure.
"""

import math
import statistics
from collections import Counter
from dataclasses import replace

import numpy as np

from .base import ExecutionLog, Strategy
from .strategies import register


# ---------------------------------------------------------------------------- shared helpers
def standardised(M: np.ndarray) -> np.ndarray:
    """Every column centred and scaled to unit variance; a constant column becomes zeros."""
    return (M - M.mean(0)) / (M.std(0) + 1e-9)


def kmeans(X: np.ndarray, k: int, iters: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Plain k-means with a deterministic start: the row nearest the mean, then farthest-point seeding. Returns
    the label of every row and the centres."""
    # seeding: the row nearest the mean, then each time the row farthest from the centres chosen so far
    centres = [X[int(np.argmin(((X - X.mean(0)) ** 2).sum(1)))]]
    while len(centres) < k:
        nearest = np.min([((X - c) ** 2).sum(1) for c in centres], axis=0)
        centres.append(X[int(np.argmax(nearest))])
    C = np.array(centres)
    # Lloyd's iterations: every row to its nearest centre, every centre to the mean of its rows (an empty one stays)
    for _ in range(iters):
        labels = np.argmin(((X[:, None, :] - C[None, :, :]) ** 2).sum(2), axis=1)
        for j in range(k):
            if (labels == j).any():
                C[j] = X[labels == j].mean(0)
    return labels, C


def sigmoid(z: np.ndarray) -> np.ndarray:
    """The logistic function, with the input clipped so that ``exp`` cannot overflow on an extreme row."""
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


def fit_logistic(
    X: np.ndarray, y: np.ndarray, l2: float = 1.0, w=None, iters: int = 10, sample_weight=None, free_intercept=False
) -> np.ndarray:
    """Logistic regression with a ridge penalty, by Newton's method, started from ``w`` when given (a warm start
    converges in a step or two). The penalty keeps the fit finite with few observations or one class.
    ``sample_weight`` weighs the rows (to balance two classes of unequal size, say); with ``free_intercept`` the
    first column, a constant, is left out of the penalty, as the libraries do with their intercept."""
    w = np.zeros(X.shape[1]) if w is None else w.copy()
    s = np.ones(len(y)) if sample_weight is None else np.asarray(sample_weight, dtype=float)
    penalty = l2 * np.ones(X.shape[1])
    if free_intercept:
        penalty[0] = 0.0
    for _ in range(iters):
        # one Newton step on the penalised log-likelihood; done once the step is negligible
        p = sigmoid(X @ w)
        gradient = X.T @ (s * (p - y)) + penalty * w
        hessian = (X * (s * p * (1.0 - p))[:, None]).T @ X + np.diag(penalty)
        step = np.linalg.solve(hessian, gradient)
        w -= step
        if np.abs(step).max() < 1e-6:
            break
    return w


# ---------------------------------------------------------------------------- CASPER
def run_signals(r: dict) -> list[float]:
    """Behavioural signals of one recorded run: the shape of the run, not its outcome. CASPER's ten signals
    describe software-issue resolution (files edited, test turns, plan compliance); these are their counterparts
    for an agent that calls tools and hands off to other agents."""
    calls = r.get("tools", [])
    counts = Counter(calls)
    n = max(1, len(calls))
    return [
        r.get("steps") or 0,  # turns of the run
        len(calls),  # tool calls
        len(counts),  # distinct tools
        max(counts.values(), default=0) / n,  # share of the most-called tool (CASPER's dominant-file ratio)
        -sum(c / n * math.log(c / n) for c in counts.values()),  # entropy of the calls (its trajectory entropy)
        len(r.get("agents", [])) - 1,  # hand-offs between agents
        len(r.get("skills", [])),  # skills loaded
        len(r.get("config_keys", [])),  # settings read
        math.log1p(r.get("tokens", 0)),  # size of the run
        r.get("completion_tokens", 0) / max(1, r.get("tokens", 1)),  # share the model wrote, not read
    ]


def signals(stats) -> list[float]:
    """The signals of one test on the original app: those of its baseline runs, averaged. Runs the environment
    broke are left out as long as a valid run exists."""
    rows = [run_signals(r) for r in (stats.valid_runs or stats.runs)]
    return [statistics.fmean(col) for col in zip(*rows, strict=True)]


@register
class CasperSlices(Strategy):
    """CASPER on this testbed.

    1. Signals. CASPER mines ten behavioural signals from the agent's logs on the original app (V0) and
       standardises them. ``signals`` computes their counterparts from the baseline traces here.
    2. Slices. CASPER searches the slices with a genetic algorithm (NSGA-II) that trades coherence in signal space
       against consistency of the outcome, with slices of 5 to about 18 instances. Here: k-means on the standardised
       signals, with the baseline outcome as an extra, heavier column, so that the tests the model already fails tend
       to fall in slices of their own; the number of slices follows from the target slice size, and a slice
       smaller than the minimum joins the slice whose centre is nearest.
    3. Representatives. CASPER runs K instances of every slice on the changed app (V1), the nearest to the centroid
       or chosen by furthest-point sampling. Here K = 2, among the slice's tests that pass on V0 (no strategy runs
       the others): the one nearest the centroid, then the one farthest from it. Cheaper slices go first, so that a
       small budget samples many slices.
    4. Ranking. CASPER scores a slice by how much a model trained on V0 signals changes its predicted success from
       V0 to V1. Here the model is a logistic regression of the baseline outcome on the ten signals, and a slice's
       score is the mean rise of the predicted failure probability of its representatives, from their signals on V0
       to those of the run just made on V1 (``oracle.records``). The slices then run in the order of their score,
       each nearest the centroid first, until the budget is spent. CASPER also labels a slice by the change of its
       failure rate; here a failure ends the run, so when the slices are ranked every representative has passed.
    It never looks at the diff.
    """

    name = "casper_slices"

    def __init__(self, slice_size=8, min_size=4, outcome_weight=3.0, representatives=2):
        """The settings of steps 2 and 3 of the class docstring, each explained beside its field."""
        self.slice_size = slice_size  # tests per slice, on average
        self.min_size = min_size  # a smaller slice is merged into its nearest neighbour
        self.outcome_weight = outcome_weight  # weight of the baseline outcome against one standardised signal
        self.representatives = representatives  # K: tests of a slice run before the slices are ranked

    def slices(self, ctx) -> list[tuple[list[str], list[str]]]:
        """The slices of the suite: (members nearest the centroid first, representatives). They depend on the
        baseline recording only."""
        tests = ctx.tests()
        # step 1: the signal matrix, one row per test, standardised
        Z = standardised(np.array([signals(ctx.history.baseline[t]) for t in tests]))
        # step 2: the baseline pass rate as an extra column, heavier than one signal, then k-means into slices
        outcome = standardised(np.array([[ctx.history.baseline_pass_rate(t)] for t in tests]))
        Z = np.hstack([Z, self.outcome_weight * outcome])
        labels, C = kmeans(Z, max(1, math.ceil(len(tests) / self.slice_size)))
        while True:  # the smallest slice under the minimum joins the slice whose centre is nearest
            sizes = {j: int((labels == j).sum()) for j in range(len(C)) if (labels == j).any()}
            small = min(sizes, key=sizes.get)
            if sizes[small] >= self.min_size or len(sizes) == 1:
                break
            target = min((j for j in sizes if j != small), key=lambda j: float(((C[j] - C[small]) ** 2).sum()))
            labels[labels == small] = target
            C[target] = Z[labels == target].mean(0)
        # step 3: each slice as (members nearest the centroid first, its K representatives)
        out = []
        for j in range(len(C)):
            members = sorted(np.flatnonzero(labels == j), key=lambda i: float(((Z[i] - C[j]) ** 2).sum()))
            if not members:
                continue
            # representatives among the tests that can be run: nearest the centroid, then furthest-point sampling
            able = [i for i in members if ctx.runnable(tests[i])]
            reps = able[:1]
            while len(reps) < min(self.representatives, len(able)):
                reps.append(max(able, key=lambda i: min(float(((Z[i] - Z[r]) ** 2).sum()) for r in reps)))
            out.append(([tests[i] for i in members], [tests[i] for i in reps]))
        return out

    def run(self, ctx, oracle) -> ExecutionLog:
        """Steps 3 and 4 on the changed copy: the representatives of every slice, then whole slices in the order of
        their score. The run ends at the first failure, when the budget is spent or when no test is left."""
        log = ExecutionLog(self.name)
        remaining, ran, kept_out = ctx.budget, set(), False

        def failed(t) -> bool:
            """Run ``t`` if it can be run and fits the budget; True when it failed, which ends the run."""
            nonlocal remaining, kept_out
            if t in ran or not ctx.runnable(t):
                return False
            if ctx.cost(t) > remaining:
                kept_out = True  # the budget, not the order, left it unrun
                return False
            passed, spent = oracle(t)
            ran.add(t)
            remaining -= spent
            log.steps.append((t, passed, spent))
            return not passed

        # step 3: the representatives of every slice, the cheapest slices first
        slices = self.slices(ctx)
        for _members, reps in sorted(slices, key=lambda s: sum(ctx.cost(t) for t in s[1])):
            for t in reps:
                if failed(t):
                    log.stop_reason = "regression"
                    return log

        # step 4, the model: a logistic regression of "the test fails on the original app" on the ten signals,
        # standardised with the suite's own mean and spread
        tests = ctx.tests()
        raw = np.array([signals(ctx.history.baseline[t]) for t in tests])
        mean, spread = raw.mean(0), raw.std(0) + 1e-9
        fails = np.array([float(not ctx.runnable(t)) for t in tests])
        weights = fit_logistic(np.hstack([np.ones((len(tests), 1)), (raw - mean) / spread]), fails)

        def predicted_failure(run_signal_values) -> float:
            return float(sigmoid(np.r_[1.0, (np.array(run_signal_values) - mean) / spread] @ weights))

        # step 4, the score of a slice: how much the model's prediction rose for its representatives, from their
        # signals on the original app to those of the run just made on the changed copy (kept by the oracle)
        records = getattr(oracle, "records", {})
        score = []
        for _members, reps in slices:
            rise = [
                predicted_failure(run_signals(records[t])) - predicted_failure(signals(ctx.history.baseline[t]))
                for t in reps
                if t in ran and t in records
            ]
            score.append(statistics.fmean(rise) if rise else 0.0)
        # the slices whole, highest score first (equal scores keep the slices' own order), nearest the centroid first
        for j in sorted(range(len(slices)), key=lambda j: -score[j]):
            for t in slices[j][0]:
                if failed(t):
                    log.stop_reason = "regression"
                    return log
        log.stop_reason = "budget" if kept_out else "exhausted"
        return log

    def order(self, ctx):
        """Non-adaptive view for the prioritization metrics: the order of a run in which every test passes."""
        return self.run(replace(ctx, budget=float("inf")), lambda t: (True, ctx.cost(t))).executed


# ---------------------------------------------------------------------------- Risk-Aware Adaptive Evaluation
def context(case, stats) -> list[float]:
    """What is known about a test before it runs on the changed app: its definition and the shape of its baseline
    runs. The paper's context vector describes a scenario's definition the same way (actions, constraints,
    expected horizon)."""
    # the shape of the test's first valid baseline run
    run0 = (stats.valid_runs or stats.runs)[0]
    return [
        case.severity,  # the risk level
        float(case.fault_profile != "healthy"),  # a fault is injected
        float(case.dataset is not None),  # a dataset item: one prompt, one expected answer
        float(case.workflow is not None),  # a multi-agent workflow run end to end
        float(case.is_safety),  # checks a safety property
        math.log1p(len(case.declared_components())),  # how much the author declared
        len(run0.get("agents", [])) - 1,  # hand-offs (the paper's expected horizon)
        len(run0.get("tools", [])),  # tool calls
        math.log1p(stats.mean_tokens),  # cost
    ]


@register
class RiskAwareTS(Strategy):
    """Risk-Aware Adaptive Evaluation on this testbed.

    The paper allocates a budget of trials over tau-bench airline scenarios. A scenario's context is a vector of
    features of its definition, its impact a fixed score from 1 (read-only) to 5 (an irreversible action), and the
    reward of a trial is impact x failure. Each round, a logistic regression fitted on every outcome so far gives a
    failure probability to every scenario, pulled or not; a Beta posterior per scenario mixes it, with weight
    lambda, with the scenario's own outcomes; one draw from each posterior, times the impact, picks the next
    scenario (Thompson sampling). Here:
    - the scenarios are the tests, the context comes from the case and the shape of its baseline runs
      (``context``), and the impact is the case's risk weight (critical 4 ... low 1);
    - the paper's bandit collects failures over a budget of trials; here, as for every strategy, the question is
      whether the change broke anything, so the run ends at the first failure and what it learns from is the tests
      that passed: the model lowers the failure probability of the tests that resemble them;
    - the budget is in tokens, so the run ends when no test that can be run fits, and each test runs at most once,
      like every strategy here, because the models decode greedily and a rerun would repeat the answer (the paper
      reruns its stochastic scenarios up to their recorded trials);
    - the choice does not look at a test's cost, as in the paper, where every trial costs one;
      ``risk_aware_ts_per_token`` divides by it.
    ``order``, for the prioritization metrics, is the paper's static risk-aware ranking: by impact, cheapest first.
    It never looks at the diff.
    """

    name = "risk_aware_ts"

    def __init__(self, context_weight=2.0, l2=1.0, per_token=False):
        """lambda, from the paper, the ridge penalty that the few outcomes of one run call for, and whether the
        choice is per token."""
        self.context_weight = context_weight  # lambda: the pooled model's weight against a test's own outcomes
        self.l2 = l2  # ridge penalty of the logistic regression: few observations, several features
        self.per_token = per_token  # divide the draw times the impact by the test's cost

    def run(self, ctx, oracle) -> ExecutionLog:
        """The bandit: each round refits the model of which tests fail, draws a failure probability for every unrun
        test and runs the one whose draw times its impact is highest, until a test fails or none fits the budget."""
        log = ExecutionLog(self.name)
        tests = ctx.tests()
        # the context matrix, one row per test, standardised
        X = standardised(np.array([context(ctx.catalog[t], ctx.history.baseline[t]) for t in tests]))
        X = np.hstack([np.ones((len(tests), 1)), X])  # with an intercept
        # the impact of each test is its risk weight (critical 4 ... low 1)
        impact = np.array([ctx.catalog[t].severity for t in tests])
        cost = np.array([ctx.cost(t) for t in tests])
        able = np.array([ctx.runnable(t) for t in tests])
        # per test: times run (at most once here) and times failed, the test's own outcomes
        pulls, fails = np.zeros(len(tests)), np.zeros(len(tests))
        draws = np.random.default_rng(ctx.rng.getrandbits(32))  # the posterior draws, seeded by the replay seed
        # w: the weights of the pooled logistic model, warm-started from one round to the next
        w, remaining = None, ctx.budget
        while True:
            # the unrun tests that can be run and fit the remaining budget
            candidates = np.flatnonzero((pulls == 0) & able & (cost <= remaining))
            if len(candidates) == 0:
                break
            if not log.steps:  # the first pull is uniform at random, as in the paper
                i = int(candidates[ctx.rng.randrange(len(candidates))])
            else:
                seen = pulls > 0
                w = fit_logistic(X[seen], fails[seen], self.l2, w)  # the population model on the outcomes so far
                p = sigmoid(X @ w)
                a = 1.0 + self.context_weight * p + fails  # Beta(1, 1) prior, the model's guess, the test's outcomes
                b = 1.0 + self.context_weight * (1.0 - p) + pulls - fails
                # Thompson sampling: one draw per candidate; the highest draw x impact runs (per token, if set)
                score = impact[candidates] * draws.beta(a[candidates], b[candidates])
                i = int(candidates[np.argmax(score / cost[candidates] if self.per_token else score)])
            passed, spent = oracle(tests[i])
            pulls[i] += 1
            fails[i] += not passed
            remaining -= spent
            log.steps.append((tests[i], passed, spent))
            if not passed:
                log.stop_reason = "regression"
                return log
        log.stop_reason = "budget" if ((pulls == 0) & able).any() else "exhausted"
        return log

    def order(self, ctx):
        """The paper's static risk-aware ranking: by impact, the cheaper first among equals (per token: by impact
        over cost)."""
        if self.per_token:
            return sorted(ctx.tests(), key=lambda t: (-ctx.catalog[t].severity / ctx.cost(t), t))
        return sorted(ctx.tests(), key=lambda t: (-ctx.catalog[t].severity, ctx.cost(t), t))


@register
class RiskAwareTSPerToken(RiskAwareTS):
    """The bandit with its choice per token: the paper counts trials, each of the same cost, while the tests here
    differ in cost by more than an order of magnitude, and the testbed's own ranking strategies divide by cost.
    It is not in the default comparison (``strategies.CORE``): per token, the cheapest tests come first, and those
    are the dataset items, which seldom reveal a change, so it finds less than the bandit it varies."""

    name = "risk_aware_ts_per_token"

    def __init__(self):
        super().__init__(per_token=True)
