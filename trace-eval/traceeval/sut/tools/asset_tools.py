"""Tool adapters for digital assets."""

from ..services import repository
from .registry import ToolContext, tool


@tool(
    "upload_asset",
    "write",
    "Upload a new asset into a DAM folder.",
    {"name": "file name", "folder": "DAM folder path", "mime": "MIME type, e.g. image/png"},
)
def upload_asset(ctx: ToolContext, name: str, folder: str, mime: str):
    return repository.upload_asset(
        ctx.state, name, folder, mime, actor=ctx.user_id, idempotency_key=ctx.idempotency_key
    )


@tool("get_asset", "read", "Fetch an asset's metadata.", {"asset_id": "asset identifier"})
def get_asset(ctx: ToolContext, asset_id: str):
    return repository.get_asset(ctx.state, asset_id)


@tool(
    "attach_asset",
    "write",
    "Attach an existing asset to a page.",
    {"page_id": "page identifier", "asset_id": "asset identifier"},
)
def attach_asset(ctx: ToolContext, page_id: str, asset_id: str):
    return repository.attach_asset(ctx.state, page_id, asset_id, actor=ctx.user_id)
