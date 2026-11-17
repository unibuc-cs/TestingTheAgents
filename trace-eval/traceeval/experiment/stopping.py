"""A clean verdict with a bounded miss rate: the threshold at which a check may stop, set on recorded changes.

The adaptive method ends a run with "clean" when its probability that the change broke something falls under a
threshold (``selection/adaptive_bayes.py``, step 4). As a constant, that threshold promises nothing. Here it is
set on the changes of a recording, whose outcomes are known (``docs/RESEARCH_PLAN.md`` §3.4):

1. the recorded changes are split in two fixed halves, and the method learns from one of them;
2. for every regression of the other half that the replay leaves open, the method's order is followed while each
   test passes, up to the first test that reveals the change. The probability the method has reached there is that
   regression's *value*: a threshold above it would have called the regression clean;
3. for a target miss rate ``alpha`` the threshold is the k-th smallest of the n values, k = floor(alpha (n + 1)).
   A new regression, exchangeable with those n, is then called clean with probability at most alpha. With k = 0
   no threshold is safe, and every test the change reaches runs;
4. the values are kept per *group* of changes (a skill's steps, text the model reads, an agent's tools and
   skills, the configuration, the starting data, code), and a change gets the threshold of its own group, so
   that the promise holds within each group. A group with too few recorded regressions has no threshold.

The values of a recording are worked out once and kept beside it, in ``history/stop_values.json``.
"""

import hashlib
import json
import math
import random
from pathlib import Path

from traceeval.mutation.generator import split
from traceeval.selection import SelectionContext
from traceeval.selection.adaptive_bayes import AdaptiveBayes

from .history import History
from .manifest import selection_digest
from .replay_first import Replays


def group_of(change_set) -> str:
    """The group of a change, read off the kinds of its changed components before any test runs: what the change
    edits, as the method tells kinds of evidence apart (``adaptive_bayes.PRIOR``). Text the model reads (a
    skill's prose, an agent's prompt, a tool's description) is a group of its own: the method holds such an edit
    unlikely to break anything, so a threshold shared with a skill's steps would wave every such edit through. A
    change that touches several kinds is put with the first of the list below."""
    kinds = {c.kind for c in change_set.components}
    if "skill" in kinds:
        return "a skill's steps"
    if kinds & {"skill-prose", "agent-prompt", "tool-schema"}:
        return "text the model reads"
    if "agent" in kinds:
        return "an agent's tools and skills"
    if "config" in kinds:
        return "the configuration"
    if "fixture" in kinds:
        return "the starting data"
    return "code"


def threshold(values: list[float], alpha: float, confidence: float | None = None) -> float:
    """The threshold for a miss rate of at most ``alpha``, from the values of n recorded regressions in
    increasing order: the k-th smallest, so that k - 1 of the n fall under it; minus infinity when k = 0 (no
    threshold is safe: every test runs).

    Without ``confidence``, k = floor(alpha (n + 1)): the miss rate is at most alpha on average over the sets of
    regressions the threshold could have been set on (split conformal prediction). With ``confidence``, the
    largest k for which the miss rate is at most alpha for that share of such sets: the miss rate of the k-th
    smallest value is the k-th smallest of n uniform draws, which is at most alpha exactly when at least k of the
    n draws are, a binomial tail."""
    n = len(values)
    if confidence is None:
        k = math.floor(alpha * (n + 1))
    else:
        k, tail = 0, 1.0  # tail = P(at least k of n draws are at most alpha)
        while k < n:
            tail -= math.comb(n, k) * alpha**k * (1 - alpha) ** (n - k)  # ... at least k + 1 of them
            if tail < confidence:
                break
            k += 1
    return values[k - 1] if k >= 1 else -math.inf


