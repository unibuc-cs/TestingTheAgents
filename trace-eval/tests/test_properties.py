"""Tests for drafting the catalog of properties with a model (traceeval/catalog/extract.py), on scripted answers."""

import json
import shutil
from types import SimpleNamespace

import yaml

from traceeval.catalog import CATALOG_ROOT, extract, load_catalog, load_properties

CATALOG_ANSWER = {
    "properties": [
        # an existing id: the person's entry stays, it only gains sources
        {
            "id": "safety_no_broken_publish",
            "category": "safety",
            "description": "x",
            "checked_by": ["state"],
            "sources": ["skill:link-validation#prose", "skill:nonexistent#prose"],
        },
        {
            "id": "plan_order",
            "category": "orchestration",
            "description": "steps run in the planned order",
            "checked_by": ["trace"],
            "sources": ["agent:orchestrator.skills"],
        },
        {"id": "fast", "category": "speed", "description": "not a fixed category", "checked_by": ["trace"]},
        {"id": "brand_ok", "category": "safety", "description": "over the limit", "checked_by": ["state"]},
    ]
}


class ScriptedModel:
    """Answers the catalog request, then every batch of tags; the first batch over-tags PUB-01."""

    model_id = "scripted"

    def __init__(self):
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        self.calls += 1
        if self.calls == 1:
            text = json.dumps(CATALOG_ANSWER)
        elif "PUB-01" in request["messages"][1]["content"]:
            tags = {"PUB-01": ["task_completion", "plan_order", "made_up", "correct_routing"], "NOPE": ["x"]}
            text = "```json\n" + json.dumps({"tags": tags}) + "\n```"
        else:
            text = '{"tags": {}}'
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def test_draft_keeps_limits_lists_and_edits_then_applies(tmp_path):
    root = tmp_path / "catalog"
    shutil.copytree(CATALOG_ROOT, root, ignore=shutil.ignore_patterns("__pycache__"))
    saved = tmp_path / "answers.json"
    limit = len(load_properties(root)) + 1  # room for one new property
    result = extract.draft(root, max_properties=limit, per_test=2, save_response=saved, client=ScriptedModel())
    props = result["properties"]
    # the fixed category list and the limit (the existing ones + room for one new) are enforced by the code
    assert "fast" not in props and "plan_order" in props and "brand_ok" not in props and len(props) == limit
    # the person's entry keeps its wording and threshold, and gains only the known sources
    assert props["safety_no_broken_publish"]["description"].startswith("a page with broken links")
    assert props["safety_no_broken_publish"]["sources"] == ["skill:link-validation#prose"]
    assert props["plan_order"]["threshold"] == 0.95 and props["plan_order"]["mandatory"] is False
    # tags: known properties only, at most per_test, unknown tests left out
    assert result["tags"] == {"PUB-01": ["task_completion", "plan_order"]}
    assert any("NOPE" in n for n in result["notes"]) and "plan_order" in result["report"].read_text()
    # the saved answers give the same draft with no model
    again = extract.draft(root, max_properties=limit, per_test=2, replay=saved)
    assert again["properties"] == props and again["tags"] == result["tags"]
    # apply writes the catalog (keeping its comments) and the tests' properties lines
    extract.apply(root)
    assert (root / "properties.yaml").read_text().startswith("# The catalog of properties")
    assert "plan_order" in {p["id"] for p in yaml.safe_load((root / "properties.yaml").read_text())}
    assert {c.id: c.properties for c in load_catalog(root)}["PUB-01"] == ["task_completion", "plan_order"]
