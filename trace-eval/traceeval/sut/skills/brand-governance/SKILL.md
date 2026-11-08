---
name: brand-governance
version: 1
description: Check a page against the brand guidelines, find the pages that use a term, or say what the guidelines are.
tools: [get_brand_guidelines, check_brand_policy, search_pages]
---
# Brand governance

Use this skill to check whether a page meets the brand guidelines, to find the pages that use a term,
or to tell the user what the guidelines say. The guidelines forbid some terms anywhere on the site,
require the offer disclaimer on every page that advertises an offer, and allow only licensed assets.
A page that breaks any of them must not go live until it is fixed: report every violation, in the
words of the check.

## Procedure
```yaml
- id: guidelines
  when: intent == 'guidelines'
  call: get_brand_guidelines
  then: stop:guidelines
  then_message: "Forbidden terms: {result.guidelines.forbidden_terms}. Every offer must say: {result.guidelines.offer_disclaimer} Only licensed assets may be used."
- id: find
  when: intent == 'find'
  call: search_pages
  args: {query: $term}
  then: stop:found
  then_message: "Pages that use '{ctx['term']}' (id, path, status): {result.find.results}"
- id: check
  call: check_brand_policy
  args: {page_id: $page_id}
  require: last.compliant
  fail_message: "Page {ctx['page_id']} breaks the brand guidelines: it {[v['detail'] for v in result.check.violations]}."
- say: "Page {ctx['page_id']} meets the brand guidelines."
```

## Rules
- Never call a page compliant without a check that says so.
- Never change a page: report what must be fixed.
