"""SEO report over page metadata."""

from .repository import get_page


def get_seo_report(state, page_id: str, max_title_length: int = 60, require_description: bool = True) -> dict:
    """Score the SEO metadata of a page from 0 to 100 and list what is wrong with it.

    Three things are checked: the title is at most ``max_title_length`` characters long, a meta description
    is set (only when ``require_description`` is true) and at least one keyword is set. Returns ``page_id``,
    ``score``, ``issues`` (one ``{"field", "issue", ...}`` entry per problem) and ``title_length``. Raises
    NotFound for an unknown page. The report only reads the page; the tool passes both limits from the
    ``seo`` section of the configuration."""
    page = get_page(state, page_id)
    meta = page.get("metadata", {})
    issues = []
    # Judge the SEO title, falling back to the page title when no SEO title is set (an empty one counts as
    # not set).
    title = meta.get("title") or page.get("title", "")
    # One entry per problem: a title over the limit, a missing description (when one is required), no keywords.
    if len(title) > max_title_length:
        issues.append({"field": "title", "issue": "too_long", "length": len(title)})
    if require_description and not meta.get("description"):
        issues.append({"field": "description", "issue": "missing"})
    if not meta.get("keywords"):
        issues.append({"field": "keywords", "issue": "missing"})
    # Each problem costs 30 points, so a page with all three problems scores 10.
    score = max(0, 100 - 30 * len(issues))
    return {"page_id": page_id, "score": score, "issues": issues, "title_length": len(title)}
