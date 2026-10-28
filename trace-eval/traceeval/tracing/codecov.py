"""Per-test code coverage of the SUT via coverage.py dynamic contexts, reduced to *functions*.

The function level is the unit at which change sets are expressed (``code:<relpath>::<qualname>``),
so observed coverage and diff-derived components can be intersected directly."""

import ast
import os
import tempfile
from pathlib import Path


def function_index(sut_dir: Path) -> dict[str, list[tuple[str, int, int]]]:
    """relpath -> [(qualname, first_line, last_line)] for every function/method in the SUT."""
    index: dict[str, list[tuple[str, int, int]]] = {}
    for path in sorted(Path(sut_dir).rglob("*.py")):
        rel = str(path.relative_to(sut_dir))
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        entries: list[tuple[str, int, int]] = []
        _collect_functions(tree, entries)
        index[rel] = entries
    return index


def _collect_functions(node, entries: list, prefix: str = ""):
    """Append (qualified name, first line, last line) of every function below ``node``."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = f"{prefix}{child.name}"
            entries.append((name, child.lineno, child.end_lineno or child.lineno))
            _collect_functions(child, entries, name + ".")
        elif isinstance(child, ast.ClassDef):
            _collect_functions(child, entries, f"{prefix}{child.name}.")
        else:
            _collect_functions(child, entries, prefix)


def line_to_function(index_entries: list[tuple[str, int, int]], line: int) -> str | None:
    """Innermost function containing ``line`` (entries may nest; pick the smallest span)."""
    best, best_span = None, None
    for name, start, end in index_entries:
        if start <= line <= end:
            span = end - start
            if best_span is None or span < best_span:
                best, best_span = name, span
    return best


class CoverageSession:
    """Collect which SUT functions each test executed (contexts = test ids)."""

    def __init__(self, sut_dir: Path):
        import coverage

        self.sut_dir = Path(sut_dir).resolve()
        self.index = function_index(self.sut_dir)
        fd, self.data_file = tempfile.mkstemp(prefix="traceeval-cov-", suffix=".db")
        os.close(fd)
        self.cov = coverage.Coverage(data_file=self.data_file, source=[str(self.sut_dir)], branch=False)
        self.cov.start()
        self.cov.switch_context("__setup__")

    def begin(self, context: str):
        self.cov.switch_context(context)

    def finish(self) -> dict[str, set[str]]:
        """context -> {'code:<relpath>::<qualname>', 'line:<relpath>:<n>', ...}"""
        self.cov.stop()
        self.cov.save()
        data = self.cov.get_data()
        result: dict[str, set[str]] = {}
        for filename in data.measured_files():
            rel = (
                str(Path(filename).resolve().relative_to(self.sut_dir))
                if str(filename).startswith(str(self.sut_dir))
                else None
            )
            if rel is None or rel not in self.index:
                continue
            entries = self.index[rel]
            for line, contexts in (data.contexts_by_lineno(filename) or {}).items():
                fn = line_to_function(entries, line)
                comp = f"code:{rel}::{fn}" if fn else f"code:{rel}"
                for ctx in contexts:
                    if not ctx or ctx == "__setup__":
                        continue
                    bucket = result.setdefault(ctx, set())
                    bucket.add(comp)
                    bucket.add(f"line:{rel}:{line}")
        try:
            os.remove(self.data_file)
        except OSError:
            pass
        return result
