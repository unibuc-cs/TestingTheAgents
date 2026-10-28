# Spec-driven development: evidence report

5 change requests, 24 pull requests, 134 recorded baseline runs (23,527 tokens of source in 52 files).

Each request is a spec: prose intent plus machine-checkable clauses. Each PR is a variant of the system. The clauses are checked, the change-affected regression tests are run, and the result is an evidence record with the assurance rung reached per clause (L0 reviewed, L1 example-tested, L2 property-tested, L3 monitored, L4 statically checked, L5 proven).

## Verdicts

| request | PR | expected | verdict | what failed / gap | rungs reached | clause runs | regression cases (of full) | tokens (of full) | s |
|---|---|---|---|---|---|---|---|---|---|
| FS-0101 | pr_correct | accepted | **accepted** | - | L5×1, L4×2, L3×1, L1×4 | 18 | 31 (134) | 206,691 (472,679) | 0.7 |
| FS-0101 | pr_no_lower_bound | rejected | **rejected** | age-rule (contract) | L4×2, L3×1, L1×4 | 18 | 31 (134) | 206,691 (472,679) | 0.6 |
| FS-0101 | pr_off_by_one | rejected | **rejected** | age-rule (contract), boundary-publishes (example) | L4×2, L3×1, L1×3 | 18 | 31 (134) | 206,691 (472,679) | 0.5 |
| FS-0101 | pr_in_adapter | rejected | **rejected** | age-rule (contract), lives-in-service (placement) | L4×1, L3×1, L1×4 | 18 | 49 (134) | 314,616 (472,679) | 0.7 |
| FS-0101 | pr_unwired | rejected | **rejected** | stale-refused (example) | L5×1, L4×2, L3×1, L1×3 | 18 | 31 (134) | 206,691 (472,679) | 0.6 |
| FS-0102 | current | rejected | **rejected** | made-up-token-refused (contract), approver-recorded (trace), with-token (example), made-up-token (example), one-gate (placement) | L4×1, L3×1, L1×2 | 13 | 0 (134) | 60,530 (472,679) | 0.2 |
| FS-0102 | pr_correct | accepted | **accepted** | - | L4×2, L3×2, L2×1, L1×4 | 13 | 134 (134) | 497,860 (472,679) | 1.6 |
| FS-0102 | pr_self_approved | rejected | **rejected** | made-up-token-refused (contract), made-up-token (example) | L4×2, L3×2, L1×3 | 13 | 134 (134) | 497,860 (472,679) | 1.6 |
| FS-0102 | pr_in_dispatcher | rejected | **rejected** | one-gate (placement) | L4×1, L3×2, L2×1, L1×4 | 13 | 134 (134) | 497,860 (472,679) | 1.5 |
| FS-0102 | code_approval_gate_bypass | rejected | **rejected** | made-up-token-refused (contract), approver-recorded (trace), no-unknown-token (trace), made-up-token (example), without-token (example), regression-tests (example) | L4×2, L1×1 | 13 | 134 (134) | 497,860 (472,679) | 1.6 |
| FS-0103 | pr_correct | accepted | **accepted** | - | L5×1, L4×1, L3×2, L1×4 | 45 | 45 (134) | 295,310 (472,679) | 0.7 |
| FS-0103 | pr_gate_ignores_version | rejected | **rejected** | clean-check-rule (contract) | L4×1, L3×2, L1×4 | 45 | 45 (134) | 295,310 (472,679) | 0.7 |
| FS-0103 | pr_gate_in_adapter | rejected | **rejected** | clean-check-rule (contract), rule-in-service (placement) | L3×2, L1×4 | 45 | 45 (134) | 295,310 (472,679) | 0.7 |
| FS-0103 | pr_validate_after_schedule | rejected | **rejected** | schedule-validates (example), rule-in-service (placement), regression-tests (example) | L5×1, L3×2, L1×2 | 45 | 49 (134) | 300,724 (472,679) | 0.8 |
| FS-0103 | code_links_external_lenient | rejected | **rejected** | truthful-validation (trace), broken-external (example), regression-tests (example) | L5×1, L4×1, L3×1, L1×2 | 45 | 45 (134) | 298,817 (472,679) | 0.7 |
| FS-0104 | pr_config_70 | accepted | **accepted** | - | L4×2, L3×1, L2×1, L1×3 | 78 | 6 (134) | 419,707 (472,679) | 1.0 |
| FS-0104 | pr_config_20 | rejected | **rejected** | limit-setting (setting), regression-tests (example) | L4×1, L3×1, L2×1, L1×2 | 78 | 6 (134) | 371,327 (472,679) | 1.0 |
| FS-0104 | pr_hardcoded_70 | rejected | **rejected** | no-magic-number (placement) | L4×1, L3×1, L2×1, L1×3 | 78 | 7 (134) | 412,429 (472,679) | 1.1 |
| FS-0104 | pr_drop_guard | rejected | **rejected** | applied-iff-within-limit (contract), boundary-refused (example), regression-tests (example) | L4×2, L3×1, L1×1 | 30 | 7 (134) | 186,109 (472,679) | 0.5 |
| FS-0105 | current | rejected | **rejected** | once-per-write (contract), lost-ack-schedule (example) | L4×3, L3×1, L1×2 | 31 | 0 (134) | 193,925 (472,679) | 0.5 |
| FS-0105 | pr_fix | accepted | **accepted** | - | L4×3, L3×1, L2×1, L1×3 | 31 | 8 (134) | 193,925 (472,679) | 0.5 |
| FS-0105 | pr_partial_fix | rejected | **rejected** | once-per-write (contract) | L4×3, L3×1, L1×3 | 31 | 3 (134) | 193,925 (472,679) | 0.4 |
| FS-0105 | code_retry_drop_idempotency | rejected | **rejected** | once-per-write (contract), keyed-writes (trace), lost-ack-publish (example), lost-ack-schedule (example), regression-tests (example) | L4×3 | 31 | 94 (134) | 474,427 (472,679) | 1.2 |
| FS-0105 | config_retries_0 | rejected | **rejected** | retries-on (setting), once-per-write (contract), regression-tests (example) | L4×2, L3×1, L1×2 | 31 | 94 (134) | 464,497 (472,679) | 1.2 |

![resources](figures/resources.png)

## Resources: with the spec vs. without

| | without a spec (today) | with the spec (this run) |
|---|---|---|
| context handed to the coding agent | the repository: 23,527 tokens, 52 files | the brief: 2,301–4,185 tokens (12% of the repo on average) |
| checks per PR | full suite: 134 runs, 472,679 agent tokens | clause checks: 13–78 runs; change-selected regression cases: 0–134 of 134 (36% on average; a harness change selects most of the suite, a config change a few cases); 67% of the full-suite tokens in total |
| what the checks say | pass/fail of example tests (L1) | per clause: 2 at L5, 10 at L4, 7 at L3, 3 at L2, 18 at L1 over the accepted PRs |
| when a PR is wrong | a test fails, somewhere | the failing clause names the rule, the counterexample or the misplaced code |

## FS-0101: An editorial approval is valid for 30 days

A page may only be published or scheduled while its editorial approval is recent. The validity
window is a platform setting (30 days to start with), not a number in code. A stale approval is
refused with an explanation and leaves an audit entry; the author has to request a new review.
Approving a review records the approval date.

**Clauses**

