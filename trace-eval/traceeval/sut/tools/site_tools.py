"""Tool adapters for site analytics, the site audit and alt texts."""

from ..services import repository, site
from .registry import ToolContext, tool


@tool(
    "get_page_metrics",
    "read",
    "Page analytics (views, bounce rate, conversions, load time): one page, or the live pages of a section "
    "ranked by views.",
    {
        "page_id": "one page (leave empty for a ranking)",
        "section": "path of the section to rank, e.g. /content/site/blog",
        "top_n": "how many pages to rank",
        "order": "worst (fewest views first) or best",
    },
)
def get_page_metrics(ctx: ToolContext, page_id: str = "", section: str = "", top_n: int = 3, order: str = "worst"):
    """Return a page's analytics, or a ranking of a section's live pages by views, from the site service."""
    return site.page_metrics(ctx.state, page_id=page_id, section=section, top_n=top_n, order=order)


@tool(
    "audit_site",
    "read",
    "Audit the live pages of a section: broken links, images without alt text, missing descriptions, slow pages.",
    {"section": "path of the section, e.g. /content/site/blog"},
)
def audit_site(ctx: ToolContext, section: str):
    """Audit a section through the site service; a page counts as slow above ``optimizer.max_load_ms``."""
    return site.audit_site(ctx.state, section, max_load_ms=int(ctx.config.get("optimizer.max_load_ms")))


@tool(
    "fix_alt_text",
    "write",
    "Set the alt text of an image asset.",
    {"asset_id": "asset identifier", "alt": "the alt text"},
)
def fix_alt_text(ctx: ToolContext, asset_id: str, alt: str):
    """Set an asset's alt text through the repository service, on behalf of the requesting user."""
    return repository.set_alt_text(ctx.state, asset_id, alt, actor=ctx.user_id)
