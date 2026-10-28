"""TRACE-Eval: change-aware, cost-bounded regression test selection for LLM agent systems.

Package layout
--------------
- ``traceeval.sut``        the system under test (agents, skills, tools, services, harness, config);
                           it is copied and mutated by the experiment framework, so everything in it
                           uses *relative* imports only.
- ``traceeval.catalog``    the eval catalog (scenario tests + dataset-style evals) and its loader.
- ``traceeval.tracing``    trace recorder (tool calls, skills, config reads, code coverage, cost) + OTel export.
- ``traceeval.scoring``    deterministic scorers and verdict classification.
- ``traceeval.mutation``   controlled mutations (patch operators) and change-set extraction (diff -> components).
- ``traceeval.selection``  selection / prioritization / stopping strategies.
- ``traceeval.experiment`` record-then-replay experiment runner, metrics, report.
"""

__version__ = "0.1.0"