- `window-setting` (setting): the validity window is a configuration value between 1 and 365 days, set to 30
- `age-rule` (contract): review_age_ok(age, max) holds exactly when 0 <= age <= max, for every max >= 1
- `no-stale-go-live` (trace): whenever a page goes live, its approval was at most the configured number of days old
- `stale-refused` (example): publishing a page approved 45 days ago is refused, audited, and explained
- `boundary-publishes` (example): a page approved exactly max days ago still publishes (boundary)
- `fresh-publishes` (example): the ordinary publish scenario is unchanged
- `lives-in-service` (placement): the rule is a service function; adapters, skills and the harness do no date arithmetic and hold no limit

**Agent brief (the locate step)**

Read 5 files, ~2,338 tokens (10% of the repository):

- `config/runtime.yaml` — publishing.review_max_age_days
- `services/workflow.py` — publish_page, request_review, schedule_publish
- `skills/page-authoring/SKILL.md` — call: request_review
- `skills/publishing-workflow/SKILL.md` — call: publish_page, call: request_review, call: schedule_publish
- `tools/publish_tools.py` — publish_page, request_review, schedule_publish

Checks that will run: window-setting (setting, 0 runs), age-rule (contract, 0 runs, 300 examples + proof), no-stale-go-live (trace, 15 runs), stale-refused (example, 1 runs), boundary-publishes (example, 1 runs), fresh-publishes (example, 1 runs), lives-in-service (placement, 0 runs). Recorded runs in scope: 15 of 134.

### FS-0101/pr_correct — Add the 30-day approval window (config + service + adapters + skill prose)

Verdict: **accepted** (expected accepted). rule in the service layer, limit in config, proven for all inputs. Change: 4 file(s), 55 diff lines; components: `code:services/workflow.py`, `code:services/workflow.py::_check_review_age`, `code:services/workflow.py::approval_age_days`, `code:services/workflow.py::approve_review`, `code:services/workflow.py::publish_page`, `code:services/workflow.py::review_age_ok`, `code:services/workflow.py::schedule_publish`, `code:tools/publish_tools.py::publish_page` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| window-setting | setting | L4 | pass | publishing.review_max_age_days = 30 |
| age-rule | contract | L5 | pass | proven for all inputs in the stated domain (solver: unsat) |
| no-stale-go-live | trace | L3 | pass | holds over 15 runs |
| stale-refused | example | L1 | pass | expected outcome observed |
| boundary-publishes | example | L1 | pass | expected outcome observed |
| fresh-publishes | example | L1 | pass | expected outcome observed |
| lives-in-service | placement | L4 | pass | 4 rules hold |
| regression-tests | example | L1 | pass | 31 of 134 catalog cases selected by observed dependencies; all pass |

### FS-0101/pr_no_lower_bound — Same, but `age_days <= max_age_days` (no lower bound)

Verdict: **rejected** (expected rejected). a future-dated approval (negative age) would be accepted; no fixture has one, only the proof sees it. Change: 4 file(s), 55 diff lines; components: `code:services/workflow.py`, `code:services/workflow.py::_check_review_age`, `code:services/workflow.py::approval_age_days`, `code:services/workflow.py::approve_review`, `code:services/workflow.py::publish_page`, `code:services/workflow.py::review_age_ok`, `code:services/workflow.py::schedule_publish`, `code:tools/publish_tools.py::publish_page` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| window-setting | setting | L4 | pass | publishing.review_max_age_days = 30 |
| age-rule | contract | L5 | FAIL | counterexample found (property test and solver) |
| no-stale-go-live | trace | L3 | pass | holds over 15 runs |
| stale-refused | example | L1 | pass | expected outcome observed |
| boundary-publishes | example | L1 | pass | expected outcome observed |
| fresh-publishes | example | L1 | pass | expected outcome observed |
| lives-in-service | placement | L4 | pass | 4 rules hold |
| regression-tests | example | L1 | pass | 31 of 134 catalog cases selected by observed dependencies; all pass |

- counterexample {'age_days': -1, 'max_age_days': 1, 'result': True}: 'result == (0 <= age_days <= max_age_days)' is false
- solver counterexample: {'age_days': -1, 'max_age_days': 1}

### FS-0101/pr_off_by_one — Same, but `<` instead of `<=` at the boundary

Verdict: **rejected** (expected rejected). an approval exactly 30 days old is refused. Change: 4 file(s), 55 diff lines; components: `code:services/workflow.py`, `code:services/workflow.py::_check_review_age`, `code:services/workflow.py::approval_age_days`, `code:services/workflow.py::approve_review`, `code:services/workflow.py::publish_page`, `code:services/workflow.py::review_age_ok`, `code:services/workflow.py::schedule_publish`, `code:tools/publish_tools.py::publish_page` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| window-setting | setting | L4 | pass | publishing.review_max_age_days = 30 |
| age-rule | contract | L5 | FAIL | counterexample found (property test and solver) |
| no-stale-go-live | trace | L3 | pass | holds over 15 runs |
| stale-refused | example | L1 | pass | expected outcome observed |
| boundary-publishes | example | L1 | FAIL | failed checks: state:pages.p4.status, required:publish_page, audit:publish_page, response~Published |
| fresh-publishes | example | L1 | pass | expected outcome observed |
| lives-in-service | placement | L4 | pass | 4 rules hold |
| regression-tests | example | L1 | pass | 31 of 134 catalog cases selected by observed dependencies; all pass |

- counterexample {'age_days': 1, 'max_age_days': 1, 'result': False}: 'result == (0 <= age_days <= max_age_days)' is false
- solver counterexample: {'age_days': 1, 'max_age_days': 1}
- case PUB-01: 'Please publish the welcome page' -> 'I could not complete the request (validation_error): the approval of p4 is 30 days old; approvals are valid for 30 days '
- failed check state:pages.p4.status: pages.p4.status == 'published' (actual 'draft')
- failed check required:publish_page: ok tools: ['check_permission', 'get_page', 'validate_links']
- failed check audit:publish_page: expected 1, found 0
- failed check response~Published: message: 'I could not complete the request (validation_error): the approval of p4 is 30 days old; approvals are valid for 30 days '

### FS-0101/pr_in_adapter — Same behaviour, but the date logic written inside tools/publish_tools.py

Verdict: **rejected** (expected rejected). every run-time check passes; the contract cannot find the function where the spec says it lives, and the placement rules fail. Change: 4 file(s), 25 diff lines; components: `code:services/workflow.py::approve_review`, `code:tools/publish_tools.py`, `code:tools/publish_tools.py::_refuse_stale_approval`, `code:tools/publish_tools.py::publish_page`, `code:tools/publish_tools.py::schedule_publish`, `config:publishing.review_max_age_days`, `line:services/workflow.py:29`, `line:tools/publish_tools.py:2` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| window-setting | setting | L4 | pass | publishing.review_max_age_days = 30 |
| age-rule | contract | L2 | FAIL | services/workflow.py::review_age_ok does not exist |
| no-stale-go-live | trace | L3 | pass | holds over 15 runs |
| stale-refused | example | L1 | pass | expected outcome observed |
| boundary-publishes | example | L1 | pass | expected outcome observed |
| fresh-publishes | example | L1 | pass | expected outcome observed |
| lives-in-service | placement | L4 | FAIL | review_age_ok is not defined in services/workflow.py; approval_age_days is not defined in services/workflow.py; tools/publish_tools.py imports datetime (line 3) |
| regression-tests | example | L1 | pass | 49 of 134 catalog cases selected by observed dependencies; all pass |

