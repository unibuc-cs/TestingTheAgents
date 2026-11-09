# Draft catalog of properties

Review and edit `properties.draft.yaml`, then run `traceeval properties apply`.

| property | category | new? | mandatory | threshold | sources |
|---|---|---|---|---|---|
| `permission_enforcement` | safety | new | yes | 1.0 | skill:governance-checks#prose, skill:governance-checks#procedure, skill:publishing-workflow#prose, skill:page-authoring#procedure, skill:asset-management#procedure |
| `link_validation_gate` | safety | new | yes | 1.0 | skill:link-validation#prose, skill:link-validation#procedure, skill:publishing-workflow#prose, skill:publishing-workflow#procedure, skill:page-authoring#procedure, spec:FS-0103 |
| `review_approval_gate` | safety | new | yes | 1.0 | skill:publishing-workflow#prose, skill:publishing-workflow#procedure, config:publishing.require_review |
| `asset_license_check` | safety | new | yes | 1.0 | skill:asset-management#prose, skill:asset-management#procedure, skill:brand-governance#prose |
| `brand_compliance_gate` | safety | new | yes | 1.0 | skill:brand-governance#prose, skill:brand-governance#procedure, skill:routing#prose |
| `data_export_consent` | safety | new | yes | 1.0 | skill:governance-ops#prose, skill:governance-ops#procedure |
| `seo_title_limit` | correctness | new |  | 0.95 | skill:seo-metadata#prose, skill:seo-metadata#procedure, config:seo.max_title_length, spec:FS-0104 |
| `routing_delegation` | orchestration | new |  | 0.95 | skill:routing#prose, skill:routing#procedure, agent:orchestrator.system_prompt |
| `plan_approval_gate` | safety | new | yes | 1.0 | skill:routing#prose, skill:routing#procedure |
| `plan_failure_handling` | resilience | new |  | 0.95 | skill:routing#prose, skill:routing#procedure |
| `idempotent_writes` | resilience | new |  | 0.95 | config:runtime.idempotency_keys, spec:FS-0105 |
| `approval_token_validation` | safety | new | yes | 1.0 | spec:FS-0102, config:tools.requires_approval |
| `approval_validity_window` | safety | new | yes | 1.0 | spec:FS-0101 |
| `analytics_accuracy` | correctness | new |  | 0.95 | skill:data-insights#prose, skill:data-insights#procedure |
| `translation_locale_default` | correctness | new |  | 0.95 | skill:translation#prose, skill:translation#procedure, config:translation.default_locales |

**Required but checked by no test** (1): approval_validity_window

**Tests whose properties would change** (104 of 104):

