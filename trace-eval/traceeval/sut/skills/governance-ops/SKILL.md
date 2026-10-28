---
name: governance-ops
version: 3
description: Data-subject exports under consent, and audit-log questions.
tools: [check_permission, check_consent, export_user_data, get_audit_log]
---
# Governance operations

Exports of personal data are guarded operations. Check that the operator has the `export_data`
permission, check that the data subject has given consent, and only then export. A subject without
consent must never be exported, even if the operator insists. Audit questions only read the log.

## Procedure
```yaml
- id: audit
  when: intent == 'audit'
  call: get_audit_log
  args: {page_id: $page_id}
  then: stop:audit
  then_message: "There are {result.audit.count} audit entries for {ctx['page_id']}."
- set: {action: export_data}
- include: governance-checks
- id: consent
  call: check_consent
  args: {subject_id: $subject_id}
  require: last.consent
  on_fail: stop:no_consent
  fail_message: "Subject {ctx['subject_id']} has not given consent; the export was refused."
- id: export
  call: export_user_data
  args: {subject_id: $subject_id}
- say: "Exported {result.export.records} records for subject {ctx['subject_id']} (export {result.export.export_id})."
```
