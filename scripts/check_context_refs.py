"""Verify every reference in the context system resolves on disk.

Acceptance criterion A2 of `planning/specs/engineering-standards-alignment_spec.md`:
root `CLAUDE.md` and the four domain `CONTEXT.md` files route agents by pointing
at paths, skills and documents. When one of those targets is absent the route
dead-ends (audit findings F1-F4). A human read-through missed them twice; this
script does not.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent

# The context system A2 covers: the root router plus the four domain contexts.
DEFAULT_ROOTS = (
    "CLAUDE.md",
    "app/CONTEXT.md",
    "frontend/CONTEXT.md",
    "planning/CONTEXT.md",
    "docs/CONTEXT.md",
)

MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
TABLE_SEPARATOR = re.compile(r"^\|[\s:|-]+\|$")
SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
WORKSPACE_PATH = re.compile(r"^/[\w.-]+(?:/[\w.-]+)*$")
DOC_PATH = re.compile(r"^[\w.-]+(?:/[\w.-]+)*\.md$")
WORKSPACE_BULLET = re.compile(r"^\s*[-*]\s+`?(/[\w.-]+(?:/[\w.-]+)*)`?(?:\s|$)")
ADR_CITATION = re.compile(r"\bADR\s+\**(\d{4}-\d{2}-\d{2})")

SKILLS_DIR = ".claude/skills"
DECISIONS_DIR = "planning/decisions"

# Link targets that name something other than a file in this repo.
EXTERNAL_SCHEMES = ("http://", "https://", "mailto:")


@dataclass(frozen=True)
class _Ref:
    """A reference from the context system to a target that must exist on disk.

    The extractors build one before checking; `find_dangling_refs` keeps the ones
    that do not resolve, stamping each with the `source` file it sits in and the
    `expected` target that is missing. A dangling reference is just a `_Ref` with
    those two fields set — there is no separate broken-reference type.
    """

    line: int  # 1-indexed line the reference sits on
    kind: str  # what sort of edge it is (link, workspace, doc, skill, adr)
    target: str  # the reference exactly as written
    path: Path
    # Repo-relative glob, for targets whose exact filename is the author's choice
    # (an ADR is dated, but the slug after the date is free text).
    glob: str | None = None
    # Filled in only for dangling refs, by find_dangling_refs (see class docstring).
    source: str = ""  # repo-relative file holding the reference
    expected: str = ""  # repo-relative path (or glob) that did not resolve

    def resolves(self, repo_root: Path) -> bool:
        if self.glob is not None:
            return any(repo_root.glob(self.glob))
        return self.path.exists()

    def _expected_target(self, repo_root: Path) -> str:
        """Repo-relative target that must exist for this reference to resolve."""
        if self.glob is not None:
            return self.glob
        return _relative(self.path, repo_root)


def find_dangling_refs(
    roots: Iterable[Path], repo_root: Path
) -> list[_Ref]:
    """Return every reference in `roots` that does not resolve under `repo_root`.

    Each returned `_Ref` is stamped with its `source` file and the `expected`
    target that is missing, so it is a self-describing worklist row for the report.
    """
    repo_root = repo_root.resolve()
    broken: list[_Ref] = []
    for root in roots:
        source = _relative(root.resolve(), repo_root)
        for ref in _extract_refs(root, repo_root):
            if ref.resolves(repo_root):
                continue
            broken.append(
                replace(ref, source=source, expected=ref._expected_target(repo_root))
            )
    return broken


def _extract_refs(root: Path, repo_root: Path) -> list[_Ref]:
    """Every reference `root` makes, paired with the path it must resolve to."""
    lines = root.read_text().splitlines()
    refs = _dedupe(
        _link_refs(lines, root.parent)
        + _table_refs(lines, repo_root)
        + _bullet_refs(lines, repo_root)
        + _adr_refs(lines, repo_root)
    )
    # Report in reading order, not extractor order — the report is a worklist.
    return sorted(refs, key=lambda ref: ref.line)


def _dedupe(refs: list[_Ref]) -> list[_Ref]:
    """Drop repeat references to the same target on the same line.

    A routing-table cell written as a markdown link is extracted twice — once as
    a link, once as a column — and one broken edge should be reported once.
    """
    seen: set[tuple[int, Path, str | None]] = set()
    unique: list[_Ref] = []
    for ref in refs:
        key = (ref.line, ref.path, ref.glob)
        if key not in seen:
            seen.add(key)
            unique.append(ref)
    return unique


def _adr_refs(lines: list[str], repo_root: Path) -> list[_Ref]:
    """Prose ADR citations — `ADR 2026-06-01` must have a decision record.

    F4's dead edge is a citation in running text, not a link: the rule the spec
    most needs (§5.6) is that citing a document that does not exist is a defect.
    """
    refs: list[_Ref] = []
    for lineno, line in enumerate(lines, start=1):
        for date in ADR_CITATION.findall(line):
            refs.append(
                _Ref(
                    lineno,
                    "adr",
                    f"ADR {date}",
                    repo_root / DECISIONS_DIR,
                    glob=f"{DECISIONS_DIR}/{date}-*.md",
                )
            )
    return refs


def _link_refs(lines: list[str], base: Path) -> list[_Ref]:
    """Markdown links, resolved relative to the file that holds them."""
    refs: list[_Ref] = []
    for lineno, line in enumerate(lines, start=1):
        for target in MARKDOWN_LINK.findall(line):
            if target.startswith(EXTERNAL_SCHEMES) or target.startswith("#"):
                continue
            refs.append(
                _Ref(lineno, "link", target, (base / target).resolve())
            )
    return refs


def _bullet_refs(lines: list[str], repo_root: Path) -> list[_Ref]:
    """Workspace bullets — `- /app — Backend pipeline code` in the root router."""
    refs: list[_Ref] = []
    for lineno, line in enumerate(lines, start=1):
        match = WORKSPACE_BULLET.match(line)
        if match:
            workspace = match.group(1)
            refs.append(
                _Ref(
                    lineno,
                    "workspace",
                    workspace,
                    repo_root / workspace.lstrip("/"),
                )
            )
    return refs


def _table_refs(lines: list[str], repo_root: Path) -> list[_Ref]:
    """Routing-table cells: the workspace, the context doc, and the skills.

    A routing row is only as good as its three targets, so all three columns are
    checked — F1's dead `/ops` row is a workspace and a `CONTEXT.md`, not a link.
    """
    refs: list[_Ref] = []
    header: list[str] | None = None
    columns: dict[str, int] = {}
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            header, columns = None, {}
            continue
        if TABLE_SEPARATOR.match(stripped):
            if header is not None:
                columns = _routing_columns(header)
            continue
        cells = _cells(stripped)
        if header is None:
            header = cells
            continue
        refs.extend(_row_refs(cells, columns, lineno, repo_root))
    return refs


def _row_refs(
    cells: list[str], columns: dict[str, int], lineno: int, repo_root: Path
) -> list[_Ref]:
    """The references one routing-table row makes."""
    refs: list[_Ref] = []
    workspace = _cell(cells, columns.get("go to"))
    if workspace and WORKSPACE_PATH.match(workspace):
        refs.append(
            _Ref(lineno, "workspace", workspace, repo_root / workspace.lstrip("/"))
        )
    doc = _cell(cells, columns.get("read"))
    if doc and DOC_PATH.match(doc):
        refs.append(_Ref(lineno, "doc", doc, repo_root / doc))
    for name in _skill_names(_cell(cells, columns.get("skills"))):
        refs.append(_Ref(lineno, "skill", name, repo_root / SKILLS_DIR / name))
    return refs


def _routing_columns(header: list[str]) -> dict[str, int]:
    wanted = ("go to", "read", "skills")
    found = {}
    for index, cell in enumerate(header):
        name = cell.strip().lower()
        if name in wanted:
            found[name] = index
    return found


def _cell(cells: list[str], index: int | None) -> str:
    """The cell at `index`, stripped of markdown emphasis; empty when absent."""
    if index is None or index >= len(cells):
        return ""
    return cells[index].strip().strip("`*")


def _cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _skill_names(cell: str) -> list[str]:
    """Skill slugs in a `Skills` cell, ignoring prose notes and em-dashes."""
    names = []
    for chunk in cell.split(","):
        name = chunk.strip().strip("`*")
        if SKILL_NAME.match(name):
            names.append(name)
    return names


def _relative(path: Path, repo_root: Path) -> str:
    """Repo-relative form of `path`, falling back to absolute if outside the repo."""
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return str(path)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: exit 0 when every reference resolves."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="markdown files to check (default: the context system)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="root the references resolve against (default: this repo)",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    roots = args.files or [repo_root / name for name in DEFAULT_ROOTS]
    broken = find_dangling_refs(roots, repo_root=repo_root)
    print(_report(broken, checked=len(roots)))
    return 1 if broken else 0


def _report(broken: Sequence[_Ref], checked: int) -> str:
    """One block per broken edge — file, line, kind, and the path that is missing."""
    if not broken:
        return f"check-refs: {checked} file(s) checked, every reference resolves."

    lines = [f"check-refs: {len(broken)} dangling reference(s):", ""]
    for ref in broken:
        lines.append(f"  {ref.source}:{ref.line}  [{ref.kind}] {ref.target}")
        lines.append(f"      -> {ref.expected} (missing)")
    lines.append("")
    lines.append(
        "Every path, skill, and document referenced by CLAUDE.md and the domain "
        "CONTEXT.md files must resolve on disk (engineering-standards-alignment "
        "spec A2). Fix the reference or create the target."
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
