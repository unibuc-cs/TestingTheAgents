---
name: asset-management
version: 3
description: Upload assets into the DAM, find assets, and attach them to pages.
tools: [get_page, upload_asset, search_assets, get_asset, attach_asset, check_permission]
---
# Asset management

Use this skill to upload a new asset (image, video or PDF), to find assets by their name or tags,
and/or to attach an asset to a page. Always confirm the page exists before attaching.

When the user describes the asset instead of naming it ("a hero image tagged spring"), search the DAM
and attach the first match whose licence is valid: an asset whose licence has expired may not be used
on the site. If no licensed asset matches, attach nothing and tell the user.

## Procedure
```yaml
- id: find
  when: intent == 'find'
  call: search_assets
  args: {query: $asset_query}
  then: stop:found
  then_message: "Assets matching '{ctx['asset_query']}' (id, name, tags, licence): {result.find.assets}"
- id: search
  when: intent == 'attach' and ctx.get('asset_id') is None
  call: search_assets
  args: {query: $asset_query}
- when: intent == 'attach' and ctx.get('asset_id') is None
  set: {asset_id: "=[a['asset_id'] for a in result.search.assets if a['license'] == 'licensed'][0]"}
- set: {action: attach}
- include: governance-checks
- id: fetch
  call: get_page
  args: {page_id: $page_id}
- id: upload
  when: intent == 'upload'
  call: upload_asset
  args: {name: $asset_name, folder: $folder, mime: $mime}
- when: intent == 'upload'
  set: {asset_id: =result.upload.asset_id}
- id: attach
  call: attach_asset
  args: {page_id: $page_id, asset_id: $asset_id}
- say: "Attached asset {ctx['asset_id']} to {ctx['page_id']}."
```
