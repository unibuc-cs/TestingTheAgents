"""TRACE-Eval: change-aware, cost-bounded regression test selection for LLM agent systems.

Package layout
--------------
- ``traceeval.sut``        the system under test (agents, skills, tools, services, harness, config);
                           it is copied and mutated by the experiment framework, so everything in it
                           uses *relative* imports only.
- ``traceeval.catalog``    the tests and datasets, the catalog of properties, the workflows and the features,
                           and their loader.
- ``traceeval.tracing``    trace recorder (tool calls, skills, config reads, code coverage, cost).
- ``traceeval.llm``        the client of the agents' model (Gemma, Qwen or gpt-oss, served or replayed) and the
                           cache of its answers.
- ``traceeval.scoring``    deterministic scorers, the model judge, and verdict classification.
- ``traceeval.mutation``   the controlled changes (patch operators), the generated ones, and change-set
                           extraction (diff -> components).
- ``traceeval.selection``  the strategies: which tests to run, in what order, and when to stop.
- ``traceeval.experiment`` recording, replay-first, the offline evaluation, the live check, metrics and the
                           report.
- ``traceeval.spec``       spec-driven development layer (clause catalog, checkers, demo PRs); the specs
                           themselves are in ``openspec/specs`` (linked as ``traceeval/specs``).
- ``traceeval.cli``        the ``traceeval`` command.
"""

__version__ = "0.1.0"
