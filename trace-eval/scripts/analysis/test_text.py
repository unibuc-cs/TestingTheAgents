"""What is "the text of a test"? ``EvalCase.text()`` joins the id, name, request, context, properties, workflow and
the hand-declared dependency block, which shares words with the component ids of a change. ``ir_tfidf`` and the
adaptive method are replayed with the declared block taken out of the text, and with the name and request alone, in
this process only.

    python scripts/analysis/test_text.py [recording]               # default runs/gemma8
"""

import json

import pandas as pd
from replaylib import CachedAB, leave_one_out, load, recording, replay

from traceeval.catalog.loader import EvalCase
from traceeval.selection import get_strategy

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)

h, catalog = load(recording())
variants = sorted(h.variants)


def without_declared(case):
    parts = [case.id, case.name, case.request, json.dumps(case.context, default=str), " ".join(case.properties)]
    return " ".join([*parts, case.workflow or ""])


def name_and_request(case):
    return " ".join([case.name, case.request])


def show(label):
    columns = []
    for name in ("ir_tfidf", "adaptive_bayes"):
        # a new instance of the adaptive method each time: it keeps the model it built from the text
        strategy = CachedAB() if name == "adaptive_bayes" else get_strategy(name)
        d = replay(h, catalog, strategy, variants, leave_one_out(variants))
        # as in the report: detection over the revealed regressions, tokens as a mean over all changes
        detected = d[d.is_regression].groupby("budget").detected.mean()
        columns.append(detected.round(3).rename(f"{name}, detected"))
        columns.append(d.groupby("budget").cost_fraction.mean().round(3).rename(f"{name}, tokens over all changes"))
    print(f"\n=== the text of a test: {label}")
    print(pd.concat(columns, axis=1).T.to_string())


original = EvalCase.text
try:
    show("as in the code (id, name, request, context, properties, workflow, declared block)")
    EvalCase.text = without_declared
    show("without the declared block")
    EvalCase.text = name_and_request
    show("name and request only")
finally:
    EvalCase.text = original
