"""Textual patch operators used by the mutation catalog. Every operator asserts that the anchor text
exists so that a mutation can never silently become a no-op after the SUT evolves."""

from pathlib import Path


class PatchError(RuntimeError):
    pass


def replace(sut_dir: Path, rel: str, old: str, new: str):
    """Replace ``old``, which must occur exactly once."""
    path = Path(sut_dir) / rel
    text = path.read_text()
    n = text.count(old)
    if n == 0:
        raise PatchError(f"anchor not found in {rel}: {old!r}")
    if n != 1:
        raise PatchError(f"anchor found {n} times in {rel} (expected 1): {old!r}")
    path.write_text(text.replace(old, new, 1))


def delete_line(sut_dir: Path, rel: str, containing: str):
    """Delete the single line containing ``containing``."""
    path = Path(sut_dir) / rel
    lines = path.read_text().splitlines(keepends=True)
    hits = [i for i, line in enumerate(lines) if containing in line]
    if len(hits) != 1:
        raise PatchError(f"expected exactly one line containing {containing!r} in {rel}, found {len(hits)}")
    del lines[hits[0]]
    path.write_text("".join(lines))


def delete_block(sut_dir: Path, rel: str, start_containing: str, until_containing: str):
    """Delete from the line containing ``start_containing`` up to (not including) the next line
    containing ``until_containing``."""
    path = Path(sut_dir) / rel
    lines = path.read_text().splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if start_containing in line]
    if len(starts) != 1:
        raise PatchError(f"expected one start anchor {start_containing!r} in {rel}, found {len(starts)}")
    i = starts[0]
    j = i + 1
    while j < len(lines) and until_containing not in lines[j]:
        j += 1
    del lines[i:j]
    path.write_text("".join(lines))


def append(sut_dir: Path, rel: str, new_text: str):
    path = Path(sut_dir) / rel
    path.write_text(path.read_text() + new_text)


def replace_lines(sut_dir: Path, rel: str, first: int, old: str, new: str):
    """Replace the whole lines that start at line ``first`` (counted from 1), which must read ``old``, by ``new``
    (whole lines too; empty deletes them). For an edit whose text occurs more than once in the file, as the
    generated changes' do (``generator.py``): the line number says which occurrence, and the text is the anchor."""
    path = Path(sut_dir) / rel
    lines = path.read_text().splitlines(keepends=True)
    n = len(old.splitlines())
    found = "".join(lines[first - 1 : first - 1 + n])
    if found != old:
        raise PatchError(f"line {first} of {rel} does not read {old!r} but {found!r}")
    lines[first - 1 : first - 1 + n] = [new] if new else []
    path.write_text("".join(lines))