- define {'function': 'review_age_ok', 'in': 'services/workflow.py'}
- define {'function': 'approval_age_days', 'in': 'services/workflow.py'}
- forbid_import {'module': 'datetime', 'in': ['tools', 'harness']}
- forbid_literal {'value': 30, 'in': ['services/workflow.py', 'tools', 'skills']}
- review_age_ok is not defined in services/workflow.py
- approval_age_days is not defined in services/workflow.py
- tools/publish_tools.py imports datetime (line 3)

### FS-0101/pr_unwired — Service functions added and proven, but the adapters never pass the limit

Verdict: **rejected** (expected rejected). the unit-level proof holds, the system-level monitor and the example fail. Change: 3 file(s), 43 diff lines; components: `code:services/workflow.py`, `code:services/workflow.py::_check_review_age`, `code:services/workflow.py::approval_age_days`, `code:services/workflow.py::approve_review`, `code:services/workflow.py::publish_page`, `code:services/workflow.py::review_age_ok`, `code:services/workflow.py::schedule_publish`, `config:publishing.review_max_age_days` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| window-setting | setting | L4 | pass | publishing.review_max_age_days = 30 |
| age-rule | contract | L5 | pass | proven for all inputs in the stated domain (solver: unsat) |
| no-stale-go-live | trace | L3 | pass | holds over 15 runs |
| stale-refused | example | L1 | FAIL | failed checks: state:pages.p11.status, audit:publish_refused, audit:publish_page, response~30 days, response~new review |
| boundary-publishes | example | L1 | pass | expected outcome observed |
| fresh-publishes | example | L1 | pass | expected outcome observed |
| lives-in-service | placement | L4 | pass | 4 rules hold |
| regression-tests | example | L1 | pass | 31 of 134 catalog cases selected by observed dependencies; all pass |

- case inline: 'Please publish the stale-approval page' -> 'Published p11 at /content/site/blog/stale-approval.'
- failed check state:pages.p11.status: pages.p11.status == 'draft' (actual 'published')
- failed check audit:publish_refused: expected 1, found 0
- failed check audit:publish_page: expected 0, found 1
- failed check response~30 days: message: 'Published p11 at /content/site/blog/stale-approval.'
- failed check response~new review: message: 'Published p11 at /content/site/blog/stale-approval.'

## FS-0102: A guarded operation needs a valid approval token and records who approved

unpublish_page, export_user_data and approve_review are guarded: the harness refuses them unless the
request carries an approval token that belongs to a known user, and it records that user as the
approver (audit entry `approval_used`, `approved_by` on the call). Today any non-empty token passes
and nobody is recorded. The gate stays in one place (the dispatcher); resolving a token to a user is
a permissions-service function; the harness never inspects the user table itself.

**Clauses**

- `guarded-list` (setting): the three guarded tools are in the list of tools that require approval
- `made-up-token-refused` (contract): for each guarded tool with a recorded run, the same request with a made-up token is refused and nothing is audited
- `approver-recorded` (trace): every successful guarded call names the owner of the token that was presented
- `no-unknown-token` (trace): no guarded call ever succeeds on a token that belongs to nobody
- `with-token` (example): an admin with her own token can take a page down, and the approval is audited to her
- `made-up-token` (example): a publisher with a made-up token is refused
- `without-token` (example): without any token the request is refused
- `one-gate` (placement): the gate is the dispatcher; token resolution is a permissions-service function; the harness never reads the user table

**Agent brief (the locate step)**

Read 9 files, ~4,185 tokens (18% of the repository):

- `config/runtime.yaml` — tools.requires_approval
- `harness/dispatcher.py`
- `services/governance.py` — export_user_data
- `services/permissions.py`
- `services/workflow.py` — approve_review, unpublish_page
- `skills/governance-ops/SKILL.md` — call: export_user_data
- `skills/publishing-workflow/SKILL.md` — call: unpublish_page
- `tools/governance_tools.py` — export_user_data
- `tools/publish_tools.py` — approve_review, unpublish_page

Checks that will run: guarded-list (setting, 0 runs), made-up-token-refused (contract, 2 runs), approver-recorded (trace, 8 runs), no-unknown-token (trace, 8 runs), with-token (example, 1 runs), made-up-token (example, 1 runs), without-token (example, 1 runs), one-gate (placement, 0 runs). Recorded runs in scope: 8 of 134.

### FS-0102/current — The current gate: any non-empty token passes and nobody is recorded

Verdict: **rejected** (expected rejected). the spec exposes a weakness of the current code: a made-up token takes a page down. No change: the current code.

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| guarded-list | setting | L4 | pass | tools.requires_approval = ['approve_review', 'export_user_data', 'unpublish_page'] |
| made-up-token-refused | contract | L2 | FAIL | counterexample found |
| approver-recorded | trace | L3 | FAIL | 6 violation(s) in 8 runs |
| no-unknown-token | trace | L3 | pass | holds over 8 runs |
| with-token | example | L1 | FAIL | failed checks: audit:approval_used |
| made-up-token | example | L1 | FAIL | failed checks: state:pages.p7.status, forbidden:unpublish_page, audit:unpublish_page, response~approval |
| without-token | example | L1 | pass | expected outcome observed |
| one-gate | placement | L4 | FAIL | approver_for is not defined in services/permissions.py |
| regression-tests | example | L1 | pass | 0 of 134 catalog cases selected by observed dependencies; all pass |

- enumerated 2 values ['unpublish_page', 'export_user_data']
- tool='unpublish_page' (case PUB-06, fault healthy): post-condition false
- 8 runs in scope, 6 matching events checked
- PUB-06: {'kind': 'tool.call', 'tool': 'unpublish_page', 'args': {'page_id': 'p7'}, 'status': 'ok', 'idempotency_key': 'idem-27ddfe9873'}
- GOV-01: {'kind': 'tool.call', 'tool': 'export_user_data', 'args': {'subject_id': 's1'}, 'status': 'ok', 'idempotency_key': 'idem-6391e429ce'}
- ORC-02: {'kind': 'tool.call', 'tool': 'unpublish_page', 'args': {'page_id': 'p7'}, 'status': 'ok', 'idempotency_key': 'idem-2925062073'}
- DS-INTENTS/i03: {'kind': 'tool.call', 'tool': 'unpublish_page', 'args': {'page_id': 'p7'}, 'status': 'ok', 'idempotency_key': 'idem-4793dfafba'}
- DS-INTENTS/i04: {'kind': 'tool.call', 'tool': 'unpublish_page', 'args': {'page_id': 'p7'}, 'status': 'ok', 'idempotency_key': 'idem-aa72f7c062'}
- case PUB-06: 'Take down the old news page' -> 'Unpublished p7 (/content/site/blog/old-news).'
- failed check audit:approval_used: expected 1, found 0
- case inline: 'Take down the old news page' -> 'Unpublished p7 (/content/site/blog/old-news).'
- failed check state:pages.p7.status: pages.p7.status == 'published' (actual 'draft')
- failed check forbidden:unpublish_page: ok tools: ['check_permission', 'get_page', 'unpublish_page']
- failed check audit:unpublish_page: expected 0, found 1
- failed check response~approval: message: 'Unpublished p7 (/content/site/blog/old-news).'
- define {'function': 'approver_for', 'in': 'services/permissions.py'}
- define {'function': 'Dispatcher._needs_approval', 'in': 'harness/dispatcher.py'}
- forbid_name {'name': 'users', 'in': ['harness']}
- forbid_literal {'value': 'tools.requires_approval', 'in': ['tools', 'services', 'skills']}
- approver_for is not defined in services/permissions.py

