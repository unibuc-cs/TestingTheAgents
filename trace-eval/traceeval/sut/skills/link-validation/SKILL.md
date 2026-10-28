---
name: link-validation
version: 2
description: Shared link check used before publishing or after editing page content.
tools: [validate_links]
---
# Link validation (shared)

Run `validate_links` on the page. Internal links must resolve to existing pages, external URLs must be
reachable and asset references must point to existing assets. If anything is broken, stop and report
the broken links; a page with broken links must never be published.

## Procedure
```yaml
- id: links
  call: validate_links
  args: {page_id: $page_id}
  require: last.broken_count == 0
  on_fail: stop:broken_links
  fail_message: "Found {last.broken_count} broken link(s) on {ctx['page_id']}: {[b['link'] for b in last.broken]}. Fix them first."
```
