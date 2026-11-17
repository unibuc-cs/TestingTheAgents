"""The manifest of a recording: what it was made from and with (``history/manifest.json``).

A recording (``runs/<name>``) fits one version of the app and of the tests, and nothing in its files says which:
- its answers are found again by the exact request, which every prompt, skill, tool schema and fixture enters;
- its code dependencies are line numbers of the app as it was;
- the tests' requests, checks and declared blocks are read from the catalog of today.

``traceeval baseline`` writes the manifest, ``traceeval mutants`` adds how the changed copies were run, and
``drift`` compares it with the files of today. ``traceeval check`` refuses a recording whose app differs from
today's; the commands that only read a recording say what differs and go on.

    model, judge         who answered, and who judged the cases with a rubric
    servers              per model server: its version and the models it serves, when it says
    commit, dirty        the repository's commit, and whether files differed from it
    app, catalog         digests of the app's files and of the catalog's
    baseline, changes    how each part was run: backend, repetitions, cases in parallel, settings
"""

import hashlib
import json
import os
import platform
import subprocess
import urllib.request
from pathlib import Path

from traceeval.catalog import CATALOG_ROOT
from traceeval.mutation.changeset import TEXT_SUFFIXES
from traceeval.sut import SUT_ROOT


def manifest_path(workdir: Path) -> Path:
    """Where a recording keeps its manifest."""
    return Path(workdir) / "history" / "manifest.json"


def tree_digest(root: Path, suffixes=TEXT_SUFFIXES) -> str:
    """A fingerprint of the text files under ``root``: their relative paths and contents, in a fixed order. Line
    endings are read as one kind, so a checkout on another system has the same digest; any other difference, a
    comment included, changes it (a comment moves the lines below it, and code is matched by line number)."""
    h = hashlib.sha256()
    files = [p for p in Path(root).rglob("*") if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts]
    for path in sorted(files, key=lambda p: p.relative_to(root).as_posix()):
        h.update(path.relative_to(root).as_posix().encode() + b"\0")
        h.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()[:16]


def catalog_digest() -> str:
    """A fingerprint of the catalog: the tests, the datasets, the properties, the workflows and the features."""
    return tree_digest(CATALOG_ROOT, suffixes={".yaml", ".yml"})


def selection_digest() -> str:
    """A fingerprint of the strategies' code (``traceeval/selection``), constants included. A recording of changed
    copies keeps it: a strategy evaluated on those copies with the same digest was not tuned on them."""
    return tree_digest(Path(__file__).resolve().parents[1] / "selection", suffixes={".py"})


def _git(*args: str) -> str | None:
    """The output of one git command in the repository, or None when git or the repository is not there."""
    try:
        out = subprocess.run(["git", *args], cwd=SUT_ROOT, capture_output=True, text=True, timeout=20, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip()


def _servers(backend: str) -> list[dict]:
    """What each model server says about itself: its version and the models it serves, for a vLLM server. Asked
    once, with a short wait; a server that does not answer leaves an empty entry. The addresses are not kept."""
    from traceeval.llm.chat import server_urls

    def ask(address: str):
        """The JSON a server answers at ``address``, or None when it does not answer."""
        try:
            with urllib.request.urlopen(address, timeout=5) as resp:  # noqa: S310 - the user's own server
                return json.load(resp)
        except (OSError, ValueError):
            return None

    out = []
    for url in server_urls(backend):
        base = url.rstrip("/")
        # <server>/version and <server>/v1/models, the two places a vLLM server describes itself
        version, models = ask(base.removesuffix("/v1") + "/version"), ask(base + "/models")
        out.append(
            {
                "version": (version or {}).get("version"),
                # per model served: its name, where its weights come from and the longest prompt it takes
                "models": [
                    {k: m.get(k) for k in ("id", "root", "max_model_len")} for m in (models or {}).get("data", [])
                ],
            }
        )
    return out


def write_manifest(workdir: Path, part: str, **how) -> dict:
    """Write or update a recording's manifest. ``part`` is "baseline" or "changes" and ``how`` says how that part
    was run (backend, repetitions, cases in parallel, settings). The baseline's call starts the manifest anew: it
    fixes the app, the catalog, the commit and the model; the changed copies' call only adds its part."""
    path = manifest_path(workdir)
    manifest = json.loads(path.read_text()) if part != "baseline" and path.exists() else {}
    if part == "baseline":
        from traceeval.llm.chat import model_name

        backend = how["backend"]
        manifest = {
            "model": model_name(backend),
            "judge": os.environ.get("TRACEEVAL_JUDGE") or ("qwen" if backend == "llm" else "gemma"),
            "servers": _servers(backend),
            "commit": _git("rev-parse", "--short", "HEAD"),
            "dirty": bool(_git("status", "--porcelain")),
            # the app as the recording copied it (variants/baseline/sut is the copy itself), and the tests
            "app": tree_digest(SUT_ROOT),
            "catalog": catalog_digest(),
            "python": platform.python_version(),
        }
    manifest[part] = how
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=1, default=str))
    return manifest


def load_manifest(workdir: Path) -> dict:
    """A recording's manifest; empty for a recording made before manifests were written."""
    path = manifest_path(workdir)
    return json.loads(path.read_text()) if path.exists() else {}


def baseline_copy(workdir: Path) -> Path:
    """The recording's own copy of the original app: what its baseline ran, and what its changed copies are
    made from and compared with."""
    return Path(workdir) / "variants" / "baseline" / "sut"


def drift(workdir: Path) -> dict[str, str]:
    """What differs between a recording and the files of today, as {"app" or "catalog": a sentence}; empty when
    nothing does. The app is compared with the recording's own copy of it, so that a recording without a
    manifest is checked too; the catalog only by the manifest's digest."""
    out = {}
    copy = baseline_copy(workdir)
    recorded = tree_digest(copy) if copy.exists() else load_manifest(workdir).get("app")
    if recorded and recorded != tree_digest(SUT_ROOT):
        out["app"] = (
            f"traceeval/sut differs from the app {workdir} was recorded on ({copy}): recorded answers are found "
            "by the exact request and code by line number, so neither fits any more"
        )
    recorded = load_manifest(workdir).get("catalog")
    if recorded and recorded != catalog_digest():
        out["catalog"] = (
            f"the catalog differs from the one {workdir} was recorded with: a test whose request or checks changed "
            "is read as it is today"
        )
    return out
