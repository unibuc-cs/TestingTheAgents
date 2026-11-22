# Proposed changes: three workflow specs for the implementability study

Three change requests for new multi-agent workflows of ContentOps, written against the clause catalog
(`traceeval/spec/catalog.yaml`) like the specs in `openspec/specs/`. Two can be implemented; one cannot. The specs
themselves do not say which: this file is the ground truth, kept apart from them so that a checker is not handed
the answer.

| change | spec | workflow | expected |
|---|---|---|---|
| `add-licence-expiry-sweep-workflow` | FS-0301 | W7: assets → brand → publishing | implementable |
| `add-page-retirement-workflow` | FS-0302 (and a delta of FS-0214) | W8: brand → authoring → publishing | implementable |
| `add-instant-bulk-takedown-workflow` | FS-0303 | W9: publishing (per page) → translation | **not implementable** |
| `add-scheduled-batch-republish-workflow` | FS-0304 | W10: orchestrator → authoring → brand → publishing | implementable | Haiku 4.5 made

Nothing runs these specs yet: `traceeval sdd` loads `openspec/specs/fs-*/spec.md` only, and every spec there needs
its PRs in `traceeval/spec/prs.py`. Each new spec has the heading and `## Purpose` the loader needs, so
`traceeval.spec.model.load_spec(path)` reads it, and `openspec validate --all --strict` accepts all three changes.

## What each implementable spec introduces

Against today's product model, `validate_spec` reports:

- **FS-0301**: one note (the function `replacement_allowed`) and errors for the two tools it introduces
  (`find_asset_usage`, `replace_asset`); the validator treats an unknown tool as an error, since no earlier request
  added one. Its three scenarios are inline cases.
- **FS-0302**: one note (the function `may_take_down`) and no error. It adds no tool, agent or setting. It changes
  one existing requirement, in FS-0214: a legal takedown now leaves up a page that a live page links to. The
  recorded takedowns (p7, p13, p14) are unaffected: no page links to them in the starting data.
- **FS-0304**: one note (the function `can_batch_republish`) and no error. It introduces one setting
  (`republish.batch_window_minutes`), one service function, and scheduled times on pages. It does not change any
  existing spec. Eight scenarios: two setting checks, two contract proofs (batch conflict checker, budgets
  respected), two inline orchestrator cases (batch succeeds, batch rejects on conflict), one always-on audit, one
  forbidden-call audit.

All three keep the budgets, the dispatcher, the approval mechanism and the rule that only the orchestrator delegates.

## Why FS-0303 cannot be implemented

Its proposal states that no existing spec changes. Under that condition four of its demands cannot be met, each for
a different kind of reason.

1. **Batch size against the step budgets (arithmetic, with the runtime's counting).** The spec asks for one plan and
   one successful delegation to publishing per page, for every `n` up to 60, and pins `runtime.max_tool_calls` ≤ 12
   and `runtime.max_run_tool_calls` ≤ 40. The runtime counts every tool call and every delegation as a step
   (`harness/runtime.py::Runtime._run_agent`). The orchestrator alone needs `1 + n` steps, so `n ≤ 11`; the run
   needs at least `1 + n + n` (plan, delegations, takedowns), so `n ≤ 19`. For `n` from 20 to 60 the clause
   `property_over_range:n` cannot hold together with the two `setting_in_range` clauses and FS-0210 ("No request
   exceeds its budget", "Every request ends with an answer, not at a budget").
2. **No approval against the plan rule of FS-0201 (two trace rules that exclude each other).** FS-0303 requires
   `make_plan` once, a successful `unpublish_page`, and no `request_approval` in the run. FS-0201 ("Nothing goes
   live or down in a plan without an approval") requires an approved `request_approval` before every successful
   `unpublish_page` in a run with a plan. Below the specs, the dispatcher refuses a guarded tool without a token,
   bob has none, and the only thing that puts the approver's token into the request is an approved
   `request_approval` (`Runtime._run_agent`, `governance.request_approval`): a delegation cannot pass one on, since
   the runtime drops `approval_token` from the values it passes (`HARNESS_SLOTS`).
3. **Hand-over between specialists against FS-0201 (delegation topology).** FS-0303 requires a successful
   `agent.route` from publishing to translation. FS-0201 requires that only the orchestrator delegates: its clause
   "A request without a plan is delegated once" demands `e.source == 'orchestrator'` for every delegation of a run
   in which `get_page`, `check_permission` or `validate_links` succeeds, and FS-0202 has publishing check the
   permission before `unpublish_page`. Only the orchestrator's definition lists `route_to_agent`, and the runtime
   refuses a delegation from an agent whose definition does not (`Dispatcher.gate`, asked by `Runtime._delegate`).
4. **Two contracts on one function (no implementation satisfies both).** `function_contract:bulk_size_ok` requires
   `result == (1 <= n <= limit)` for `limit >= 1`, and `function_contract:bulk_size_ok#2` requires `result == True`
   for `n == 0 and limit >= 1`. At `n = 0` the first gives false and the second true. This one needs no knowledge of
   the application: the spec contradicts itself.

Conflicts 2 and 3 are between FS-0303 and an as-built spec; conflict 1 needs the architecture (how steps are
counted) as well; conflict 4 is internal. Removing any one of them leaves the other three.
