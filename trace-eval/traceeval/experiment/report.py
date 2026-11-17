"""Markdown report (+ figures) from the replay results: ground truth, detection vs. cost with intervals over the
changes, waste on the changes no test reveals, verdicts, APFD, properties, coverage (of the suite and of each
change) and, for a recording that has been replayed (``replay_first.py``), what replay-first testing gives."""

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from traceeval.catalog import load_catalog, load_properties  # noqa: E402
from traceeval.mutation.generator import kind_of as kind_of_generated  # noqa: E402

from .generated import Generated  # noqa: E402
from .history import History  # noqa: E402
from .manifest import load_manifest  # noqa: E402
from .replay_first import Replays, cassette_path  # noqa: E402

# the strategies, in the order the tables and figures show them; a strategy not listed here is not shown
ORDER = [
    "full",
    "random",
    "cheapest",  # the two orders only the replay-first comparison has
    "late_divergence",
    "declared",
    "ir_tfidf",
    "observed",
    "observed_diverse",
    "cost_aware",
    "history_ml",
    "casper_slices",
    "risk_aware_ts",
    "risk_aware_ts_per_token",
    "adaptive_bayes",
    "adaptive_bayes_tfidf",  # the method's variants, shown when a replay included them
    "adaptive_bayes_notext",
    "adaptive_bayes_nomandatory",
]
# the figures' colours: the method black, its variants grey; a strategy without one gets matplotlib's next default
COLOR = {
    "full": "#9e9e9e",
    "random": "#bdbdbd",
    "cheapest": "#ff7f0e",
    "late_divergence": "#98df8a",
    "declared": "#e6a100",
    "ir_tfidf": "#7b61ff",
    "observed": "#1f77b4",
    "observed_diverse": "#17becf",
    "cost_aware": "#2ca02c",
    "history_ml": "#d62728",
    "casper_slices": "#e377c2",
    "risk_aware_ts": "#bcbd22",
    "risk_aware_ts_per_token": "#8c6d31",
    "adaptive_bayes": "#111111",
    "adaptive_bayes_tfidf": "#555555",
    "adaptive_bayes_notext": "#888888",
    "adaptive_bayes_nomandatory": "#8c564b",
}
# tokens spent in % of the full suite: the x axis of the detection figure (log scale)
SPENT_TICKS = [1, 2, 5, 10, 20, 50, 100]
# the budgets at which the report gives intervals over the changes and the verdicts
FOCUS_BUDGETS = (0.05, 0.2)
# above this many changes, section 1 has one row per kind of change instead of one per change
MANY_CHANGES = 60
# the stop reasons that say "no regression": the adaptive method's verdict, a change with nothing to test, and a
# strategy that ran every test of its order without a failure
CLEAN_STOPS = ("clean", "no_components", "exhausted")


def _axes(ax, title, xlabel, ylabel):
    """The look the figures share: a left-aligned title, no top or right frame, faint horizontal grid lines."""
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25)


