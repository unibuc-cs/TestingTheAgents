"""Link validation: internal page links, external URLs and asset references."""

from .repository import get_page


def _internal_exists(state, path: str) -> bool:
    """True when a page of the site lives at exactly ``path``. The page's status is not looked at, so a link
    to a draft page counts as valid."""
    return any(p["path"] == path for p in state.pages.values())


def _external_status(state, url: str) -> str:
    """The known reachability of an external URL: "ok", "broken", or "unknown" for a URL the platform has no
    record of. Nothing is fetched over the network; the answer comes from the state's ``external_links``
    table."""
    table = state.data.get("external_links", {})
    return table.get(url, "unknown")


def broken_links(state, page) -> tuple[int, list[dict]]:
    """(how many references were looked at, the broken ones) for a page record; see ``validate_links``."""
    broken: list[dict] = []
    checked = 0
    # The form of a link says what it points at: an http(s) URL is external, "asset:<id>" names an asset,
    # and anything else is taken as the path of a page on this site.
    for link in page.get("links", []):
        checked += 1
        if link.startswith("http://") or link.startswith("https://"):
            # Only a URL known to be reachable passes: a broken URL and an unknown one are both reported.
            status = _external_status(state, link)
            if status != "ok":
                broken.append({"link": link, "kind": "external", "status": status})
        elif link.startswith("asset:"):
            if link[len("asset:") :] not in state.assets:
                broken.append({"link": link, "kind": "asset", "status": "missing"})
        else:
            if not _internal_exists(state, link):
                broken.append({"link": link, "kind": "internal", "status": "missing"})
    # The assets attached to the page must exist too, whether or not the body links to them.
    for asset_id in page.get("assets", []):
        checked += 1
        if asset_id not in state.assets:
            broken.append({"link": f"asset:{asset_id}", "kind": "asset", "status": "missing"})
    return checked, broken


def validate_links(state, page_id: str) -> dict:
    """Check every link and asset reference of a page and report the broken ones.

    The links checked are the ones recorded for the page, which are taken from its body whenever the body
    is saved; the assets attached to the page are checked as well. Returns ``page_id``, ``checked`` (how
    many references were looked at), ``broken_count`` and ``broken``: one ``{"link", "kind", "status"}``
    entry per problem, where ``kind`` is "external", "asset" or "internal". Raises NotFound for an unknown
    page. The check changes nothing on the page, but it is written to the audit log."""
    page = get_page(state, page_id)
    checked, broken = broken_links(state, page)
    # Record the check, with no actor (the tool does not pass the user), so that it can be seen later that
    # the page was validated and how many problems were found.
    state.audit("validate_links", None, page_id=page_id, broken=len(broken))
    return {"page_id": page_id, "checked": checked, "broken_count": len(broken), "broken": broken}
