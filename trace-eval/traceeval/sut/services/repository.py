"""Content repository: pages, versions, assets, search.

Each change is written to the audit log. ``create_page``, ``update_page_content`` and ``upload_asset`` accept
an idempotency key: a retried call with the same key returns the first answer instead of applying the change
a second time. Permissions are not checked here; the skills check them before they act."""

import re

from .errors import NotFound, ValidationError


def _next_id(kind: str, state) -> str:
    """Deterministic identifier allocation derived from the state only (no process-level counters).

    ``kind`` is "page" or "asset". The new id is the first free one counting from 100 (p100, p101, ... or
    a100, a101, ...), so the same state always yields the same id, and created items stay apart from the
    small ids of the initial data."""
    prefix = {"page": "p", "asset": "a"}[kind]
    existing = state.pages if kind == "page" else state.assets
    n = 100
    while f"{prefix}{n}" in existing:
        n += 1
    return f"{prefix}{n}"


def get_page(state, page_id: str) -> dict:
    """The stored record of a page, which the other services use to look a page up before they read or
    change it. The record itself is returned, not a copy, so a change made to it is a change to the page.
    Raises NotFound for an unknown page id."""
    page = state.pages.get(page_id)
    if page is None:
        raise NotFound(f"page '{page_id}' does not exist")
    return page


def search_pages(state, query: str) -> list[dict]:
    """Pages whose title, path or body contain ``query``, ignoring case and surrounding spaces, as short
    summaries (page id, path, title, status) in the order the pages are stored. Drafts are included, and an
    empty query matches every page."""
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
    """Create a new draft page under ``parent_path`` and return its ``page_id`` and ``path``.

    The path is the parent path followed by a slug of the title (lower case, words joined by hyphens, cut to
    40 characters). Neither the parent path nor the uniqueness of the new path is checked. Raises
    ValidationError for an empty title or a template other than "article", "landing" or "product". A retry
    with the same idempotency key returns the first answer and creates nothing."""
    # A retry of a call that already went through gets the first answer back; no second page is created.
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    # A page needs a title that is not blank and one of the site's three templates.
    if not title or len(title.strip()) == 0:
        raise ValidationError("title must not be empty")
    if template not in ("article", "landing", "product"):
        raise ValidationError(f"unknown template '{template}'")
    # The next free page id, and a slug made from the title: "Spring Sale 2026" becomes "spring-sale-2026".
    pid = _next_id("page", state)
    slug = "-".join(title.lower().split())[:40]
    # A new page starts as an empty draft in en-US, with no review and its empty body as version 1. The page
    # gets a published_at once it is published.
    page = {
        "path": f"{parent_path.rstrip('/')}/{slug}",  # where the page lives on the site; links point here
        "title": title,
        "body": "",  # the content; links inside it are written as [[...]]
        "template": template,
        "status": "draft",  # "draft", "scheduled" or "published"
        "metadata": {},  # SEO metadata: title, description, keywords
        "links": [],  # the [[...]] links of the body, extracted again whenever the body is saved
        "assets": [],  # ids of the assets attached to the page
        "locale": "en-US",  # the language the page is written in
        "review": {"status": "none", "reviewer": None},  # "none", "requested" or "approved", and who approved
        "versions": [{"v": 1, "body": ""}],  # every saved body, numbered from 1; the last is the current one
        "translations": {},  # target locale -> translation status, e.g. "queued"
        "scheduled_at": None,  # the planned publication time (ISO-8601) of a scheduled page
        "created_by": actor,
    }
    state.pages[pid] = page
    state.audit("create_page", actor, page_id=pid, idempotency_key=idempotency_key)
    return state.remember(idempotency_key, {"page_id": pid, "path": page["path"]})


def update_page_content(state, page_id: str, body: str, actor: str, idempotency_key: str | None = None) -> dict:
    """Replace the body of a page, saving it as a new version, and return ``page_id``, the new ``version``
    number and the ``links`` found in the new body.

    The edit withdraws the page's review, whether it was approved or only requested, so the new text has to
    be reviewed again. The page's status does not change: a published page stays published. Raises NotFound
    for an unknown page. A retry with the same idempotency key returns the first answer and adds no second
    version."""
    # A retry of an edit that already went through gets the first answer back; no second version is added.
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    page = get_page(state, page_id)
    # The new body becomes the current text with its links extracted again, and is kept as the next version.
    page["body"] = body
    page["links"] = _extract_links(body)
    version = {"v": len(page["versions"]) + 1, "body": body}
    page["versions"].append(version)
    # An approval was given for the old text, so changing the text withdraws it.
    page["review"] = {"status": "none", "reviewer": None}  # edits invalidate approvals
    state.audit("update_page_content", actor, page_id=page_id, version=version["v"], idempotency_key=idempotency_key)
    return state.remember(idempotency_key, {"page_id": page_id, "version": version["v"], "links": list(page["links"])})


