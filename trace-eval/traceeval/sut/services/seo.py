"""SEO report over page metadata."""

from .repository import get_page


def get_seo_report(state, page_id: str, max_title_length: int = 60, require_description: bool = True) -> dict:
    page = get_page(state, page_id)
    meta = page.get("metadata", {})
    issues = []
    title = meta.get("title") or page.get("title", "")
    if len(title) > max_title_length:
        issues.append({"field": "title", "issue": "too_long", "length": len(title)})
    if require_description and not meta.get("description"):
        issues.append({"field": "description", "issue": "missing"})
    if not meta.get("keywords"):
        issues.append({"field": "keywords", "issue": "missing"})
    score = max(0, 100 - 30 * len(issues))
    return {"page_id": page_id, "score": score, "issues": issues, "title_length": len(title)}
