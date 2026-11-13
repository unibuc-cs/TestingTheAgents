"""The proposed method: adaptive Bayesian test selection with budget-aware stopping.

In plain words
  1. Each changed component (a function, a skill procedure, a config key, ...) may or may not be broken.
     We keep a probability for every combination of broken components (2^k, k <= 8).
  2. For every test we estimate how likely it is to FAIL if a given component is broken ("sensitivity").
     Covering a component is weak evidence by itself, so the sensitivity is calibrated from history:
     among the tests that statically looked impacted by earlier changes of the same kind, how many
     actually revealed the change?  A ratio learned from one or two changes stays near a default for its kind,
     so that a single earlier change cannot make a whole kind look certain.  That ratio is then scaled by the
     test's own record on earlier changes of that kind that touched it: the changes it revealed over those an
     average impacted test would have revealed.  Catching a change that broke almost everything says little;
     being the one test that caught a subtle change says a lot.  The sensitivity is finally tilted up for tests
     whose own text (name, request, expectations) shares vocabulary with the diff, and for tests whose author
     declared the dependency.  An agent's tool or skill list that only lost items reaches only the
     tests that used one of them.  How text is compared is an option (``text``): word overlap by default,
     the TF-IDF similarity of the ``ir_tfidf`` strategy, or not at all (the variants registered at the end).
  3. We run the test with the best expected information per token, update the probabilities with the
     outcome, and repeat; each test runs at most once.  A test that already fails on the original app (a
     mistake of the model) tells nothing either way.  After a test passes, tests that behave exactly like it
     (same agents, tools, fault profile, dataset) count for much less.
  4. We stop with "regression" as soon as a test that passed on the original app fails: the models decode
     greedily, so that failure shows a changed behaviour (it is what the ground truth calls revealing).  We
     stop with "clean" when P(something is broken) drops below eps_clean, and otherwise when the budget is
     spent or no test could change the verdict.
  5. A run that found no regression does not end before every mandatory property the change may affect (the
     catalog of properties, ``experiment/coverage.py``) has a test, the cheapest that checks it, while the budget
     allows (``cover_mandatory``; switched off in the ablation ``adaptive_bayes_nomandatory``).
"""

import math
from dataclasses import replace
from itertools import product

import numpy as np

from .base import ExecutionLog, SelectionContext, Strategy, matches
from .strategies import CostAware, change_text, register, tfidf_relevance, tokens

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
# code:line = tests that ran a changed line, code:fn = tests that only called the changed function or module
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


def _reach(comp) -> tuple[str, ...]:
    """The dependency ids through which a non-code component reaches a test: the items an agent's tool or skill
    list lost, when the change set names them ("removed: tool:x"), since only the runs that used one of them can
    notice; otherwise the component itself or its base (agent:x.tools -> agent:x)."""
    if comp.detail.startswith("removed: "):
        return tuple(comp.detail.split()[1:])
    return (comp.id, comp.base)


