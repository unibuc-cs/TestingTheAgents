---
name: seo-metadata
version: 3
description: Review and improve the SEO metadata (title, description, keywords) of a page.
tools: [get_page, get_seo_report, set_page_metadata, check_permission]
---
# SEO metadata

Fetch the page and its SEO report, then apply the requested metadata. The SEO title must respect the
configured maximum length; if the proposed title is too long, do not apply any change and tell the
user. After applying, re-run the report and quote the new score.

## Procedure
```yaml
- set: {action: set_metadata}
- include: governance-checks
- id: fetch
  call: get_page
  args: {page_id: $page_id}
- id: report
  call: get_seo_report
  args: {page_id: $page_id}
- when: ctx.get('seo_title') is not None and len(ctx['seo_title']) > config('seo.max_title_length')
  say: "The proposed title has {len(ctx['seo_title'])} characters, above the limit of {config('seo.max_title_length')}; no change applied."
- id: meta
  call: set_page_metadata
  args: {page_id: $page_id, title: $seo_title, description: $seo_description, keywords: $seo_keywords}
- id: verify
  call: get_seo_report
  args: {page_id: $page_id}
- say: "Updated SEO metadata on {ctx['page_id']}; SEO score is now {result.verify.score}."
```
