"""Link validation: internal page links, external URLs and asset references."""

from .repository import get_page


def _internal_exists(state, path: str) -> bool:
    return any(p["path"] == path for p in state.pages.values())


def _external_status(state, url: str) -> str:
    table = state.data.get("external_links", {})
    return table.get(url, "unknown")


def validate_links(state, page_id: str) -> dict:
    page = get_page(state, page_id)
    broken: list[dict] = []
    checked = 0
    for link in page.get("links", []):
        checked += 1
        if link.startswith("http://") or link.startswith("https://"):
            status = _external_status(state, link)
            if status != "ok":
                broken.append({"link": link, "kind": "external", "status": status})
        elif link.startswith("asset:"):
            if link[len("asset:") :] not in state.assets:
                broken.append({"link": link, "kind": "asset", "status": "missing"})
        else:
            if not _internal_exists(state, link):
                broken.append({"link": link, "kind": "internal", "status": "missing"})
    for asset_id in page.get("assets", []):
        checked += 1
        if asset_id not in state.assets:
            broken.append({"link": f"asset:{asset_id}", "kind": "asset", "status": "missing"})
    state.audit("validate_links", None, page_id=page_id, broken=len(broken))
    return {"page_id": page_id, "checked": checked, "broken_count": len(broken), "broken": broken}
