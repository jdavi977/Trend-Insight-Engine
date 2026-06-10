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


def _row(
    status_="preflight_ready",
    signal_strength="high",
    target_gap=None,
    candidate_count=5,
):
    """Build an `idea_runs` row. `candidate_count` is the pre-flight candidate
    pool size persisted to `competitors_json` — the low-signal gate (issue #69)
    keys off its length, so it defaults to >= LOW_SIGNAL_CANDIDATE_THRESHOLD."""
    return {
        "id": RUN_ID,
        "idea": "note-taking app with better offline sync",
        "target_gap": target_gap,
        "status": status_,
        "category": "productivity",
        "signal_strength": signal_strength,
        "competitors_json": [
            _competitor(identifier=f"vid_{i}").model_dump()
            for i in range(candidate_count)
        ],
    }


@pytest.fixture(autouse=True)
def _clear_jobs():
    svc._jobs.clear()
    yield
    svc._jobs.clear()


@pytest.fixture(autouse=True)
def _no_backoff_sleep(mocker):
    """Collapse the per-source retry backoff so tests don't actually wait."""
    mocker.patch.object(svc, "_backoff_delay", return_value=0)


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

    def test_below_threshold_without_ack_400(self, mocker):
        # Below LOW_SIGNAL_CANDIDATE_THRESHOLD (4) candidates → ack required.
        mocker.patch.object(svc, "get_idea_run", return_value=_row(candidate_count=3))
        update_running = mocker.patch.object(svc, "update_idea_run_running")

        with pytest.raises(HTTPException) as exc:
            svc.approve(RUN_ID, RunApprove(competitors=[_competitor()]), BackgroundTasks())

        assert exc.value.status_code == 400
        update_running.assert_not_called()

    def test_below_threshold_with_ack_proceeds(self, mocker):
        mocker.patch.object(svc, "get_idea_run", return_value=_row(candidate_count=3))
        mocker.patch.object(svc, "update_idea_run_running")
        mocker.patch.object(svc, "run_pipeline")

        result = svc.approve(
            RUN_ID,
            RunApprove(competitors=[_competitor()], acknowledged_low_signal=True),
            BackgroundTasks(),
        )

        assert result["status"] == "running"

    def test_at_threshold_proceeds_without_ack(self, mocker):
        # >= threshold candidates approve freely regardless of the LLM grade.
        mocker.patch.object(
            svc,
            "get_idea_run",
            return_value=_row(signal_strength="low", candidate_count=4),
        )
        mocker.patch.object(svc, "update_idea_run_running")
        run_pipeline = mocker.patch.object(svc, "run_pipeline")

        result = svc.approve(
            RUN_ID, RunApprove(competitors=[_competitor()]), BackgroundTasks()
        )

        assert result["status"] == "running"
        run_pipeline.assert_not_called()  # enqueued via BackgroundTasks, not called

    def test_zero_candidates_without_ack_400(self, mocker):
        # US-S1 no-sources band (0 candidates) is below threshold → still gated.
        mocker.patch.object(svc, "get_idea_run", return_value=_row(candidate_count=0))
        update_running = mocker.patch.object(svc, "update_idea_run_running")

        with pytest.raises(HTTPException) as exc:
            svc.approve(RUN_ID, RunApprove(competitors=[_competitor()]), BackgroundTasks())

        assert exc.value.status_code == 400
        update_running.assert_not_called()


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


# --- source resilience: retry + partial-source threshold (issue #60) ---------


def _extract_dispatch(*, fail_ids=(), fail_once_ids=()):
    """An `extract_per_source` side_effect keyed by `metadata.source_id`.

    - `fail_ids`: raise on every attempt (permanent failure).
    - `fail_once_ids`: raise on the first attempt only, then succeed (transient).
    A surviving source yields one pain item + one quote tagged with its id.
    Thread-safe attempt counting — sources fan out across worker threads.
    """
    attempts: dict[str, int] = {}
    lock = threading.Lock()

    def _extract(comments, metadata):
        sid = metadata.source_id
        with lock:
            n = attempts.get(sid, 0)
            attempts[sid] = n + 1
        if sid in fail_ids:
            raise RuntimeError(f"{sid} permafail")
        if sid in fail_once_ids and n == 0:
            raise RuntimeError(f"{sid} transient")
        qid = f"q_{sid}"
        return (
            [PainItem(source="youtube", source_id=sid, text="p", quote_ids=[qid])],
            [_quote(qid, source_id=sid)],
        )

    return _extract


def _ten_competitors():
    return [
        _competitor(identifier=f"vid_{i}", url=f"https://youtu.be/vid_{i}", name=f"Vid {i}")
        for i in range(10)
    ]


