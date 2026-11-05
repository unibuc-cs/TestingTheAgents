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
    """Queue one translation job for a page, covering all the given locales, through the translation service.

    Returns the job id, the page, the locales (sorted) and the status ``queued``. The service refuses an
    empty locale list and any locale it does not support. The adapter copies the locales into a new list,
    and it passes the call's idempotency key through, so a retried call returns the first job instead of
    queuing a second one."""
    return translation.create_translation_job(
        ctx.state, page_id, list(locales), actor=ctx.user_id, idempotency_key=ctx.idempotency_key
    )


@tool("get_translation_status", "read", "Get the status of a translation job.", {"job_id": "job identifier"})
def get_translation_status(ctx: ToolContext, job_id: str):
    """Return a translation job as the translation service stores it (page, locales, status, requester),
    with its id. An unknown job id is reported as not found."""
    return translation.get_translation_status(ctx.state, job_id)


@tool(
    "get_seo_report",
    "read",
    "Compute an SEO report (title length, description, keywords) for a page.",
    {"page_id": "page identifier"},
)
def get_seo_report(ctx: ToolContext, page_id: str):
    """Compute a page's SEO report through the SEO service: a score, the issues found and the title length.

    The report looks at the SEO title (or the page title when there is none), the description and the
    keywords; each issue costs 30 points of a score that starts at 100. The adapter reads the title-length
    limit and whether a description is required from the configuration on every call and passes them to
    the service, so a configuration change applies at once and each read shows up in the trace."""
    return seo.get_seo_report(
        ctx.state,
        page_id,
        max_title_length=int(ctx.config.get("seo.max_title_length")),
        require_description=bool(ctx.config.get("seo.require_description")),
    )
