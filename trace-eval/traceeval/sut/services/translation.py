"""Translation jobs.

A job records a request to translate a page into one or more locales. Nothing in the platform carries out
the translation or moves a job past ``queued``: the job and the page show what was requested."""

from .errors import NotFound, ValidationError
from .repository import get_page

# The locales a page can be translated into. Pages are written in en-US, which is not a translation target.
SUPPORTED_LOCALES = {"de-DE", "fr-FR", "es-ES", "it-IT", "ja-JP", "ro-RO"}


def create_translation_job(
    state, page_id: str, locales: list[str], actor: str, idempotency_key: str | None = None
) -> dict:
    """Queue the translation of a page into the given locales and return the job: ``job_id``, ``page_id``,
    the sorted ``locales`` and ``status`` "queued".

    Raises NotFound for an unknown page, and ValidationError when no locale is given or any of them is not
    in SUPPORTED_LOCALES; nothing is queued then. A retry with the same idempotency key returns the job the
    first call created instead of creating a second one."""
    # A retry of a call that already went through gets back the job it created.
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    page = get_page(state, page_id)
    # The whole request is refused if it names no locale, or a single unsupported one.
    if not locales:
        raise ValidationError("at least one target locale is required")
    bad = [loc for loc in locales if loc not in SUPPORTED_LOCALES]
    if bad:
        raise ValidationError(f"unsupported locales: {bad}")
    # Jobs are numbered in the order they are created: tj-1, tj-2, ...
    jobs = state.data["translation_jobs"]
    job_id = f"tj-{len(jobs) + 1}"
    jobs[job_id] = {"page_id": page_id, "locales": sorted(locales), "status": "queued", "requested_by": actor}
    # The page itself shows which translations are on their way: each requested locale is marked as queued.
    for loc in locales:
        page["translations"][loc] = "queued"
    state.audit(
        "create_translation_job",
        actor,
        page_id=page_id,
        job_id=job_id,
        locales=sorted(locales),
        idempotency_key=idempotency_key,
    )
    return state.remember(
        idempotency_key, {"job_id": job_id, "page_id": page_id, "locales": sorted(locales), "status": "queued"}
    )


def get_translation_status(state, job_id: str) -> dict:
    """A copy of the job with its ``job_id``: the page, the locales, the status and who requested it. Raises
    NotFound for an unknown job id."""
    job = state.data["translation_jobs"].get(job_id)
    if job is None:
        raise NotFound(f"translation job '{job_id}' does not exist")
    return dict(job, job_id=job_id)