class TestSourceResilience:
    def test_source_that_fails_once_is_retried_and_contributes(self, mocker):
        competitors = [_competitor(identifier="vid_1"),
                       _competitor(identifier="vid_2", url="https://youtu.be/vid_2")]
        coverage = Coverage(quotes_retrieved=2, quotes_cited=2, citation_ratio=1.0)
        done, failed, _ = _wire_pipeline(
            mocker,
            extract_returns=_extract_dispatch(fail_once_ids=("vid_2",)),
            gaps=[_gap()], coverage=coverage,
        )
        synth = mocker.patch("app.llm.synthesis.synthesize",
                             return_value=([_gap()], coverage))

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        failed.assert_not_called()
        done.assert_called_once()
        # The retried source's quote made it into the pool → it contributed.
        pooled_quotes = synth.call_args.args[2]
        assert {q.quote_id for q in pooled_quotes} == {"q_vid_1", "q_vid_2"}
        # A fully-recovered run carries no partial_sources block.
        assert done.call_args.kwargs["partial_sources"] is None

    def test_two_of_ten_failing_completes_done_with_partial_sources(self, mocker):
        competitors = _ten_competitors()
        coverage = Coverage(quotes_retrieved=8, quotes_cited=8, citation_ratio=1.0)
        done, failed, _ = _wire_pipeline(
            mocker,
            extract_returns=_extract_dispatch(fail_ids=("vid_3", "vid_7")),
            gaps=[_gap()], coverage=coverage,
        )
        mocker.patch("app.llm.synthesis.synthesize", return_value=([_gap()], coverage))

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        failed.assert_not_called()
        done.assert_called_once()
        partial = done.call_args.kwargs["partial_sources"]
        assert partial["succeeded_count"] == 8
        assert partial["total_count"] == 10
        failed_names = {f["name"] for f in partial["failed"]}
        assert failed_names == {"Vid 3", "Vid 7"}

    def test_four_of_ten_failing_ends_failed_below_threshold(self, mocker):
        svc._jobs[RUN_ID] = {"status": "running", "stage": "queued",
                             "started_at": None, "future": None}
        competitors = _ten_competitors()
        coverage = Coverage(quotes_retrieved=6, quotes_cited=6, citation_ratio=1.0)
        done, failed, _ = _wire_pipeline(
            mocker,
            extract_returns=_extract_dispatch(fail_ids=("vid_0", "vid_1", "vid_2", "vid_3")),
            gaps=[_gap()], coverage=coverage,
        )

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        done.assert_not_called()
        failed.assert_called_once()
        assert failed.call_args.args[1] == "sources_below_threshold"
        assert svc._jobs[RUN_ID]["status"] == "failed"

    def test_one_source_raising_does_not_cancel_siblings(self, mocker):
        # 1 of 5 fails (80% ≥ 70%) → siblings must all still contribute.
        competitors = [
            _competitor(identifier=f"vid_{i}", url=f"https://youtu.be/vid_{i}")
            for i in range(5)
        ]
        coverage = Coverage(quotes_retrieved=4, quotes_cited=4, citation_ratio=1.0)
        done, failed, _ = _wire_pipeline(
            mocker,
            extract_returns=_extract_dispatch(fail_ids=("vid_2",)),
            gaps=[_gap()], coverage=coverage,
        )
        synth = mocker.patch("app.llm.synthesis.synthesize",
                             return_value=([_gap()], coverage))

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        failed.assert_not_called()
        done.assert_called_once()
        pooled_quotes = synth.call_args.args[2]
        assert {q.quote_id for q in pooled_quotes} == {
            "q_vid_0", "q_vid_1", "q_vid_3", "q_vid_4",
        }

    def test_threshold_is_read_from_constants(self):
        from app.config import constants
        assert constants.PARTIAL_SOURCE_THRESHOLD == 0.70
        assert svc.PARTIAL_SOURCE_THRESHOLD is constants.PARTIAL_SOURCE_THRESHOLD


# --- quality signals (slice 3 §5 / issue #67) -------------------------------


