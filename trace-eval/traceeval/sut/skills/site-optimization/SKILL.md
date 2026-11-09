---
name: site-optimization
version: 2
description: Check the health of a section of the site, fix a page's broken links, or set the alt text of an image.
tools: [audit_site, fix_broken_links, fix_alt_text, check_permission]
---
# Site optimization

Use this skill to check the health of a section of the site (broken links, images without alt text,
pages without a meta description, pages that load slowly), to fix the broken links of a page, or to set
the alt text of an image. A health check only reports: list every page with its issues. Fixing a page's
broken links unlinks them (the text stays) and changes nothing else. Fixing links and setting an alt text
change the site, so the user needs the `edit` permission.

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
- id: fix_links
  when: intent == 'fix_links'
  call: fix_broken_links
  args: {page_id: $page_id}
  then: stop:links_fixed
  then_message: "Unlinked the broken links of {ctx['page_id']}: {result.fix_links.unlinked}."
- id: fix
  call: fix_alt_text
  args: {asset_id: $asset_id, alt: $alt}
- say: "Set the alt text of asset {ctx['asset_id']} to \"{ctx['alt']}\"."
```