### FS-0102/pr_correct — Resolve the token against the user table (permissions service) and record the approver (dispatcher)

Verdict: **accepted** (expected accepted). 2 files: the lookup is a permissions-service function, the gate stays in the one place it lives. Change: 2 file(s), 17 diff lines; components: `code:harness/dispatcher.py`, `code:harness/dispatcher.py::Dispatcher.call`, `code:services/permissions.py::approver_for`, `line:harness/dispatcher.py:22`, `line:harness/dispatcher.py:23`, `line:harness/dispatcher.py:29`, `line:harness/dispatcher.py:32`, `line:harness/dispatcher.py:5` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| guarded-list | setting | L4 | pass | tools.requires_approval = ['approve_review', 'export_user_data', 'unpublish_page'] |
| made-up-token-refused | contract | L2 | pass | holds over 2 runs |
| approver-recorded | trace | L3 | pass | holds over 8 runs |
| no-unknown-token | trace | L3 | pass | holds over 8 runs |
| with-token | example | L1 | pass | expected outcome observed |
| made-up-token | example | L1 | pass | expected outcome observed |
| without-token | example | L1 | pass | expected outcome observed |
| one-gate | placement | L4 | pass | 4 rules hold |
| regression-tests | example | L1 | pass | 134 of 134 catalog cases selected by observed dependencies; all pass |

### FS-0102/pr_self_approved — Same, but an unknown token falls back to 'approved by the caller'

Verdict: **rejected** (expected rejected). property, monitor and example all catch the made-up token. Change: 2 file(s), 19 diff lines; components: `code:harness/dispatcher.py`, `code:harness/dispatcher.py::Dispatcher.call`, `code:services/permissions.py::approver_for`, `line:harness/dispatcher.py:22`, `line:harness/dispatcher.py:23`, `line:harness/dispatcher.py:29`, `line:harness/dispatcher.py:32`, `line:harness/dispatcher.py:5` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| guarded-list | setting | L4 | pass | tools.requires_approval = ['approve_review', 'export_user_data', 'unpublish_page'] |
| made-up-token-refused | contract | L2 | FAIL | counterexample found |
| approver-recorded | trace | L3 | pass | holds over 8 runs |
| no-unknown-token | trace | L3 | pass | holds over 8 runs |
| with-token | example | L1 | pass | expected outcome observed |
| made-up-token | example | L1 | FAIL | failed checks: state:pages.p7.status, forbidden:unpublish_page, audit:unpublish_page, audit:approval_used, response~approval |
| without-token | example | L1 | pass | expected outcome observed |
| one-gate | placement | L4 | pass | 4 rules hold |
| regression-tests | example | L1 | pass | 134 of 134 catalog cases selected by observed dependencies; all pass |

- enumerated 2 values ['unpublish_page', 'export_user_data']
- tool='unpublish_page' (case PUB-06, fault healthy): post-condition false
- case inline: 'Take down the old news page' -> 'Unpublished p7 (/content/site/blog/old-news).'
- failed check state:pages.p7.status: pages.p7.status == 'published' (actual 'draft')
- failed check forbidden:unpublish_page: ok tools: ['check_permission', 'get_page', 'unpublish_page']
- failed check audit:unpublish_page: expected 0, found 1
- failed check audit:approval_used: expected 0, found 1
- failed check response~approval: message: 'Unpublished p7 (/content/site/blog/old-news).'

### FS-0102/pr_in_dispatcher — Same behaviour, but the user-table lookup written inside the dispatcher

Verdict: **rejected** (expected rejected). every run-time check passes; the harness must not inspect the user table (placement). Change: 1 file(s), 12 diff lines; components: `code:harness/dispatcher.py`, `code:harness/dispatcher.py::Dispatcher.call`, `line:harness/dispatcher.py:22`, `line:harness/dispatcher.py:23`, `line:harness/dispatcher.py:29`, `line:harness/dispatcher.py:32`, `line:harness/dispatcher.py:5`, `line:harness/dispatcher.py:6` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| guarded-list | setting | L4 | pass | tools.requires_approval = ['approve_review', 'export_user_data', 'unpublish_page'] |
| made-up-token-refused | contract | L2 | pass | holds over 2 runs |
| approver-recorded | trace | L3 | pass | holds over 8 runs |
| no-unknown-token | trace | L3 | pass | holds over 8 runs |
| with-token | example | L1 | pass | expected outcome observed |
| made-up-token | example | L1 | pass | expected outcome observed |
| without-token | example | L1 | pass | expected outcome observed |
| one-gate | placement | L4 | FAIL | approver_for is not defined in services/permissions.py; harness/dispatcher.py uses users (line 26) |
| regression-tests | example | L1 | pass | 134 of 134 catalog cases selected by observed dependencies; all pass |

- define {'function': 'approver_for', 'in': 'services/permissions.py'}
- define {'function': 'Dispatcher._needs_approval', 'in': 'harness/dispatcher.py'}
- forbid_name {'name': 'users', 'in': ['harness']}
- forbid_literal {'value': 'tools.requires_approval', 'in': ['tools', 'services', 'skills']}
- approver_for is not defined in services/permissions.py
- harness/dispatcher.py uses users (line 26)

### FS-0102/code_approval_gate_bypass — Correct PR plus a later change: the dispatcher stops enforcing the gate

Verdict: **rejected** (expected rejected). monitor: a guarded call succeeded without an approver. Change: 2 file(s), 19 diff lines; components: `code:harness/dispatcher.py`, `code:harness/dispatcher.py::Dispatcher._needs_approval`, `code:harness/dispatcher.py::Dispatcher.call`, `code:services/permissions.py::approver_for`, `line:harness/dispatcher.py:22`, `line:harness/dispatcher.py:23`, `line:harness/dispatcher.py:29`, `line:harness/dispatcher.py:32` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| guarded-list | setting | L4 | pass | tools.requires_approval = ['approve_review', 'export_user_data', 'unpublish_page'] |
| made-up-token-refused | contract | L2 | FAIL | counterexample found |
| approver-recorded | trace | L3 | FAIL | 1 violation(s) in 8 runs |
| no-unknown-token | trace | L3 | FAIL | 1 violation(s) in 8 runs |
| with-token | example | L1 | pass | expected outcome observed |
| made-up-token | example | L1 | FAIL | failed checks: state:pages.p7.status, forbidden:unpublish_page, audit:unpublish_page, audit:approval_used, response~approval |
| without-token | example | L1 | FAIL | failed checks: state:pages.p7.status, forbidden:unpublish_page, audit:unpublish_page, response~approval |
| one-gate | placement | L4 | pass | 4 rules hold |
| regression-tests | example | L1 | FAIL | 134 of 134 catalog cases selected by observed dependencies; failed: ['PUB-07'] |

