"""Load a (possibly mutated) copy of the SUT package from an arbitrary directory under a unique module
name, so that several variants can coexist in one process and code mutations take effect."""

import importlib
import importlib.util
import itertools
import shutil
import stat
import sys
from pathlib import Path

from traceeval.sut import SUT_ROOT

_COUNTER = itertools.count(1)  # numbers the module names sut_variant_1, sut_variant_2, ...


def copy_sut(dest: Path, source: Path = SUT_ROOT) -> Path:
    """Copy the SUT tree to ``dest`` (replacing what is there), without bytecode caches."""
    dest = Path(dest)
    if dest.exists():
        # The copy keeps the attributes of the source folders, and on Windows a read-only folder (OneDrive
        # marks new ones so) cannot be removed: make everything writable first.
        for p in [dest, *dest.rglob("*")]:
            p.chmod(p.stat().st_mode | stat.S_IWRITE)
        shutil.rmtree(dest)
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


class LoadedSUT:
    """Handle to a loaded SUT module tree: ``name`` is its top-level module name, ``path`` its directory."""

    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = Path(path)

    def sub(self, dotted: str):
        """A submodule of this copy, e.g. ``sub("harness.runtime")``."""
        return importlib.import_module(f"{self.name}.{dotted}")

    @property
    def tools(self) -> dict:
        return self.sub("tools").TOOLS

    def unload(self):
        """Forget this copy's modules, so that a long experiment does not keep every variant in memory."""
        for key in [k for k in sys.modules if k == self.name or k.startswith(self.name + ".")]:
            del sys.modules[key]


def load_sut(path: Path | str) -> LoadedSUT:
    """Import the SUT package at ``path`` under a fresh module name. The SUT uses relative imports only,
    so every module of the copy resolves inside the copy."""
    path = Path(path).resolve()
    name = f"sut_variant_{next(_COUNTER)}"
    spec = importlib.util.spec_from_file_location(name, path / "__init__.py", submodule_search_locations=[str(path)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    # eagerly import the parts the runtime needs (also registers the tools)
    importlib.import_module(f"{name}.tools")
    importlib.import_module(f"{name}.harness.runtime")
    importlib.import_module(f"{name}.harness.backends.llm_openai")
    return LoadedSUT(name, path)