class LearnsOnce(AdaptiveBayes):
    """The adaptive method with what it learns from the other changes worked out once per set of them: it does not
    depend on the change under evaluation, and the changes a threshold is set on all learn from the same set."""

    def __init__(self, **settings):
        super().__init__(**settings)
        self._learnt = (None, None)  # the changes learnt from, and what ``calibrate`` returned for them

    def calibrate(self, ctx):
        if self._learnt[0] != ctx.train_variants:
            self._learnt = (list(ctx.train_variants), super().calibrate(ctx))
        return self._learnt[1]


def stop_values(history: History, replays: Replays, catalog: dict, learn: list[str], calibrate: list[str]) -> dict:
    """Per group of changes, in increasing order: the value of every regression among ``calibrate`` that the
    replay leaves open, with the method learning from ``learn``."""
    method = LearnsOnce()
    passes = {t: history.baseline_pass_rate(t) >= 0.5 for t in history.baseline}
    values: dict[str, list[float]] = {}
    for v in calibrate:
        if v not in replays.rows:
            continue
        revealing, missing = history.revealing_tests(v), history.missing(v)
        # A replayed test that fails settles the change before any test runs: no threshold has a say there.
        if any(passes[t] for t in replays.new_failures(v)):
            continue
        ctx = SelectionContext(
            history.changesets[v],
            catalog,
            history,
            float("inf"),
            random.Random(0),
            train_variants=learn,
            replayed=replays.replayed(v),
            prefix=replays.prefix(v),
            missing=missing,
        )
        # the probability the method has reached when the first revealing test comes up; a change that no test
        # it can run reveals, or that leaves it no component to reason about, has no value
        value = next((p for t, p in method.trajectory(ctx) if t in revealing), None)
        if value is not None:
            values.setdefault(group_of(history.changesets[v]), []).append(value)
    return {group: sorted(vs) for group, vs in values.items()}


def clean_threshold(
    history_dir: Path, history: History, catalog: dict, change_set, alpha: float, allowed: list[str]
) -> tuple[float, list[str], str]:
    """For a check of ``change_set`` against a recording: the threshold of its group for a miss rate of at most
    ``alpha``, the changes the method is to learn from (the half the values were not taken from, so that its
    probabilities are those the threshold was set on), and a sentence that says what the threshold rests on.
    ``allowed`` are the recorded changes the check may use: all of them but the change itself and its members."""
    replays = Replays.load(history_dir)
    if replays is None:
        raise SystemExit(f"{history_dir} has not been replayed: run traceeval replay-first --workdir {history_dir}")
    learn, calibrate = split(allowed)
    # The values depend on the recording, on the two halves, on the strategies' code and on this module (the
    # groups). They are kept when the check uses every recorded change (a change of its own is under test), and
    # read back while all four hold.
    path = Path(history_dir) / "history" / "stop_values.json"
    here = hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16]
    stamp = {"selection": selection_digest(), "stopping": here, "learn": learn, "calibrate": calibrate}
    kept = json.loads(path.read_text()) if path.exists() else {}
    if all(kept.get(k) == v for k, v in stamp.items()):
        values = kept["values"]
    else:
        values = stop_values(history, replays, catalog, learn, calibrate)
        if set(allowed) == set(history.variants):
            path.write_text(json.dumps({**stamp, "values": values}))
    group = group_of(change_set)
    mine = values.get(group, [])
    tau = threshold(mine, alpha)
    if tau == -math.inf:
        need = math.ceil(1 / alpha) - 1  # the fewest values for which k = floor(alpha (n + 1)) is at least 1
        basis = (
            f"no threshold for a miss rate of {alpha:.0%}: {len(mine)} recorded regressions are changes to {group}, "
            f"and {need} are needed; a clean verdict takes every test the change reaches"
        )
    else:
        # three significant digits: where the method was sure of itself and wrong, the threshold is next to zero
        basis = (
            f"clean when P(something broke) is under {tau:.3g}: set on {len(mine)} recorded regressions that are "
            f"changes to {group}, for a miss rate of at most {alpha:.0%}"
        )
    return tau, learn, basis