- enumerated 2 values ['unpublish_page', 'export_user_data']
- tool='unpublish_page' (case PUB-06, fault healthy): post-condition false
- 8 runs in scope, 7 matching events checked
- PUB-07: {'kind': 'tool.call', 'tool': 'unpublish_page', 'args': {'page_id': 'p7'}, 'status': 'ok', 'idempotency_key': 'idem-bb2f6d2146'}
- 8 runs in scope, 7 matching events checked
- PUB-07: {'kind': 'tool.call', 'tool': 'unpublish_page', 'args': {'page_id': 'p7'}, 'status': 'ok', 'idempotency_key': 'idem-bb2f6d2146'}
- case inline: 'Take down the old news page' -> 'Unpublished p7 (/content/site/blog/old-news).'
- failed check state:pages.p7.status: pages.p7.status == 'published' (actual 'draft')
- failed check forbidden:unpublish_page: ok tools: ['check_permission', 'get_page', 'unpublish_page']
- failed check audit:unpublish_page: expected 0, found 1
- failed check audit:approval_used: expected 0, found 1
- failed check response~approval: message: 'Unpublished p7 (/content/site/blog/old-news).'
- case PUB-07: 'Take down the old news page' -> 'Unpublished p7 (/content/site/blog/old-news).'
- failed check state:pages.p7.status: pages.p7.status == 'published' (actual 'draft')
- failed check forbidden:unpublish_page: ok tools: ['check_permission', 'get_page', 'unpublish_page']
- failed check audit:unpublish_page: expected 0, found 1
- failed check response~approval: message: 'Unpublished p7 (/content/site/blog/old-news).'
- PUB-07

## FS-0103: Nothing goes live without a clean link check of its current version

Today "validate links before publishing" is enforced only by the order of steps in the publishing
skill - a prompt. Move the rule into the service layer: a link validation is stamped on the page
together with the page version it was made for, and publishing or scheduling is refused (audited as
publish_refused, rule FS-0103) unless the page carries a clean stamp for its *current* version.
The validation result itself must be truthful: it reports exactly the links that are broken
according to the platform's reachability data.

**Clauses**

- `validated-first` (trace): every publish or schedule is preceded, for the same page and version, by a validation that found 0 broken links
- `truthful-validation` (trace): the number of broken links reported equals the number computed independently from the fixture tables
- `clean-check-rule` (contract): links_clean(check_version, page_version, broken) holds exactly when the check is for the current version and found nothing
- `broken-external` (example): a page with a broken external link stays a draft
- `schedule-validates` (example): scheduling validates links and is stamped with the version
- `fresh-publishes` (example): the ordinary publish scenario is unchanged
- `rule-in-service` (placement): the gate and its rule live in the workflow service; adapters and the harness do not look at link stamps; the skill still validates first

**Agent brief (the locate step)**

Read 5 files, ~2,301 tokens (10% of the repository):

- `services/links.py` — validate_links
- `services/workflow.py` — publish_page, schedule_publish, unpublish_page
- `skills/link-validation/SKILL.md` — call: validate_links
- `skills/publishing-workflow/SKILL.md` — call: publish_page, call: schedule_publish, call: unpublish_page
- `tools/publish_tools.py` — publish_page, schedule_publish, unpublish_page, validate_links

Checks that will run: validated-first (trace, 15 runs), truthful-validation (trace, 42 runs), clean-check-rule (contract, 0 runs, 200 examples + proof), broken-external (example, 1 runs), schedule-validates (example, 1 runs), fresh-publishes (example, 1 runs), rule-in-service (placement, 0 runs). Recorded runs in scope: 42 of 134.

### FS-0103/pr_correct — Stamp each validation on the page (links service); publish and schedule refuse without a clean stamp for the current version (workflow service)

Verdict: **accepted** (expected accepted). 2 files: the rule moves from the skill procedure (a prompt) into the service, and is proven. Change: 2 file(s), 28 diff lines; components: `code:services/links.py::validate_links`, `code:services/workflow.py::_require_clean_links`, `code:services/workflow.py::links_clean`, `code:services/workflow.py::publish_page`, `code:services/workflow.py::schedule_publish`, `line:services/links.py:35`, `line:services/links.py:36`, `line:services/workflow.py:38` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| validated-first | trace | L3 | pass | holds over 15 runs |
| truthful-validation | trace | L3 | pass | holds over 42 runs |
| clean-check-rule | contract | L5 | pass | proven for all inputs in the stated domain (solver: unsat) |
| broken-external | example | L1 | pass | expected outcome observed |
| schedule-validates | example | L1 | pass | expected outcome observed |
| fresh-publishes | example | L1 | pass | expected outcome observed |
| rule-in-service | placement | L4 | pass | 5 rules hold |
| regression-tests | example | L1 | pass | 45 of 134 catalog cases selected by observed dependencies; all pass |

### FS-0103/pr_gate_ignores_version — Same, but the gate looks only at the broken count, not at the version the check was made for

Verdict: **rejected** (expected rejected). no recorded scenario edits a page after validating it; only the proof sees the stale check. Change: 2 file(s), 28 diff lines; components: `code:services/links.py::validate_links`, `code:services/workflow.py::_require_clean_links`, `code:services/workflow.py::links_clean`, `code:services/workflow.py::publish_page`, `code:services/workflow.py::schedule_publish`, `line:services/links.py:35`, `line:services/links.py:36`, `line:services/workflow.py:38` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| validated-first | trace | L3 | pass | holds over 15 runs |
| truthful-validation | trace | L3 | pass | holds over 42 runs |
| clean-check-rule | contract | L5 | FAIL | counterexample found (solver) |
| broken-external | example | L1 | pass | expected outcome observed |
| schedule-validates | example | L1 | pass | expected outcome observed |
| fresh-publishes | example | L1 | pass | expected outcome observed |
| rule-in-service | placement | L4 | pass | 5 rules hold |
| regression-tests | example | L1 | pass | 45 of 134 catalog cases selected by observed dependencies; all pass |

- 200 examples, no counterexample
- solver counterexample: {'check_version': 2, 'page_version': 1, 'broken': 0}

### FS-0103/pr_gate_in_adapter — Same behaviour, but the gate written inside tools/publish_tools.py

Verdict: **rejected** (expected rejected). every run-time check passes; the contract cannot find links_clean in the service and the placement rules fail. Change: 3 file(s), 25 diff lines; components: `code:services/links.py::validate_links`, `code:services/workflow.py::publish_page`, `code:services/workflow.py::schedule_publish`, `code:tools/publish_tools.py::_require_clean_links`, `code:tools/publish_tools.py::publish_page`, `code:tools/publish_tools.py::schedule_publish`, `line:services/links.py:35`, `line:services/links.py:36` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| validated-first | trace | L3 | pass | holds over 15 runs |
| truthful-validation | trace | L3 | pass | holds over 42 runs |
| clean-check-rule | contract | L2 | FAIL | services/workflow.py::links_clean does not exist |
| broken-external | example | L1 | pass | expected outcome observed |
| schedule-validates | example | L1 | pass | expected outcome observed |
| fresh-publishes | example | L1 | pass | expected outcome observed |
| rule-in-service | placement | L4 | FAIL | links_clean is not defined in services/workflow.py |
| regression-tests | example | L1 | pass | 45 of 134 catalog cases selected by observed dependencies; all pass |

- define {'function': 'links_clean', 'in': 'services/workflow.py'}
- define {'function': 'validate_links', 'in': 'services/links.py'}
- forbid_name {'name': 'link_check', 'in': ['tools', 'harness']}
- skill_order {'skill': 'publishing-workflow', 'first': {'include': 'link-validation'}, 'then': {'call': 'publish_page'}}
- skill_order {'skill': 'publishing-workflow', 'first': {'include': 'link-validation'}, 'then': {'call': 'schedule_publish'}}
- links_clean is not defined in services/workflow.py

### FS-0103/pr_validate_after_schedule — Correct PR plus a skill reordering: link validation moved after the schedule step

