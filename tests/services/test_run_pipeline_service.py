"""Background pipeline + approve tests (issue #50 / spec §6 + §8).

The pipeline's external edges are mocked at the module boundary:
- ingestion via `_ingest`
- per-source extraction via `extract_per_source`
- synthesis via `synthesis_stage.synthesize`
- idea-match via `match_idea`
- PII redaction via `redact`
- persistence via the supabase update/insert functions

…leaving the real orchestration (fan-out, semaphore, pooling, state transitions,
gap-row mapping) under test.
"""
from __future__ import annotations

import asyncio
import threading
import time

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.schemas.runs import Competitor, Coverage, GapItem, PainItem, Quote, RunApprove
from app.services import run_pipeline_service as svc

RUN_ID = "11111111-1111-1111-1111-111111111111"


# --- builders ---------------------------------------------------------------


def _competitor(source="youtube", identifier="vid_1", url="https://youtu.be/vid_1", name="Vid"):
    return Competitor(source=source, url=url, name=name, identifier=identifier)


def _quote(qid, source="youtube", source_id="vid_1", text="sync is broken"):
    return Quote(quote_id=qid, source=source, source_id=source_id,
                 text_redacted=text, like_count=10)


def _gap(gap_id="gap_001", evidence=("q01", "q02")):
    return GapItem(gap_id=gap_id, gap="Offline edits lost", severity=4,
                   frequency=len(evidence), spread=2,
                   competitors_present=["youtube:vid_1", "appstore:app_1"],
                   evidence_quote_ids=list(evidence))


def _row(status_="preflight_ready", signal_strength="high", target_gap=None):
    return {
        "id": RUN_ID,
        "idea": "note-taking app with better offline sync",
        "target_gap": target_gap,
        "status": status_,
        "category": "productivity",
        "signal_strength": signal_strength,
    }


@pytest.fixture(autouse=True)
def _clear_jobs():
    svc._jobs.clear()
    yield
    svc._jobs.clear()


# --- approve() --------------------------------------------------------------


class TestApprove:
    def test_happy_path_transitions_and_enqueues(self, mocker):
        mocker.patch.object(svc, "get_idea_run", return_value=_row())
        update_running = mocker.patch.object(svc, "update_idea_run_running")
        run_pipeline = mocker.patch.object(svc, "run_pipeline")
        bg = BackgroundTasks()

        result = svc.approve(RUN_ID, RunApprove(competitors=[_competitor()]), bg)

        assert result == {"run_id": RUN_ID, "status": "running"}
        update_running.assert_called_once()
        assert update_running.call_args.args[0] == RUN_ID
        assert svc._jobs[RUN_ID]["status"] == "running"
        assert len(bg.tasks) == 1  # pipeline enqueued, not yet run
        run_pipeline.assert_not_called()  # BackgroundTasks runs it later

    def test_missing_run_404(self, mocker):
        mocker.patch.object(svc, "get_idea_run", return_value=None)

        with pytest.raises(HTTPException) as exc:
            svc.approve(RUN_ID, RunApprove(competitors=[_competitor()]), BackgroundTasks())

        assert exc.value.status_code == 404

    def test_wrong_status_409(self, mocker):
        mocker.patch.object(svc, "get_idea_run", return_value=_row(status_="running"))

        with pytest.raises(HTTPException) as exc:
            svc.approve(RUN_ID, RunApprove(competitors=[_competitor()]), BackgroundTasks())

        assert exc.value.status_code == 409

    def test_low_signal_without_ack_400(self, mocker):
        mocker.patch.object(svc, "get_idea_run", return_value=_row(signal_strength="low"))
        update_running = mocker.patch.object(svc, "update_idea_run_running")

        with pytest.raises(HTTPException) as exc:
            svc.approve(RUN_ID, RunApprove(competitors=[_competitor()]), BackgroundTasks())

        assert exc.value.status_code == 400
        update_running.assert_not_called()

    def test_low_signal_with_ack_proceeds(self, mocker):
        mocker.patch.object(svc, "get_idea_run", return_value=_row(signal_strength="low"))
        mocker.patch.object(svc, "update_idea_run_running")
        mocker.patch.object(svc, "run_pipeline")

        result = svc.approve(
            RUN_ID,
            RunApprove(competitors=[_competitor()], acknowledged_low_signal=True),
            BackgroundTasks(),
        )

        assert result["status"] == "running"


