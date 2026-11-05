"""Tool adapters for content authoring (pages, versions, metadata)."""

from ..services import repository
from .registry import ToolContext, tool


@tool("search_pages", "read", "Search pages by text in title, path or body.", {"query": "free-text query"})
def search_pages(ctx: ToolContext, query: str):
    """Search the pages through the repository service and return the matches under ``results``.

    The search is a case-insensitive substring match on the title, path and body of every page, and each
    match gives the page's id, path, title and status. The list is wrapped in a dict because every tool
    answers with a dict."""
    return {"results": repository.search_pages(ctx.state, query)}


@tool(
    "get_page",
    "read",
    "Fetch a page with its status, metadata, links, assets and review state.",
    {"page_id": "identifier of the page, e.g. p1"},
)
def get_page(ctx: ToolContext, page_id: str):
    """Fetch a page from the repository service and return a summary of it rather than the stored record.

    The summary does not include the body, and it gives the number of versions instead of the versions
    themselves. ``review_approved`` is derived from the review status; it is the flag the publishing skill
    checks before it publishes. Metadata, links and assets are copied, so later changes to the page do not
    alter a result the agent already holds. A page without a locale is reported as ``en-US``."""
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
    """Create a draft page through the repository service and return its id and path.

    The template defaults to ``article``; the service accepts article, landing and product only, refuses an
    empty title, and builds the path from the parent path and a slug of the title. The author is the user
    the agent acts for, and the call's idempotency key is passed through, so a retried call returns the page
    made by the first try instead of creating a second one."""
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
    """Replace a page's body through the repository service and return the new version number and links.

    The service keeps the new body as a new version, reads the links again from the ``[[...]]`` markers in
    it, and resets the page's review, so an approval given before the edit no longer counts. The call's
    idempotency key is passed through, so a retried call does not add a second version."""
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
    """Set a page's SEO metadata through the repository service and return all of its metadata afterwards.

    Only the fields that are given change; a field left as None keeps its current value. The SEO title is
    stored in the metadata and does not rename the page. The configured title-length limit is not checked
    here: the SEO skill checks it before it calls this tool. No idempotency key is passed on; a repeated
    call sets the same values again and writes another audit entry."""
    return repository.set_page_metadata(
        ctx.state, page_id, title=title, description=description, keywords=keywords, actor=ctx.user_id
    )


@tool("list_versions", "read", "List the versions of a page.", {"page_id": "page identifier"})
def list_versions(ctx: ToolContext, page_id: str):
    """List a page's versions through the repository service, oldest first, together with the page id.
    Each version gives its number and the length of its body, not the body itself."""
    return {"page_id": page_id, "versions": repository.list_versions(ctx.state, page_id)}


@tool(
    "rollback_page",
    "write",
    "Restore a page body from an earlier version.",
    {"page_id": "page identifier", "version": "version number to restore"},
)
def rollback_page(ctx: ToolContext, page_id: str, version: int):
    """Restore the body of an earlier version through the repository service; returns the restored and the
    new version number.

    The restored body is saved as a new version that records where it came from, so no version is lost.
    Unlike an edit, a rollback leaves the page's review state as it is. No idempotency key is passed on: a
    retry after a lost acknowledgement restores the body once more and adds another version."""
    # A model may send the version number as a string, while the service compares it with the stored
    # integer version numbers; hence the conversion.
    return repository.rollback_page(ctx.state, page_id, int(version), actor=ctx.user_id)
