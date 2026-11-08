"""The proposed method: adaptive Bayesian test selection with budget-aware stopping.

In plain words
  1. Each changed component (a function, a skill procedure, a config key, ...) may or may not be broken.
     We keep a probability for every combination of broken components (2^k, k <= 8).
  2. For every test we estimate how likely it is to FAIL if a given component is broken ("sensitivity").
     Covering a component is weak evidence by itself, so the sensitivity is calibrated from history:
     among the tests that statically looked impacted by earlier changes of the same kind, how many
     actually revealed the change?  It is then tilted up for tests whose own text (name, request,
     expectations) shares vocabulary with the diff, and for tests whose author declared the dependency.
  3. We run the test with the best expected information per token, update the probabilities with the
     outcome (taking the test's baseline flakiness into account), and repeat.  After a test passes, tests
     that behave exactly like it (same agents, tools, fault profile, dataset) count for much less.
  4. We stop when P(something is broken) drops below eps_clean ("clean"), when a failure has pushed it
     above 1 - eps_detect ("regression"), or when the budget is spent.  A failure that does not push it
     that far is confirmed first: the same test runs once more before any other.  Flakiness rarely fails
     a test twice in a row; a broken component does.  Without this, the passes that follow a real failure
     wear the evidence down and the method runs on to the end of its budget.
"""

import math
from dataclasses import replace
from itertools import product

import numpy as np

from .base import ExecutionLog, SelectionContext, Strategy, matches
from .strategies import CostAware, change_text, register, tokens

# prior probability that a changed component of this kind is broken
PRIOR = {
    "code": 0.5,
    "tool": 0.5,
    "skill": 0.5,
    "config": 0.45,
    "agent": 0.45,
    "agent-prompt": 0.15,
    "skill-prose": 0.12,
    "fixture": 0.3,
    "other": 0.3,
}
# fallback reveal ratios when no history is available to calibrate from
DEFAULT_REVEAL = {
    "code:line": 0.12,
    "code:fn": 0.03,
    "skill": 0.30,
    "agent": 0.30,
    "config": 0.12,
    "agent-prompt": 0.05,
    "skill-prose": 0.05,
    "fixture": 0.3,
    "other": 0.2,
}


def _kind_key(comp) -> str:
    """Calibration bucket of a component: agent fields are calibrated separately (triggers vs tools...)."""
    if comp.kind == "agent" and "." in comp.id:
        return "agent." + comp.id.split(".", 1)[1]
    return comp.kind


