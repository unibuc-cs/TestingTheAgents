"""Markdown report (+ three figures) from the replay results: ground truth, detection vs. cost,
waste on benign changes, stopping accuracy, APFD, properties, and coverage (of the suite and of each change)."""

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from traceeval.catalog import load_catalog, load_properties  # noqa: E402

from .history import History  # noqa: E402

ORDER = [
    "full",
    "random",
    "declared",
    "ir_tfidf",
    "observed",
    "observed_diverse",
    "cost_aware",
    "history_ml",
    "adaptive_bayes",
    "adaptive_bayes_tfidf",  # the method's variants, shown when a replay included them
    "adaptive_bayes_notext",
    "adaptive_bayes_nomandatory",
]
COLOR = {
    "full": "#9e9e9e",
    "random": "#bdbdbd",
    "declared": "#e6a100",
    "ir_tfidf": "#7b61ff",
    "observed": "#1f77b4",
    "observed_diverse": "#17becf",
    "cost_aware": "#2ca02c",
    "history_ml": "#d62728",
    "adaptive_bayes": "#111111",
    "adaptive_bayes_tfidf": "#555555",
    "adaptive_bayes_notext": "#888888",
    "adaptive_bayes_nomandatory": "#8c564b",
}
BUDGET_TICKS = [2, 5, 10, 20, 30, 50, 100]


def _axes(ax, title, xlabel, ylabel):
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25)


