"""Tool adapters for translation and SEO."""

from ..services import seo, translation
from .registry import ToolContext, tool


@tool(
    "create_translation_job",
    "write",
    "Create a translation job for a page into target locales.",
    {"page_id": "page identifier", "locales": "list of locale codes such as de-DE"},
)
def create_translation_job(ctx: ToolContext, page_id: str, locales: list):
    return translation.create_translation_job(
        ctx.state, page_id, list(locales), actor=ctx.user_id, idempotency_key=ctx.idempotency_key
    )


@tool("get_translation_status", "read", "Get the status of a translation job.", {"job_id": "job identifier"})
def get_translation_status(ctx: ToolContext, job_id: str):
    return translation.get_translation_status(ctx.state, job_id)


@tool(
    "get_seo_report",
    "read",
    "Compute an SEO report (title length, description, keywords) for a page.",
    {"page_id": "page identifier"},
)
def get_seo_report(ctx: ToolContext, page_id: str):
    return seo.get_seo_report(
        ctx.state,
        page_id,
        max_title_length=int(ctx.config.get("seo.max_title_length")),
        require_description=bool(ctx.config.get("seo.require_description")),
    )