@register
class AdaptiveBayes(Strategy):
    name = "adaptive_bayes"

    def __init__(
        self, eps_clean=0.05, eps_detect=0.02, max_components=8, indirect=0.02, risk_tilt=0.25, duplicate_discount=0.35
    ):
        self.eps_clean, self.eps_detect = eps_clean, eps_detect  # stopping thresholds (step 4)
        self.max_components = max_components  # 2^k hypotheses, so k stays small
        self.indirect = indirect  # sensitivity of a test with no known link to the component
        self.risk_tilt = risk_tilt  # how much a riskier test is preferred
        self.duplicate_discount = duplicate_discount  # factor on a near-duplicate's sensitivity after a pass

    # ------------------------------------------------------------------ step 1: hypotheses
    def components(self, ctx):
        """The changed components we reason about, with their prior. tool: and line: ids are other views of a
        code change (its adapter, its lines), not separate causes; line hits come back in the sensitivities."""
        comps, seen = [], set()
        for c in ctx.change.components:
            if c.kind in ("tool", "line") or c.id in seen:
                continue
            seen.add(c.id)
            comps.append((c, PRIOR.get(c.kind, 0.3)))
        comps.sort(key=lambda cp: -cp[1])  # with too many components, keep the likeliest culprits
        return comps[: self.max_components]

    # ------------------------------------------------------------------ step 2: sensitivities
    @staticmethod
    def impacted(ctx, change, comp) -> dict[str, set[str]]:
        """Tests that statically look impacted by ``comp``: executed a changed line / the function / match."""
        out = {"line": set(), "fn": set(), "match": set()}
        lines = [c for c in change.components if c.kind == "line" and c.file == comp.file]
        for t in ctx.tests():
            deps = ctx.history.deps(t)
            if comp.kind == "code":
                if any(c.id in deps for c in lines):
                    out["line"].add(t)
                elif matches(comp, deps):
                    out["fn"].add(t)
            elif matches(comp, deps):
                out["match"].add(t)
        return out

    def calibrate(self, ctx) -> dict[str, float]:
        """Reveal ratio per component kind, measured on the training changes (never on the one under test):
        |revealing tests among impacted tests| / |impacted tests|.  "Coverage does not imply detection"."""
        sums: dict[str, list[float]] = {}
        for v in ctx.train_variants:
            change = ctx.history.changesets.get(v)
            if change is None:
                continue
            revealing = ctx.history.revealing_tests(v)
            for comp in change.components:
                if comp.kind in ("line", "tool"):
                    continue
                imp = self.impacted(ctx, change, comp)
                if comp.kind == "code":
                    # two buckets: running a changed line is much stronger evidence than calling the function
                    for sub in ("line", "fn"):
                        if imp[sub]:
                            sums.setdefault(f"code:{sub}", []).append(len(revealing & imp[sub]) / len(imp[sub]))
                elif imp["match"]:
                    sums.setdefault(_kind_key(comp), []).append(len(revealing & imp["match"]) / len(imp["match"]))
        ratios = dict(DEFAULT_REVEAL)
        for k, vals in sums.items():
            ratios[k] = max(0.01, min(0.9, sum(vals) / len(vals)))  # mean over changes, kept off 0 and 1
        return ratios

    @staticmethod
    def lexical_relevance(ctx) -> dict[str, float]:
        """Per test, how much vocabulary it shares with the change text (0..1, the closest test gets 1)."""
        # the change's words: its changed code lines, its component ids without the kind prefix, its diff
        qt = set(
            tokens(
                " ".join(c.detail for c in ctx.change.components if c.kind == "line")
                + " "
                + " ".join(c.id.split(":", 1)[1] for c in ctx.change.components)
                + " "
                + change_text(ctx.change)
            )
        )
        rel = {}
        for t in ctx.tests():
            tt = set(tokens(ctx.catalog[t].text()))
            rel[t] = len(qt & tt) / math.sqrt(max(1, len(qt)) * max(1, len(tt)))  # cosine of the two word sets
        mx = max(rel.values()) or 1.0
        return {t: v / mx for t, v in rel.items()}

    def sensitivity(self, ctx, t, comp, lex, ratios) -> float:
        """P(test t fails | component comp is broken)."""
        freq = ctx.history.baseline[t].dep_frequency
        deps = set(freq)
        declared = matches(comp, ctx.catalog[t].declared_components())
        tilt = 0.5 + lex + (0.5 if declared else 0.0)  # lexical relevance [0.5, 1.5] + declared bonus
        # base = calibrated reveal ratio x how often the baseline runs exercised the component
        base = None
        if comp.kind == "code":
            hit = [
                freq[c.id] for c in ctx.change.components if c.kind == "line" and c.file == comp.file and c.id in deps
            ]
            if hit:
                base = ratios["code:line"] * max(hit)
            elif matches(comp, deps):
                base = ratios["code:fn"]
        elif matches(comp, deps):
            # an agent field without training data of its own falls back to the ratio of its kind
            ratio = ratios.get(_kind_key(comp), ratios.get(comp.kind, 0.2))
            base = ratio * max(freq[d] for d in deps if d in (comp.id, comp.base))
        if base is not None:
            return min(0.9, max(0.02, base * tilt))
        if declared:  # declared by the test's author but never observed: half the reveal ratio
            return min(0.9, max(0.02, 0.5 * ratios.get("code:line" if comp.kind == "code" else comp.kind, 0.1)))
        return self.indirect

    # ------------------------------------------------------------------ model assembly
    def model(self, ctx) -> dict:
        """Everything the run needs that does not depend on outcomes."""
        comps, tests = self.components(ctx), ctx.tests()
        k = len(comps)
        # one row per combination of broken components; row 0 (all zeros) is "nothing is broken"
        hyps = np.array(list(product([0, 1], repeat=k)), dtype=float) if k else np.zeros((1, 0))
        prior = np.ones(len(hyps))
        for j, (_comp, pi) in enumerate(comps):  # a priori the components break independently
            prior *= np.where(hyps[:, j] > 0, pi, 1 - pi)
        # a test may fail with nothing broken (baseline flakiness); the floor keeps any failure possible
        flaky = np.array([max(0.01, 1.0 - ctx.history.baseline_pass_rate(t)) for t in tests])
        lex, ratios = self.lexical_relevance(ctx), self.calibrate(ctx)
        S = (
            np.array([[self.sensitivity(ctx, t, c, lex[t], ratios) for c, _ in comps] for t in tests])
            if k
            else np.zeros((len(tests), 0))
        )
        # near-duplicate tests: same agents and tools in the first baseline run, same fault profile and dataset
        groups: dict[tuple, list[int]] = {}
        for i, t in enumerate(tests):
            run0 = ctx.history.baseline[t].runs[0]
            sig = (
                tuple(run0.get("agents", [])),
                tuple(sorted(set(run0.get("tools", [])))),
                ctx.catalog[t].fault_profile,
                ctx.catalog[t].dataset,
            )
            groups.setdefault(sig, []).append(i)
        return {
            "comps": comps,
            "tests": tests,
            "hyps": hyps,
            "prior": prior,
            "flaky": flaky,
            "S": S,
            "groups": groups,
            "group_of": {i: g for g, members in groups.items() for i in members},
            "cost": np.array([ctx.cost(t) for t in tests]),
            "risk": np.array([1.0 + self.risk_tilt * (ctx.catalog[t].severity - 1.0) for t in tests]),
        }

    # ------------------------------------------------------------------ inference helpers
    @staticmethod
    def p_fail_matrix(S, flaky, hyps):
        """P(test fails | hypothesis) for every test x hypothesis: 1 - (1-flaky) * prod_{broken c} (1 - S_tc).
        A test passes only if neither flakiness nor any of the broken components makes it fail."""
        return 1.0 - (1.0 - flaky)[:, None] * np.exp(np.log1p(-np.clip(S, 0, 0.999)) @ hyps.T)

    @staticmethod
    def _entropy(P):
        with np.errstate(divide="ignore", invalid="ignore"):
            return -np.where(P > 1e-12, P * np.log(P), 0.0).sum(axis=-1)

    def info_gain(self, post, p_fail):
        """Expected reduction of posterior entropy for every test, over its two possible outcomes."""
        pf = np.clip(p_fail @ post, 1e-12, 1 - 1e-12)  # P(test fails) under the current posterior
        post_if_fail = (p_fail * post[None, :]) / pf[:, None]
        post_if_pass = ((1 - p_fail) * post[None, :]) / (1 - pf)[:, None]
        gain = self._entropy(post) - (pf * self._entropy(post_if_fail) + (1 - pf) * self._entropy(post_if_pass))
        return np.maximum(gain, 0.0)

    # ------------------------------------------------------------------ steps 3 and 4: run and stop
    def run(self, ctx: SelectionContext, oracle, stopping: bool = True) -> ExecutionLog:
        """Run tests one by one through ``oracle``. ``stopping=False`` (used by ``order``) disables both the
        early stops and the confirmation re-run."""
        log = ExecutionLog(self.name)
        m = self.model(ctx)
        tests, hyps, cost, risk, flaky = m["tests"], m["hyps"], m["cost"], m["risk"], m["flaky"]
        if hyps.shape[1] == 0:  # no component to reason about
            log.stop_reason = "no_components"
            return log
        S = m["S"]
        p_fail = self.p_fail_matrix(S, flaky, hyps)
        post = m["prior"]
        runs_left = np.where(flaky > 0.1, 2, 1)  # flaky tests may be re-run once
        remaining = ctx.budget
        seen_failure = False
        confirm, confirmed = None, set()  # a failed test to re-run before any other; tests already re-run
        while True:
            p_any = 1.0 - post[0]  # hypothesis 0 = nothing broken
            if stopping and p_any < self.eps_clean:
                log.stop_reason = "clean"
                break
            if stopping and seen_failure and p_any > 1.0 - self.eps_detect:
                log.stop_reason = "regression"
                break
            if confirm is not None and cost[confirm] <= remaining:
                i = confirm
            else:
                # best information per token, weighted by risk; tests that cannot or need not run are ruled out
                gain = self.info_gain(post, p_fail)
                score = gain * risk / cost
                score[(runs_left <= 0) | (cost > remaining) | (gain <= 1e-9)] = -1.0
                i = int(np.argmax(score))
                if score[i] <= 0:
                    log.stop_reason = "budget" if remaining < cost.min() else "uninformative"
                    break
            confirm = None
            passed, spent = oracle(tests[i])
            runs_left[i] -= 1
            remaining -= spent
            seen_failure = seen_failure or not passed
            if stopping and not passed and i not in confirmed:
                confirm = i
                confirmed.add(i)
            log.steps.append((tests[i], passed, spent))
            # Bayes' rule: weigh every hypothesis by the likelihood of the observed outcome
            post = post * ((1 - p_fail[i]) if passed else p_fail[i])
            post /= post.sum() or 1e-12
            if passed:  # near-duplicates of a passed test are correlated evidence: discount them
                for j in m["groups"][m["group_of"][i]]:
                    if j != i and runs_left[j] > 0:
                        S[j] *= self.duplicate_discount
                        p_fail[j] = self.p_fail_matrix(S[j][None, :], flaky[j : j + 1], hyps)[0]
            if remaining <= 0:
                log.stop_reason = "budget"
                break
        return log

    def order(self, ctx):
        """Non-adaptive view for APFD metrics: the greedy order assuming every test passes, no stopping,
        followed by the untouched tests in cost-aware order."""
        unlimited = replace(ctx, budget=float("inf"))
        executed = self.run(unlimited, lambda t: (True, ctx.cost(t)), stopping=False).executed
        seen = set(executed)
        return executed + [t for t in CostAware().order(ctx) if t not in seen]
