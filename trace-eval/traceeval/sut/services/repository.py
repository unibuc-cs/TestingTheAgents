"""Content repository: pages, versions, assets, search."""

import re

from .errors import NotFound, ValidationError


def _next_id(kind: str, state) -> str:
    """Deterministic identifier allocation derived from the state only (no process-level counters)."""
    prefix = {"page": "p", "asset": "a"}[kind]
    existing = state.pages if kind == "page" else state.assets
    n = 100
    while f"{prefix}{n}" in existing:
        n += 1
    return f"{prefix}{n}"


def get_page(state, page_id: str) -> dict:
    page = state.pages.get(page_id)
    if page is None:
        raise NotFound(f"page '{page_id}' does not exist")
    return page


def search_pages(state, query: str) -> list[dict]:
    q = query.lower().strip()
    hits = []
    for pid, page in state.pages.items():
        hay = " ".join([page.get("title", ""), page.get("path", ""), page.get("body", "")]).lower()
        if q in hay:
            hits.append({"page_id": pid, "path": page["path"], "title": page["title"], "status": page["status"]})
    return hits


def create_page(
    state, parent_path: str, title: str, template: str, actor: str, idempotency_key: str | None = None
) -> dict:
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    if not title or len(title.strip()) == 0:
        raise ValidationError("title must not be empty")
    if template not in ("article", "landing", "product"):
        raise ValidationError(f"unknown template '{template}'")
    pid = _next_id("page", state)
    slug = "-".join(title.lower().split())[:40]
    page = {
        "path": f"{parent_path.rstrip('/')}/{slug}",
        "title": title,
        "body": "",
        "template": template,
        "status": "draft",
        "metadata": {},
        "links": [],
        "assets": [],
        "locale": "en-US",
        "review": {"status": "none", "reviewer": None},
        "versions": [{"v": 1, "body": ""}],
        "translations": {},
        "scheduled_at": None,
        "created_by": actor,
    }
    state.pages[pid] = page
    state.audit("create_page", actor, page_id=pid, idempotency_key=idempotency_key)
    return state.remember(idempotency_key, {"page_id": pid, "path": page["path"]})


def update_page_content(state, page_id: str, body: str, actor: str, idempotency_key: str | None = None) -> dict:
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    page = get_page(state, page_id)
    page["body"] = body
    page["links"] = _extract_links(body)
    version = {"v": len(page["versions"]) + 1, "body": body}
    page["versions"].append(version)
    page["review"] = {"status": "none", "reviewer": None}  # edits invalidate approvals
    state.audit("update_page_content", actor, page_id=page_id, version=version["v"], idempotency_key=idempotency_key)
    return state.remember(idempotency_key, {"page_id": page_id, "version": version["v"], "links": list(page["links"])})


_LINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


def _extract_links(body: str) -> list[str]:
    """Links are written as ``[[/internal/path]]``, ``[[https://url]]`` or ``[[asset:a1]]``."""
    return [m.group(1).strip() for m in _LINK_RE.finditer(body)]


def set_page_metadata(
    state, page_id: str, title: str | None, description: str | None, keywords: list[str] | None, actor: str
) -> dict:
    page = get_page(state, page_id)
    meta = page.setdefault("metadata", {})
    if title is not None:
        meta["title"] = title
    if description is not None:
        meta["description"] = description
    if keywords is not None:
        meta["keywords"] = list(keywords)
    state.audit("set_page_metadata", actor, page_id=page_id)
    return {"page_id": page_id, "metadata": dict(meta)}


def list_versions(state, page_id: str) -> list[dict]:
    page = get_page(state, page_id)
    return [{"v": v["v"], "length": len(v["body"])} for v in page["versions"]]


def rollback_page(state, page_id: str, version: int, actor: str) -> dict:
    page = get_page(state, page_id)
    target = next((v for v in page["versions"] if v["v"] == version), None)
    if target is None:
        raise NotFound(f"page '{page_id}' has no version {version}")
    page["body"] = target["body"]
    page["links"] = _extract_links(target["body"])
    new_v = {"v": len(page["versions"]) + 1, "body": target["body"], "restored_from": version}
    page["versions"].append(new_v)
    state.audit("rollback_page", actor, page_id=page_id, restored_from=version, version=new_v["v"])
    return {"page_id": page_id, "restored_from": version, "version": new_v["v"]}


def upload_asset(state, name: str, folder: str, mime: str, actor: str, idempotency_key: str | None = None) -> dict:
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    if not mime.startswith(("image/", "video/", "application/pdf")):
        raise ValidationError(f"unsupported mime type '{mime}'")
    aid = _next_id("asset", state)
    state.assets[aid] = {"name": name, "folder": folder, "mime": mime, "uploaded_by": actor}
    state.audit("upload_asset", actor, asset_id=aid, idempotency_key=idempotency_key)
    return state.remember(idempotency_key, {"asset_id": aid, "path": f"{folder.rstrip('/')}/{name}"})


def get_asset(state, asset_id: str) -> dict:
    asset = state.assets.get(asset_id)
    if asset is None:
        raise NotFound(f"asset '{asset_id}' does not exist")
    return dict(asset, asset_id=asset_id)


def attach_asset(state, page_id: str, asset_id: str, actor: str) -> dict:
    page = get_page(state, page_id)
    get_asset(state, asset_id)
    if asset_id not in page["assets"]:
        page["assets"].append(asset_id)
    state.audit("attach_asset", actor, page_id=page_id, asset_id=asset_id)
    return {"page_id": page_id, "assets": list(page["assets"])}
