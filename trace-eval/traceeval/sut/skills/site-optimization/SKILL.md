---
name: site-optimization
version: 1
description: Check the health of a section of the site, or set the alt text of an image.
tools: [audit_site, fix_alt_text, check_permission]
---
# Site optimization

Use this skill to check the health of a section of the site (broken links, images without alt text,
pages without a meta description, pages that load slowly) or to set the alt text of an image. A health
check only reports: list every page with its issues. Setting an alt text changes an asset, so the user
needs the `edit` permission.

## Procedure
```yaml
- id: audit
  when: intent == 'audit'
  call: audit_site
  args: {section: $section}
  then: stop:audited
  then_message: "Health check of {ctx['section']}: {result.audit.issue_count} issues. {result.audit.pages}"
- set: {action: edit}
- include: governance-checks
- id: fix
  call: fix_alt_text
  args: {asset_id: $asset_id, alt: $alt}
- say: "Set the alt text of asset {ctx['asset_id']} to \"{ctx['alt']}\"."
```