class TestQualitySignalsComputation:
    """Pure-function checks on `_compute_quality_signals`."""

    def test_diversity_is_one_minus_max_source_share(self):
        # Cited quotes: 3 youtube + 1 appstore → max_share 3/4 → diversity 0.25.
        quotes = [
            _quote("q01", source="youtube"),
            _quote("q02", source="youtube"),
            _quote("q03", source="youtube"),
            _quote("q04", source="appstore"),
        ]
        gap = GapItem(gap_id="g1", gap="g", severity=3, frequency=4, spread=2,
                      evidence_quote_ids=["q01", "q02", "q03", "q04"])
        signals = svc._compute_quality_signals([gap], quotes, [])

        assert signals.quote_source_diversity == 0.25

    def test_diversity_zero_when_single_source(self):
        quotes = [_quote("q01"), _quote("q02")]
        gap = _gap(evidence=("q01", "q02"))  # both youtube
        signals = svc._compute_quality_signals([gap], quotes, [])
        assert signals.quote_source_diversity == 0.0

    def test_diversity_zero_when_no_gaps_cite_anything(self):
        signals = svc._compute_quality_signals([], [_quote("q01")], [])
        assert signals.quote_source_diversity == 0.0

    def test_only_cited_quotes_count_toward_diversity(self):
        # q03 (appstore) is in the pool but uncited → must not lift diversity.
        quotes = [_quote("q01"), _quote("q02"), _quote("q03", source="appstore")]
        gap = _gap(evidence=("q01", "q02"))
        signals = svc._compute_quality_signals([gap], quotes, [])
        assert signals.quote_source_diversity == 0.0

    def test_severity_distribution_is_length_five_counts(self):
        gaps = [
            _gap(gap_id="g1"),  # severity 4
            GapItem(gap_id="g2", gap="g", severity=1, frequency=2, spread=1,
                    evidence_quote_ids=["q01", "q02"]),
            GapItem(gap_id="g3", gap="g", severity=4, frequency=2, spread=2,
                    evidence_quote_ids=["q01", "q02"]),
        ]
        signals = svc._compute_quality_signals(gaps, [_quote("q01"), _quote("q02")], [])
        assert signals.severity_distribution == [1, 0, 0, 2, 0]

    def test_single_source_gap_count_is_spread_equals_one(self):
        gaps = [
            GapItem(gap_id="g1", gap="g", severity=3, frequency=2, spread=1,
                    evidence_quote_ids=["q01", "q02"]),
            GapItem(gap_id="g2", gap="g", severity=3, frequency=2, spread=3,
                    evidence_quote_ids=["q01", "q02"]),
            GapItem(gap_id="g3", gap="g", severity=3, frequency=2, spread=1,
                    evidence_quote_ids=["q01", "q02"]),
        ]
        signals = svc._compute_quality_signals(gaps, [_quote("q01"), _quote("q02")], [])
        assert signals.single_source_gap_count == 2


class TestQualitySignalsPersistence:
    def test_done_run_persists_all_four_subfields(self, mocker):
        competitors = [
            _competitor(identifier="vid_1"),
            _competitor(source="appstore", identifier="app_1",
                        url="https://apps.apple.com/app/id123"),
        ]
        extract_returns = [
            ([PainItem(source="youtube", source_id="vid_1", text="p1", quote_ids=["q01"])],
             [_quote("q01")]),
            ([], [_quote("q02", source="appstore", source_id="app_1")]),
        ]
        coverage = Coverage(quotes_retrieved=2, quotes_cited=2, citation_ratio=1.0)
        done, _, _ = _wire_pipeline(
            mocker, extract_returns=extract_returns,
            gaps=[_gap(evidence=("q01", "q02"))], coverage=coverage,
        )

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        qs = done.call_args.kwargs["quality_signals"]
        assert qs is not None
        # _gap cites q01 (youtube) + q02 (appstore) → even split → diversity 0.5.
        assert qs["quote_source_diversity"] == 0.5
        assert qs["severity_distribution"] == [0, 0, 0, 1, 0]  # _gap is severity 4
        assert qs["single_source_gap_count"] == 0  # _gap spread == 2
        assert len(qs["extraction_yield"]) == 2

    def test_extraction_yield_reflects_comment_and_pain_counts(self, mocker):
        competitors = [_competitor(identifier="vid_1")]
        # _ingest is mocked to return one comment row per source by _wire_pipeline.
        extract_returns = [
            ([PainItem(source="youtube", source_id="vid_1", text="p1", quote_ids=["q01"]),
              PainItem(source="youtube", source_id="vid_1", text="p2", quote_ids=["q02"])],
             [_quote("q01"), _quote("q02")]),
        ]
        coverage = Coverage(quotes_retrieved=2, quotes_cited=2, citation_ratio=1.0)
        done, _, _ = _wire_pipeline(
            mocker, extract_returns=extract_returns,
            gaps=[_gap(evidence=("q01", "q02"))], coverage=coverage,
        )

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        yields = done.call_args.kwargs["quality_signals"]["extraction_yield"]
        assert yields == [
            {"source": "youtube", "comment_count": 1, "pain_item_count": 2},
        ]

    def test_computation_error_persists_null_and_run_still_done(self, mocker):
        competitors = [_competitor(identifier="vid_1")]
        coverage = Coverage(quotes_retrieved=1, quotes_cited=2, citation_ratio=1.0)
        done, failed, _ = _wire_pipeline(
            mocker, extract_returns=[([], [_quote("q01")])],
            gaps=[_gap()], coverage=coverage,
        )
        mocker.patch.object(svc, "_compute_quality_signals",
                            side_effect=RuntimeError("boom"))

        asyncio.run(svc.run_pipeline(run_id=RUN_ID, idea="idea", target_gap=None,
                                     category="productivity", competitors=competitors))

        failed.assert_not_called()
        done.assert_called_once()
        assert done.call_args.kwargs["quality_signals"] is None


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