# --- run_pipeline() ---------------------------------------------------------


def _wire_pipeline(mocker, *, extract_returns, gaps, coverage, idea_match=None):
    """Mock every pipeline edge; return the persistence mocks for assertions."""
    mocker.patch.object(svc, "_ingest", return_value=[{"Likes": 100, "Text": "x"}])
    mocker.patch.object(svc, "extract_per_source", side_effect=extract_returns)
    mocker.patch.object(svc, "redact", side_effect=lambda t: t.replace("john@example.com", "[REDACTED_EMAIL]"))
    mocker.patch("app.llm.synthesis.synthesize", return_value=(gaps, coverage))
    mocker.patch.object(svc, "match_idea", return_value=idea_match)
    done = mocker.patch.object(svc, "update_idea_run_done")
    failed = mocker.patch.object(svc, "update_idea_run_failed")
    insert = mocker.patch.object(svc, "insert_gaps")
    return done, failed, insert


class TestRunPipeline:
    def test_happy_path_pools_persists_and_marks_done(self, mocker):
        competitors = [_competitor(identifier="vid_1"), _competitor(source="appstore", identifier="app_1", url="https://apps.apple.com/app/id123")]
        extract_returns = [
            ([PainItem(source="youtube", source_id="vid_1", text="p1", quote_ids=["q01"])],
             [_quote("q01")]),
            ([], [_quote("q02", source="appstore", source_id="app_1")]),
        ]
        coverage = Coverage(quotes_retrieved=2, quotes_cited=2, citation_ratio=1.0)
        done, failed, insert = _wire_pipeline(
            mocker, extract_returns=extract_returns, gaps=[_gap()], coverage=coverage,
        )

        asyncio.run(svc.run_pipeline(
            run_id=RUN_ID, idea="idea", target_gap=None,
            category="productivity", competitors=competitors,
        ))

        failed.assert_not_called()
        done.assert_called_once()
        kwargs = done.call_args.kwargs
        assert set(kwargs["quotes"].keys()) == {"q01", "q02"}
        assert kwargs["coverage"]["quotes_retrieved"] == 2
        assert kwargs["idea_match"] is None
        # gaps inserted with run_id + ordinal
        rows = insert.call_args.args[0]
        assert rows[0]["run_id"] == RUN_ID
        assert rows[0]["ordinal"] == 1
        assert rows[0]["gap_id"] == "gap_001"
        assert svc._jobs.get(RUN_ID, {}).get("status") != "failed"

    def test_synthesis_sees_pooled_quotes_and_pain(self, mocker):
        competitors = [_competitor(identifier="vid_1"), _competitor(identifier="vid_2", url="https://youtu.be/vid_2")]
        extract_returns = [
            ([PainItem(source="youtube", source_id="vid_1", text="a", quote_ids=["q01"])], [_quote("q01")]),
            ([PainItem(source="youtube", source_id="vid_2", text="b", quote_ids=["q02"])], [_quote("q02", source_id="vid_2")]),
        ]
        _wire_pipeline(mocker, extract_returns=extract_returns,
                       gaps=[_gap()], coverage=Coverage(quotes_retrieved=2, quotes_cited=2, citation_ratio=1.0))
        synth = mocker.patch("app.llm.synthesis.synthesize",
                             return_value=([_gap()], Coverage(quotes_retrieved=2, quotes_cited=2, citation_ratio=1.0)))

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="my idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        args = synth.call_args.args
        assert args[0] == "my idea"          # idea
        pooled_quotes = args[2]
        pooled_pain = args[3]
        assert {q.quote_id for q in pooled_quotes} == {"q01", "q02"}
        assert len(pooled_pain) == 2

    def test_redaction_applied_before_persistence(self, mocker):
        competitors = [_competitor(identifier="vid_1")]
        raw_quote = _quote("q01", text="email me at john@example.com please")
        _wire_pipeline(
            mocker,
            extract_returns=[([], [raw_quote])],
            gaps=[],
            coverage=Coverage(quotes_retrieved=1, quotes_cited=0, citation_ratio=0.0),
        )
        done = mocker.patch.object(svc, "update_idea_run_done")

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        persisted = done.call_args.kwargs["quotes"]["q01"]["text_redacted"]
        assert "john@example.com" not in persisted
        assert "[REDACTED_EMAIL]" in persisted

    def test_idea_match_populated_when_target_gap_supplied(self, mocker):
        competitors = [_competitor(identifier="vid_1")]
        from app.schemas.runs import IdeaMatch
        idea_match = IdeaMatch(gap_id="gap_001", verdict="matches", evidence_quote_ids=["q01"])
        done, _, _ = _wire_pipeline(
            mocker,
            extract_returns=[([], [_quote("q01")])],
            gaps=[_gap()],
            coverage=Coverage(quotes_retrieved=1, quotes_cited=2, citation_ratio=1.0),
            idea_match=idea_match,
        )

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap="offline reliability",
                                     category="productivity", competitors=competitors))

        assert done.call_args.kwargs["idea_match"] == {
            "gap_id": "gap_001", "verdict": "matches", "evidence_quote_ids": ["q01"],
        }

    def test_idea_match_skipped_without_target_gap(self, mocker):
        competitors = [_competitor(identifier="vid_1")]
        _wire_pipeline(mocker, extract_returns=[([], [_quote("q01")])], gaps=[_gap()],
                       coverage=Coverage(quotes_retrieved=1, quotes_cited=2, citation_ratio=1.0))
        match = mocker.patch.object(svc, "match_idea", return_value=None)

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        match.assert_not_called()

    def test_source_failure_marks_run_failed(self, mocker):
        # approve() registers the job before enqueuing; simulate that here.
        svc._jobs[RUN_ID] = {"status": "running", "stage": "queued",
                             "started_at": None, "future": None}
        competitors = [_competitor(identifier="vid_1"), _competitor(identifier="vid_2", url="https://youtu.be/vid_2")]
        mocker.patch.object(svc, "_ingest", return_value=[])
        mocker.patch.object(svc, "redact", side_effect=lambda t: t)
        mocker.patch.object(svc, "extract_per_source",
                            side_effect=[([], [_quote("q01")]), RuntimeError("youtube 500")])
        done = mocker.patch.object(svc, "update_idea_run_done")
        failed = mocker.patch.object(svc, "update_idea_run_failed")

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        done.assert_not_called()
        failed.assert_called_once()
        assert "youtube 500" in failed.call_args.args[1]
        assert svc._jobs[RUN_ID]["status"] == "failed"

    def test_semaphore_caps_concurrent_openai_calls_at_five(self, mocker):
        competitors = [_competitor(identifier=f"vid_{i}", url=f"https://youtu.be/vid_{i}") for i in range(10)]
        mocker.patch.object(svc, "_ingest", return_value=[])
        mocker.patch.object(svc, "redact", side_effect=lambda t: t)
        mocker.patch("app.llm.synthesis.synthesize",
                     return_value=([], Coverage(quotes_retrieved=0, quotes_cited=0, citation_ratio=0.0)))
        mocker.patch.object(svc, "update_idea_run_done")
        mocker.patch.object(svc, "insert_gaps")

        lock = threading.Lock()
        state = {"current": 0, "max": 0}

        def _tracking_extract(comments, metadata):
            with lock:
                state["current"] += 1
                state["max"] = max(state["max"], state["current"])
            time.sleep(0.02)
            with lock:
                state["current"] -= 1
            return ([], [])

        mocker.patch.object(svc, "extract_per_source", side_effect=_tracking_extract)

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        assert state["max"] <= svc._OPENAI_CONCURRENCY
        assert state["max"] > 1  # genuinely concurrent, not serialised


class TestAppStoreIdResolution:
    def test_numeric_id_extracted_from_url(self):
        c = _competitor(source="appstore", identifier="md.obsidian",
                        url="https://apps.apple.com/us/app/obsidian/id1557175442?uo=4")
        assert svc._appstore_review_id(c) == "1557175442"

    def test_numeric_identifier_used_as_fallback(self):
        c = _competitor(source="appstore", identifier="123456", url="https://example.com")
        assert svc._appstore_review_id(c) == "123456"

    def test_unresolvable_raises(self):
        c = _competitor(source="appstore", identifier="md.obsidian", url="https://example.com")
        with pytest.raises(ValueError):
            svc._appstore_review_id(c)
