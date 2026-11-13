---
name: data-insights
version: 1
description: Report the analytics of a page, or rank the live pages of a section by views.
tools: [get_page_metrics]
---
# Data insights

Use this skill for questions about how pages perform. For one page, report its views, bounce rate and
conversions. For a ranking ("the three worst blog posts", "our best pages"), rank the live pages of
the section by views and list them in that order, each with its views. Report the numbers as the
analytics give them; do not estimate.

## Procedure
```yaml
- id: page
  when: ctx.get('page_id') is not None
  call: get_page_metrics
  args: {page_id: $page_id}
  then: stop:page
  then_message: "Analytics of {ctx['page_id']}: {result.page.pages}"
- id: ranking
  call: get_page_metrics
  args: {section: $section, top_n: $top_n, order: $order}
- say: "The {ctx['order']} {ctx['top_n']} pages of {ctx['section']} by views: {result.ranking.pages}"
```