def fig_detection_vs_cost(df, out, title="Regressions detected vs. tokens spent"):
    """Detection of the revealed regressions against the tokens spent over all changes: up and to the left is
    better."""
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for name in ORDER:
        sub = df[df.strategy == name]
        if sub.empty:
            continue
        # one point per nominal budget: the mean tokens spent over every change against the detection of the
        # changes some test reveals
        cost = sub.groupby("budget")["cost_fraction"].mean()
        det = sub[sub.is_regression].groupby("budget")["detected"].mean().reindex(cost.index)
        ax.plot(
            cost * 100,
            det * 100,
            marker="o",
            ms=4,
            label=name,
            color=COLOR.get(name),
            lw=2.2 if name == "adaptive_bayes" else 1.4,
        )
    _axes(
        ax,
        title,
        "tokens spent, mean over all changes (% of full suite)",
        "revealed regressions detected (%)",
    )
    ax.set_xscale("log")
    ax.set_xticks(SPENT_TICKS)
    ax.set_xticklabels([str(b) for b in SPENT_TICKS])
    ax.set_ylim(0, 102)
    ax.legend(fontsize=8, ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_benign_waste(df, out):
    """Tokens spent on the changes no test reveals: one group of bars per strategy, one bar per nominal budget."""
    ben = df[~df.is_regression]
    budgets = sorted(ben.budget.unique())
    names = [n for n in ORDER if n in set(ben.strategy)]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    # a strategy's bars share a slot of width 0.8, lighter to darker blue as the budget grows
    width = 0.8 / max(1, len(budgets))
    for k, b in enumerate(budgets):
        vals = [ben[(ben.strategy == n) & (ben.budget == b)]["cost_fraction"].mean() * 100 for n in names]
        ax.bar(
            [i + k * width for i in range(len(names))],
            vals,
            width=width,
            label=f"budget {int(b * 100)}%",
            color=plt.cm.Blues(0.35 + 0.6 * k / max(1, len(budgets) - 1)),
        )
    # the strategy's name under the middle of its group
    ax.set_xticks([i + width * (len(budgets) - 1) / 2 for i in range(len(names))])
    ax.set_xticklabels(names, rotation=25, ha="right", fontsize=8)
    _axes(ax, "Tokens spent on changes no test reveals (lower is better)", "", "tokens spent (% of full suite)")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_apfdc(pr, out):
    """APFD_c of each strategy's complete prioritized order over the revealed changes: one box per strategy."""
    names = [n for n in ORDER if n in set(pr.strategy)]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    # outliers left out; each box in the colour of the strategy's line in the other figures
    boxes = ax.boxplot(
        [pr[pr.strategy == n]["apfdc"].dropna().values for n in names], patch_artist=True, widths=0.6, showfliers=False
    )["boxes"]
    for patch, n in zip(boxes, names, strict=True):
        patch.set_facecolor(COLOR.get(n, "#cccccc"))
        patch.set_alpha(0.75)
    ax.set_xticks(range(1, len(names) + 1))
    ax.set_xticklabels(names, rotation=25, ha="right", fontsize=8)
    _axes(ax, "Cost-cognizant APFD of the complete prioritized order", "", "APFD_c")
    ax.set_ylim(0, 1.02)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def _table(df, fmt="{:.2f}"):
    """A DataFrame as a Markdown table: the index as the first column, floats in ``fmt``, the rest as text."""
    cols = list(df.columns)
    rows = [
        "| " + " | ".join([df.index.name or "strategy"] + [str(c) for c in cols]) + " |",
        "|" + "---|" * (len(cols) + 1),
    ]
    for idx, row in df.iterrows():
        cells = [fmt.format(v) if isinstance(v, float) else str(v) for v in row]
        rows.append("| " + " | ".join([str(idx)] + cells) + " |")
    return "\n".join(rows)


def _by_budget(df, value, fmt="{:.2f}"):
    """The mean of ``value`` per strategy (rows, in ORDER) and nominal budget (columns, in % of the full suite), as a
    Markdown table; a strategy the replay did not run is left out."""
    t = (
        df.pivot_table(index="strategy", columns="budget", values=value, aggfunc="mean")
        .reindex(ORDER)
        .dropna(how="all")
    )
    t.columns = [f"{int(b * 100)}%" for b in t.columns]
    return _table(t, fmt)


def _optional_table(df, value, title, fmt="{:.2f}") -> list[str]:
    """A titled table by budget, or nothing when the replay has no such column (a replay made by an older version)
    or no value in it (no change breaks a safety property, say)."""
    if value not in df or df[value].isna().all():
        return []
    return [title, "", _by_budget(df.dropna(subset=[value]).astype({value: float}), value, fmt), ""]


def _detection_at(df, budget: float, draws: int = 10000) -> list[str]:
    """At one nominal budget: each strategy's detection of the revealed regressions with a 95% bootstrap interval,
    the tokens it spends as a mean over all changes, and its paired difference to the strategy that detects most.
    The sample is the changes: a change's detection is first averaged over the replay seeds, then the changes are
    resampled, the same draws for every strategy."""
    at = df[np.isclose(df.budget, budget)]
    reg = at[at.is_regression]
    if reg.empty:
        return []
    # one row per revealed regression, one column per strategy: the share of the seeds in which it was detected
    per_change = reg.assign(detected=reg.detected.astype(float)).pivot_table(
        index="variant", columns="strategy", values="detected", aggfunc="mean"
    )
    names = [n for n in ORDER if n in per_change.columns]
    # tokens over every change of the replay, revealed or not: what the strategy costs on a day's mix of changes
    spent = at.groupby("strategy")["cost_fraction"].mean()
    # the bootstrap: ``draws`` samples of the changes, with replacement, from a fixed seed so that the report is the
    # same on every run; each row of ``idx`` is one sample, used for every strategy so that differences are paired
    idx = np.random.default_rng(0).integers(0, len(per_change), size=(draws, len(per_change)))

    def interval(values):
        """The 2.5% and 97.5% quantiles of the mean of ``values`` (one per change) over the samples."""
        means = values[idx].mean(1)
        return np.quantile(means, 0.025), np.quantile(means, 0.975)

    best = max(names, key=lambda n: per_change[n].mean())  # the first of ORDER among equals
    rows = [
        "| strategy | detected | 95% interval | tokens, all changes | difference to the best | 95% interval |",
        "|---|---|---|---|---|---|",
    ]
    for n in names:
        values = per_change[n].to_numpy()
        low, high = interval(values)
        cells = [n, f"{values.mean():.2f}", f"{low:.2f} to {high:.2f}", f"{spent[n]:.3f}"]
        if n == best:
            cells += ["best", ""]
        else:
            # change by change, this strategy's detection minus the best one's: an interval that holds 0 means the
            # recording cannot tell the two apart
            diff = values - per_change[best].to_numpy()
            low, high = interval(diff)
            cells += [f"{diff.mean():+.2f}", f"{low:+.2f} to {high:+.2f}"]
        rows.append("| " + " | ".join(cells) + " |")
    return [
        f"At a budget of {budget:.0%}, over the {len(per_change)} revealed regressions (intervals: bootstrap over the "
        "changes; a difference whose interval holds 0 is not established):",
        "",
        *rows,
        "",
    ]


def _verdicts_at(df, budget: float) -> list[str]:
    """At one nominal budget: how each strategy's runs end, as shares of its runs on the revealed regressions and
    on the other changes. A run says "regression" when a test fails, "clean" when the adaptive method says so,
    when the change has nothing to test or when every test of the strategy's order ran and passed; a run the
    budget ended has no verdict. The last column is the share of the clean verdicts given on a revealed
    regression."""
    at = df[np.isclose(df.budget, budget)]

    def shares(runs) -> list[str]:
        """The shares of ``runs`` that end with a regression verdict, with a clean one, and with none."""
        if runs.empty:
            return ["", "", ""]
        found = runs.stop_reason == "regression"
        cleared = runs.stop_reason.isin(CLEAN_STOPS)
        return [f"{found.mean():.2f}", f"{cleared.mean():.2f}", f"{(~found & ~cleared).mean():.2f}"]

    rows = [
        "| strategy | regressions: found | called clean | no verdict | other changes: called clean | "
        "called regression | no verdict | clean verdicts on a regression |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for n in ORDER:
        g = at[at.strategy == n]
        if g.empty:
            continue
        # the strategy's runs on the changes some test reveals, and on the changes none does
        found, cleared, none = shares(g[g.is_regression])
        o_found, o_cleared, o_none = shares(g[~g.is_regression])
        # of all its clean verdicts, the share that was given on a revealed regression: a miss called clean
        clean = g[g.stop_reason.isin(CLEAN_STOPS)]
        wrong = f"{clean.is_regression.mean():.2f}" if len(clean) else ""
        rows.append(f"| {n} | {found} | {cleared} | {none} | {o_cleared} | {o_found} | {o_none} | {wrong} |")
    return [f"Verdicts at a budget of {budget:.0%} (shares of the runs):", "", *rows, ""] if len(rows) > 2 else []


def _properties_section(history, reg) -> list[str]:
    """Section 5: every property of the catalog with its tests' pass rate on the original app against its
    threshold, and how much of the properties a change breaks each strategy exercised."""
    cases = {c.id: c for c in load_catalog()}
    rows = []
    for p in load_properties().values():
        # the recorded tests that check the property; its pass rate is the mean of theirs on the original app
        tests = [t for t, c in cases.items() if p.id in c.properties and t in history.baseline]
        rate = sum(history.baseline_pass_rate(t) for t in tests) / len(tests) if tests else float("nan")
        met = "yes" if rate >= p.threshold else "**no**"
        rows.append(
            f"| `{p.id}` | {p.category} | {'yes' if p.mandatory else ''} | {p.threshold:.2f} | {len(tests)} | "
            f"{rate:.2f} | {met} |"
        )
    out = [
        "## 5. Properties",
        "",
        "The catalog of properties (`traceeval/catalog/properties.yaml`): for each, its tests' pass rate on the "
        "original app against its threshold:",
        "",
        "| property | category | mandatory | threshold | tests | pass rate | met |",
        "|---|---|---|---|---|---|---|",
        *rows,
        "",
    ]
    if "property_coverage" in reg:
        out += [
            "Coverage of the affected properties (those of a change's revealing tests) by the tests each strategy ran:",
            "",
            _by_budget(reg, "property_coverage"),
            "",
        ]
    return out


def suite_coverage_lines(history, sut_dir) -> list[str]:
    """The coverage of the test suite as Markdown: per dimension, then per agent, skill, tool and feature (also printed
    by ``traceeval coverage``)."""
    from .coverage import suite_coverage, tests_per_component

    cases = {c.id: c for c in load_catalog()}
    table = ["| dimension | components | declared | observed | not covered |", "|---|---|---|---|---|"]
    for r in suite_coverage(history, cases, load_properties(), sut_dir):
        # at most eight uncovered components per row; a row with none shows its detail instead (the risk row)
        gaps = ", ".join(r["not covered"][:8]) + (" ..." if len(r["not covered"]) > 8 else "")
        table.append(
            f"| {r['dimension']} | {r['components']} | {'' if r['declared'] is None else r['declared']} | "
            f"{r['observed']} | {gaps or r.get('detail', '')} |"
        )
    out = [
        "Coverage of the test suite: per dimension, how many components the tests declare and the traces show, and "
        "what no test covers. A feature (`catalog/features.yaml`) is covered by the tests that declare or call one of "
        "its tools. A tool error path is a place in the code where a tool call is refused, reached when a run executes "
        "it. A workflow is declared by the tests that name it and observed when a run delegates to exactly its agents "
        "in order. Execution paths are the distinct agent and tool sequences; risk lists tests per level.",
        "",
        *table,
        "",
        "Per component: how many tests declare it in their metadata, and how many invoke it in their recorded runs. A "
        "component few tests invoke is thinly covered. A difference between the two counts is where the hand-written "
        "metadata and the runs disagree.",
        "",
    ]
    for dim, rows in tests_per_component(history, cases, sut_dir).items():
        out += [f"| {dim} | declared | invoked |", "|---|---|---|", *(f"| {n} | {d} | {o} |" for n, d, o in rows), ""]
    return out


def _coverage_section(workdir, history, df) -> list[str]:
    """Section 6: coverage of the test suite by dimension, and change coverage per strategy over every change (it
    needs no ground truth)."""
    from traceeval.sut import SUT_ROOT

    sut_dir = workdir / "variants" / "baseline" / "sut"
    out = ["## 6. Coverage", "", *suite_coverage_lines(history, sut_dir if sut_dir.exists() else SUT_ROOT)]
    if "component_coverage" in df:
        # a run that found a regression is over whatever it left untested; the mandatory rule concerns the others
        open_runs = df[df.stop_reason != "regression"].astype({"mandatory_covered": float})
        out += [
            "Change coverage over every change, without the ground truth: the share of the changed components the "
            "executed tests exercised, and the share of the properties the change may affect (`coverage.py`) that "
            "they checked.",
            "",
            "Changed components exercised:",
            "",
            _by_budget(df, "component_coverage"),
            "",
            "Affected properties checked:",
            "",
            _by_budget(df, "affected_property_coverage"),
            "",
            "Runs that found no regression and tested every affected mandatory property (the method's step 5):",
            "",
            _by_budget(open_runs, "mandatory_covered"),
            "",
        ]
        # a recording made before the workflow tests existed affects no workflow: the table is then left out
        if "affected_workflow_coverage" in df and df["affected_workflow_coverage"].notna().any():
            out += [
                "Affected workflows run (the workflows of the tests that exercised a changed component):",
                "",
                _by_budget(df, "affected_workflow_coverage"),
                "",
            ]
        out += _optional_table(
            df,
            "affected_feature_coverage",
            "Affected features reached (the features with a tool or a part the change touches), over the changes that "
            "affect one:",
        )
    return out


def _kind(history, variant: str) -> str:
    """The kind a change is tabled under: the generator's kind for a generated change (step deleted, setting, ...),
    the catalog's category for a hand-written one (code, skill, config, ...)."""
    if variant.startswith("g_"):
        return kind_of_generated(variant)
    return history.mutation_meta.get(variant, {}).get("category", "?")


def _settled_by_replay(history, replays, kind_of: dict[str, str]) -> tuple[pd.DataFrame, list[str], dict[str, int]]:
    """What a replay settles without a model, for the changes ``kind_of`` names (change -> its kind): one row per
    change, the table by kind that sections 7 and 8 show, and where the diverged tests first reach the model."""
    tests, full = history.test_ids(), history.total_cost()
    passes = {t: history.baseline_pass_rate(t) >= 0.5 for t in tests}
    per_change, where = [], {"prompt": 0, "tool result": 0}
    for v, kind in kind_of.items():
        diverged, prefix = replays.diverged(v), replays.prefix(v)
        for t in diverged:
            where[replays.rows[v][t]["diverged_in"]] += 1
        per_change.append(
            {
                "change": v,
                "kind": kind,
                "nothing diverges": not diverged,
                "a replayed test fails": any(passes.get(t) for t in replays.new_failures(v)),
                "diverged": len(diverged),
                # the diverged tests run whole, and from their divergence point on, as shares of the suite's tokens
                "whole": sum(history.cost(t) for t in diverged) / full,
                "left": sum(max(0.0, history.cost(t) - prefix[t]) for t in diverged) / full,
            }
        )
    frame = pd.DataFrame(per_change)
    table = [
        "| kind of change | changes | no test diverges | a replayed test fails | diverged tests, mean | "
        "their share of the suite's tokens | after the divergence point |",
        "|---|---|---|---|---|---|---|",
    ]
    for kind, g in [*frame.groupby("kind"), ("all", frame)]:
        table.append(
            f"| {kind} | {len(g)} | {int(g['nothing diverges'].sum())} | {int(g['a replayed test fails'].sum())} | "
            f"{g.diverged.mean():.0f} of {len(tests)} | {g.whole.mean():.3f} | {g.left.mean():.3f} |"
        )
    return frame, table, where


def _generated_section(workdir, history) -> list[str]:
    """Section 8, for a recording whose generated changes have been replayed (``generated.py``): what the replay
    alone says about several hundred changes nobody labelled, for no tokens."""
    made = Generated.load(workdir)
    if made is None:
        return []
    frame, table, _ = _settled_by_replay(history, made.replays, {c: line["kind"] for c, line in made.changes.items()})
    clean = frame[frame["nothing diverges"] & ~frame["a replayed test fails"]]
    found = frame[frame["a replayed test fails"]]
    rest = frame[~frame["nothing diverges"] & ~frame["a replayed test fails"]]
    return [
        "## 8. Generated changes, replayed",
        "",
        f"The {len(frame)} changes that `mutation/generator.py` makes mechanically from the app (one per place an "
        "edit of its kind applies to), each applied to a copy of the original app and replayed against the "
        "recording's cassette (`traceeval replay-first --generated`). No model is called, and no change has a label.",
        "",
        *table,
        "",
        f"- settled as clean, no test diverges and none fails: {len(clean)} of {len(frame)};",
        f"- settled as a regression, a test that passes on the original app replays to a failure: {len(found)};",
        f"- left for the model: {len(rest)}, whose diverged tests cost {rest.left.mean():.1%} of the suite's tokens "
        f"after their divergence points on average (median {rest.left.median():.1%}), and {rest.whole.mean():.1%} "
        "run whole.",
        "",
    ]


def _replay_first_section(workdir, history, figs, replays) -> list[str]:
    """Section 7, for a recording that has been replayed: what the replay settles without a model, how it compares
    with the recorded ground truth and with the recorded runs, and the strategies run replay-first."""
    variants = [v for v in sorted(history.variants) if v in replays.rows]
    tests = history.test_ids()
    passes = {t: history.baseline_pass_rate(t) >= 0.5 for t in tests}
    # ---- per change: how many tests diverge, what they cost, and whether a replayed test already fails
    _, kinds, where = _settled_by_replay(history, replays, {v: _kind(history, v) for v in variants})

    # ---- against the ground truth: the replayed outcomes, and where the revealing tests ended up
    replayed_pairs, differ, revealing_pairs = 0, [], {"fail": 0, "diverge": 0, "pass": 0}
    missed, false_failures = [], []
    for v in variants:
        rows, revealing = replays.rows[v], history.revealing_tests(v)
        for t, r in rows.items():
            if r["replayed"]:
                replayed_pairs += 1
                if r["passed"] != (history.variant_pass_rate(v, t) >= 0.5):
                    differ.append(f"`{t}` under `{v}`")
        for t in revealing:
            revealing_pairs["diverge" if not rows[t]["replayed"] else "pass" if rows[t]["passed"] else "fail"] += 1
        # a regression is missed when every one of its revealing tests replays to a pass
        if revealing and all(rows[t]["replayed"] and rows[t]["passed"] for t in revealing):
            missed.append(f"`{v}`")
        if not revealing and any(passes[t] for t in replays.new_failures(v)):
            false_failures.append(f"`{v}`")
    regressions = sum(bool(history.revealing_tests(v)) for v in variants)

    # ---- against the recorded runs, one by one: does a run that was really made equal the replay of its test?
    def same_as_replay(variant, stats_by_test):
        """Over the recorded runs of the tests that replay to the end on ``variant``: how many there are, how many
        end like the replay, and how many are the replay's conversation (same tool calls, final answer, final state
        and token count)."""
        runs = outcome = identical = 0
        for t, r in replays.rows[variant].items():
            if not r["replayed"] or t not in stats_by_test:
                continue
            shape = (r["passed"], r["tokens"], r["tools"], r["final_message"], r["state_digest"])
            for x in stats_by_test[t].valid_runs:
                if x.get("stand_in"):  # no run was made: the replay itself stands in (History.load)
                    continue
                runs += 1
                outcome += x["passed"] == r["passed"]
                identical += (x["passed"], x["tokens"], x["tools"], x["final_message"], x["state_digest"]) == shape
        return runs, outcome, identical

    base = same_as_replay("baseline", history.baseline) if "baseline" in replays.rows else (0, 0, 0)
    # the empty change is the original app too, run as the changed copies are: the same replay is its reference
    empty = same_as_replay("baseline", history.unchanged) if "baseline" in replays.rows else (0, 0, 0)
    copies = [same_as_replay(v, history.variants[v]) for v in variants]
    changed = tuple(sum(c[i] for c in copies) for i in range(3))
    run_rows = [f"| the original app | {base[0]} | {base[1]} | {base[2]} |"]
    if empty[0]:
        run_rows.append(f"| the original app, run as the changed copies are | {empty[0]} | {empty[1]} | {empty[2]} |")
    run_rows.append(f"| the changed copies | {changed[0]} | {changed[1]} | {changed[2]} |")
    # a recording of the tests each change reaches only (``runner.record_mutants(reached_only=True)``)
    lean = any(run.get("stand_in") for v in variants for stats in history.variants[v].values() for run in stats.runs)

    # ---- request by request: is a model call a function of its request? Three measures, each over the requests
    # that were sent more than once: by the baseline's own repetitions, by the empty change and by the changed copies
    # (the latter two against the answer the cassette keeps, the one the baseline's repetitions gave most often).
    again, twice = _answered_twice(workdir)
    asked = [_answers(history.variants[v]) for v in variants]
    otherwise = "answered otherwise than the cassette"
    rows = [
        ("the baseline's repetitions, one test at a time", again, twice, "got more than one answer"),
        ("the empty change", *_answers(history.unchanged)[1:], otherwise),
        ("the changed copies", sum(a[1] for a in asked), sum(a[2] for a in asked), otherwise),
    ]
    condition = [f"| {who} | {n} | {k} ({k / n:.2%}) {what} |" for who, n, k, what in rows if n]
    if condition:
        condition = [
            "The condition itself, a model call being a function of its request, request by request:",
            "",
            "| requests of | sent before | of which |",
            "|---|---|---|",
            *condition,
            "",
        ]

    out = [
        "## 7. Replay-first",
        "",
        "Every test was run on every changed copy with the model's calls answered from the answers recorded on the "
        "original app (`traceeval replay-first`; no model is called). A test either replays to the end, and its "
        "outcome on the changed copy is known for no tokens, or diverges at the first request the original app never "
        "made, and needs the model from there on.",
        "",
        "What the replay settles alone, by kind of change:",
        "",
        *kinds,
        "",
        f"Over the {sum(where.values())} diverged (change, test) pairs, the change first reaches the model in what an "
        f"agent is sent up front (its prompt, skills, tools or task) on {where['prompt']}, and in a tool result on "
        f"{where['tool result']}.",
        "",
        "The replay against the recorded ground truth:",
        "",
        # a copy recorded for the tests it reaches only has no run of a replayed test to compare the replay with
        "- the tests that replay to the end were not run on these copies: the replay's outcome is the one on record;"
        if lean
        else f"- replayed outcomes that differ from the recorded majority: {len(differ)} of {replayed_pairs}"
        + (f" ({', '.join(differ[:5])})" if differ else "")
        + ";",
        f"- the {sum(revealing_pairs.values())} revealing (change, test) pairs: {revealing_pairs['fail']} replay to "
        f"a failure, {revealing_pairs['diverge']} diverge, {revealing_pairs['pass']} replay to a pass;",
        f"- revealed regressions with a revealing test that fails in the replay or diverges: "
        f"{regressions - len(missed)} of {regressions}" + (f" (missed: {', '.join(missed)})" if missed else "") + ";",
        f"- changes no test reveals on which a replayed test fails: {len(false_failures)}"
        + (f" ({', '.join(false_failures)})" if false_failures else "")
        + ".",
        "",
        "The replay against the recorded runs, one by one, over the tests that replay to the end. A run is identical "
        "to the replay when it has the same tool calls, final answer, final state and token count:",
        "",
        "| recorded runs of | runs | end like the replay | identical to the replay |",
        "|---|---|---|---|",
        *run_rows,
        "",
        *condition,
    ]

    # ---- the strategies run replay-first, when the evaluation was made
    path = workdir / "results" / "replay_first.csv"
    if not path.exists():
        return out
    rf = pd.read_csv(path)
    reg = rf[rf.is_regression]
    fig_detection_vs_cost(rf, figs / "replay_first.png", "Replay-first: regressions detected vs. tokens spent")
    out += [
        "The strategies run replay-first: a test that replays to the end is not run, a replayed failure of a test that "
        "passes on the original app ends the run for no tokens, and a diverged test costs its tokens after the "
        "divergence point. A run that ends because every diverged test has run and passed is a clean verdict that "
        "leaves no reachable test untested.",
        "",
        "Fraction of the revealed regressions detected, by nominal budget:",
        "",
        _by_budget(reg, "detected"),
        "",
        "Tokens spent, as a mean over all changes (fraction of the full suite):",
        "",
        _by_budget(rf, "cost_fraction", "{:.3f}"),
        "",
        "The same tests run whole, without the replayed part taken off:",
        "",
        _by_budget(rf, "whole_cost_fraction", "{:.3f}"),
        "",
        *[line for b in FOCUS_BUDGETS if np.isclose(rf.budget, b).any() for line in _detection_at(rf, b)],
        "![replay-first: detection vs cost](figures/replay_first.png)",
        "",
        *[line for b in (FOCUS_BUDGETS[-1], 1.0) if np.isclose(rf.budget, b).any() for line in _verdicts_at(rf, b)],
    ]
    return out


def _answers(stats_by_test: dict) -> tuple[int, int, int]:
    """Over the recorded runs of one copy of the app: the requests they sent the model, those the original app had
    sent too, and those of the latter the model answered otherwise (``llm/cache.py::Compare``). Zeros for a
    recording made without the comparison."""
    counts = [r.get("cassette") or {} for st in stats_by_test.values() for r in st.runs]
    return tuple(sum(c.get(k, 0) for c in counts) for k in ("requests", "known", "differ"))


def _answered_twice(workdir) -> tuple[int, int]:
    """Over the requests the baseline's repetitions sent more than once (a recording's cassette keeps the counts,
    ``llm/cache.py::Tee``): how many there are, and how many got more than one answer. Zeros without a cassette."""
    path = cassette_path(workdir)
    if not path.exists():
        return 0, 0
    with open(path, encoding="utf-8") as fh:
        entries = [json.loads(line) for line in fh if line.strip()]
    again = [e for e in entries if e.get("asked", 1) > 1]
    return len(again), sum(e["distinct"] > 1 for e in again)


def _recording_lines(workdir, history) -> list[str]:
    """Under the report's header: how the recording was made (its manifest), what the empty change shows, and the
    pairs it has no valid run of. A recording made before these were kept has none of the lines."""
    out = []
    m = load_manifest(workdir)
    if m:
        base, changes = m.get("baseline", {}), m.get("changes", {})
        copies = f"; the changed copies {changes.get('reps')} times, {changes.get('workers')} cases at a time"
        out.append(
            f"- Recorded with `{m.get('model')}` (judge: {m.get('judge')}) at commit `{m.get('commit')}`"
            + (", with uncommitted edits" if m.get("dirty") else "")
            + f"; the original app {base.get('reps')} times, one case at a time"
            + (copies if changes else "")
            + "."
        )
    if history.unchanged:
        flips = history.unchanged_flips()
        requests, known, differ = _answers(history.unchanged)
        asked = f"; of its {requests} requests, {known} are the baseline's, {differ} of them answered otherwise"
        out.append(
            "- The empty change (the original app, run as the changed copies are): "
            f"{len(flips)} of {len(history.unchanged)} tests end otherwise than in the baseline"
            + (f" ({', '.join(f'`{t}`' for t in flips[:8])})" if flips else "")
            + (asked if requests else "")
            + "."
        )
    missing = history.summary()["missing_pairs"]
    if missing:
        out.append(f"- (change, test) pairs with no valid run, left out as missing: {missing}.")
    return [*out, ""] if out else []


def write_report(workdir: Path) -> Path:
    """Write results/report.md and its figures from replay.csv and, when it exists, prioritization.csv (results/)."""
    workdir = Path(workdir)
    res, figs = workdir / "results", workdir / "results" / "figures"
    figs.mkdir(exist_ok=True, parents=True)
    history = History.load(workdir)
    df = pd.read_csv(res / "replay.csv")
    pr = pd.read_csv(res / "prioritization.csv") if (res / "prioritization.csv").exists() else None
    # the runs on the changes some test reveals, and on the changes none does
    reg, ben = df[df.is_regression], df[~df.is_regression]

    fig_detection_vs_cost(df, figs / "detection_vs_cost.png")
    fig_benign_waste(df, figs / "benign_waste.png")
    if pr is not None:
        fig_apfdc(pr, figs / "apfdc.png")

    # section 1: the changes by category, with how many tests reveal each; the testbed is sane when a change is
    # revealed exactly when its label says regression. A recording that has been replayed (replay_first.py) also
    # says, per change, how many tests diverge and how many tests that pass on the original app replay to a failure
    replays = Replays.load(workdir)
    meta = history.mutation_meta
    truth_rows, sane, labelled = [], True, 0
    by_kind: dict[str, list[int]] = {}  # kind -> the number of revealing tests of each of its changes
    for v in sorted(history.variants, key=lambda v: (meta.get(v, {}).get("category", ""), v)):
        n = len(history.revealing_tests(v))
        by_kind.setdefault(_kind(history, v), []).append(n)
        # a hand-written change is labelled a regression or benign; a generated one has no label, and no part
        # in the sanity check
        expected = meta.get(v, {}).get("expected_regression")
        if expected is not None:
            labelled += 1
            sane &= (n > 0) == expected
        label = {True: "regression", False: "benign", None: "no label"}[expected]
        row = f"| `{v}` | {meta.get(v, {}).get('category', '?')} | {label} | {n} |"
        if replays and v in replays.rows:
            failures = [t for t in replays.new_failures(v) if history.baseline_pass_rate(t) >= 0.5]
            row += f" {len(replays.diverged(v))} | {len(failures)} |"
        truth_rows.append(row)
    truth_head = [
        "| change | category | expected | revealing tests |"
        + (" diverged tests | replayed failures |" if replays else ""),
        "|---|---|---|---|" + ("---|---|" if replays else ""),
    ]
    if len(truth_rows) > MANY_CHANGES:
        # several hundred changes: one row per kind instead of one per change (replay.csv has them all)
        truth_head = [
            "| kind of change | changes | revealed by a test | revealing tests of those, median |",
            "|---|---|---|---|",
        ]
        truth_rows = [
            f"| {kind} | {len(ns)} | {sum(n > 0 for n in ns)} | {np.median([n for n in ns if n] or [0]):.0f} |"
            for kind, ns in sorted(by_kind.items())
        ]
        every = [n for ns in by_kind.values() for n in ns]
        truth_rows.append(
            f"| all | {len(every)} | {sum(n > 0 for n in every)} | {np.median([n for n in every if n] or [0]):.0f} |"
        )
    if labelled:
        sanity = (
            "Testbed sanity (every change labelled a regression revealed by at least one test, none labelled benign "
            f"revealed): **{'OK' if sane else 'VIOLATED'}**."
        )
    else:
        revealed = sum(bool(history.revealing_tests(v)) for v in history.variants)
        sanity = f"None of these changes has a label: {revealed} of {len(history.variants)} are revealed by a test."
    summ = history.summary()
    # an evaluation may cover some of the recorded changes only: the half held out of what the strategies learn from
    evaluated = (
        "" if df.variant.nunique() == summ["variants"] else f" ({df.variant.nunique()} evaluated, the rest learnt from)"
    )
    # per strategy: the mean tokens until the first true failure, over the runs that detected one
    c2d = reg[reg.detected].groupby("strategy")["cost_to_detect_fraction"].mean().reindex(ORDER).dropna()
    # the budgets of the interval and verdict tables that this replay has
    focus = [b for b in FOCUS_BUDGETS if np.isclose(df.budget, b).any()]

    parts = [
        "# TRACE-Eval experiment report",
        "",
        f"`{workdir.as_posix()}` · {summ['tests']} tests · {summ['variants']} changes{evaluated} · "
        f"{summ['baseline_reps']} baseline repetitions · full suite = {summ['total_tokens_full_suite']:,} tokens · "
        f"tests failing on the original app: {len(summ['failing_tests'])} · "
        f"runs the environment broke, left out: {summ['infra_invalid_runs']}",
        "",
        *_recording_lines(workdir, history),
        "## 1. Ground truth — which changes are revealed by how many tests",
        "",
        *truth_head,
        *truth_rows,
        "",
        sanity,
        "",
        "## 2. Detection within a budget",
        "",
        "Every strategy is run the same way: a test that fails on the original app is not run, and a run ends at "
        "its first failure.",
        "",
        "Fraction of the revealed regressions detected, by nominal budget (% of full-suite tokens):",
        "",
        _by_budget(reg, "detected"),
        "",
        "Tokens spent, as a mean over all changes, revealed or not (fraction of the full suite):",
        "",
        _by_budget(df, "cost_fraction", "{:.3f}"),
        "",
        *[line for b in focus for line in _detection_at(df, b)],
        "Tokens spent on the revealed regressions only:",
        "",
        _by_budget(reg, "cost_fraction", "{:.3f}"),
        "",
        *_optional_table(
            reg,
            "time_fraction",
            "Time spent on those changes (fraction of the full suite's run time, from each test's mean time on the "
            "original app):",
            "{:.3f}",
        ),
        *_optional_table(
            reg[reg.safety_recall.notna()],  # the changes one of whose revealing tests checks a safety property
            "detected",
            "Critical regressions: the same detection rate, over the changes that break a safety property only:",
        ),
        "![detection vs cost](figures/detection_vs_cost.png)",
        "",
        "Cost until the first true detection (fraction of the full suite, detected cases only):",
        "",
        _table(c2d.to_frame("cost_to_first_detection"), "{:.3f}"),
        "",
        "## 3. Changes no test reveals, and verdicts",
        "",
        "Tokens spent on the changes no test reveals:",
        "",
        _by_budget(ben, "cost_fraction", "{:.3f}"),
        "",
        "![tokens spent on changes no test reveals](figures/benign_waste.png)",
        "",
        *[line for b in focus for line in _verdicts_at(df, b)],
    ]
    # section 4, when the prioritization replay was made
    if pr is not None:
        g = pr.groupby("strategy")[["apfd", "apfdc", "selection_recall", "selected_cost_fraction"]].mean()
        parts += [
            "## 4. Prioritization and selection quality",
            "",
            "APFD / cost-cognizant APFD of the complete order, each change one fault found by the first of its "
            "revealing tests (an order drawn at random: the mean over the seeds); selection recall = revealing tests "
            "inside the selected subset; selected cost = what that subset costs:",
            "",
            _table(g.reindex(ORDER).dropna(how="all"), "{:.3f}"),
            "",
            "![apfdc](figures/apfdc.png)",
            "",
        ]
    parts += _properties_section(history, reg)
    parts += _coverage_section(workdir, history, df)
    if replays:
        parts += _replay_first_section(workdir, history, figs, replays)
    parts += _generated_section(workdir, history)
    parts += [
        "## How to read this",
        "",
        "`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens "
        "*spent*, not equal nominal budget: every run ends at its first failure, the selecting strategies also run "
        "out of tests, and `adaptive_bayes` also stops when it is confident. A good strategy is high in the first "
        "table of section 2 and low in the second. The sample is the changes: the seeds only draw which recorded "
        "run answers a test and the choices of the strategies that draw at random, so an interval is over the "
        "changes. A clean verdict is worth what the last column of the verdict tables says.",
        "",
    ]
    if replays:
        parts += [
            "Section 7 reads like section 2, with the replay in front: compare a strategy's row there with its row "
            "here. Replay-first, a strategy that orders the whole suite gives a clean verdict once every diverged "
            "test has run and passed; that verdict holds as far as the replay agrees with the recording, which the "
            "first lines of the section measure.",
            "",
        ]
    out = res / "report.md"
    out.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    return out
