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
    """Upload an asset through the repository service and return its new id and its path in the DAM.

    Only the asset's record is stored (name, folder, MIME type and uploader); there is no file content. The
    service accepts images, videos and PDFs. The uploader is the user the agent acts for, and the call's
    idempotency key is passed through, so a retried upload returns the first asset instead of creating a
    second one."""
    return repository.upload_asset(
        ctx.state, name, folder, mime, actor=ctx.user_id, idempotency_key=ctx.idempotency_key
    )


@tool(
    "search_assets",
    "read",
    "Search the DAM by words in an asset's name, folder, tags or description.",
    {"query": "words to search for, e.g. 'spring hero'"},
)
def search_assets(ctx: ToolContext, query: str):
    """Search the assets through the repository service; each match has its id, name, tags and licence."""
    return repository.search_assets(ctx.state, query)


@tool("get_asset", "read", "Fetch an asset's metadata.", {"asset_id": "asset identifier"})
def get_asset(ctx: ToolContext, asset_id: str):
    """Return an asset's record (name, folder, MIME type, uploader) and its id, from the repository service.
    An unknown asset id is reported as not found."""
    return repository.get_asset(ctx.state, asset_id)


@tool(
    "attach_asset",
    "write",
    "Attach an existing asset to a page.",
    {"page_id": "page identifier", "asset_id": "asset identifier"},
)
def attach_asset(ctx: ToolContext, page_id: str, asset_id: str):
    """Attach an existing asset to a page through the repository service and return the page's asset list.

    Both the page and the asset must exist, and an asset that is already on the page is not added twice.
    No idempotency key is passed on; a repeated call only writes another audit entry."""
    return repository.attach_asset(ctx.state, page_id, asset_id, actor=ctx.user_id)
