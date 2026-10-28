---
name: rollback
version: 2
description: Restore an earlier version of a page and re-validate its links.
tools: [get_page, list_versions, rollback_page, validate_links, check_permission]
---
# Rollback

Restoring an earlier version is a content change: check the permission, list the versions to make
sure the requested one exists, restore it, and validate links of the restored body.

## Procedure
```yaml
- set: {action: rollback}
- include: governance-checks
- id: fetch
  call: get_page
  args: {page_id: $page_id}
- id: versions
  call: list_versions
  args: {page_id: $page_id}
- id: restore
  call: rollback_page
  args: {page_id: $page_id, version: $version}
- include: link-validation
- say: "Restored {ctx['page_id']} to version {ctx['version']} (now v{result.restore.version})."
```
