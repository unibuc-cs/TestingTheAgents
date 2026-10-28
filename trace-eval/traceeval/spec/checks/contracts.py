"""contract clause -> property test (L2) and, for pure functions, a proof attempt (L5).

Two shapes.

A function contract (pure function of the implementation):
    function: services/workflow.py::review_age_ok
    inputs: {age_days: int, max_age_days: int}
    assume: max_age_days >= 1                         # domain, optional
    ensures: result == (0 <= age_days <= max_age_days)
    probe_outside_domain: true                        # report violations outside `assume` as a gap
  Hypothesis searches for a counterexample (L2). Then the function's source is translated into a Z3
  expression - straight-line bodies only: assignments and one return over arithmetic, comparisons and
  boolean operators - and ``assume and not ensures`` is handed to the solver: unsat = proven for all
  inputs (L5), sat = counterexample. Loops, branches and calls are not translated: the clause then
  stays at L2 and the record says so.

A behavioural contract (property of the agent system, quantified over the product model or over data):
    forall: {tool: write_tools}                       # a finite set: write_tools, catalog_cases, [a, b, c],
                                                      # {skill_write_tools: <skill>}; or a Hypothesis strategy
                                                      # {n: {integers: {min_value: 1, max_value: 120}}}
    scenario: {case: "=first_case_calling(tool)", fault_profile: "='ack_timeout_once:' + tool"}
    ensures: run.passed and audit_count(run, tool) == audit_count(baseline_run(run.test_id), tool)
  Model sets are enumerated exhaustively; Hypothesis strategies are sampled (``examples``, default 40).
"""

import ast
import copy
import inspect
import textwrap
import time
from dataclasses import replace

from traceeval.catalog import EvalCase

from ..context import evaluate, resolve
from ..model import ClauseResult

_PY_TYPES = {"int": int, "bool": bool, "str": str}


def check(clause, ctx) -> ClauseResult:
    t0 = time.perf_counter()
    if "function" in clause.data:
        res = _function_contract(clause, ctx)
    else:
        res = _behaviour_contract(clause, ctx)
    res.cost["seconds"] = round(time.perf_counter() - t0, 2)
    return res


# ---------------------------------------------------------------------------- function contracts
def _function_contract(clause, ctx) -> ClauseResult:
    rel, _, qual = clause["function"].partition("::")
    module = rel[: -len(".py")].replace("/", ".")
    try:
        fn = ctx.sut.sub(module)
        for part in qual.split("."):
            fn = getattr(fn, part)
    except (ImportError, AttributeError):
        return ClauseResult(clause.id, "contract", "L2", "fail", f"{clause['function']} does not exist", [])
    names = list(clause["inputs"])
    assume, ensures = clause.get("assume"), clause["ensures"]
    details, status, rung = [], "pass", "L2"
    cost = {"examples": 0}

    # L2: property test with Hypothesis -------------------------------------------------------
    from hypothesis import HealthCheck, Phase, settings
    from hypothesis import strategies as st
    from hypothesis.errors import NoSuchExample

    strat = st.tuples(*[_strategy(st, clause["inputs"][n]) for n in names])
    budget = int(clause.get("examples", 200))

    def violates(values):
        env = dict(zip(names, values, strict=True))
        cost["examples"] += 1
        if assume and not evaluate(assume, dict(env)):
            return False
        try:
            env["result"] = fn(**env)
            return not evaluate(ensures, env)
        except Exception as exc:  # noqa: BLE001 - an exception on in-domain input is a violation
            env["result"] = f"raised {type(exc).__name__}: {exc}"
            return True

    try:
        cx = find(strat, violates, budget, settings, Phase, HealthCheck)
        env = dict(zip(names, cx, strict=True))
        try:
            env["result"] = fn(**env)
        except Exception as exc:  # noqa: BLE001
            env["result"] = f"raised {type(exc).__name__}"
        details.append(f"counterexample {env}: '{ensures}' is false")
        status = "fail"
    except NoSuchExample:
        details.append(f"{cost['examples']} examples, no counterexample")

    # L5: symbolic execution + solver ----------------------------------------------------------
    proof = _prove(fn, names, clause["inputs"], assume, ensures, bool(clause.get("probe_outside_domain")))
    details.extend(proof["notes"])
    if proof["proved"] or proof["counterexample"]:
        rung = "L5"  # the solver had the last word, either way
    if proof["counterexample"]:
        status = "fail"
    if proof["gap"] and status == "pass":
        status = "gap"
    summary = _summary(
        status,
        rung,
        proof,
        cost["examples"],
        found_by_test=status == "fail" and details[0].startswith("counterexample"),
    )
    return ClauseResult(clause.id, "contract", rung, status, summary, details, cost)