Verdict: **rejected** (expected rejected). the service gate holds (nothing unvalidated is scheduled) but scheduling stops working: example and skill-order lint fail. Change: 3 file(s), 30 diff lines; components: `code:services/links.py::validate_links`, `code:services/workflow.py::_require_clean_links`, `code:services/workflow.py::links_clean`, `code:services/workflow.py::publish_page`, `code:services/workflow.py::schedule_publish`, `line:services/links.py:35`, `line:services/links.py:36`, `line:services/workflow.py:38` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| validated-first | trace | L3 | pass | holds over 15 runs |
| truthful-validation | trace | L3 | pass | holds over 42 runs |
| clean-check-rule | contract | L5 | pass | proven for all inputs in the stated domain (solver: unsat) |
| broken-external | example | L1 | pass | expected outcome observed |
| schedule-validates | example | L1 | FAIL | failed checks: state:pages.p4.status, state:pages.p4.link_check.broken, required:validate_links, required:schedule_publish, audit:validate_links, audit:schedule_publish |
| fresh-publishes | example | L1 | pass | expected outcome observed |
| rule-in-service | placement | L4 | FAIL | skill publishing-workflow: {'include': 'link-validation'} comes after {'call': 'schedule_publish'} |
| regression-tests | example | L1 | FAIL | 49 of 134 catalog cases selected by observed dependencies; failed: ['DS-INTENTS/i05', 'DS-INTENTS/i06', 'PUB-09'] |

- case PUB-09: 'Schedule the welcome page for 2026-11-01T09:00:00Z' -> 'I could not complete the request (validation_error): p4 has no clean link check for its current version (v1); validate i'
- failed check state:pages.p4.status: pages.p4.status == 'scheduled' (actual 'draft')
- failed check state:pages.p4.link_check.broken: pages.p4.link_check.broken missing
- failed check required:validate_links: ok tools: ['check_permission', 'get_page']
- failed check required:schedule_publish: ok tools: ['check_permission', 'get_page']
- failed check audit:validate_links: expected 1, found 0
- failed check audit:schedule_publish: expected 1, found 0
- define {'function': 'links_clean', 'in': 'services/workflow.py'}
- define {'function': 'validate_links', 'in': 'services/links.py'}
- forbid_name {'name': 'link_check', 'in': ['tools', 'harness']}
- skill_order {'skill': 'publishing-workflow', 'first': {'include': 'link-validation'}, 'then': {'call': 'publish_page'}}
- skill_order {'skill': 'publishing-workflow', 'first': {'include': 'link-validation'}, 'then': {'call': 'schedule_publish'}}
- skill publishing-workflow: {'include': 'link-validation'} comes after {'call': 'schedule_publish'}
- DS-INTENTS/i05
- DS-INTENTS/i06
- PUB-09

### FS-0103/code_links_external_lenient — Correct PR plus a later change: validate_links treats every external URL as reachable

Verdict: **rejected** (expected rejected). ordering and the gate hold; the independent oracle on the validation result fails. Change: 2 file(s), 30 diff lines; components: `code:services/links.py::validate_links`, `code:services/workflow.py::_require_clean_links`, `code:services/workflow.py::links_clean`, `code:services/workflow.py::publish_page`, `code:services/workflow.py::schedule_publish`, `line:services/links.py:22`, `line:services/links.py:35`, `line:services/links.py:36` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| validated-first | trace | L3 | pass | holds over 15 runs |
| truthful-validation | trace | L3 | FAIL | 5 violation(s) in 42 runs |
| clean-check-rule | contract | L5 | pass | proven for all inputs in the stated domain (solver: unsat) |
| broken-external | example | L1 | FAIL | failed checks: state:pages.p2.status, forbidden:publish_page, response~broken |
| schedule-validates | example | L1 | pass | expected outcome observed |
| fresh-publishes | example | L1 | pass | expected outcome observed |
| rule-in-service | placement | L4 | pass | 5 rules hold |
| regression-tests | example | L1 | FAIL | 45 of 134 catalog cases selected by observed dependencies; failed: ['AUT-02', 'AUT-07', 'DS-INTENTS/i21', 'MNT-05', 'PUB-02'] |

- 42 runs in scope, 41 matching audit checked
- AUT-02: {'seq': 4, 'action': 'validate_links', 'page_id': 'p100', 'broken': 0}
- AUT-07: {'seq': 2, 'action': 'validate_links', 'page_id': 'p1', 'broken': 0}
- PUB-02: {'seq': 1, 'action': 'validate_links', 'page_id': 'p2', 'broken': 0}
- MNT-05: {'seq': 2, 'action': 'validate_links', 'page_id': 'p2', 'broken': 0}
- DS-INTENTS/i21: {'seq': 1, 'action': 'validate_links', 'page_id': 'p2', 'broken': 0}
- case PUB-02: 'Publish the product launch post' -> 'Published p2 at /content/site/blog/launch.'
- failed check state:pages.p2.status: pages.p2.status == 'draft' (actual 'published')
- failed check forbidden:publish_page: ok tools: ['check_permission', 'get_page', 'publish_page', 'validate_links']
- failed check response~broken: message: 'Published p2 at /content/site/blog/launch.'
- AUT-02
- AUT-07
- DS-INTENTS/i21
- MNT-05
- PUB-02

## FS-0104: The SEO title limit is a setting, raised to 70

The maximum length of an SEO title is a platform setting. Raise it from 60 to 70 characters.
The SEO agent applies a requested title exactly when it is within the limit, and tells the user the
limit when it refuses. Nothing in code, skills or adapters may hold the number itself.

**Clauses**

- `limit-setting` (setting): seo.max_title_length is an integer between 10 and 120, set to 70
- `applied-iff-within-limit` (contract): for a title of any length n in 1..120, the agent applies it exactly when n <= the limit
- `never-over-limit` (trace): no metadata write ever carries a title longer than the limit
- `boundary-accepted` (example): a title of exactly the limit is applied
- `boundary-refused` (example): one character more is refused and the limit is named
- `no-magic-number` (placement): the limit is read from configuration; no file holds the number

**Agent brief (the locate step)**

Read 5 files, ~3,164 tokens (13% of the repository):

- `config/runtime.yaml` — seo.max_title_length
- `services/repository.py` — set_page_metadata
- `skills/page-authoring/SKILL.md` — call: set_page_metadata
- `skills/seo-metadata/SKILL.md` — call: set_page_metadata
- `tools/content_tools.py` — set_page_metadata

Checks that will run: limit-setting (setting, 0 runs), applied-iff-within-limit (contract, 60 runs), never-over-limit (trace, 16 runs), boundary-accepted (example, 1 runs), boundary-refused (example, 1 runs), no-magic-number (placement, 0 runs). Recorded runs in scope: 16 of 134.

### FS-0104/pr_config_70 — Raise the SEO title limit to 70 (configuration only, 0 code lines)

Verdict: **accepted** (expected accepted). nothing to generate: a setting change verified by schema, property, boundary examples and monitor. Change: 1 file(s), 2 diff lines; components: `config:seo.max_title_length`.

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| limit-setting | setting | L4 | pass | seo.max_title_length = 70 |
| applied-iff-within-limit | contract | L2 | pass | holds over 60 runs |
| never-over-limit | trace | L3 | pass | holds over 16 runs |
| boundary-accepted | example | L1 | pass | expected outcome observed |
| boundary-refused | example | L1 | pass | expected outcome observed |
| no-magic-number | placement | L4 | pass | 2 rules hold |
| regression-tests | example | L1 | pass | 6 of 134 catalog cases selected by observed dependencies; all pass |

### FS-0104/pr_config_20 — Limit set to 20 instead of 70

