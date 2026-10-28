"""Markdown report (+ three figures) from the replay results: ground truth, detection vs. cost,
waste on benign changes, stopping accuracy, APFD."""

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

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
        f"`{workdir}` · {summ['tests']} tests · {summ['variants']} changes · {summ['baseline_reps']} baseline "
        f"repetitions · full suite = {summ['total_tokens_full_suite']:,} tokens · {len(summ['flaky_tests'])} flaky "
        "tests at baseline",
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
    out.write_text("\n".join(parts))
    return out
