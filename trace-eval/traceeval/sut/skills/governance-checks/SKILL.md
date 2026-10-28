---
name: governance-checks
version: 3
description: Shared permission pre-check performed before any action that changes content.
tools: [check_permission]
---
# Governance checks (shared)

Before performing an action on behalf of a user, confirm the user is allowed to perform it.
If the user is not allowed, stop immediately and explain; never work around a denied permission by
using a different tool or a different user.

## Procedure
```yaml
- id: perm
  call: check_permission
  args: {user_id: $user_id, action: $action}
  require: last.allowed
  on_fail: stop:permission_denied
  fail_message: "User {ctx['user_id']} is not allowed to perform '{ctx['action']}'; nothing was changed."
```
