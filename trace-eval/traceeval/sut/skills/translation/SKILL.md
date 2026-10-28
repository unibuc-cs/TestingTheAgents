---
name: translation
version: 2
description: Create translation jobs for pages and report translation status.
tools: [get_page, check_permission, create_translation_job, get_translation_status]
---
# Translation

For a translation request, fetch the page and create one translation job covering all requested
locales. When no locales are given, use the platform's default locales. For a status question,
look up the job and report its state.

## Procedure
```yaml
- id: status
  when: intent == 'status'
  call: get_translation_status
  args: {job_id: $job_id}
  then: stop:status
  then_message: "Translation job {ctx['job_id']} is {result.status.status} for {result.status.locales}."
- set: {action: translate}
- include: governance-checks
- id: fetch
  call: get_page
  args: {page_id: $page_id}
- when: ctx.get('locales') is None
  set: {locales: =config('translation.default_locales')}
- id: job
  call: create_translation_job
  args: {page_id: $page_id, locales: $locales}
- say: "Created translation job {result.job.job_id} for {ctx['page_id']} into {ctx['locales']}."
```
