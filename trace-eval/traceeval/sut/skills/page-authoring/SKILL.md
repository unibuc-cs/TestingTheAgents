---
name: page-authoring
version: 4
description: Create new draft pages or update the body of existing pages.
tools: [get_page, create_page, update_page_content, set_page_metadata, validate_links, request_review, check_permission]
---
# Page authoring

Use this skill to create a new draft page or to replace the body text of an existing page.

When creating a page, create it under the requested parent path, write the body if one was given,
validate the links in the body, and set the initial SEO metadata (title, description, keywords) from
the request. When editing, replace the body and validate links. If the user asked for a review,
request one at the end.

## Procedure
```yaml
- when: intent == 'create'
  set: {action: create}
- when: intent == 'edit'
  set: {action: edit}
- include: governance-checks
- id: create
  when: intent == 'create'
  call: create_page
  args: {parent_path: $parent_path, title: $title, template: $template}
- when: intent == 'create'
  set: {page_id: =result.create.page_id}
- id: write
  when: ctx.get('body') is not None
  call: update_page_content
  args: {page_id: $page_id, body: $body}
- id: meta
  when: intent == 'create'
  call: set_page_metadata
  args: {page_id: $page_id, title: $title, description: $description, keywords: $keywords}
- include: link-validation
- id: review
  when: ctx.get('request_review')
  call: request_review
  args: {page_id: $page_id}
- say: "Saved {ctx['page_id']} ({intent}); links validated."
```
