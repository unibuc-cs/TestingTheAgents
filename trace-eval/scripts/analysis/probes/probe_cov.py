"""Probe: which SUT modules are imported lazily, and which test gets their module-level lines."""

import sys

from traceeval.catalog import load_catalog
from traceeval.experiment.runner import run_suite
from traceeval.experiment.sutloader import load_sut
from traceeval.sut import SUT_ROOT

sut = load_sut(SUT_ROOT)
loaded = sorted(k[len(sut.name) + 1 :] for k in sys.modules if k.startswith(sut.name + "."))
print("eagerly imported:", loaded)

cases = load_catalog()[:4]
print("cases:", [c.id for c in cases])
records = run_suite(sut, cases, reps=2, variant="baseline", backend="replay", config_overrides=None, with_coverage=True)
after = sorted(k[len(sut.name) + 1 :] for k in sys.modules if k.startswith(sut.name + "."))
print("imported during the runs:", sorted(set(after) - set(loaded)))
for rec in records:
    deps = rec["deps"]
    module_level = sorted(d for d in deps if d.startswith("code:") and "::" not in d)
    n_lines = sum(1 for d in deps if d.startswith("line:"))
    state_lines = sorted(int(d.rsplit(":", 1)[1]) for d in deps if d.startswith("line:services/state.py:"))
    print(
        rec["test_id"],
        "rep",
        rec["rep"],
        rec["classification"],
        "lines",
        n_lines,
        "module-level comps",
        module_level,
        "state.py lines",
        len(state_lines),
        state_lines[:12],
    )
