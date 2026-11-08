"""Tool adapters for brand governance."""

from ..services import brand
from .registry import ToolContext, tool


@tool("get_brand_guidelines", "read", "Read the brand guidelines (forbidden terms, offer disclaimer, asset licences).")
def get_brand_guidelines(ctx: ToolContext):
    """Return the brand guidelines from the brand service."""
    return brand.guidelines(ctx.state)


@tool(
    "check_brand_policy",
    "read",
    "Check a page against the brand guidelines; lists every violation.",
    {"page_id": "page identifier"},
)
def check_brand_policy(ctx: ToolContext, page_id: str):
    """Check a page through the brand service: forbidden terms, the disclaimer of an offer, licensed assets.
    Returns ``compliant`` and the ``violations``."""
    return brand.check_page(ctx.state, page_id)
