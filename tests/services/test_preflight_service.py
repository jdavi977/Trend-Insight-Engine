"""Orchestration tests for `app.services.preflight_service` (spec §7)."""
from __future__ import annotations

from app.llm.preflight import GenerateQueriesResult
from app.schemas.runs import PreflightResult
from app.services import preflight_service


def _stub_pipeline(mocker, queries, apps_by_query, videos_by_query, ranked):
    # generate_queries now returns a validated GenerateQueriesResult (§7.1); the
    # stub validates the dict so the test exercises the same attribute contract.
    mocker.patch.object(
        preflight_service, "generate_queries",
        return_value=GenerateQueriesResult.model_validate(queries),
    )
    mocker.patch.object(
        preflight_service, "itunes_search",
        side_effect=lambda q: list(apps_by_query.get(q, [])),
    )
    mocker.patch.object(
        preflight_service, "search_videos",
        side_effect=lambda q: list(videos_by_query.get(q, [])),
    )
    mocker.patch.object(
        preflight_service, "rank_candidates", return_value=ranked,
    )


def test_run_returns_preflight_result_with_youtube_and_appstore_candidates(mocker):
    _stub_pipeline(
        mocker,
        queries={
            "appstore": ["notes app"],
            "youtube": ["best notes app review"],
            "category": "note-taking",
            "signal_strength": "high",
            "signal_reasoning": "established consumer category.",
        },
        apps_by_query={"notes app": [{
            "bundle_id": "md.obsidian", "name": "Obsidian", "genre": "Productivity",
            "description": "d", "rating_count": 100,
            "url": "https://apps.apple.com/obsidian",
        }]},
        videos_by_query={"best notes app review": [{
            "video_id": "abc", "title": "Review", "channel": "Ch",
            "description": "d", "url": "https://www.youtube.com/watch?v=abc",
        }]},
        ranked={
            "apps": [{
                "bundle_id": "md.obsidian", "name": "Obsidian",
                "justification": "j", "url": "https://apps.apple.com/obsidian",
            }],
            "videos": [{
                "video_id": "abc", "title": "Review",
                "justification": "j", "url": "https://www.youtube.com/watch?v=abc",
            }],
        },
    )

    result = preflight_service.run("note-taking app with better offline sync")

    assert isinstance(result, PreflightResult)
    assert result.category == "note-taking"
    assert result.signal_strength == "high"
    sources = {c.source for c in result.candidates}
    assert sources == {"appstore", "youtube"}
    appstore_c = next(c for c in result.candidates if c.source == "appstore")
    assert appstore_c.identifier == "md.obsidian"
    assert appstore_c.name == "Obsidian"
    youtube_c = next(c for c in result.candidates if c.source == "youtube")
    assert youtube_c.identifier == "abc"
    assert youtube_c.name == "Review"


def test_run_dedupes_raw_candidates_before_ranking(mocker):
    """Multiple queries that hit the same app/video must not double-count."""
    duplicate_app = {
        "bundle_id": "md.obsidian", "name": "Obsidian", "genre": "Productivity",
        "description": "d", "rating_count": 100,
        "url": "https://apps.apple.com/obsidian",
    }
    duplicate_video = {
        "video_id": "abc", "title": "Review", "channel": "Ch",
        "description": "d", "url": "https://www.youtube.com/watch?v=abc",
    }
    _stub_pipeline(
        mocker,
        queries={
            "appstore": ["q1", "q2"],
            "youtube": ["v1", "v2"],
            "category": "c",
            "signal_strength": "high",
            "signal_reasoning": "r",
        },
        apps_by_query={"q1": [duplicate_app], "q2": [duplicate_app]},
        videos_by_query={"v1": [duplicate_video], "v2": [duplicate_video]},
        ranked={"apps": [], "videos": []},
    )

    preflight_service.run("idea")

    apps_arg = preflight_service.rank_candidates.call_args.args[1]
    videos_arg = preflight_service.rank_candidates.call_args.args[2]
    assert len(apps_arg) == 1
    assert len(videos_arg) == 1


def test_run_caps_raw_candidates_at_thirty_per_source(mocker):
    """Spec §7 / prototype §9: bound the ranker prompt context."""
    many_apps = [
        {
            "bundle_id": f"app.{i}", "name": f"App {i}", "genre": "g",
            "description": "d", "rating_count": i, "url": f"https://app/{i}",
        }
        for i in range(60)
    ]
    many_videos = [
        {
            "video_id": f"vid{i}", "title": f"Vid {i}", "channel": "c",
            "description": "d", "url": f"https://yt/{i}",
        }
        for i in range(60)
    ]
    _stub_pipeline(
        mocker,
        queries={
            "appstore": ["q"], "youtube": ["q"],
            "category": "c", "signal_strength": "low", "signal_reasoning": "r",
        },
        apps_by_query={"q": many_apps},
        videos_by_query={"q": many_videos},
        ranked={"apps": [], "videos": []},
    )

    preflight_service.run("idea")

    apps_arg = preflight_service.rank_candidates.call_args.args[1]
    videos_arg = preflight_service.rank_candidates.call_args.args[2]
    assert len(apps_arg) == 30
    assert len(videos_arg) == 30


def test_run_drops_ranked_entries_missing_identifier_or_url(mocker):
    """Defensive: a hallucinated id leaves URL blank — that candidate is dropped
    rather than persisted with an empty URL."""
    _stub_pipeline(
        mocker,
        queries={
            "appstore": ["q"], "youtube": ["q"],
            "category": "c", "signal_strength": "medium", "signal_reasoning": "r",
        },
        apps_by_query={"q": []},
        videos_by_query={"q": []},
        ranked={
            "apps": [
                {"bundle_id": "ok", "name": "OK", "justification": "j", "url": "https://ok"},
                {"bundle_id": "missing.url", "name": "X", "justification": "j", "url": ""},
                {"bundle_id": "", "name": "no-id", "justification": "j", "url": "https://x"},
            ],
            "videos": [
                {"video_id": "v1", "title": "T", "justification": "j", "url": "https://v1"},
                {"video_id": "v2", "title": "", "justification": "j", "url": "https://v2"},
            ],
        },
    )

    result = preflight_service.run("idea")

    identifiers = [c.identifier for c in result.candidates]
    assert identifiers == ["ok", "v1"]
