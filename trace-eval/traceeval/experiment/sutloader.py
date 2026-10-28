"""Load a (possibly mutated) copy of the SUT package from an arbitrary directory under a unique module
name, so that several variants can coexist in one process and code mutations take effect."""

import importlib
import importlib.util
import shutil
import sys
from pathlib import Path

from traceeval.sut import SUT_ROOT

_COUNTER = [0]


def copy_sut(dest: Path, source: Path = SUT_ROOT) -> Path:
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


class LoadedSUT:
    """Handle to a loaded SUT module tree (``module`` is the package object)."""

    def __init__(self, module, name: str, path: Path):
        self.module = module
        self.name = name
        self.path = Path(path)

    def sub(self, dotted: str):
        return importlib.import_module(f"{self.name}.{dotted}")

    @property
    def tools(self) -> dict:
        return self.sub("tools").TOOLS

    def unload(self):
        for key in [k for k in sys.modules if k == self.name or k.startswith(self.name + ".")]:
            del sys.modules[key]


def load_sut(path: Path | str, name: str | None = None) -> LoadedSUT:
    path = Path(path).resolve()
    if name is None:
        _COUNTER[0] += 1
        name = f"sut_variant_{_COUNTER[0]}"
    spec = importlib.util.spec_from_file_location(name, path / "__init__.py", submodule_search_locations=[str(path)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    # eagerly import the parts the runtime needs (also registers the tools)
    importlib.import_module(f"{name}.tools")
    importlib.import_module(f"{name}.harness.runtime")
    importlib.import_module(f"{name}.harness.backends.simulated")
    return LoadedSUT(module, name, path)
