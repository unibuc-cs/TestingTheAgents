---
name: publishing-workflow
version: 5
description: Publish, schedule or unpublish a page safely (permission, link and review gates).
tools: [get_page, check_permission, validate_links, request_review, publish_page, schedule_publish, unpublish_page]
---
# Publishing workflow

Use this skill when the user wants a page published, scheduled for publication, or taken down.

Order of operations: fetch the page, check the permission for the requested action, then (for
publishing and scheduling) validate links and make sure the page has an approved review when the
platform requires one. Only then publish or schedule. Taking a page down does not require link
validation but does require the `unpublish` permission and an approval token.

## Procedure
```yaml
- id: fetch
  call: get_page
  args: {page_id: $page_id}
- when: intent == 'unpublish'
  set: {action: unpublish}
- when: intent == 'schedule'
  set: {action: schedule}
- when: intent == 'publish'
  set: {action: publish}
- include: governance-checks
- id: unpublish
  when: intent == 'unpublish'
  call: unpublish_page
  args: {page_id: $page_id}
  then: stop:unpublished
  then_message: "Unpublished {ctx['page_id']} ({result.fetch.path})."
- include: link-validation
- id: review
  when: config('publishing.require_review') and not result.fetch.review_approved
  call: request_review
  args: {page_id: $page_id}
  then: stop:review_requested
  then_message: "Page {ctx['page_id']} needs an approved review before it can go live; I requested one."
- id: schedule
  when: intent == 'schedule'
  call: schedule_publish
  args: {page_id: $page_id, at: $publish_at}
  then: stop:scheduled
  then_message: "Scheduled {ctx['page_id']} for publication at {ctx['publish_at']}."
- id: publish
  call: publish_page
  args: {page_id: $page_id}
- say: "Published {ctx['page_id']} at {result.fetch.path}."
```

## Rules
- Never publish a page whose links failed validation.
- Never call `publish_page` or `schedule_publish` for a user without the matching permission.
- Do not unpublish anything unless explicitly asked to take a page down.