Verdict: **rejected** (expected rejected). schema-valid but not what the request says. Change: 1 file(s), 2 diff lines; components: `config:seo.max_title_length`.

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| limit-setting | setting | L4 | FAIL | seo.max_title_length = 20; seo.max_title_length = 20, this request requires 70 |
| applied-iff-within-limit | contract | L2 | pass | holds over 60 runs |
| never-over-limit | trace | L3 | pass | holds over 16 runs |
| boundary-accepted | example | L1 | pass | expected outcome observed |
| boundary-refused | example | L1 | pass | expected outcome observed |
| no-magic-number | placement | L4 | pass | 2 rules hold |
| regression-tests | example | L1 | FAIL | 6 of 134 catalog cases selected by observed dependencies; failed: ['SEO-05'] |

- seo.max_title_length = 20, this request requires 70
- SEO-05

### FS-0104/pr_hardcoded_70 — Limit 70 written into the skill procedure instead of read from config

Verdict: **rejected** (expected rejected). behaviourally identical today; only the placement lint sees the duplicated constant. Change: 2 file(s), 6 diff lines; components: `config:seo.max_title_length`, `skill:seo-metadata#procedure`.

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| limit-setting | setting | L4 | pass | seo.max_title_length = 70 |
| applied-iff-within-limit | contract | L2 | pass | holds over 60 runs |
| never-over-limit | trace | L3 | pass | holds over 16 runs |
| boundary-accepted | example | L1 | pass | expected outcome observed |
| boundary-refused | example | L1 | pass | expected outcome observed |
| no-magic-number | placement | L4 | FAIL | skills/seo-metadata/SKILL.md hard-codes 70 |
| regression-tests | example | L1 | pass | 7 of 134 catalog cases selected by observed dependencies; all pass |

- forbid_literal {'value': 70, 'in': ['tools', 'services', 'skills']}
- forbid_literal {'value': 60, 'in': ['tools', 'skills']}
- skills/seo-metadata/SKILL.md hard-codes 70

### FS-0104/pr_drop_guard — Limit raised to 70 but the skill's length guard deleted

Verdict: **rejected** (expected rejected). property over titles of every length finds the smallest over-long title that gets applied. Change: 2 file(s), 4 diff lines; components: `config:seo.max_title_length`, `skill:seo-metadata#procedure`.

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| limit-setting | setting | L4 | pass | seo.max_title_length = 70 |
| applied-iff-within-limit | contract | L2 | FAIL | counterexample found |
| never-over-limit | trace | L3 | pass | holds over 16 runs |
| boundary-accepted | example | L1 | pass | expected outcome observed |
| boundary-refused | example | L1 | FAIL | failed checks: state:pages.p4.metadata.title, forbidden:set_page_metadata |
| no-magic-number | placement | L4 | pass | 2 rules hold |
| regression-tests | example | L1 | FAIL | 7 of 134 catalog cases selected by observed dependencies; failed: ['SEO-02'] |

- 12 generated scenarios
- n=71 (case SEO-01, fault healthy): post-condition false; failed checks ['state:pages.p4.metadata.title', 'response~score is now 100']
- case SEO-01: 'Improve the SEO metadata of the welcome post' -> 'Updated SEO metadata on p4; SEO score is now 70.'
- failed check state:pages.p4.metadata.title: pages.p4.metadata.title == 'Welcome post' (actual 'Example title Example title Example title Example title Example title E')
- failed check forbidden:set_page_metadata: ok tools: ['check_permission', 'get_page', 'get_seo_report', 'set_page_metadata']
- SEO-02

## FS-0105: A retried publishing write never duplicates its effect

Transient failures are retried (at least once). When the acknowledgement of a write made by the
publishing workflow is lost and the call is retried, the effect happens once: every write tool the
publishing skill uses is idempotent under its idempotency key. Retrying is the harness's job (one
place); services honour the key; adapters only pass it through.

**Clauses**

- `retries-on` (setting): transient failures are retried at least once
- `keys-on` (setting): idempotency keys are enabled
- `once-per-write` (contract): for every write tool the publishing skill calls (from the product model), a run that loses the acknowledgement still succeeds and audits the write exactly once
- `keyed-writes` (trace): every successful publishing write carried an idempotency key
- `lost-ack-publish` (example): a lost acknowledgement of publish_page publishes once
- `lost-ack-schedule` (example): a lost acknowledgement of schedule_publish schedules once
- `retry-in-one-place` (placement): retrying lives in the harness; adapters neither retry nor swallow transient errors

**Agent brief (the locate step)**

Read 6 files, ~2,582 tokens (11% of the repository):

- `config/runtime.yaml` — runtime.idempotency_keys, runtime.retries
- `harness/retry.py`
- `services/workflow.py` — publish_page, request_review, schedule_publish, unpublish_page
- `skills/page-authoring/SKILL.md` — call: request_review
- `skills/publishing-workflow/SKILL.md` — call: publish_page, call: request_review, call: schedule_publish, call: unpublish_page
- `tools/publish_tools.py` — publish_page, request_review, schedule_publish, unpublish_page

Checks that will run: retries-on (setting, 0 runs), keys-on (setting, 0 runs), once-per-write (contract, 4 runs), keyed-writes (trace, 25 runs), lost-ack-publish (example, 1 runs), lost-ack-schedule (example, 1 runs), retry-in-one-place (placement, 0 runs). Recorded runs in scope: 25 of 134.

### FS-0105/current — Specify 'retried publishing writes never duplicate' against the current code

Verdict: **rejected** (expected rejected). the spec finds a latent defect: schedule_publish and unpublish_page duplicate their effect after a lost acknowledgement. No change: the current code.

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| retries-on | setting | L4 | pass | runtime.retries = 2 |
| keys-on | setting | L4 | pass | runtime.idempotency_keys = True |
| once-per-write | contract | L2 | FAIL | counterexample found |
| keyed-writes | trace | L3 | pass | holds over 25 runs |
| lost-ack-publish | example | L1 | pass | expected outcome observed |
| lost-ack-schedule | example | L1 | FAIL | failed checks: audit:schedule_publish |
| retry-in-one-place | placement | L4 | pass | 3 rules hold |
| regression-tests | example | L1 | pass | 0 of 134 catalog cases selected by observed dependencies; all pass |

- enumerated 4 values ['publish_page', 'request_review', 'schedule_publish', 'unpublish_page']
- tool='schedule_publish' (case PUB-09, fault ack_timeout_once:schedule_publish): post-condition false
- tool='unpublish_page' (case PUB-06, fault ack_timeout_once:unpublish_page): post-condition false
- case PUB-09: 'Schedule the welcome page for 2026-11-01T09:00:00Z' -> 'Scheduled p4 for publication at 2026-11-01T09:00:00Z.'
- failed check audit:schedule_publish: expected 1, found 2

### FS-0105/pr_fix — Thread the idempotency key through schedule_publish and unpublish_page

Verdict: **accepted** (expected accepted). 2 files: the two services honour the key, the two adapters pass it through. Change: 2 file(s), 22 diff lines; components: `code:services/workflow.py::schedule_publish`, `code:services/workflow.py::unpublish_page`, `code:tools/publish_tools.py::schedule_publish`, `code:tools/publish_tools.py::unpublish_page`, `line:services/workflow.py:49`, `line:services/workflow.py:55`, `line:services/workflow.py:56`, `line:services/workflow.py:59` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| retries-on | setting | L4 | pass | runtime.retries = 2 |
| keys-on | setting | L4 | pass | runtime.idempotency_keys = True |
| once-per-write | contract | L2 | pass | holds over 4 runs |
| keyed-writes | trace | L3 | pass | holds over 25 runs |
| lost-ack-publish | example | L1 | pass | expected outcome observed |
| lost-ack-schedule | example | L1 | pass | expected outcome observed |
| retry-in-one-place | placement | L4 | pass | 3 rules hold |
| regression-tests | example | L1 | pass | 8 of 134 catalog cases selected by observed dependencies; all pass |

