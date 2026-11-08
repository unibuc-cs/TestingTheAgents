"""What a checker gets: the loaded variant, its product model, the catalog, a run cache with cost
accounting, and the expression environment in which clause expressions (``where``, ``ensures``,
``=...`` values) are evaluated."""

import builtins
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date

from traceeval.catalog import EvalCase
from traceeval.experiment.executor import run_case

from .product import ProductModel

SAFE_BUILTINS = {
    n: getattr(builtins, n)
    for n in ("len", "min", "max", "sum", "any", "all", "sorted", "abs", "str", "int", "bool", "list", "set", "round")
}


class Obj(dict):
    """Attribute access over dicts for clause expressions: ``event.args.page_id``; missing keys read as None."""

    def __getattr__(self, name):
        return wrap(self.get(name))


def wrap(value):
    """Wrap dicts (also inside lists) in Obj; anything else is returned as it is."""
    if isinstance(value, Obj):
        return value
    if isinstance(value, dict):
        return Obj(value)
    if isinstance(value, list):
        return [wrap(v) for v in value]
    return value


def evaluate(expr: str, env: dict):
    """Evaluate a clause expression. Specs are trusted repository content; builtins are limited anyway."""
    return eval(compile(str(expr), "<clause>", "eval"), {"__builtins__": SAFE_BUILTINS}, env)


def resolve(value, env: dict):
    """Strings starting with '=' are expressions ('==' is left alone); containers are resolved recursively."""
    if isinstance(value, str) and value.startswith("=") and not value.startswith("=="):
        return evaluate(value[1:], env)
    if isinstance(value, dict):
        return {k: resolve(v, env) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, env) for v in value]
    return value


@dataclass
class CheckContext:
    sut: object  # LoadedSUT of the variant under evaluation
    model: ProductModel  # static facts of the variant + dynamic facts of the baseline
    catalog: dict[str, EvalCase]
    variant: str = "baseline"
    backend: str | None = None  # who plays the agents (run_case's backend; None: its default)
    workers: int = 1  # cases run at once by run_many
    runs: dict = field(default_factory=dict)  # (test_id, fault_profile) -> record
    cost: Counter = field(default_factory=Counter)  # runs, tokens

    # ---------------------------------------------------------------- running cases on the variant
    def run(self, case: EvalCase, fault_profile: str | None = None, cache: bool = True) -> dict:
        """Run a case on the variant and count its cost. Catalog cases run once per PR (trace clauses and the
        regression tests share them); scenarios (contract and example clauses) pass ``cache=False`` because
        they may patch the case, and a patched case keeps its catalog id."""
        key = (case.id, fault_profile)
        if cache and key in self.runs:
            return self.runs[key]
        rec = self._run_case(case, fault_profile)
        self.cost["runs"] += 1
        self.cost["tokens"] += rec["tokens"]
        if cache:
            self.runs[key] = rec
        return rec

    def _run_case(self, case: EvalCase, fault_profile: str | None = None) -> dict:
        return run_case(
            self.sut, case, backend=self.backend, variant=self.variant, fault_profile=fault_profile, keep_state=True
        )

    def run_many(self, ids: list[str]) -> dict[str, dict]:
        """``run`` for several catalog cases, ``workers`` of them at a time (a served model batches them)."""
        todo = [t for t in ids if (t, None) not in self.runs]
        if self.workers > 1 and len(todo) > 1:
            # the threads only run the cases; their records and costs are stored here, in one thread
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                for tid, rec in zip(todo, pool.map(lambda t: self._run_case(self.catalog[t]), todo), strict=True):
                    self.cost["runs"] += 1
                    self.cost["tokens"] += rec["tokens"]
                    self.runs[(tid, None)] = rec
        return {tid: self.run(self.catalog[tid]) for tid in ids}  # cache hits, or one at a time when not parallel

    # ---------------------------------------------------------------- expression environment
    def env(self, run: dict | None = None, **extra) -> dict:
        """The names a clause expression may use: the helpers below, ``run`` (the record, if any) and ``extra``."""
        env = {
            "config": self.model.config_value,
            "approval_age": approval_age,
            "expected_broken": expected_broken,
            "audit_count": audit_count,
            "applied": applied,
            "token_owner": token_owner,
            "title_of_length": title_of_length,
            "first_case_calling": lambda tool: next(iter(self.model.cases_calling([tool], ok_only=True)), None),
            "baseline_run": lambda test_id: wrap(with_context(self.model.baseline_runs[test_id])),
        }
        if run is not None:
            env["run"] = wrap(with_context(run))
        env.update(extra)
        return env


def with_context(run: dict) -> dict:
    """The run record plus ``context`` (the request context recorded in its run.start event)."""
    start = next((e for e in run.get("events", []) if e.get("kind") == "run.start"), {})
    return dict(run, context=start.get("context", {}))


# -------------------------------------------------------------------- helpers usable in clause expressions
def approval_age(run, page_id: str) -> int:
    """Days between the page's recorded approval and the fixture's ``today`` (state before the run)."""
    state = run["initial_state"]
    page = state["pages"].get(page_id)
    if page is None:
        raise ValueError(f"unknown page {page_id}")
    approved_on = (page.get("review") or {}).get("approved_on")
    if not approved_on:
        raise ValueError(f"page {page_id} has no recorded approval date")
    return (date.fromisoformat(state["today"]) - date.fromisoformat(approved_on)).days


def expected_broken(run, page_id: str) -> int:
    """Independent oracle: how many of the page's links/assets are broken according to the state's own tables
    (state at the end of the run: pages may be created or edited before they are validated)."""
    state = run["final_state"]
    page = state["pages"][page_id]
    paths = {p["path"] for p in state["pages"].values()}
    broken = 0
    for link in page.get("links", []):
        if link.startswith(("http://", "https://")):
            broken += state.get("external_links", {}).get(link, "unknown") != "ok"
        elif link.startswith("asset:"):
            broken += link[len("asset:") :] not in state["assets"]
        else:
            broken += link not in paths
    broken += sum(a not in state["assets"] for a in page.get("assets", []))
    return broken


def audit_count(run, action: str, **match) -> int:
    """Audit entries of ``action`` at the end of the run whose fields equal ``match``."""
    return sum(
        1
        for e in run["final_state"].get("audit", [])
        if e.get("action") == action and all(e.get(k) == v for k, v in match.items())
    )


def token_owner(run, token) -> str | None:
    """The user whose approval token ``token`` is, according to the fixture's user table (None if nobody's)."""
    if not token:
        return None
    users = run["initial_state"]["users"]
    return next((uid for uid, u in users.items() if u.get("approval_token") == token), None)


def applied(run, tool: str) -> bool:
    """Did the run call ``tool`` successfully?"""
    return any(
        e.get("kind") == "tool.call" and e.get("tool") == tool and e.get("status") == "ok" for e in run["events"]
    )


def title_of_length(n: int) -> str:
    """A page title exactly ``n`` characters long (boundary values for length limits)."""
    return ("Example title " * (n // 14 + 1))[:n]
