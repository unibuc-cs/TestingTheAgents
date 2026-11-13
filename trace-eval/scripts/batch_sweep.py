"""The batch-size sweep: twenty batches of catalog changes drawn at random, recorded, replayed and checked live.

The batches are drawn with ``random.Random(0)`` from the changes whose edits name their file (the change with a
custom edit and the two comment-only changes are left out): three of each size from 2 to 7 and two of 8, the
members of a batch editing pairwise disjoint files so that their edits compose, four of the batches of a size the
harmless changes can fill drawn from those only. They are not in the catalog, so the experiment never records
them by itself; the results are in ``docs/results/gemma7/batch_sweep.md``.

    python scripts/batch_sweep.py list                                  # the batches and their members
    python scripts/batch_sweep.py record runs/gemma7_sweep [reps] [workers]   # into a copy of runs/gemma7
    traceeval evaluate --workdir runs/gemma7_sweep && traceeval report --workdir runs/gemma7_sweep
    python scripts/batch_sweep.py check runs/gemma7 batch_sweep_2_1 [budget]  # live, like `traceeval check`
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

from traceeval.mutation.catalog import BATCHES, MUTATIONS, Mutation, batch

EXCLUDED = {"benign_code_comment_docstring", "benign_config_comments_reordered"}
SIZES = [2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8]


def _files(m: Mutation) -> set[str]:
    return {e[1] for e in m.edits}


def _draw(rng: random.Random, pool: list[Mutation], size: int) -> list[Mutation] | None:
    """Members in drawing order with pairwise disjoint files; None when the shuffled pool cannot fill the size."""
    order = pool[:]
    rng.shuffle(order)
    chosen: list[Mutation] = []
    used: set[str] = set()
    for m in order:
        if _files(m) & used:
            continue
        chosen.append(m)
        used |= _files(m)
        if len(chosen) == size:
            return chosen
    return None


def draw_sweep() -> list[Mutation]:
    """The twenty batches, the same every time."""
    rng = random.Random(0)
    pool = [m for m in MUTATIONS if m.id not in EXCLUDED and not any(e[0] == "custom" for e in m.edits)]
    benign = [m for m in pool if not m.expected_regression]
    benign_only = set(rng.sample([i for i, s in enumerate(SIZES) if s <= len(benign)], 4))
    seen: set[frozenset[str]] = set()
    out: list[Mutation] = []
    count: dict[int, int] = {}
    for i, size in enumerate(SIZES):
        source = benign if i in benign_only else pool
        while True:
            members = _draw(rng, source, size)
            if members is None:
                continue
            key = frozenset(m.id for m in members)
            if key not in seen:
                seen.add(key)
                break
        count[size] = count.get(size, 0) + 1
        description = f"Batch-size sweep: {size} catalog changes drawn at random" + (
            ", harmless ones only." if i in benign_only else "."
        )
        out.append(batch(f"batch_sweep_{size}_{count[size]}", description, [m.id for m in members]))
    return out


SWEEP = draw_sweep()


def record(workdir: Path, reps: int, workers: int) -> None:
    """Record every batch into <workdir>/history/variants/, as the experiment records the catalog's changes."""
    from traceeval.catalog import load_catalog
    from traceeval.experiment.executor import write_jsonl
    from traceeval.experiment.runner import run_suite
    from traceeval.experiment.sutloader import load_sut
    from traceeval.mutation import materialize_variant

    cases = load_catalog()
    for m in SWEEP:
        out = workdir / "history" / "variants" / f"{m.id}.jsonl"
        if out.exists():
            print(f"[{m.id}] already recorded, skipped", file=sys.stderr, flush=True)
            continue
        started = time.time()
        sut_dir, _ = materialize_variant(m, workdir / "variants")
        sut = load_sut(sut_dir)
        try:
            records = run_suite(
                sut,
                cases,
                reps=reps,
                variant=m.id,
                backend="vllm",
                config_overrides=None,
                with_coverage=False,
                workers=workers,
            )
        finally:
            sut.unload()
        write_jsonl(out, records)
        failing = sorted({r["test_id"] for r in records if not r["passed"]})
        print(
            f"[{m.id}] {len(records)} runs, {len(failing)} failing tests, {time.time() - started:.0f} s",
            file=sys.stderr,
            flush=True,
        )


def main(argv: list[str]) -> None:
    if not argv or argv[0] == "list":
        regressions = {m.id: m.expected_regression for m in MUTATIONS}
        for b in SWEEP:
            print(
                f"{b.id:16s} {len(b.members)} members, {sum(regressions[x] for x in b.members)} regressions: "
                f"{', '.join(b.members)}"
            )
    elif argv[0] == "record":
        record(Path(argv[1]), int(argv[2]) if len(argv) > 2 else 5, int(argv[3]) if len(argv) > 3 else 32)
    elif argv[0] == "check":
        from traceeval.experiment.check import check

        BATCHES.extend(SWEEP)  # so that the check finds the batch by id, as it finds the catalog's
        check(argv[2], Path(argv[1]), float(argv[3]) if len(argv) > 3 else 0.2, "vllm")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