@register
class AdaptiveBayes(Strategy):
    """The proposed method, in the five steps of the module docstring. The keyword arguments of ``__init__`` are
    its settings; the variants registered at the end of the module change one of them each."""

    name = "adaptive_bayes"

    def __init__(
        self,
        eps_clean=0.05,
        max_components=8,
        indirect=0.02,
        risk_tilt=0.25,
        duplicate_discount=0.35,
        prior_strength=2.0,
        text="overlap",
        cover_mandatory=True,
    ):
        """The settings, each explained beside its field with the step of the module docstring it enters."""
        self.eps_clean = eps_clean  # "clean" below this P(something is broken) (step 4)
        self.max_components = max_components  # 2^k hypotheses, so k stays small
        self.indirect = indirect  # sensitivity of a test with no known link to the component
        self.risk_tilt = risk_tilt  # how much a riskier test is preferred
        self.duplicate_discount = duplicate_discount  # factor on a near-duplicate's sensitivity after a pass
        self.prior_strength = prior_strength  # padding of a test's record (step 2): a short record moves little
        self.text = text  # how a test's text is compared with the change (step 2): "overlap", "tfidf" or "none"
        self.cover_mandatory = cover_mandatory  # test every mandatory property the change may affect (step 5)

    # ------------------------------------------------------------------ step 1: hypotheses
    def components(self, ctx):
        """The changed components we reason about, with their prior. tool: and line: ids are other views of a
        code change (its adapter, its lines), not separate causes; line hits come back in the sensitivities."""
        comps, seen = [], set()
        # one hypothesis per distinct component, with the prior of its kind
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
        # the changed lines of the component's file: running one is the finest observed link to the change
        lines = [c for c in change.components if c.kind == "line" and c.file == comp.file]
        for t in ctx.tests():
            # observed dependencies: everything the test exercised in at least one baseline run
            deps = ctx.history.deps(t)
            # a code component has two buckets: ran a changed line, or only called the changed function or module
            if comp.kind == "code":
                if any(c.id in deps for c in lines):
                    out["line"].add(t)
                elif matches(comp, deps):
                    out["fn"].add(t)
            # any other component: the test used it, or one of the items its list lost
            elif any(d in deps for d in _reach(comp)):
                out["match"].add(t)
        return out

    def calibrate(self, ctx) -> tuple[dict[str, float], dict[tuple[str, str], list[float]]]:
        """Reveal ratios measured on the training changes (never on the one under test), per kind of
        component and per test.  "Coverage does not imply detection".

        Per kind (bucket): |revealing tests among impacted tests| / |impacted tests|, averaged over changes.
        Per test and bucket: [changes it revealed, changes an impacted test would reveal on average], summed over
        the training changes that impacted it through that bucket. The second number is the change's own reveal
        rate, so revealing a change that breaks almost every test it touches adds little to a test's record."""
        # sums: bucket -> the reveal ratio of each training change that impacted tests through it
        sums: dict[str, list[float]] = {}
        # record: (test, bucket) -> [O, E], the two counts of the test's lift (step 2)
        record: dict[tuple[str, str], list[float]] = {}
        # one pass per other recorded change; its revealing tests (the ground truth of that change: majority
        # outcome flipped from pass on the baseline to fail on the changed copy) are what everything is measured on
        for v in ctx.train_variants:
            change = ctx.history.changesets.get(v)
            if change is None:
                continue
            revealing = ctx.history.revealing_tests(v)
            touched: dict[str, set[str]] = {}  # bucket -> tests this change impacted through it
            for comp in change.components:
                if comp.kind in ("line", "tool"):
                    continue
                imp = self.impacted(ctx, change, comp)
                if comp.kind == "code":
                    # two buckets: running a changed line is much stronger evidence than calling the function
                    for sub in ("line", "fn"):
                        if imp[sub]:
                            sums.setdefault(f"code:{sub}", []).append(len(revealing & imp[sub]) / len(imp[sub]))
                            touched.setdefault(f"code:{sub}", set()).update(imp[sub])
                elif imp["match"]:
                    sums.setdefault(_kind_key(comp), []).append(len(revealing & imp["match"]) / len(imp["match"]))
                    touched.setdefault(_kind_key(comp), set()).update(imp["match"])
            for bucket, tests in touched.items():  # once per change, however many of its components hit the test
                rate = len(revealing & tests) / len(tests)  # how often an impacted test revealed this change
                for t in tests:
                    # The test's record on this bucket: [changes it revealed, changes an average impacted test
                    # would have revealed]. A change that broke most of the tests it touched adds nearly 1 to
                    # both numbers, so revealing it is no distinction; a change that only this test caught adds 1
                    # to the first and little to the second, which is what raises the test's lift later.
                    seen = record.setdefault((t, bucket), [0.0, 0.0])
                    seen[0] += t in revealing
                    seen[1] += rate
        # the reveal ratio per bucket (r_kind of the paper); a bucket no training change touched keeps its default
        ratios = dict(DEFAULT_REVEAL)
        for k, vals in sums.items():
            # the mean over changes, padded like the test records: a ratio learned from one or two changes stays
            # near the default of its kind (agent.tools falls back to agent), and it is kept off 0 and 1
            prior = DEFAULT_REVEAL.get(k, DEFAULT_REVEAL.get(k.split(".", 1)[0], 0.2))
            mean = (sum(vals) + self.prior_strength * prior) / (len(vals) + self.prior_strength)
            ratios[k] = max(0.01, min(0.9, mean))
        return ratios, record

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

    def text_relevance(self, ctx) -> dict[str, float]:
        """Per test, 0..1: how close its text is to the change, by the measure ``text`` names. "none" gives every
        test the middle value, so text plays no part (an ablation)."""
        if self.text == "none":
            return {t: 0.5 for t in ctx.tests()}
        if self.text == "tfidf":
            rel = tfidf_relevance(ctx)
            mx = max(rel.values()) or 1.0
            return {t: v / mx for t, v in rel.items()}  # the closest test gets 1, as with word overlap
        return self.lexical_relevance(ctx)

    def sensitivity(self, ctx, t, comp, lex, ratios, record) -> float:
        """P(test t fails | component comp is broken)."""
        # observed dependencies, each with how often the baseline runs exercised it (the coverage factor)
        freq = ctx.history.baseline[t].dep_frequency
        deps = set(freq)
        # the author declared the component (or its base) as a dependency of the test
        declared = matches(comp, ctx.catalog[t].declared_components())
        tilt = 0.5 + lex + (0.5 if declared else 0.0)  # text relevance [0.5, 1.5] + declared bonus

        def own(bucket, ratio):
            """The bucket's reveal ratio times this test's lift on it: the changes it revealed over the changes an
            average impacted test would have revealed, both padded with prior_strength so that a short record
            moves the lift little (a lift of 1 = an average test)."""
            revealed, expected = record.get((t, bucket), (0.0, 0.0))
            return ratio * (revealed + self.prior_strength) / (expected + self.prior_strength)

        # base = calibrated reveal ratio x how often the baseline runs exercised the component
        base = None
        # a code component: the changed-line ratio times how often the most-run changed line of the file ran; a
        # test that only called the function gets the weaker code:fn ratio, with no coverage factor
        if comp.kind == "code":
            hit = [
                freq[c.id] for c in ctx.change.components if c.kind == "line" and c.file == comp.file and c.id in deps
            ]
            if hit:
                base = own("code:line", ratios["code:line"]) * max(hit)
            elif matches(comp, deps):
                base = own("code:fn", ratios["code:fn"])
        # any other component: the ratio of its bucket times how often the test used it, or one of the items it lost
        elif any(d in deps for d in _reach(comp)):
            # an agent field without training data of its own falls back to the ratio of its kind
            ratio = ratios.get(_kind_key(comp), ratios.get(comp.kind, 0.2))
            base = own(_kind_key(comp), ratio) * max(freq[d] for d in _reach(comp) if d in deps)
        # sensitivity = reveal ratio x lift x coverage x tilt, kept inside [0.02, 0.9] so that no outcome is certain
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
        # P(test fails with nothing broken): 1 for a test the model already fails on the original app; the floor
        # keeps every outcome possible, so that no single result rules a hypothesis out completely
        fails_anyway = np.array([max(0.01, 1.0 - ctx.history.baseline_pass_rate(t)) for t in tests])
        # the inputs of the four factors: text relevance (tilt), reveal ratios and the tests' records (lift)
        lex, (ratios, record) = self.text_relevance(ctx), self.calibrate(ctx)
        # S[t, c] = P(test t fails | component c is broken), the sensitivity of step 2
        S = (
            np.array([[self.sensitivity(ctx, t, c, lex[t], ratios, record) for c, _ in comps] for t in tests])
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
            "fails_anyway": fails_anyway,
            "S": S,
            "groups": groups,
            # test index -> its signature, to find the near-duplicates of a test that just passed
            "group_of": {i: g for g, members in groups.items() for i in members},
            # expected tokens of each test, the denominator of the policy
            "cost": np.array([ctx.cost(t) for t in tests]),
            # risk weight of each test: 1 for a low-risk case, 1 + 3 x risk_tilt for a critical one
            "risk": np.array([1.0 + self.risk_tilt * (ctx.catalog[t].severity - 1.0) for t in tests]),
        }

    # ------------------------------------------------------------------ inference helpers
    @staticmethod
    def p_fail_matrix(S, fails_anyway, hyps):
        """P(test fails | hypothesis) for every test x hypothesis:
        1 - (1 - fails_anyway) * prod_{broken c} (1 - S_tc).  A test passes only if it would pass on the original
        app and none of the broken components makes it fail."""
        return 1.0 - (1.0 - fails_anyway)[:, None] * np.exp(np.log1p(-np.clip(S, 0, 0.999)) @ hyps.T)

    @staticmethod
    def _entropy(P):
        """Entropy of each distribution along the last axis; a zero probability contributes nothing."""
        with np.errstate(divide="ignore", invalid="ignore"):
            return -np.where(P > 1e-12, P * np.log(P), 0.0).sum(axis=-1)

    def info_gain(self, post, p_fail):
        """Expected reduction of posterior entropy for every test, over its two possible outcomes."""
        pf = np.clip(p_fail @ post, 1e-12, 1 - 1e-12)  # P(test fails) under the current posterior
        # the posterior after each of the two outcomes, by Bayes' rule
        post_if_fail = (p_fail * post[None, :]) / pf[:, None]
        post_if_pass = ((1 - p_fail) * post[None, :]) / (1 - pf)[:, None]
        gain = self._entropy(post) - (pf * self._entropy(post_if_fail) + (1 - pf) * self._entropy(post_if_pass))
        return np.maximum(gain, 0.0)

    # ------------------------------------------------------------------ steps 3 to 5: run and stop
    def run(self, ctx: SelectionContext, oracle, stopping: bool = True) -> ExecutionLog:
        """Run tests one by one through ``oracle``. ``stopping=False`` (used by ``order``) disables the early
        stops."""
        log = ExecutionLog(self.name)
        m = self.model(ctx)
        tests, hyps, cost, risk, fails_anyway = m["tests"], m["hyps"], m["cost"], m["risk"], m["fails_anyway"]
        if hyps.shape[1] == 0:  # no component to reason about
            log.stop_reason = "no_components"
            return log
        S = m["S"]
        # the likelihood table P(test fails | hypothesis); a row changes when a near-duplicate of its test passes
        p_fail = self.p_fail_matrix(S, fails_anyway, hyps)
        # the posterior over the hypotheses, starting from the prior of step 1
        post = m["prior"]
        ran = np.zeros(len(tests), dtype=bool)  # each test runs at most once: a rerun would give the same answer
        remaining = ctx.budget
        # step 3: pick the test with the best information per token, run it, update; step 4 decides when to stop
        while True:
            if stopping and 1.0 - post[0] < self.eps_clean:  # hypothesis 0 = nothing broken
                log.stop_reason = "clean"
                break
            # best information per token, weighted by risk; tests that cannot or need not run are ruled out
            gain = self.info_gain(post, p_fail)
            score = gain * risk / cost
            score[ran | (cost > remaining) | (gain <= 1e-9)] = -1.0
            i = int(np.argmax(score))
            if score[i] <= 0:
                log.stop_reason = "budget" if remaining < cost.min() else "uninformative"
                break
            # run it on the changed copy (the oracle: a replay of the recording, or the live app in traceeval check)
            passed, spent = oracle(tests[i])
            ran[i] = True
            remaining -= spent
            log.steps.append((tests[i], passed, spent))
            # Bayes' rule: weigh every hypothesis by the likelihood of the observed outcome
            post = post * ((1 - p_fail[i]) if passed else p_fail[i])
            post /= post.sum() or 1e-12
            if stopping and not passed and fails_anyway[i] < 0.5:  # it passed on the original app: step 4
                post[0] = 0.0  # a changed behaviour rules out "nothing is broken"
                log.stop_reason = "regression"
                break
            if passed:  # near-duplicates of a passed test are correlated evidence: discount them
                for j in m["groups"][m["group_of"][i]]:
                    if j != i and not ran[j]:
                        S[j] *= self.duplicate_discount
                        p_fail[j] = self.p_fail_matrix(S[j][None, :], fails_anyway[j : j + 1], hyps)[0]
            if remaining <= 0:
                log.stop_reason = "budget"
                break
        # step 5: after a run that ended clean, on budget or uninformative, the mandatory-coverage rule
        if stopping and self.cover_mandatory and log.stop_reason != "regression":
            post = self._cover_mandatory(ctx, oracle, log, m, ran, remaining, post, p_fail, fails_anyway)
        # the verdict's probability: P(at least one component is broken | the outcomes)
        log.p_broken = float(1.0 - post[0])
        # and per component, the marginal P(broken): the posterior mass of the hypotheses in which it is broken
        marginals = post @ hyps  # hyps[h, c] = 1 when component c is broken under hypothesis h
        pairs = zip(m["comps"], marginals, strict=True)
        log.blame = sorted(((c.id, float(p)) for (c, _), p in pairs), key=lambda cp: -cp[1])
        return log

    @staticmethod
    def _cover_mandatory(ctx, oracle, log, m, ran, remaining, post, p_fail, fails_anyway):
        """Step 5, the mandatory-coverage rule: a run that found no regression does not end before every mandatory
        property the change may affect (``coverage.affected_properties``) has a test, the cheapest that checks it,
        while the budget allows. Only tests that pass on the original app count: one that fails there checks
        nothing. A failure is a regression, as in step 4, and ends the run. Returns the posterior."""
        from traceeval.catalog import load_properties
        from traceeval.experiment.coverage import affected_properties

        tests, cost, props = m["tests"], m["cost"], load_properties()
        # the properties the tests run so far already check
        checked = {p for i in np.flatnonzero(ran) for p in ctx.catalog[tests[i]].properties}
        # the properties the change may affect, from the components it touched and the tests that exercise them
        affected = affected_properties(ctx.change, ctx.history, ctx.catalog, props)
        # each mandatory one still unchecked gets the cheapest unrun test that checks it and passes on the original app
        for pid in sorted(p for p in affected if props[p].mandatory):
            options = [
                i
                for i in range(len(tests))
                if not ran[i]
                and cost[i] <= remaining
                and fails_anyway[i] < 0.5
                and pid in ctx.catalog[tests[i]].properties
            ]
            if pid in checked or not options:
                continue
            i = min(options, key=lambda j: cost[j])
            passed, spent = oracle(tests[i])
            ran[i] = True
            remaining -= spent
            log.steps.append((tests[i], passed, spent))
            checked |= set(ctx.catalog[tests[i]].properties)
            # the same Bayes update and regression stop as in step 4
            post = post * ((1 - p_fail[i]) if passed else p_fail[i])
            post /= post.sum() or 1e-12
            if not passed:
                post[0] = 0.0
                log.stop_reason = "regression"
                break
        return post

    def order(self, ctx):
        """Non-adaptive view for APFD metrics: the greedy order assuming every test passes, no stopping,
        followed by the untouched tests in cost-aware order."""
        unlimited = replace(ctx, budget=float("inf"))
        executed = self.run(unlimited, lambda t: (True, ctx.cost(t)), stopping=False).executed
        seen = set(executed)
        return executed + [t for t in CostAware().order(ctx) if t not in seen]


# The same method with another text measure (step 2) or without step 5, registered under their own names so that
# a replay can compare them with --strategies; none is in the default comparison.
@register
class AdaptiveBayesTfidf(AdaptiveBayes):
    """Text compared by the TF-IDF similarity of the ir_tfidf strategy instead of word overlap."""

    name = "adaptive_bayes_tfidf"

    def __init__(self):
        super().__init__(text="tfidf")


@register
class AdaptiveBayesNoText(AdaptiveBayes):
    """No text at all: only coverage, history and declarations decide (an ablation)."""

    name = "adaptive_bayes_notext"

    def __init__(self):
        super().__init__(text="none")


@register
class AdaptiveBayesNoMandatory(AdaptiveBayes):
    """Without the mandatory-coverage rule (step 5): an ablation, to measure what the rule costs and adds."""

    name = "adaptive_bayes_nomandatory"

    def __init__(self):
        super().__init__(cover_mandatory=False)
