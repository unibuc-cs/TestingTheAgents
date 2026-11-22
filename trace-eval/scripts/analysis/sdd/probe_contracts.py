"""Probe 1: what the function-contract checker reports for functions the Z3 translation mis-reads.
Read-only with respect to the repository: imports the checker, runs it on scratch functions."""

import importlib
import sys

import probe_fns

from traceeval.spec.checks import contracts
from traceeval.spec.model import Clause

sys.stdout.reconfigure(encoding="utf-8")  # the checker's details use logic symbols a Windows console cannot encode


class FakeSut:
    def sub(self, module):
        return importlib.import_module(module)


class Ctx:
    sut = FakeSut()


def run(name, inputs, ensures, assume=None, examples=200):
    data = {"function": f"probe_fns.py::{name}", "inputs": inputs, "ensures": ensures, "examples": examples}
    if assume:
        data["assume"] = assume
    res = contracts.check(Clause(name, "contract", data=data), Ctx())
    print(f"--- {name}: ensures {ensures!r}" + (f" assume {assume!r}" if assume else ""))
    print(f"    status={res.status} rung={res.rung} summary={res.summary}")
    for d in res.details:
        print(f"    . {d}")


# 1. conditional expression on an equality: bool(z3 ==) is structural, so the translation silently takes the else-branch
run("f_ifexp", {"a": "int", "b": "int"}, "result == 0")
print("    real value at a=1000003, b=0:", probe_fns.f_ifexp(1000003, 0))
run("f_ifexp_bool", {"a": "int", "b": "int"}, "result == (a < b)")
print("    real value at a=1000003, b=0:", probe_fns.f_ifexp_bool(1000003, 0), "expected by ensures:", 1000003 < 0)
run("f_ne_ifexp", {"a": "int", "b": "int"}, "result == 0")
print("    real value at a=0, b=0:", probe_fns.f_ne_ifexp(0, 0))

# 2. true division: Python float division vs z3 integer division
run("f_truediv", {"n": "int"}, "result == True")
print("    real value at n=1000003:", probe_fns.f_truediv(1000003))

# 3. membership test: evaluated with Python semantics over z3 terms
run("f_in", {"x": "int"}, "result == (x == 1 or x == 2)")
print("    real values:", {x: probe_fns.f_in(x) for x in (0, 1, 2, 3)})

# 4. modulo with a negative divisor: Python result takes the divisor's sign, SMT-LIB mod is never negative
run("f_mod_neg", {"a": "int"}, "result == True")
print("    real values:", {a: probe_fns.f_mod_neg(a) for a in (-4, -1, 0, 1, 2, 5)})

# 5. floor division
run("f_floordiv", {"a": "int"}, "result == True")

# 6. the demo's own function, for reference
run(
    "f_review_age_ok",
    {"age_days": "int", "max_age_days": "int"},
    "result == (0 <= age_days <= max_age_days)",
    assume="max_age_days >= 1",
    examples=300,
)
