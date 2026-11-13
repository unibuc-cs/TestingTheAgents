"""Brand governance: the brand guidelines and the check of a page against them.

The guidelines live in the state under ``brand``: ``forbidden_terms`` (never on the site), ``offer_words``
(the words that make a page an offer), ``offer_disclaimer`` (the sentence every offer must carry) and the
rule that only licensed assets may be used (each asset has a ``license``: "licensed" or "expired")."""

from .repository import get_page


def guidelines(state) -> dict:
    """A copy of the brand guidelines."""
    return dict(state.data["brand"])


def check_page(state, page_id: str) -> dict:
    """Check a page against the brand guidelines and return ``page_id``, ``compliant`` and ``violations``: one
    ``{"rule", "detail"}`` entry per problem.

    Three rules, over the page's title and body: no forbidden term, in any letter case; an offer (a page that
    uses an offer word) carries the offer disclaimer; and every attached asset is licensed. Raises NotFound for
    an unknown page. The check only reads."""
    page = get_page(state, page_id)
    rules = state.data["brand"]
    text = f"{page['title']} {page['body']}".lower()
    violations = []
    for term in rules["forbidden_terms"]:
        if term.lower() in text:
            violations.append({"rule": "forbidden_term", "detail": f"uses the forbidden term '{term}'"})
    disclaimer = rules["offer_disclaimer"]
    if any(w in text for w in rules["offer_words"]) and disclaimer.lower() not in text:
        violations.append({"rule": "offer_disclaimer", "detail": f"is an offer without the disclaimer '{disclaimer}'"})
    for asset_id in page.get("assets", []):
        license_ = state.assets.get(asset_id, {}).get("license", "licensed")
        if license_ != "licensed":
            violations.append(
                {"rule": "asset_license", "detail": f"uses asset {asset_id}, whose licence is {license_}"}
            )
    return {"page_id": page_id, "compliant": not violations, "violations": violations}
