"""Context-reference checker tests (engineering-standards-alignment spec A2).

The checker is the durable answer to why F1-F4 recurred: a read-through misses
dangling edges, a script does not. These tests build throwaway repo trees so the
checker's behaviour is asserted against fixtures, not against the live repo
(whose reference graph is the thing under repair).
"""
from __future__ import annotations

from pathlib import Path

from scripts.check_context_refs import (
    DEFAULT_ROOTS,
    default_roots,
    find_dangling_refs,
    main,
)

KINDS = {"link", "workspace", "doc", "skill", "adr"}


def _repo(tmp_path: Path) -> Path:
    """A minimal repo tree: the dirs the checker resolves references against."""
    (tmp_path / "app").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "planning" / "decisions").mkdir(parents=True)
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    return tmp_path


def _stage_table(invokes: str) -> str:
    """An ICM workspace stage table with one stage, naming `invokes`."""
    return (
        "## Stages\n"
        "| #  | Stage     | Invokes | Artifact                 | Gate  |\n"
        "|----|-----------|---------|--------------------------|-------|\n"
        f"| 02 | **Spec**  | {invokes} | `planning/specs/<slug>_spec.md` | light |\n"
    )


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


def test_reports_stage_table_skill_that_has_no_skill_directory(tmp_path):
    """#94: an ICM stage table is built out of skills, and its `Invokes` column
    names them in backticks — a renamed skill must break the workspace loudly."""
    repo = _repo(tmp_path)
    (repo / ".claude" / "skills" / "map-architecture").mkdir()
    context = repo / "icm" / "feature-planning" / "CONTEXT.md"
    context.parent.mkdir(parents=True)
    context.write_text(_stage_table("`grill-with-docs` skill"))

    broken = find_dangling_refs([context], repo_root=repo)

    assert [(b.kind, b.target) for b in broken] == [("skill", "grill-with-docs")]
    assert broken[0].expected == ".claude/skills/grill-with-docs"
    assert broken[0].line == 4


def test_accepts_a_stage_table_whose_invoked_skill_exists(tmp_path):
    """The prose a stage hangs off the slug — `tdd` skill (planning only) — is a
    note to the reader, not part of the name."""
    repo = _repo(tmp_path)
    (repo / ".claude" / "skills" / "tdd").mkdir()
    context = repo / "icm" / "feature-planning" / "CONTEXT.md"
    context.parent.mkdir(parents=True)
    context.write_text(_stage_table("`tdd` skill (**Workflow step 1 only**)"))

    assert find_dangling_refs([context], repo_root=repo) == []


def test_stage_table_config_link_is_not_read_as_a_skill(tmp_path):
    """Stage 01 invokes a config file, not a skill. It is one dangling *link*
    when absent — never a bogus `.claude/skills/_config/...` finding too."""
    repo = _repo(tmp_path)
    context = repo / "icm" / "feature-planning" / "CONTEXT.md"
    context.parent.mkdir(parents=True)
    context.write_text(
        _stage_table(
            "[`_config/feature-questions.md`](_config/feature-questions.md)"
        )
    )

    broken = find_dangling_refs([context], repo_root=repo)

    assert [(b.kind, b.target) for b in broken] == [
        ("link", "_config/feature-questions.md")
    ]


def test_default_roots_follow_the_routing_table_into_every_icm_workspace(tmp_path):
    """#94's part 1: the ICM files are found by glob, so a workspace added later
    is guarded by construction rather than by editing this script."""
    repo = _repo(tmp_path)
    for name in DEFAULT_ROOTS:
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text("# root\n")
    (repo / "icm" / "feature-planning" / "_config").mkdir(parents=True)
    (repo / "icm" / "feature-planning" / "CONTEXT.md").write_text("# ws\n")
    (repo / "icm" / "feature-planning" / "_config" / "feature-questions.md").write_text(
        "# questions\n"
    )
    (repo / "icm" / "release-planning").mkdir(parents=True)
    (repo / "icm" / "release-planning" / "CONTEXT.md").write_text("# next ws\n")

    roots = [path.relative_to(repo).as_posix() for path in default_roots(repo)]

    assert set(DEFAULT_ROOTS) <= set(roots)
    assert set(roots) - set(DEFAULT_ROOTS) == {
        "icm/feature-planning/CONTEXT.md",
        "icm/feature-planning/_config/feature-questions.md",
        "icm/release-planning/CONTEXT.md",
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


def test_cli_walks_the_icm_workspaces_when_no_files_are_named(tmp_path, capsys):
    """`make check-refs` passes no files, so the ICM coverage has to come from
    the default roots — the gap #94 was filed about."""
    repo, _ = _clean_repo(tmp_path)
    for name in DEFAULT_ROOTS:
        if not (repo / name).exists():
            (repo / name).write_text("# root\n")
    context = repo / "icm" / "feature-planning" / "CONTEXT.md"
    context.parent.mkdir(parents=True)
    context.write_text(_stage_table("`grill-with-docs` skill"))

    exit_code = main(["--repo-root", str(repo)])

    assert exit_code != 0
    report = capsys.readouterr().out
    assert "icm/feature-planning/CONTEXT.md:4" in report
    assert ".claude/skills/grill-with-docs" in report


def test_checks_the_real_context_system():
    """Every default root — the five A2 names plus the ICM workspaces the
    routing table routes into — exists and is walkable.

    Deliberately asserts nothing about *how many* edges dangle: the checker is
    RED on today's tree and goes green when the routing table is repaired, and a
    test that has to be inverted at that point is worse than no test.
    """
    repo = Path(__file__).resolve().parents[2]
    roots = default_roots(repo)

    assert [root for root in roots if not root.exists()] == []
    assert repo / "icm" / "feature-planning" / "CONTEXT.md" in roots
    assert repo / "icm" / "feature-planning" / "_config" / "feature-questions.md" in roots
    assert {ref.kind for ref in find_dangling_refs(roots, repo_root=repo)} <= KINDS