def find(strat, predicate, budget, settings, Phase, HealthCheck):
    from hypothesis import find as h_find

    return h_find(
        strat,
        predicate,
        settings=settings(
            max_examples=budget,
            database=None,
            phases=(Phase.generate, Phase.shrink),
            suppress_health_check=list(HealthCheck),
            deadline=None,
        ),
    )


def _strategy(st, spec):
    if isinstance(spec, dict):  # {integers: {min_value: 1, max_value: 120}}
        ((name, kwargs),) = spec.items()
        return getattr(st, name)(**(kwargs or {}))
    return {"int": st.integers(), "bool": st.booleans(), "str": st.text(max_size=80)}[spec]


def _summary(status, rung, proof, examples, found_by_test=False):
    if status == "fail":
        by = [w for w, hit in (("property test", found_by_test), ("solver", proof["counterexample"])) if hit]
        return "counterexample found (" + " and ".join(by) + ")"
    if rung == "L5":
        s = "proven for all inputs in the stated domain (solver: unsat)"
    else:
        s = f"holds on {examples} generated examples; " + (proof["why_not"] or "no proof attempted")
    if status == "gap":
        s += "; GAP outside the stated domain"
    return s


def _prove(fn, names, inputs, assume, ensures, probe):
    out = {"proved": False, "counterexample": None, "gap": None, "notes": [], "why_not": ""}
    try:
        import z3
    except ImportError:
        out["why_not"] = "z3 not installed"
        return out
    if any(inputs[n] not in ("int", "bool") for n in names):
        out["why_not"] = "inputs are not int/bool"
        return out
    sym = {n: (z3.Int(n) if inputs[n] == "int" else z3.Bool(n)) for n in names}
    try:
        result = _symbolic_call(fn, sym, z3)
        env = dict(sym, result=result, z3=z3)
        a = _z3_eval(assume, env) if assume else z3.BoolVal(True)
        e = _z3_eval(ensures, env)
    except Exception as exc:  # noqa: BLE001 - not translatable
        out["why_not"] = f"no proof: {exc}"
        return out
    s = z3.Solver()
    s.add(a, z3.Not(e))
    verdict = s.check()
    if verdict == z3.unsat:
        out["proved"] = True
        out["notes"].append("solver: assume ∧ ¬ensures is unsat -> the post-condition holds for every input")
    elif verdict == z3.sat:
        m = s.model()
        cx = {n: m.eval(sym[n], model_completion=True) for n in names}
        out["counterexample"] = cx
        out["notes"].append(f"solver counterexample: {cx}")
    else:
        out["why_not"] = "solver gave up"
    if probe and assume and out["proved"]:
        s2 = z3.Solver()
        s2.add(z3.Not(a), z3.Not(e))
        if s2.check() == z3.sat:
            m = s2.model()
            cx = {n: m.eval(sym[n], model_completion=True) for n in names}
            out["gap"] = cx
            out["notes"].append(
                f"outside the domain '{assume}' the post-condition fails, e.g. {cx}: the spec says nothing about "
                "such inputs - decide and widen the clause (spec gap)"
            )
    return out


class _ToZ3(ast.NodeTransformer):
    """Rewrite Python boolean operators and chained comparisons into z3 calls."""

    def _call(self, name, args):
        return ast.Call(ast.Attribute(ast.Name("z3", ast.Load()), name, ast.Load()), args, [])

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        return self._call("And" if isinstance(node.op, ast.And) else "Or", node.values)

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        return self._call("Not", [node.operand]) if isinstance(node.op, ast.Not) else node

    def visit_Compare(self, node):
        self.generic_visit(node)
        if len(node.ops) == 1:
            return node
        parts, left = [], node.left
        for op, right in zip(node.ops, node.comparators, strict=True):
            parts.append(ast.Compare(left, [op], [right]))
            left = right
        return self._call("And", parts)


def _z3_eval(expr: str, env: dict):
    return _z3_eval_node(ast.parse(expr, mode="eval").body, env)