# A link in a page body is written between double square brackets, e.g. [[/content/site/home]]; the link
# target itself may not contain square brackets.
_LINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


def _extract_links(body: str) -> list[str]:
    """Links are written as ``[[/internal/path]]``, ``[[https://url]]`` or ``[[asset:a1]]``.

    Returns the link targets in the order they appear in ``body``, without surrounding spaces; a link that
    appears twice is listed twice."""
    return [m.group(1).strip() for m in _LINK_RE.finditer(body)]


def set_page_metadata(
    state, page_id: str, title: str | None, description: str | None, keywords: list[str] | None, actor: str
) -> dict:
    """Set the SEO metadata of a page (SEO title, meta description, keywords) and return ``page_id`` and a
    copy of the resulting ``metadata``.

    Only the fields that are given change: None keeps the current value, while an empty string or list
    clears it. The SEO title is separate from the page's own title. No limits are checked here (the SEO
    report is what flags an over-long title), and the page's review is not affected. Raises NotFound for an
    unknown page."""
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
    """The versions of a page, oldest first, as ``{"v": number, "length": characters in that body}``; the
    bodies themselves are not returned. Raises NotFound for an unknown page."""
    page = get_page(state, page_id)
    return [{"v": v["v"], "length": len(v["body"])} for v in page["versions"]]


def rollback_page(state, page_id: str, version: int, actor: str) -> dict:
    """Restore the body of an earlier version and return ``page_id``, ``restored_from`` (the version that
    was restored) and ``version``, the number of the new version.

    History is never rewritten: the old body is saved again as a new version that records where it came
    from. Unlike an edit, a rollback leaves the page's review as it is. It takes no idempotency key, so a
    retry after a lost acknowledgement adds one more version. Raises NotFound for an unknown page or
    version."""
    page = get_page(state, page_id)
    # Find the requested version; versions are numbered from 1.
    target = next((v for v in page["versions"] if v["v"] == version), None)
    if target is None:
        raise NotFound(f"page '{page_id}' has no version {version}")
    # The old body becomes the current text again, with its links, and is saved as the newest version.
    page["body"] = target["body"]
    page["links"] = _extract_links(target["body"])
    new_v = {"v": len(page["versions"]) + 1, "body": target["body"], "restored_from": version}
    page["versions"].append(new_v)
    state.audit("rollback_page", actor, page_id=page_id, restored_from=version, version=new_v["v"])
    return {"page_id": page_id, "restored_from": version, "version": new_v["v"]}


def upload_asset(state, name: str, folder: str, mime: str, actor: str, idempotency_key: str | None = None) -> dict:
    """Register a new asset (an image, a video or a PDF) in a DAM folder and return its ``asset_id`` and
    ``path`` (the folder followed by the file name).

    Only the asset's description is stored; no file content is involved. Raises ValidationError for any
    other MIME type. A retry with the same idempotency key returns the first answer and registers nothing
    new."""
    cached = state.idempotent(idempotency_key)
    if cached:
        return cached
    # The digital asset library (DAM) holds images, videos and PDFs only.
    if not mime.startswith(("image/", "video/", "application/pdf")):
        raise ValidationError(f"unsupported mime type '{mime}'")
    aid = _next_id("asset", state)
    state.assets[aid] = {"name": name, "folder": folder, "mime": mime, "uploaded_by": actor}
    state.audit("upload_asset", actor, asset_id=aid, idempotency_key=idempotency_key)
    return state.remember(idempotency_key, {"asset_id": aid, "path": f"{folder.rstrip('/')}/{name}"})


def get_asset(state, asset_id: str) -> dict:
    """A copy of the stored asset record (name, folder, MIME type, uploader) with its ``asset_id``. Raises
    NotFound for an unknown asset id."""
    asset = state.assets.get(asset_id)
    if asset is None:
        raise NotFound(f"asset '{asset_id}' does not exist")
    return dict(asset, asset_id=asset_id)


def attach_asset(state, page_id: str, asset_id: str, actor: str) -> dict:
    """Attach an existing asset to a page and return ``page_id`` and the page's ``assets`` list.

    Attaching an asset that is already attached changes nothing, though the call is still audited. Raises
    NotFound for an unknown page or asset."""
    page = get_page(state, page_id)
    # Called only to make sure the asset exists: it raises NotFound otherwise.
    get_asset(state, asset_id)
    # An asset is attached at most once.
    if asset_id not in page["assets"]:
        page["assets"].append(asset_id)
    state.audit("attach_asset", actor, page_id=page_id, asset_id=asset_id)
    return {"page_id": page_id, "assets": list(page["assets"])}