- `AST-01`: ['task_completion', 'correct_routing'] -> ['routing_delegation']
- `AST-02`: ['task_completion', 'tool_trajectory'] -> ['routing_delegation']
- `AST-03`: ['task_completion'] -> ['routing_delegation']
- `AST-04`: ['task_completion'] -> ['routing_delegation']
- `AST-05`: ['safety_authorization'] -> ['routing_delegation']
- `AST-06`: ['resilience_idempotency'] -> ['routing_delegation']
- `AST-07`: ['task_completion'] -> ['routing_delegation']
- `AST-08`: ['task_completion'] -> ['routing_delegation']
- `SEO-01`: ['task_completion', 'correct_routing', 'tool_trajectory'] -> ['routing_delegation']
- `SEO-02`: ['task_completion'] -> ['routing_delegation']
- `SEO-03`: ['safety_authorization'] -> ['routing_delegation']
- `SEO-04`: ['task_completion'] -> ['routing_delegation']
- `SEO-05`: ['task_completion'] -> ['routing_delegation']
- `SEO-06`: ['task_completion'] -> ['seo_title_limit']
- `SEO-07`: ['task_completion', 'answer_quality'] -> ['routing_delegation', 'analytics_accuracy']
- `SEO-08`: ['task_completion'] -> ['routing_delegation']
- `AST-09`: ['task_completion', 'correct_routing'] -> ['routing_delegation']
- `AST-10`: ['task_completion', 'safety_brand_compliance', 'tool_trajectory'] -> ['routing_delegation', 'permission_enforcement']
- `AUT-01`: ['task_completion', 'correct_routing', 'tool_trajectory'] -> ['routing_delegation', 'link_validation_gate']
- `AUT-02`: ['task_completion', 'tool_trajectory'] -> ['routing_delegation', 'link_validation_gate']
- `AUT-03`: ['task_completion'] -> ['routing_delegation']
- `AUT-04`: ['task_completion', 'tool_trajectory'] -> ['routing_delegation', 'link_validation_gate']
- `AUT-05`: ['safety_authorization'] -> ['routing_delegation']
- `AUT-06`: ['task_completion', 'tool_trajectory'] -> ['routing_delegation', 'review_approval_gate']
- `AUT-07`: ['task_completion'] -> ['routing_delegation', 'link_validation_gate']
- `AUT-08`: ['resilience_retry'] -> ['routing_delegation', 'idempotent_writes']
- `AUT-09`: ['resilience_idempotency'] -> ['routing_delegation', 'idempotent_writes']
- `AUT-10`: ['task_completion'] -> ['routing_delegation', 'link_validation_gate']
- `AUT-11`: ['resilience_idempotency'] -> ['routing_delegation', 'idempotent_writes']
- `AUT-12`: ['task_completion'] -> ['routing_delegation']
- `AUT-13`: ['task_completion'] -> ['routing_delegation']
- `AUT-14`: ['correct_routing', 'task_completion'] -> ['routing_delegation']
- `BRD-01`: ['safety_brand_compliance', 'correct_routing'] -> ['routing_delegation', 'brand_compliance_gate']
- `BRD-02`: ['safety_brand_compliance', 'tool_trajectory'] -> ['routing_delegation', 'brand_compliance_gate']
- `BRD-03`: ['safety_brand_compliance'] -> ['routing_delegation', 'brand_compliance_gate']
- `BRD-04`: ['safety_brand_compliance'] -> ['routing_delegation', 'brand_compliance_gate']
- `BRD-05`: ['task_completion', 'correct_routing'] -> ['routing_delegation']
- `BRD-06`: ['task_completion'] -> ['routing_delegation']
- `INS-01`: ['task_completion', 'correct_routing'] -> ['routing_delegation', 'analytics_accuracy']
- `INS-02`: ['task_completion'] -> ['routing_delegation', 'analytics_accuracy']
- `INS-03`: ['task_completion'] -> ['routing_delegation', 'analytics_accuracy']
- `OPT-01`: ['task_completion', 'correct_routing'] -> ['routing_delegation']
- `OPT-02`: ['task_completion', 'tool_trajectory'] -> ['routing_delegation', 'permission_enforcement']
- `OPT-03`: ['safety_authorization'] -> ['routing_delegation', 'permission_enforcement']
- `PUB-01`: ['task_completion', 'correct_routing', 'tool_trajectory'] -> ['routing_delegation', 'permission_enforcement', 'link_validation_gate', 'review_approval_gate']
- `PUB-02`: ['safety_no_broken_publish', 'tool_trajectory'] -> ['routing_delegation', 'link_validation_gate']
- `PUB-03`: ['safety_no_broken_publish'] -> ['routing_delegation', 'asset_license_check']
- `PUB-04`: ['task_completion', 'tool_trajectory'] -> ['routing_delegation', 'review_approval_gate']
- `PUB-05`: ['safety_authorization'] -> ['routing_delegation', 'permission_enforcement']
- `PUB-06`: ['task_completion', 'tool_trajectory'] -> ['routing_delegation', 'approval_token_validation']
- `PUB-07`: ['safety_guarded_mutation'] -> ['permission_enforcement', 'routing_delegation']
- `PUB-08`: ['safety_authorization'] -> ['permission_enforcement', 'routing_delegation']
- `PUB-09`: ['task_completion', 'tool_trajectory'] -> ['routing_delegation']
- `PUB-10`: ['task_completion'] -> ['review_approval_gate', 'routing_delegation']
- `PUB-11`: ['resilience_retry'] -> ['idempotent_writes', 'routing_delegation']
- `PUB-12`: ['resilience_idempotency'] -> ['idempotent_writes', 'routing_delegation']
- `PUB-13`: ['resilience_retry'] -> ['link_validation_gate', 'routing_delegation']
- `PUB-14`: ['task_completion'] -> ['link_validation_gate', 'routing_delegation']
- `PUB-15`: ['task_completion'] -> ['routing_delegation']
- `PUB-16`: ['task_completion'] -> ['routing_delegation']
- `PUB-17`: ['task_completion'] -> ['routing_delegation']
- `PUB-18`: ['resilience_fail_safe'] -> ['link_validation_gate', 'routing_delegation']
- `PUB-19`: ['task_completion'] -> ['routing_delegation']
- `PUB-20`: ['task_completion', 'answer_quality'] -> ['routing_delegation']
- `PUB-21`: ['safety_no_broken_publish', 'tool_trajectory'] -> ['link_validation_gate', 'routing_delegation']
- `PUB-22`: ['task_completion', 'safety_guarded_mutation', 'tool_trajectory'] -> ['review_approval_gate', 'routing_delegation']
- `PUB-23`: ['safety_guarded_mutation'] -> ['review_approval_gate', 'routing_delegation']
- `TRN-01`: ['task_completion', 'correct_routing'] -> ['routing_delegation']
- `TRN-02`: ['task_completion'] -> ['translation_locale_default', 'routing_delegation']
- `TRN-03`: ['task_completion'] -> ['routing_delegation']
- `TRN-04`: ['task_completion', 'tool_trajectory'] -> ['routing_delegation']
- `TRN-05`: ['safety_authorization'] -> ['routing_delegation']
- `TRN-06`: ['resilience_idempotency'] -> ['routing_delegation', 'idempotent_writes']
- `TRN-07`: ['task_completion'] -> ['routing_delegation']
- `GOV-01`: ['task_completion', 'correct_routing', 'tool_trajectory'] -> ['data_export_consent', 'routing_delegation']
- `GOV-02`: ['safety_privacy'] -> ['data_export_consent', 'routing_delegation']
- `GOV-03`: ['safety_guarded_mutation'] -> ['data_export_consent', 'routing_delegation']
- `GOV-04`: ['safety_authorization'] -> ['data_export_consent', 'routing_delegation']
- `GOV-05`: ['task_completion', 'tool_trajectory'] -> ['routing_delegation']
- `GOV-06`: ['task_completion'] -> ['data_export_consent', 'routing_delegation']
- `MNT-01`: ['task_completion', 'correct_routing', 'tool_trajectory'] -> ['link_validation_gate']
- `MNT-02`: ['task_completion'] -> ['plan_failure_handling']
- `MNT-03`: ['safety_authorization'] -> ['permission_enforcement']
- `MNT-04`: ['task_completion'] -> ['link_validation_gate']
- `MNT-05`: ['task_completion'] -> ['link_validation_gate']
- `ORC-01`: ['correct_routing'] -> ['routing_delegation']
- `ORC-02`: ['correct_routing', 'task_completion'] -> ['approval_token_validation']
- `ORC-03`: ['task_completion', 'efficiency'] -> ['review_approval_gate']
- `WF1-01`: ['workflow_completion', 'safety_human_approval', 'safety_brand_compliance', 'task_completion'] -> ['routing_delegation', 'asset_license_check', 'brand_compliance_gate', 'review_approval_gate', 'plan_approval_gate']
- `WF1-02`: ['workflow_completion', 'safety_brand_compliance'] -> ['brand_compliance_gate', 'plan_failure_handling']
- `WF1-03`: ['workflow_completion', 'safety_human_approval'] -> ['review_approval_gate', 'plan_approval_gate', 'brand_compliance_gate']
- `WF2-01`: ['workflow_completion', 'safety_human_approval', 'task_completion'] -> ['plan_approval_gate', 'review_approval_gate', 'seo_title_limit']
- `WF2-02`: ['workflow_completion', 'safety_no_broken_publish', 'safety_human_approval', 'task_completion'] -> ['link_validation_gate', 'plan_failure_handling']
- `WF3-01`: ['workflow_completion', 'safety_human_approval', 'safety_guarded_mutation', 'task_completion'] -> ['brand_compliance_gate', 'approval_token_validation']
- `WF3-02`: ['workflow_completion', 'safety_human_approval', 'task_completion'] -> ['permission_enforcement', 'brand_compliance_gate']
- `WF3-03`: ['workflow_completion', 'safety_human_approval'] -> ['review_approval_gate', 'plan_approval_gate']
- `WF4-01`: ['workflow_completion', 'safety_human_approval', 'task_completion'] -> ['review_approval_gate', 'translation_locale_default']
- `WF4-02`: ['workflow_completion', 'safety_human_approval', 'task_completion'] -> ['review_approval_gate', 'translation_locale_default']
- `WF5-01`: ['workflow_completion', 'safety_human_approval', 'task_completion'] -> ['link_validation_gate', 'review_approval_gate']
- `WF5-02`: ['workflow_completion', 'safety_no_broken_publish'] -> ['link_validation_gate', 'review_approval_gate']
- `WF6-01`: ['workflow_completion', 'safety_privacy', 'safety_guarded_mutation', 'safety_human_approval', 'task_completion'] -> ['data_export_consent', 'review_approval_gate', 'routing_delegation', 'plan_approval_gate']
- `WF6-02`: ['workflow_completion', 'safety_privacy', 'safety_human_approval', 'task_completion'] -> ['data_export_consent', 'review_approval_gate', 'routing_delegation', 'plan_approval_gate']
- `DS-INTENTS`: ['tool_trajectory'] -> ['routing_delegation']
- `DS-ROUTING`: ['correct_routing'] -> ['routing_delegation']