def _z3_eval_node(node: ast.AST, env: dict):
    tree = ast.fix_missing_locations(_ToZ3().visit(ast.Expression(body=copy.deepcopy(node))))
    return eval(compile(tree, "<z3>", "eval"), {"__builtins__": {}}, env)


def _symbolic_call(fn, sym: dict, z3):
    """Translate a straight-line pure function (assignments, then one return) into a z3 expression."""
    fdef = ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]
    env = dict(sym, z3=z3)
    body = fdef.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # docstring
    for stmt in body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            env[stmt.targets[0].id] = _z3_eval_node(stmt.value, env)
        elif isinstance(stmt, ast.Return):
            return _z3_eval_node(stmt.value, env)
        else:
            raise ValueError(
                f"line {stmt.lineno} is a {type(stmt).__name__}; only assignments and a return are translated"
            )
    raise ValueError("function has no return statement")


# ---------------------------------------------------------------------------- behavioural contracts
def _behaviour_contract(clause, ctx) -> ClauseResult:
    ((var, domain),) = clause["forall"].items()
    scenario, ensures = clause["scenario"], clause["ensures"]
    details, failures, skipped, n = [], [], [], 0

    def evaluate_one(value) -> bool:
        """True when the property holds (or the scenario is not applicable)."""
        nonlocal n
        env = ctx.env(**{var: value})
        sc = resolve(scenario, env)
        case = _make_case(sc, ctx)
        if case is None:
            skipped.append(f"{var}={value!r}: no recorded run exercises it")
            return True
        n += 1
        rec = ctx.run(case, fault_profile=sc.get("fault_profile"), cache=False)
        env = ctx.env(run=rec, **{var: value, "case": case.id})
        try:
            ok = bool(evaluate(ensures, env))
        except Exception as exc:  # noqa: BLE001
            ok, rec["failed_checks"] = False, [f"{type(exc).__name__}: {exc}"]
        if not ok:
            failures.append(
                f"{var}={value!r} (case {case.id}, fault {sc.get('fault_profile') or 'healthy'}): post-condition false"
                + (f"; failed checks {rec['failed_checks']}" if rec["failed_checks"] else "")
            )
        return ok

    values = ctx.model.model_set(domain, ctx.catalog)
    if values is not None:  # a finite set (literal or from the product model): enumerate exhaustively
        for v in values:
            evaluate_one(v)
        details.append(
            f"enumerated {len(values)} values {values}"
            + (f", {len(skipped)} without a recorded run" if skipped else "")
        )
    else:  # a Hypothesis strategy: sample
        from hypothesis import HealthCheck, Phase, settings
        from hypothesis import strategies as st
        from hypothesis.errors import NoSuchExample

        try:
            cx = find(
                _strategy(st, domain),
                lambda v: not evaluate_one(v),
                int(clause.get("examples", 40)),
                settings,
                Phase,
                HealthCheck,
            )
            failures = list(dict.fromkeys(f for f in failures if f"{var}={cx!r}" in f)) or failures[-1:]
        except NoSuchExample:
            pass
        details.append(f"{n} generated scenarios")
    details.extend(failures[:8] + skipped[:3])
    status = "fail" if failures else ("gap" if skipped else "pass")
    summary = ("counterexample found" if failures else f"holds over {n} runs") + (
        f"; {len(skipped)} value(s) not exercised by any recorded run" if skipped else ""
    )
    return ClauseResult(clause.id, "contract", "L2", status, summary, details, {"runs": n})


def _make_case(sc: dict, ctx) -> EvalCase | None:
    """A scenario is a catalog case id (with optional overrides) or an inline case definition."""
    base = sc.get("case")
    if isinstance(base, str):
        case = ctx.catalog[base]
    elif isinstance(base, dict):
        case = EvalCase(
            id=base.get("id", "inline"),
            name=base.get("name", "inline"),
            agent=base["agent"],
            request=base["request"],
            context=dict(base.get("context", {})),
            fixture_patch=dict(base.get("fixture_patch", {})),
            expect=dict(base.get("expect", {})),
        )
    else:
        return None
    if sc.get("context") or sc.get("fixture_patch"):
        case = replace(
            case,
            context={**case.context, **sc.get("context", {})},
            fixture_patch={**case.fixture_patch, **sc.get("fixture_patch", {})},
        )
    return case
