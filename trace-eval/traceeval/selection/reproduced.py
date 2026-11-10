"""Two published methods reproduced as baselines; ``docs/related_work.md`` ranks them the closest competitors.

    casper_slices   CASPER (Muse, Briand, Lu, Gallaba, arXiv 2608.00378): cut the suite into slices of tests that
                    behave alike on the original app, run a few representatives of every slice on the changed app,
                    and rank the slices by how much their representatives' failure rate moved.
    risk_aware_ts   Risk-Aware Adaptive Evaluation (Maji, Chowdhury, arXiv 2609.38914): a contextual Thompson-sampling
                    bandit that runs, one test at a time, the test whose sampled failure probability times its
                    impact is highest.

Neither looks at the diff: comparing with them isolates what change-awareness adds. Where the testbed differs from
a paper's setting, the class's docstring says how the method was adapted.
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
    centres = [X[int(np.argmin(((X - X.mean(0)) ** 2).sum(1)))]]
    while len(centres) < k:
        nearest = np.min([((X - c) ** 2).sum(1) for c in centres], axis=0)
        centres.append(X[int(np.argmax(nearest))])
    C = np.array(centres)
    for _ in range(iters):
        labels = np.argmin(((X[:, None, :] - C[None, :, :]) ** 2).sum(2), axis=1)
        for j in range(k):
            if (labels == j).any():
                C[j] = X[labels == j].mean(0)
    return labels, C


def sigmoid(z: np.ndarray) -> np.ndarray:
    """The logistic function, with the input clipped so that ``exp`` cannot overflow on an extreme row."""
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


def fit_logistic(X: np.ndarray, y: np.ndarray, l2: float = 1.0, w=None, iters: int = 10) -> np.ndarray:
    """Logistic regression with a ridge penalty, by Newton's method, started from ``w`` when given (a warm start
    converges in a step or two). The penalty keeps the fit finite with few observations or one class."""
    w = np.zeros(X.shape[1]) if w is None else w.copy()
    for _ in range(iters):
        p = sigmoid(X @ w)
        gradient = X.T @ (p - y) + l2 * w
        hessian = (X * (p * (1.0 - p))[:, None]).T @ X + l2 * np.eye(X.shape[1])
        step = np.linalg.solve(hessian, gradient)
        w -= step
        if np.abs(step).max() < 1e-6:
            break
    return w


# ---------------------------------------------------------------------------- CASPER
def signals(stats) -> list[float]:
    """Behavioural signals of one test, averaged over its baseline runs: the shape of the run, not its outcome.
    CASPER's ten signals describe software-issue resolution (files edited, test turns, plan compliance); these are
    their counterparts for an agent that calls tools and hands off to other agents."""
    rows = []
    for r in stats.valid_runs or stats.runs:
        calls = r.get("tools", [])
        counts = Counter(calls)
        n = max(1, len(calls))
        rows.append(
            [
                r.get("steps", 0),  # turns of the run
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
        )
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
       or chosen by furthest-point sampling. Here K = 2: the test nearest the centroid, then the one farthest from
       it. Cheaper slices go first, so that a small budget samples many slices.
    4. Ranking. CASPER scores a slice by how much a model trained on V0 signals changes its predicted success from V0
       to V1, and labels the slice regressed, improved or unchanged by the change of its failure rate. The replay
       oracle returns the outcome and the cost of a run, not its trace, so the score here is the change of the
       representatives' failure rate itself (V1 minus baseline). Regressed slices run first, then improved, then
       unchanged, each nearest the centroid first, until the budget is spent. CASPER has no stopping rule.
    It never looks at the diff.
    """

    name = "casper_slices"

    def __init__(self, slice_size=8, min_size=4, outcome_weight=3.0, representatives=2):
        self.slice_size = slice_size  # tests per slice, on average
        self.min_size = min_size  # a smaller slice is merged into its nearest neighbour
        self.outcome_weight = outcome_weight  # weight of the baseline outcome against one standardised signal
        self.representatives = representatives  # K: tests of a slice run before the slices are ranked

    def slices(self, ctx) -> list[tuple[list[str], list[str]]]:
        """The slices of the suite: (members nearest the centroid first, representatives). They depend on the
        baseline recording only."""
        tests = ctx.tests()
        Z = standardised(np.array([signals(ctx.history.baseline[t]) for t in tests]))
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
        out = []
        for j in range(len(C)):
            members = sorted(np.flatnonzero(labels == j), key=lambda i: float(((Z[i] - C[j]) ** 2).sum()))
            if not members:
                continue
            reps = [members[0]]  # nearest the centroid, then furthest-point sampling
            while len(reps) < min(self.representatives, len(members)):
                reps.append(max(members, key=lambda i: min(float(((Z[i] - Z[r]) ** 2).sum()) for r in reps)))
            out.append(([tests[i] for i in members], [tests[i] for i in reps]))
        return out

    def run(self, ctx, oracle) -> ExecutionLog:
        log = ExecutionLog(self.name)
        remaining, ran = ctx.budget, {}  # test -> passed, for the tests run so far

        def attempt(t):
            """Run ``t`` if it fits the budget (a test that does not fit is skipped, as in the greedy baselines)."""
            nonlocal remaining
            if t in ran or ctx.cost(t) > remaining:
                return
            passed, spent = oracle(t)
            ran[t] = passed
            remaining -= spent
            log.steps.append((t, passed, spent))

        slices = self.slices(ctx)
        for _members, reps in sorted(slices, key=lambda s: sum(ctx.cost(t) for t in s[1])):  # step 3
            for t in reps:
                attempt(t)
        # step 4: the shift of each slice's failure rate, from the representatives that ran
        shift = []
        for _members, reps in slices:
            seen = [t for t in reps if t in ran]
            v1 = sum(1 for t in seen if not ran[t]) / len(seen) if seen else 0.0
            v0 = sum(1.0 - ctx.history.baseline_pass_rate(t) for t in seen) / len(seen) if seen else 0.0
            shift.append(v1 - v0)
        # regressed slices (shift > 0) first, by the size of the shift; then improved; then unchanged
        ranked = sorted(
            range(len(slices)), key=lambda j: (0 if shift[j] > 0 else 1 if shift[j] < 0 else 2, -abs(shift[j]))
        )
        for j in ranked:
            for t in slices[j][0]:
                attempt(t)
        log.stop_reason = "exhausted" if remaining > 0 else "budget"
        return log

    def order(self, ctx):
        """Non-adaptive view for the prioritization metrics: the order of a run in which every test passes."""
        return self.run(replace(ctx, budget=float("inf")), lambda t: (True, ctx.cost(t))).executed


