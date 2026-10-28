"""Spec-driven development layer: machine-checkable specification clauses for the ContentOps SUT.

A *spec* (``traceeval/specs/FS-*.yaml``) is one change request written as prose intent plus a list of
clauses. Every clause has a kind, and every kind has exactly one checker that turns it into evidence:

    setting    a typed constraint on a configuration key            -> static check           (L4)
    contract   pre/post-condition on a function or on agent behaviour -> property test / proof (L2 / L5)
    trace      a temporal rule over recorded runs                    -> monitor                (L3)
    example    one concrete scenario with expected outcome           -> test                   (L1)
    placement  where code must (not) live                            -> static lint            (L4)

``runner.evaluate_pr`` applies a spec to a PR (a variant of the SUT), producing an *evidence record*;
``runner.agent_brief`` is the "locate" step: what a coding agent needs to read and which checks will
run, with the resource numbers. ``report`` renders everything as markdown.
"""

from .model import SPECS_ROOT, Clause, Spec, load_spec, load_specs

__all__ = ["SPECS_ROOT", "Clause", "Spec", "load_spec", "load_specs"]
