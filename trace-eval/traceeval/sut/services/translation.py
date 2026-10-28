"""Translation jobs."""

from .errors import NotFound, ValidationError
from .repository import get_page

SUPPORTED_LOCALES = {"de-DE", "fr-FR", "es-ES", "it-IT", "ja-JP", "ro-RO"}


def create_translation_job(
    state, page_id: str, locales: list[str], actor: str, idempotency_key: str | None = None
) -> dict:
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    page = get_page(state, page_id)
    if not locales:
        raise ValidationError("at least one target locale is required")
    bad = [loc for loc in locales if loc not in SUPPORTED_LOCALES]
    if bad:
        raise ValidationError(f"unsupported locales: {bad}")
    jobs = state.data["translation_jobs"]
    job_id = f"tj-{len(jobs) + 1}"
    jobs[job_id] = {"page_id": page_id, "locales": sorted(locales), "status": "queued", "requested_by": actor}
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
    job = state.data["translation_jobs"].get(job_id)
    if job is None:
        raise NotFound(f"translation job '{job_id}' does not exist")
    return dict(job, job_id=job_id)
