"""Markdown report of a spec-driven-development run: verdict table, per-request briefs and evidence,
resource comparison against "read the repo, run the whole suite", and one figure."""

from pathlib import Path

from .model import RUNG_LABEL

STATUS = {"pass": "pass", "fail": "FAIL", "gap": "gap", "skipped": "skipped"}


def write_report(workdir: Path, specs, briefs: dict, evidence: list[dict], model, out: Path | None = None) -> Path:
    out = Path(out) if out else Path(workdir)
    out.mkdir(parents=True, exist_ok=True)
    fig = _figure(out / "figures", specs, briefs, evidence)
    lines = [
        "# Spec-driven development: evidence report",
        "",
        f"{len(specs)} change requests, {len(evidence)} pull requests, "
        f"{len(model.baseline_runs)} recorded baseline runs "
        f"({model.repo_tokens():,} tokens of source in {len(model.files)} files).",
        "",
        "Each request is a spec: prose intent plus machine-checkable clauses. Each PR is a variant of the system. "
        "The clauses are checked, the change-affected regression tests are run, and the result is an evidence record "
        "with the assurance rung reached per clause "
        "(" + ", ".join(f"{k} {v}" for k, v in RUNG_LABEL.items()) + ").",
        "",
        "## Verdicts",
        "",
        "| request | PR | expected | verdict | what failed / gap | rungs reached | clause runs | "
        "regression cases (of full) | tokens (of full) | s |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for ev in evidence:
        bad = [f"{c['clause_id']} ({c['kind']})" for c in ev["clauses"] if c["status"] in ("fail", "gap")]
        ok = "" if ev["verdict"].startswith(ev["expected"]) else " **(unexpected)**"
        cost = ev["cost"]
        lines.append(
            f"| {ev['request']} | {ev['pr'].split('/', 1)[1]} | {ev['expected']} | **{ev['verdict']}**{ok} | "
            f"{', '.join(bad) or '-'} | {_profile(ev['assurance'])} | {cost['clause_runs']} | "
            f"{cost['regression_selected']} ({cost['full_suite_runs']}) | "
            f"{cost['tokens']:,} ({cost['full_suite_tokens']:,}) | {cost['seconds']} |"
        )
    lines += ["", f"![resources]({fig.relative_to(out).as_posix()})", ""]
    lines += _resources_section(briefs, evidence, model)
    for spec in specs:
        lines += _request_section(spec, briefs[spec.id], [e for e in evidence if e["request"] == spec.id])
    path = out / "report.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def _profile(assurance: dict) -> str:
    return ", ".join(f"{k}×{v}" for k, v in sorted(assurance.items(), reverse=True)) or "-"


def _resources_section(briefs, evidence, model) -> list[str]:
    repo = model.repo_tokens()
    full_runs = len(model.baseline_runs)
    full_tokens = sum(r["tokens"] for r in model.baseline_runs.values())
    ctx = [b["context_tokens"] for b in briefs.values()]
    cruns = [e["cost"]["clause_runs"] for e in evidence]
    rsel = [e["cost"]["regression_selected"] for e in evidence]
    toks = [e["cost"]["tokens"] for e in evidence]
    highest = {}
    for e in evidence:
        if e["verdict"].startswith("accepted"):
            for k, v in e["assurance"].items():
                highest[k] = highest.get(k, 0) + v
    return [
        "## Resources: with the spec vs. without",
        "",
        "| | without a spec (today) | with the spec (this run) |",
        "|---|---|---|",
        f"| context handed to the coding agent | the repository: {repo:,} tokens, {len(model.files)} files | "
        f"the brief: {min(ctx):,}–{max(ctx):,} tokens "
        f"({100 * sum(ctx) / len(ctx) / repo:.0f}% of the repo on average) |",
        f"| checks per PR | full suite: {full_runs} runs, {full_tokens:,} agent tokens | "
        f"clause checks: {min(cruns)}–{max(cruns)} runs; change-selected regression cases: "
        f"{min(rsel)}–{max(rsel)} of {full_runs} ({100 * sum(rsel) / len(rsel) / full_runs:.0f}% on average; "
        "a harness change selects most of the suite, a config change a few cases); "
        f"{100 * sum(toks) / len(toks) / full_tokens:.0f}% of the full-suite tokens in total |",
        "| what the checks say | pass/fail of example tests (L1) | per clause: "
        + ", ".join(f"{v} at {k}" for k, v in sorted(highest.items(), reverse=True))
        + " over the accepted PRs |",
        "| when a PR is wrong | a test fails, somewhere | "
        "the failing clause names the rule, the counterexample or the misplaced code |",
        "",
    ]


def _request_section(spec, brief: dict, evs: list[dict]) -> list[str]:
    lines = [f"## {spec.id}: {spec.title}", "", spec.intent.strip(), "", "**Clauses**", ""]
    for c in spec.clauses:
        lines.append(f"- `{c.id}` ({c.kind}): {c.text}")
    lines += [
        "",
        "**Agent brief (the locate step)**",
        "",
        f"Read {len(brief['read'])} files, ~{brief['context_tokens']:,} tokens "
        f"({100 * brief['context_tokens'] / brief['repo_tokens']:.0f}% of the repository):",
        "",
    ]
    for rel, fns in brief["read"].items():
        lines.append(f"- `{rel}`" + (f" — {', '.join(fns)}" if fns else ""))
    checks = ", ".join(
        f"{c['clause']} ({c['kind']}, {c['runs']} runs"
        + (f", {c['examples']} examples + proof)" if c.get("proof") else ")")
        for c in brief["checks"]
    )
    lines += [
        "",
        f"Checks that will run: {checks}. Recorded runs in scope: {brief['runs_planned']} of {brief['full_suite']}.",
        "",
    ]
    for ev in evs:
        lines += [
            f"### {ev['pr']} — {ev['pr_title']}",
            "",
            f"Verdict: **{ev['verdict']}** (expected {ev['expected']}). {ev['note']}. " + _change_line(ev["change"]),
            "",
            "| clause | kind | rung | status | evidence |",
            "|---|---|---|---|---|",
        ]
        for c in ev["clauses"]:
            lines.append(
                f"| {c['clause_id']} | {c['kind']} | {c['rung']} | {STATUS[c['status']]} | {_md(c['summary'])} |"
            )
        notes = [d for c in ev["clauses"] if c["status"] in ("fail", "gap") for d in c["details"][:8]]
        if notes:
            lines += [""] + [f"- {_md(n)}" for n in notes]
        lines.append("")
    return lines


def _change_line(change: dict) -> str:
    if not change["files"]:
        return "No change: the current code."
    comps = ", ".join(f"`{c}`" for c in change["components"][:8]) + (" …" if len(change["components"]) > 8 else "")
    return f"Change: {len(change['files'])} file(s), {change['diff_lines']} diff lines; components: {comps}."


def _md(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _figure(figdir: Path, specs, briefs, evidence) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figdir.mkdir(parents=True, exist_ok=True)
    ids = [s.id for s in specs]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    repo = next(iter(briefs.values()))["repo_tokens"]
    ctx = [briefs[i]["context_tokens"] for i in ids]
    axes[0].bar(ids, [repo] * len(ids), color="#d9d9d9", label="whole repository")
    axes[0].bar(ids, ctx, color="#3b6ea5", label="agent brief")
    axes[0].set_ylabel("context tokens (approx.)")
    axes[0].set_title("What the coding agent reads")
    full = evidence[0]["cost"]["full_suite_runs"]

    def mean(key, i):
        vals = [e["cost"][key] for e in evidence if e["request"] == i]
        return sum(vals) / max(1, len(vals))

    cl = [mean("clause_runs", i) for i in ids]
    extra = [mean("runs", i) - c for i, c in zip(ids, cl, strict=True)]  # regression cases not already run by a clause
    axes[1].bar(ids, [full] * len(ids), color="#d9d9d9", label="full suite")
    axes[1].bar(ids, cl, color="#3b6ea5", label="clause checks")
    axes[1].bar(ids, extra, bottom=cl, color="#9fbbd9", label="+ change-selected regression")
    axes[1].set_ylabel("agent runs per PR (mean)")
    axes[1].set_title("What is executed per PR")
    for ax, ncol in zip(axes, (2, 3), strict=True):
        ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=ncol)
        ax.tick_params(axis="x", labelsize=8)
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    path = figdir / "resources.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