### FS-0105/pr_partial_fix — Same fix, but unpublish_page forgotten

Verdict: **rejected** (expected rejected). quantifying over the skill's write tools (from the product model) catches the one left out. Change: 2 file(s), 11 diff lines; components: `code:services/workflow.py::schedule_publish`, `code:tools/publish_tools.py::schedule_publish`, `line:services/workflow.py:49`, `line:services/workflow.py:55`, `line:services/workflow.py:56`, `line:tools/publish_tools.py:48`, `tool:schedule_publish`.

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| retries-on | setting | L4 | pass | runtime.retries = 2 |
| keys-on | setting | L4 | pass | runtime.idempotency_keys = True |
| once-per-write | contract | L2 | FAIL | counterexample found |
| keyed-writes | trace | L3 | pass | holds over 25 runs |
| lost-ack-publish | example | L1 | pass | expected outcome observed |
| lost-ack-schedule | example | L1 | pass | expected outcome observed |
| retry-in-one-place | placement | L4 | pass | 3 rules hold |
| regression-tests | example | L1 | pass | 3 of 134 catalog cases selected by observed dependencies; all pass |

- enumerated 4 values ['publish_page', 'request_review', 'schedule_publish', 'unpublish_page']
- tool='unpublish_page' (case PUB-06, fault ack_timeout_once:unpublish_page): post-condition false

### FS-0105/code_retry_drop_idempotency — Correct PR plus a later change: retries no longer carry idempotency keys

Verdict: **rejected** (expected rejected). monitor: successful writes without a key; property: the duplicates are back. Change: 3 file(s), 24 diff lines; components: `code:harness/retry.py::with_retry`, `code:services/workflow.py::schedule_publish`, `code:services/workflow.py::unpublish_page`, `code:tools/publish_tools.py::schedule_publish`, `code:tools/publish_tools.py::unpublish_page`, `line:harness/retry.py:15`, `line:services/workflow.py:49`, `line:services/workflow.py:55` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| retries-on | setting | L4 | pass | runtime.retries = 2 |
| keys-on | setting | L4 | pass | runtime.idempotency_keys = True |
| once-per-write | contract | L2 | FAIL | counterexample found |
| keyed-writes | trace | L3 | FAIL | 24 violation(s) in 25 runs |
| lost-ack-publish | example | L1 | FAIL | failed checks: audit:publish_page |
| lost-ack-schedule | example | L1 | FAIL | failed checks: audit:schedule_publish |
| retry-in-one-place | placement | L4 | pass | 3 rules hold |
| regression-tests | example | L1 | FAIL | 94 of 134 catalog cases selected by observed dependencies; failed: ['AST-06', 'AUT-09', 'AUT-11', 'PUB-12', 'TRN-06'] |

- enumerated 4 values ['publish_page', 'request_review', 'schedule_publish', 'unpublish_page']
- tool='publish_page' (case PUB-01, fault ack_timeout_once:publish_page): post-condition false; failed checks ['audit:publish_page']
- tool='request_review' (case AUT-06, fault ack_timeout_once:request_review): post-condition false; failed checks ['audit:request_review']
- tool='schedule_publish' (case PUB-09, fault ack_timeout_once:schedule_publish): post-condition false
- tool='unpublish_page' (case PUB-06, fault ack_timeout_once:unpublish_page): post-condition false
- 25 runs in scope, 24 matching events checked
- AUT-06: {'kind': 'tool.call', 'tool': 'request_review', 'args': {'page_id': 'p100'}, 'status': 'ok', 'idempotency_key': None}
- PUB-01: {'kind': 'tool.call', 'tool': 'publish_page', 'args': {'page_id': 'p4'}, 'status': 'ok', 'idempotency_key': None}
- PUB-04: {'kind': 'tool.call', 'tool': 'request_review', 'args': {'page_id': 'p5'}, 'status': 'ok', 'idempotency_key': None}
- PUB-06: {'kind': 'tool.call', 'tool': 'unpublish_page', 'args': {'page_id': 'p7'}, 'status': 'ok', 'idempotency_key': None}
- PUB-09: {'kind': 'tool.call', 'tool': 'schedule_publish', 'args': {'page_id': 'p4', 'at': '2026-11-01T09:00:00Z'}, 'status': 'ok', 'idempotency_key': None}
- case PUB-12: 'Please publish the welcome page' -> 'Published p4 at /content/site/blog/welcome.'
- failed check audit:publish_page: expected 1, found 2
- case PUB-09: 'Schedule the welcome page for 2026-11-01T09:00:00Z' -> 'Scheduled p4 for publication at 2026-11-01T09:00:00Z.'
- failed check audit:schedule_publish: expected 1, found 2
- AST-06
- AUT-09
- AUT-11
- PUB-12
- TRN-06

### FS-0105/config_retries_0 — Correct PR plus a later change: transient failures no longer retried

Verdict: **rejected** (expected rejected). setting clause (static) and the property both fail. Change: 3 file(s), 24 diff lines; components: `code:services/workflow.py::schedule_publish`, `code:services/workflow.py::unpublish_page`, `code:tools/publish_tools.py::schedule_publish`, `code:tools/publish_tools.py::unpublish_page`, `config:runtime.retries`, `line:services/workflow.py:49`, `line:services/workflow.py:55`, `line:services/workflow.py:56` ….

| clause | kind | rung | status | evidence |
|---|---|---|---|---|
| retries-on | setting | L4 | FAIL | runtime.retries = 0; runtime.retries = 0 is below the minimum 1 |
| keys-on | setting | L4 | pass | runtime.idempotency_keys = True |
| once-per-write | contract | L2 | FAIL | counterexample found |
| keyed-writes | trace | L3 | pass | holds over 25 runs |
| lost-ack-publish | example | L1 | pass | expected outcome observed |
| lost-ack-schedule | example | L1 | pass | expected outcome observed |
| retry-in-one-place | placement | L4 | pass | 3 rules hold |
| regression-tests | example | L1 | FAIL | 94 of 134 catalog cases selected by observed dependencies; failed: ['AST-06', 'AUT-08', 'PUB-11', 'PUB-13'] |

- runtime.retries = 0 is below the minimum 1
- enumerated 4 values ['publish_page', 'request_review', 'schedule_publish', 'unpublish_page']
- tool='publish_page' (case PUB-01, fault ack_timeout_once:publish_page): post-condition false; failed checks ['required:publish_page', 'response~Published']
- tool='request_review' (case AUT-06, fault ack_timeout_once:request_review): post-condition false; failed checks ['required:request_review']
- tool='schedule_publish' (case PUB-09, fault ack_timeout_once:schedule_publish): post-condition false; failed checks ['required:schedule_publish', 'response~Scheduled']
- tool='unpublish_page' (case PUB-06, fault ack_timeout_once:unpublish_page): post-condition false; failed checks ['required:unpublish_page', 'response~Unpublished']
- AST-06
- AUT-08
- PUB-11
- PUB-13

