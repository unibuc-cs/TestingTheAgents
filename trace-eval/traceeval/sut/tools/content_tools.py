"""Tool adapters for content authoring (pages, versions, metadata)."""

from ..services import repository
from .registry import ToolContext, tool


@tool("search_pages", "read", "Search pages by text in title, path or body.", {"query": "free-text query"})
def search_pages(ctx: ToolContext, query: str):
    return {"results": repository.search_pages(ctx.state, query)}


@tool(
    "get_page",
    "read",
    "Fetch a page with its status, metadata, links, assets and review state.",
    {"page_id": "identifier of the page, e.g. p1"},
)
def get_page(ctx: ToolContext, page_id: str):
    page = repository.get_page(ctx.state, page_id)
    return {
        "page_id": page_id,
        "path": page["path"],
        "title": page["title"],
        "status": page["status"],
        "metadata": dict(page.get("metadata", {})),
        "links": list(page.get("links", [])),
        "assets": list(page.get("assets", [])),
        "review_status": page["review"]["status"],
        "review_approved": page["review"]["status"] == "approved",
        "versions": len(page["versions"]),
        "locale": page.get("locale", "en-US"),
        "scheduled_at": page.get("scheduled_at"),
    }


@tool(
    "create_page",
    "write",
    "Create a new draft page under a parent path.",
    {
        "parent_path": "parent folder path, e.g. /content/site/blog",
        "title": "page title",
        "template": "one of article, landing, product",
    },
)
def create_page(ctx: ToolContext, parent_path: str, title: str, template: str = "article"):
    return repository.create_page(
        ctx.state, parent_path, title, template, actor=ctx.user_id, idempotency_key=ctx.idempotency_key
    )


@tool(
    "update_page_content",
    "write",
    "Replace the body of a page (creates a new version).",
    {"page_id": "page identifier", "body": "new body text; links are written as [[/path]] or [[https://...]]"},
)
def update_page_content(ctx: ToolContext, page_id: str, body: str):
    return repository.update_page_content(
        ctx.state, page_id, body, actor=ctx.user_id, idempotency_key=ctx.idempotency_key
    )


@tool(
    "set_page_metadata",
    "write",
    "Set SEO metadata (title, description, keywords) on a page.",
    {
        "page_id": "page identifier",
        "title": "SEO title",
        "description": "meta description",
        "keywords": "list of keywords",
    },
)
def set_page_metadata(
    ctx: ToolContext,
    page_id: str,
    title: str | None = None,
    description: str | None = None,
    keywords: list | None = None,
):
    return repository.set_page_metadata(
        ctx.state, page_id, title=title, description=description, keywords=keywords, actor=ctx.user_id
    )


@tool("list_versions", "read", "List the versions of a page.", {"page_id": "page identifier"})
def list_versions(ctx: ToolContext, page_id: str):
    return {"page_id": page_id, "versions": repository.list_versions(ctx.state, page_id)}


@tool(
    "rollback_page",
    "write",
    "Restore a page body from an earlier version.",
    {"page_id": "page identifier", "version": "version number to restore"},
)
def rollback_page(ctx: ToolContext, page_id: str, version: int):
    return repository.rollback_page(ctx.state, page_id, int(version), actor=ctx.user_id)