def fig_detection_vs_cost(df, out):
    """Detection rate against tokens actually spent: strategies that select or stop sit to the left."""
    reg = df[df.is_regression]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for name in ORDER:
        sub = reg[reg.strategy == name]
        if sub.empty:
            continue
        g = sub.groupby("budget").agg(cost=("cost_fraction", "mean"), det=("detected", "mean"))
        ax.plot(
            g["cost"] * 100,
            g["det"] * 100,
            marker="o",
            ms=4,
            label=name,
            color=COLOR.get(name),
            lw=2.2 if name == "adaptive_bayes" else 1.4,
        )
    _axes(
        ax,
        "Regression detection rate vs. tokens actually spent",
        "tokens spent (% of full suite)",
        "changes detected (%)",
    )
    ax.set_xscale("log")
    ax.set_xticks(BUDGET_TICKS)
    ax.set_xticklabels([str(b) for b in BUDGET_TICKS])
    ax.set_ylim(0, 102)
    ax.legend(fontsize=8, ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_benign_waste(df, out):
    ben = df[~df.is_regression]
    budgets = sorted(ben.budget.unique())
    names = [n for n in ORDER if n in set(ben.strategy)]
    fig, ax = plt.subplots(figsize=(7.5, 4))
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
    ax.set_xticks([i + width * (len(budgets) - 1) / 2 for i in range(len(names))])
    ax.set_xticklabels(names, rotation=25, ha="right", fontsize=8)
    _axes(ax, "Tokens spent on benign changes (lower is better)", "", "tokens spent (% of full suite)")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_apfdc(pr, out):
    names = [n for n in ORDER if n in set(pr.strategy)]
    fig, ax = plt.subplots(figsize=(7.5, 4))
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


def _properties_section(history, reg) -> list[str]:
    """Section 5: every property of the catalog with its tests' pass rate on the original app against its
    threshold, and how much of the properties a change breaks each strategy exercised."""
    cases = {c.id: c for c in load_catalog()}
    rows = []
    for p in load_properties().values():
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


def _coverage_section(workdir, history, df) -> list[str]:
    """Section 6: coverage of the test suite by dimension, and change coverage per strategy over every change (it
    needs no ground truth)."""
    from traceeval.sut import SUT_ROOT

    from .coverage import suite_coverage

    sut_dir = workdir / "variants" / "baseline" / "sut"
    cases = {c.id: c for c in load_catalog()}
    rows = suite_coverage(history, cases, load_properties(), sut_dir if sut_dir.exists() else SUT_ROOT)
    table = ["| dimension | components | declared | observed | not covered |", "|---|---|---|---|---|"]
    for r in rows:
        gaps = ", ".join(r["not covered"][:8]) + (" ..." if len(r["not covered"]) > 8 else "")
        table.append(
            f"| {r['dimension']} | {r['components']} | {'' if r['declared'] is None else r['declared']} | "
            f"{r['observed']} | {gaps or r.get('detail', '')} |"
        )
    out = [
        "## 6. Coverage",
        "",
        "Coverage of the test suite: per dimension, how many components the tests declare and the traces show, and "
        "what no test covers (a workflow is declared by the tests that name it and observed when a run delegates to "
        "exactly its agents in order; execution paths are the distinct agent and tool sequences; risk lists tests per "
        "level):",
        "",
        *table,
        "",
    ]
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
    return out


def write_report(workdir: Path) -> Path:
    workdir = Path(workdir)
    res, figs = workdir / "results", workdir / "results" / "figures"
    figs.mkdir(exist_ok=True, parents=True)
    history = History.load(workdir)
    df = pd.read_csv(res / "replay.csv")
    pr = pd.read_csv(res / "prioritization.csv") if (res / "prioritization.csv").exists() else None
    reg, ben = df[df.is_regression], df[~df.is_regression]

    fig_detection_vs_cost(df, figs / "detection_vs_cost.png")
    fig_benign_waste(df, figs / "benign_waste.png")
    if pr is not None:
        fig_apfdc(pr, figs / "apfdc.png")

    meta = history.mutation_meta
    truth_rows, sane = [], True
    for v in sorted(history.variants, key=lambda v: (meta.get(v, {}).get("category", ""), v)):
        n = len(history.revealing_tests(v))
        expected = bool(meta.get(v, {}).get("expected_regression"))
        sane &= (n > 0) == expected
        truth_rows.append(
            f"| `{v}` | {meta.get(v, {}).get('category', '?')} | {'regression' if expected else 'benign'} | {n} |"
        )
    summ = history.summary()
    stops = df[df.strategy == "adaptive_bayes"].groupby(["is_regression", "stop_reason"]).size().unstack(fill_value=0)
    c2d = reg[reg.detected].groupby("strategy")["cost_to_detect_fraction"].mean().reindex(ORDER).dropna()

    parts = [
        "# TRACE-Eval experiment report",
        "",
        f"`{workdir.as_posix()}` · {summ['tests']} tests · {summ['variants']} changes · {summ['baseline_reps']} "
        f"baseline repetitions · full suite = {summ['total_tokens_full_suite']:,} tokens · "
        f"tests failing on the original app: {len(summ['failing_tests'])} · "
        f"runs the environment broke, left out: {summ['infra_invalid_runs']}",
        "",
        "## 1. Ground truth — which changes are revealed by how many tests",
        "",
        "| change | category | expected | revealing tests |",
        "|---|---|---|---|",
        *truth_rows,
        "",
        "Testbed sanity (every regression revealed by ≥1 test, no benign change revealed): "
        f"**{'OK' if sane else 'VIOLATED'}**.",
        "",
        "## 2. Detection within a budget",
        "",
        "Fraction of regression-inducing changes detected, by nominal budget (% of full-suite tokens):",
        "",
        _by_budget(reg, "detected"),
        "",
        "Tokens actually spent on those changes (fraction of the full suite):",
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
        "## 3. Benign changes — wasted budget and stopping",
        "",
        _by_budget(ben, "cost_fraction", "{:.3f}"),
        "",
        "![benign waste](figures/benign_waste.png)",
        "",
        "Stop reasons of `adaptive_bayes` (rows: is the change a regression?):",
        "",
        _table(stops, "{:d}") if not stops.empty else "(no adaptive runs)",
        "",
    ]
    if pr is not None:
        g = pr.groupby("strategy")[["apfd", "apfdc", "selection_recall", "selected_cost_fraction"]].mean()
        parts += [
            "## 4. Prioritization and selection quality",
            "",
            "APFD / cost-cognizant APFD of the complete order; selection recall = revealing tests inside the selected "
            "subset; selected cost = what that subset costs:",
            "",
            _table(g.reindex(ORDER).dropna(how="all"), "{:.3f}"),
            "",
            "![apfdc](figures/apfdc.png)",
            "",
        ]
    parts += _properties_section(history, reg)
    parts += _coverage_section(workdir, history, df)
    parts += [
        "## How to read this",
        "",
        "`detected` counts *changes* (one failing revealing test is enough). Compare strategies at equal tokens "
        "*spent*, not equal nominal budget: `declared`/`observed` select and run out of tests, `adaptive_bayes` stops "
        "when it is confident, the others always spend the whole budget. A good strategy is high in section 2 and low "
        "in section 3.",
        "",
    ]
    out = res / "report.md"
    out.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    return out
