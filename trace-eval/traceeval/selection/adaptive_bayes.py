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
     above 1 - eps_detect ("regression"), or when the budget is spent.
"""

import math
from itertools import product

import numpy as np

from .base import ExecutionLog, SelectionContext, Strategy, matches
from .strategies import STRATEGIES, CostAware, change_text, tokens

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
PRIOR_NONSEMANTIC = 0.02  # comment/whitespace-only edits
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


class AdaptiveBayes(Strategy):
    name = "adaptive_bayes"
    adaptive = True

    def __init__(
        self, eps_clean=0.05, eps_detect=0.02, max_components=8, indirect=0.02, risk_tilt=0.25, duplicate_discount=0.35
    ):
        self.eps_clean, self.eps_detect = eps_clean, eps_detect
        self.max_components, self.indirect = max_components, indirect
        self.risk_tilt, self.duplicate_discount = risk_tilt, duplicate_discount

    # ------------------------------------------------------------------ step 1: hypotheses
    def components(self, ctx):
        """The changed components we reason about, with their prior (tool:/line: ids are facets of code)."""
        comps, seen = [], set()
        for c in ctx.change.components:
            if c.kind in ("tool", "line") or c.id in seen:
                continue
            seen.add(c.id)
            comps.append((c, PRIOR.get(c.kind, 0.3) if c.semantic else PRIOR_NONSEMANTIC))
        comps.sort(key=lambda cp: -cp[1])
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
        cache = ctx.options.setdefault("bayes_calibration", {})
        key = tuple(sorted(ctx.train_variants))
        if key in cache:
            return cache[key]
        impacted_cache = ctx.options.setdefault("impacted_cache", {})
        sums: dict[str, list[float]] = {}
        for v in ctx.train_variants:
            change = ctx.history.changesets.get(v)
            if change is None:
                continue
            revealing = ctx.history.revealing_tests(v)
            for comp in change.components:
                if comp.kind in ("line", "tool") or not comp.semantic:
                    continue
                if (v, comp.id) not in impacted_cache:
                    impacted_cache[(v, comp.id)] = self.impacted(ctx, change, comp)
                imp = impacted_cache[(v, comp.id)]
                if comp.kind == "code":
                    for sub in ("line", "fn"):
                        if imp[sub]:
                            sums.setdefault(f"code:{sub}", []).append(len(revealing & imp[sub]) / len(imp[sub]))
                elif imp["match"]:
                    sums.setdefault(_kind_key(comp), []).append(len(revealing & imp["match"]) / len(imp["match"]))
        ratios = dict(DEFAULT_REVEAL)
        for k, vals in sums.items():
            ratios[k] = max(0.01, min(0.9, sum(vals) / len(vals)))
        cache[key] = ratios
        return ratios

    @staticmethod
    def lexical_relevance(ctx) -> dict[str, float]:
        """Per test, how much vocabulary it shares with the change text (0..1, cached per change)."""
        cache = ctx.options.setdefault("lexical_relevance", {})
        if ctx.change.variant not in cache:
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
                rel[t] = len(qt & tt) / math.sqrt(max(1, len(qt)) * max(1, len(tt)))
            mx = max(rel.values()) or 1.0
            cache[ctx.change.variant] = {t: v / mx for t, v in rel.items()}
        return cache[ctx.change.variant]

    def sensitivity(self, ctx, t, comp, lex, ratios) -> float:
        """P(test t fails | component comp is broken)."""
        freq = ctx.history.baseline[t].dep_frequency()
        deps = set(freq)
        declared = matches(comp, ctx.catalog[t].declared_components())
        tilt = 0.5 + lex + (0.5 if declared else 0.0)  # lexical relevance [0.5, 1.5] + declared bonus
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
            hits = [freq[d] for d in deps if d == comp.id or d == comp.base]
            base = ratios.get(_kind_key(comp) if _kind_key(comp) in ratios else comp.kind, 0.2) * (
                max(hits) if hits else 1.0
            )
        if base is not None:
            return min(0.9, max(0.02, base * tilt))
        if declared:
            return min(0.9, max(0.02, 0.5 * ratios.get("code:line" if comp.kind == "code" else comp.kind, 0.1)))
        return self.indirect

    # ------------------------------------------------------------------ model assembly (cached per change)
    def model(self, ctx) -> dict:
        cache = ctx.options.setdefault("bayes_models", {})
        key = (ctx.change.variant, self.max_components, self.indirect)
        if key in cache:
            return cache[key]
        comps, tests = self.components(ctx), ctx.tests()
        k = len(comps)
        hyps = np.array(list(product([0, 1], repeat=k)), dtype=float) if k else np.zeros((1, 0))
        prior = np.ones(len(hyps))
        for j, (_comp, pi) in enumerate(comps):
            prior *= np.where(hyps[:, j] > 0, pi, 1 - pi)
        flaky = np.array([max(0.01, 1.0 - ctx.history.baseline_pass_rate(t)) for t in tests])
        lex, ratios = self.lexical_relevance(ctx), self.calibrate(ctx)
        S = (
            np.array([[self.sensitivity(ctx, t, c, lex[t], ratios) for c, _ in comps] for t in tests])
            if k
            else np.zeros((len(tests), 0))
        )
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
        model = {
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
        cache[key] = model
        return model

    # ------------------------------------------------------------------ inference helpers
    @staticmethod
    def p_fail_matrix(S, flaky, hyps):
        """P(test fails | hypothesis) for every test x hypothesis: 1 - (1-flaky) * prod_{broken c} (1 - S_tc)."""
        return 1.0 - (1.0 - flaky)[:, None] * np.exp(np.log1p(-np.clip(S, 0, 0.999)) @ hyps.T)

    @staticmethod
    def _entropy(P):
        with np.errstate(divide="ignore", invalid="ignore"):
            return -np.where(P > 1e-12, P * np.log(P), 0.0).sum(axis=-1)

    def info_gain(self, post, p_fail):
        """Expected reduction of posterior entropy for every test, and its failure probability."""
        pf = np.clip(p_fail @ post, 1e-12, 1 - 1e-12)
        post_if_fail = (p_fail * post[None, :]) / pf[:, None]
        post_if_pass = ((1 - p_fail) * post[None, :]) / (1 - pf)[:, None]
        gain = self._entropy(post) - (pf * self._entropy(post_if_fail) + (1 - pf) * self._entropy(post_if_pass))
        return np.maximum(gain, 0.0), pf

    # ------------------------------------------------------------------ steps 3 and 4: run and stop
    def run(self, ctx: SelectionContext, oracle, stopping: bool = True) -> ExecutionLog:
        log = ExecutionLog(self.name)
        m = self.model(ctx)
        tests, hyps, cost, risk, flaky = m["tests"], m["hyps"], m["cost"], m["risk"], m["flaky"]
        if hyps.shape[1] == 0:
            log.stop_reason = "no_components"
            return log
        S = m["S"].copy()
        p_fail = self.p_fail_matrix(S, flaky, hyps)
        post = m["prior"].copy()
        runs_left = np.where(flaky > 0.1, 2, 1)  # flaky tests may be re-run once
        remaining = ctx.budget
        seen_failure = False
        trajectory = []
        while True:
            p_any = 1.0 - post[0]  # hypothesis 0 = nothing broken
            if stopping and p_any < self.eps_clean:
                log.stop_reason = "clean"
                break
            if stopping and seen_failure and p_any > 1.0 - self.eps_detect:
                log.stop_reason = "regression"
                break
            gain, _ = self.info_gain(post, p_fail)
            score = gain * risk / cost
            score[(runs_left <= 0) | (cost > remaining) | (gain <= 1e-9)] = -1.0
            i = int(np.argmax(score))
            if score[i] <= 0:
                log.stop_reason = "budget" if remaining < cost.min() else "uninformative"
                break
            passed, spent = oracle(tests[i])
            runs_left[i] -= 1
            remaining -= spent
            seen_failure = seen_failure or not passed
            log.steps.append((tests[i], passed, spent))
            post = post * ((1 - p_fail[i]) if passed else p_fail[i])
            post /= post.sum() or 1e-12
            if passed:  # near-duplicates of a passed test are correlated evidence: discount them
                for j in m["groups"][m["group_of"][i]]:
                    if j != i and runs_left[j] > 0:
                        S[j] *= self.duplicate_discount
                        p_fail[j] = self.p_fail_matrix(S[j][None, :], flaky[j : j + 1], hyps)[0]
            trajectory.append((tests[i], passed, round(float(1.0 - post[0]), 4)))
            if remaining <= 0:
                log.stop_reason = "budget"
                break
        log.diagnostics = {
            "p_any_final": float(1.0 - post[0]),
            "trajectory": trajectory[:60],
            "components": [c.id for c, _ in m["comps"]],
        }
        return log

    def order(self, ctx):
        """Non-adaptive view for APFD metrics: the greedy order assuming every test passes, no stopping,
        followed by the untouched tests in cost-aware order."""
        big = SelectionContext(
            ctx.change, ctx.catalog, ctx.history, float("inf"), ctx.rng, ctx.train_variants, options=ctx.options
        )
        executed = self.run(big, lambda t: (True, ctx.cost(t)), stopping=False).executed
        seen = set(executed)
        return executed + [t for t in CostAware().order(ctx) if t not in seen]


STRATEGIES["adaptive_bayes"] = AdaptiveBayes()
