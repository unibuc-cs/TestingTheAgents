---
name: asset-management
version: 2
description: Upload assets into the DAM and attach them to pages.
tools: [get_page, upload_asset, get_asset, attach_asset, check_permission]
---
# Asset management

Use this skill to upload a new asset (image, video or PDF) and/or attach an asset to a page.
Always confirm the page exists before attaching.

## Procedure
```yaml
- set: {action: attach}
- include: governance-checks
- id: upload
  when: intent == 'upload'
  call: upload_asset
  args: {name: $asset_name, folder: $folder, mime: $mime}
- when: intent == 'upload'
  set: {asset_id: =result.upload.asset_id}
- id: fetch
  call: get_page
  args: {page_id: $page_id}
- id: attach
  call: attach_asset
  args: {page_id: $page_id, asset_id: $asset_id}
- say: "Attached asset {ctx['asset_id']} to {ctx['page_id']}."
```
