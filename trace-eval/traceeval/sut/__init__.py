"""ContentOps: a small multi-agent content-operations platform used as the system under test.

Everything under this package is *mutable experimental material*: the experiment framework copies this
directory, applies controlled mutations (to skills, agent definitions, configuration and harness/tool code),
and loads the copy under a fresh module name. Therefore this package must only use relative imports and
must not import anything from ``traceeval`` outside of ``traceeval.sut``.
"""

from pathlib import Path

SUT_ROOT = Path(__file__).resolve().parent
SUT_VERSION = "1.0.0"
