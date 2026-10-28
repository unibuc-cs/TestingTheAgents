"""Materialise mutated SUT variants and their change sets."""

import json
from pathlib import Path

from traceeval.experiment.sutloader import copy_sut
from traceeval.sut import SUT_ROOT

from .catalog import Mutation
from .changeset import ChangeSet, compute_changeset


def materialize_variant(mutation: Mutation | None, workdir: Path, baseline: Path = SUT_ROOT) -> tuple[Path, ChangeSet]:
    """Copy the baseline SUT into ``workdir/<id>/sut``, apply the mutation, compute and persist the change set."""
    name = mutation.id if mutation else "baseline"
    vdir = Path(workdir) / name
    sut_dir = copy_sut(vdir / "sut", baseline)
    if mutation is not None:
        mutation.apply(sut_dir)
    cs = compute_changeset(baseline, sut_dir, name=name)
    (vdir / "changeset.json").write_text(json.dumps(cs.to_dict(), indent=1))
    (vdir / "diff.patch").write_text(cs.diff)
    meta = {
        "id": name,
        "category": mutation.category if mutation else "baseline",
        "description": mutation.description if mutation else "unmodified system",
        "expected_regression": mutation.expected_regression if mutation else False,
    }
    (vdir / "mutation.json").write_text(json.dumps(meta, indent=1))
    return sut_dir, cs
