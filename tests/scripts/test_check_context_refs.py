"""Context-reference checker tests (engineering-standards-alignment spec A2).

The checker is the durable answer to why F1-F4 recurred: a read-through misses
dangling edges, a script does not. These tests build throwaway repo trees so the
checker's behaviour is asserted against fixtures, not against the live repo
(whose reference graph is the thing under repair).
"""
from __future__ import annotations

from pathlib import Path

from scripts.check_context_refs import DEFAULT_ROOTS, find_dangling_refs, main

KINDS = {"link", "workspace", "doc", "skill", "adr"}


def _repo(tmp_path: Path) -> Path:
    """A minimal repo tree: the dirs the checker resolves references against."""
    (tmp_path / "app").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "planning" / "decisions").mkdir(parents=True)
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    return tmp_path


def test_reports_dangling_markdown_link(tmp_path):
    """Tracer bullet: a link whose target is absent on disk is a broken edge."""
    repo = _repo(tmp_path)
    context = repo / "app" / "CONTEXT.md"
    context.write_text(
        "# Backend Context\n"
        "\n"
        "> Authority: [docs/PRD.md](../docs/PRD.md)\n"
    )

    broken = find_dangling_refs([context], repo_root=repo)

    assert len(broken) == 1
    assert broken[0].source == "app/CONTEXT.md"
    assert broken[0].line == 3
    assert broken[0].target == "../docs/PRD.md"


def test_reports_routing_table_skill_that_has_no_skill_directory(tmp_path):
    """F2/F3: the routing table sends agents to skills nothing implements."""
    repo = _repo(tmp_path)
    (repo / ".claude" / "skills" / "tdd").mkdir()
    (repo / "app" / "CONTEXT.md").write_text("# Backend Context\n")
    claude = repo / "CLAUDE.md"
    claude.write_text(
        "## Routing Table\n"
        "| Task               | Go to | Read           | Skills                |\n"
        "|--------------------|-------|----------------|-----------------------|\n"
        "| Write backend code | /app  | app/CONTEXT.md | tdd, prompt-engineering |\n"
    )

    broken = find_dangling_refs([claude], repo_root=repo)

    assert [(b.kind, b.target) for b in broken] == [("skill", "prompt-engineering")]
    assert broken[0].expected == ".claude/skills/prompt-engineering"
    assert broken[0].line == 4


def test_reports_routing_table_workspace_and_read_columns(tmp_path):
    """F1: the `/ops` row names a workspace and a `CONTEXT.md` that were both
    deleted in the v1->v2 teardown, so the whole row dead-ends."""
    repo = _repo(tmp_path)
    claude = repo / "CLAUDE.md"
    claude.write_text(
        "## Routing Table\n"
        "| Task                       | Go to | Read           | Skills |\n"
        "|----------------------------|-------|----------------|--------|\n"
        "| Deploy or run the pipeline | /ops  | ops/CONTEXT.md | -      |\n"
    )

    broken = find_dangling_refs([claude], repo_root=repo)

    assert {(b.kind, b.target) for b in broken} == {
        ("workspace", "/ops"),
        ("doc", "ops/CONTEXT.md"),
    }


def test_reports_workspace_bullet_whose_directory_is_gone(tmp_path):
    """F1 again: `/ops` is named twice — the bullet list needs fixing too."""
    repo = _repo(tmp_path)
    claude = repo / "CLAUDE.md"
    claude.write_text(
        "## Workspaces (code domains)\n"
        "- /app   — Backend pipeline code\n"
        "- /ops   — Deployment, Supabase setup, run execution\n"
    )

    broken = find_dangling_refs([claude], repo_root=repo)

    assert [(b.kind, b.target, b.line) for b in broken] == [("workspace", "/ops", 3)]


def test_reports_adr_citation_with_no_decision_record(tmp_path):
    """F4: `frontend/CONTEXT.md` cites ADR 2026-06-01 as the authority lifting
    the no-router rule, but `planning/decisions/` holds only `.gitkeep`."""
    repo = _repo(tmp_path)
    (repo / "planning" / "decisions" / "2026-05-20-pydantic.md").write_text("# ok\n")
    context = repo / "frontend" / "CONTEXT.md"
    context.write_text(
        "The exception is authorized by **ADR 2026-06-01**, which supersedes\n"
        "the old no-router rule.\n"
    )

    broken = find_dangling_refs([context], repo_root=repo)

    assert [(b.kind, b.target) for b in broken] == [("adr", "ADR 2026-06-01")]
    assert broken[0].expected == "planning/decisions/2026-06-01-*.md"


def test_accepts_an_adr_citation_backed_by_a_decision_record(tmp_path):
    repo = _repo(tmp_path)
    (repo / "planning" / "decisions" / "2026-06-01-adopt-react-router.md").write_text(
        "# ADR\n"
    )
    context = repo / "frontend" / "CONTEXT.md"
    context.write_text("Routing is settled by ADR 2026-06-01.\n")

    assert find_dangling_refs([context], repo_root=repo) == []


def _clean_repo(tmp_path: Path) -> tuple[Path, Path]:
    """A repo whose every reference resolves, plus its `CLAUDE.md`."""
    repo = _repo(tmp_path)
    (repo / ".claude" / "skills" / "tdd").mkdir()
    (repo / "app" / "CONTEXT.md").write_text("# Backend Context\n")
    (repo / "docs" / "PRD.md").write_text("# PRD\n")
    claude = repo / "CLAUDE.md"
    claude.write_text(
        "See [docs/PRD.md](docs/PRD.md) and [the backend](app/CONTEXT.md).\n"
        "\n"
        "## Routing Table\n"
        "| Task               | Go to | Read           | Skills |\n"
        "|--------------------|-------|----------------|--------|\n"
        "| Write backend code | /app  | app/CONTEXT.md | tdd    |\n"
    )
    return repo, claude


def test_clean_tree_has_no_dangling_refs(tmp_path):
    repo, claude = _clean_repo(tmp_path)

    assert find_dangling_refs([claude], repo_root=repo) == []


def test_cli_exits_zero_on_a_clean_tree(tmp_path):
    repo, claude = _clean_repo(tmp_path)

    assert main(["--repo-root", str(repo), str(claude)]) == 0


def test_cli_exits_non_zero_and_names_each_broken_edge(tmp_path, capsys):
    """A finding must be actionable: which file, which line, which target."""
    repo, claude = _clean_repo(tmp_path)
    claude.write_text(
        claude.read_text()
        + "| Write docs | /docs | docs/CONTEXT.md | doc-authoring |\n"
    )

    exit_code = main(["--repo-root", str(repo), str(claude)])

    assert exit_code != 0
    report = capsys.readouterr().out
    assert "CLAUDE.md:7" in report
    assert "doc-authoring" in report
    assert ".claude/skills/doc-authoring" in report


def test_checks_the_real_context_system():
    """The five files A2 names all exist and are walkable.

    Deliberately asserts nothing about *how many* edges dangle: the checker is
    RED on today's tree and goes green when the routing table is repaired, and a
    test that has to be inverted at that point is worse than no test.
    """
    repo = Path(__file__).resolve().parents[2]
    roots = [repo / name for name in DEFAULT_ROOTS]

    assert [root for root in roots if not root.exists()] == []
    assert {ref.kind for ref in find_dangling_refs(roots, repo_root=repo)} <= KINDS
