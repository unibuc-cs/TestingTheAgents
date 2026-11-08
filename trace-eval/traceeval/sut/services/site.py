"""Site analytics and the site audit: how pages perform, and what is wrong with them.

The analytics live in the state under ``analytics``: page id -> ``views``, ``bounce_rate``, ``conversions`` and
``load_ms`` (how long the page takes to load), as a web-analytics product would report them for the pages that
are live."""

from .links import validate_links
from .repository import get_page


def _metrics(state, page_id: str) -> dict:
    page = get_page(state, page_id)
    numbers = state.data.get("analytics", {}).get(page_id, {})
    return {"page_id": page_id, "path": page["path"], **numbers}


def page_metrics(state, page_id: str = "", section: str = "", top_n: int = 3, order: str = "worst") -> dict:
    """The analytics of one page, or a ranking of the live pages of a section by views.

    With ``page_id``, returns that page's numbers under ``pages`` (one entry). Otherwise returns the ``top_n``
    published pages whose path lies under ``section`` (the section page itself excluded), ranked by views:
    fewest first for ``order`` "worst", most first for "best". Raises NotFound for an unknown page."""
    if page_id:
        return {"pages": [_metrics(state, page_id)], "ranked_by": "views"}
    prefix = section.rstrip("/") + "/"
    live = [pid for pid, p in state.pages.items() if p["status"] == "published" and p["path"].startswith(prefix)]
    views = state.data.get("analytics", {})
    live.sort(key=lambda pid: (views.get(pid, {}).get("views", 0), pid), reverse=(order == "best"))
    return {"pages": [_metrics(state, pid) for pid in live[: max(0, int(top_n))]], "ranked_by": "views"}


def audit_site(state, section: str, max_load_ms: int) -> dict:
    """Audit the live pages under ``section``: per page, its broken links (the link check of ``links``),
    attached assets without alt text, a missing meta description, and a load time over ``max_load_ms``.

    Returns ``section``, ``issue_count`` and ``pages``: one ``{"page_id", "path", "issues"}`` entry per page
    with at least one issue, in page order. Each link check is written to the audit log, as when the link
    tool runs."""
    prefix = section.rstrip("/") + "/"
    pages, total = [], 0
    for pid, page in state.pages.items():
        if page["status"] != "published" or not page["path"].startswith(prefix):
            continue
        issues = [f"broken link {b['link']}" for b in validate_links(state, pid)["broken"]]
        issues += [
            f"asset {a} has no alt text" for a in page.get("assets", []) if not state.assets.get(a, {}).get("alt")
        ]
        if not page.get("metadata", {}).get("description"):
            issues.append("no meta description")
        load_ms = state.data.get("analytics", {}).get(pid, {}).get("load_ms", 0)
        if load_ms > max_load_ms:
            issues.append(f"slow: loads in {load_ms} ms")
        if issues:
            pages.append({"page_id": pid, "path": page["path"], "issues": issues})
            total += len(issues)
    return {"section": section, "issue_count": total, "pages": pages}