# ---------------------------------------------------------------------------- Risk-Aware Adaptive Evaluation
def context(case, stats) -> list[float]:
    """What is known about a test before it runs on the changed app: its definition and the shape of its baseline
    runs. The paper's context vector describes a scenario's definition the same way (actions, constraints,
    expected horizon)."""
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
    - the reward is any failure, as in the paper: a test the model already fails on the original app counts as a
      find, which the proposed method is built to avoid;
    - the budget is in tokens, so the run ends when no unrun test fits, and each test runs at most once, like every
      strategy here, because the models decode greedily and a rerun would repeat the answer (the paper reruns its
      stochastic scenarios up to their recorded trials);
    - no stopping rule and no verdict, as in the paper.
    ``order``, for the prioritization metrics, is the paper's static risk-aware ranking: by impact, cheapest first.
    It never looks at the diff.
    """

    name = "risk_aware_ts"

    def __init__(self, context_weight=2.0, l2=1.0):
        self.context_weight = context_weight  # lambda: the pooled model's weight against a test's own outcomes
        self.l2 = l2  # ridge penalty of the logistic regression: few observations, several features

    def run(self, ctx, oracle) -> ExecutionLog:
        log = ExecutionLog(self.name)
        tests = ctx.tests()
        X = standardised(np.array([context(ctx.catalog[t], ctx.history.baseline[t]) for t in tests]))
        X = np.hstack([np.ones((len(tests), 1)), X])  # with an intercept
        impact = np.array([ctx.catalog[t].severity for t in tests])
        cost = np.array([ctx.cost(t) for t in tests])
        pulls, fails = np.zeros(len(tests)), np.zeros(len(tests))
        draws = np.random.default_rng(ctx.rng.getrandbits(32))  # the posterior draws, seeded by the replay seed
        w, remaining = None, ctx.budget
        while True:
            candidates = np.flatnonzero((pulls == 0) & (cost <= remaining))
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
                theta = draws.beta(a[candidates], b[candidates])
                i = int(candidates[np.argmax(impact[candidates] * theta)])
            passed, spent = oracle(tests[i])
            pulls[i] += 1
            fails[i] += not passed
            remaining -= spent
            log.steps.append((tests[i], passed, spent))
        log.stop_reason = "exhausted" if remaining > 0 else "budget"
        return log

    def order(self, ctx):
        return sorted(ctx.tests(), key=lambda t: (-ctx.catalog[t].severity, ctx.cost(t), t))
