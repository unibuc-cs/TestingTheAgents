"""Test setup: model answers come from the committed cassette, tests/cassettes/gemma.jsonl.

Cases replay it (no model) unless TRACEEVAL_BACKEND names a model backend: ``TRACEEVAL_BACKEND=vllm pytest``
answers from the cassette what it can, asks Gemma for the rest and adds those answers to the cassette.
"""

import os

from traceeval.llm.chat import CASSETTE

os.environ["TRACEEVAL_CACHE"] = str(CASSETTE)
