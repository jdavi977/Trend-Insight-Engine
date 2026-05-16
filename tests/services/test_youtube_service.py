"""Orchestration tests for the YouTube manual service."""
import app.services.youtube_service as _svc_mod
from app.services.youtube_service import youtube_manual
from app.schemas.llm import LLMExtraction, YoutubeProblemItem
from app.schemas.api import YoutubeAnalysisResponse


_LLM_RESULT = LLMExtraction(
    source="youtube",
    title="Vid",
    problems=[
        YoutubeProblemItem(
            problem="battery dies quickly",
            type="complaint",
            total_likes=200,
            severity=4,
            frequency=3,
        )
    ],
)


def test_youtube_manual_returns_validated_insights_for_real_pipeline(mocker):
    mocker.patch(
        "app.services.youtube_service.getVideoId",
        return_value="dQw4w9WgXcQ",
    )
    mocker.patch(
        "app.services.youtube_service.get_video_metadata",
        return_value={"title": "Vid"},
    )

    relevance_comments = [
        {"Title": "Vid", "Likes": 200, "Text": "battery problem on the device"},
        {"Title": "Vid", "Likes": 10, "Text": "below threshold should drop"},
    ]
    time_comments = [
        {"Title": "Vid", "Likes": 75, "Text": "the bug ruined this 🙃"},
    ]
    fetch = mocker.patch(
        "app.services.youtube_service.getYoutubeComments",
        side_effect=[relevance_comments, time_comments],
    )

    extract = mocker.patch(
        "app.services.youtube_service.extract_insights",
        return_value=_LLM_RESULT,
    )

    result = youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert isinstance(result, LLMExtraction)
    assert isinstance(result, YoutubeAnalysisResponse)
    assert result.source == "youtube"
    assert len(result.problems) == 1
    assert isinstance(result.problems[0], YoutubeProblemItem)
    assert result.problems[0].problem == "battery dies quickly"

    assert fetch.call_count == 2
    assert fetch.call_args_list[0].args == ("dQw4w9WgXcQ", "relevance")
    assert fetch.call_args_list[1].args == ("dQw4w9WgXcQ", "time")

    cleaned_passed_to_llm = extract.call_args.args[0]
    contents = [row["Content"] for row in cleaned_passed_to_llm]
    assert "battery problem on the device" in contents
    assert "the bug ruined this " in contents
    assert all("below threshold" not in c for c in contents)


def test_youtube_manual_returns_none_when_extract_insights_returns_none(mocker):
    mocker.patch("app.services.youtube_service.getVideoId", return_value="abc123")
    mocker.patch(
        "app.services.youtube_service.get_video_metadata",
        return_value={"title": "Vid"},
    )
    mocker.patch(
        "app.services.youtube_service.getYoutubeComments",
        side_effect=[[], []],
    )
    mocker.patch("app.services.youtube_service.extract_insights", return_value=None)

    result = youtube_manual("https://www.youtube.com/watch?v=abc123")

    assert result is None


class TestYoutubeManualRAGWritePath:
    def _setup(self, mocker):
        mocker.patch("app.services.youtube_service.getVideoId", return_value="dQw4w9WgXcQ")
        mocker.patch(
            "app.services.youtube_service.get_video_metadata",
            return_value={"title": "Test Video"},
        )
        mocker.patch(
            "app.services.youtube_service.getYoutubeComments",
            side_effect=[[{"Likes": 10, "Text": "good video"}], []],
        )
        mocker.patch("app.services.youtube_service.extract_insights", return_value=_LLM_RESULT)

    def test_embed_and_store_called_when_write_enabled(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_WRITE_ENABLED", True)
        embed = mocker.patch("app.services.youtube_service.embed_and_store")

        youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        embed.assert_called_once()
        call_args = embed.call_args
        assert call_args.args[0] is _LLM_RESULT
        assert "dQw4w9WgXcQ" in call_args.args[1]

    def test_embed_and_store_not_called_when_write_disabled(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_WRITE_ENABLED", False)
        embed = mocker.patch("app.services.youtube_service.embed_and_store")

        youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        embed.assert_not_called()

    def test_retrieve_similar_not_called(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_WRITE_ENABLED", False)
        mocker.patch.object(_svc_mod, "RAG_READ_ENABLED", False)
        retrieve = mocker.patch("app.rag.rag.retrieve_similar")

        youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        retrieve.assert_not_called()

    def test_embed_and_store_not_called_when_extract_returns_none(self, mocker):
        mocker.patch("app.services.youtube_service.getVideoId", return_value="abc")
        mocker.patch(
            "app.services.youtube_service.get_video_metadata",
            return_value={"title": "Test Video"},
        )
        mocker.patch("app.services.youtube_service.getYoutubeComments", side_effect=[[], []])
        mocker.patch("app.services.youtube_service.extract_insights", return_value=None)
        mocker.patch.object(_svc_mod, "RAG_WRITE_ENABLED", True)
        embed = mocker.patch("app.services.youtube_service.embed_and_store")

        youtube_manual("https://www.youtube.com/watch?v=abc")

        embed.assert_not_called()


class TestYoutubeManualRAGReadPath:
    def _setup(self, mocker):
        mocker.patch("app.services.youtube_service.getVideoId", return_value="dQw4w9WgXcQ")
        mocker.patch(
            "app.services.youtube_service.get_video_metadata",
            return_value={"title": "Rick Astley"},
        )
        mocker.patch(
            "app.services.youtube_service.getYoutubeComments",
            side_effect=[[{"Likes": 100, "Text": "battery drains way too fast on this device"}], []],
        )
        mocker.patch("app.services.youtube_service.extract_insights", return_value=_LLM_RESULT)
        mocker.patch("app.services.youtube_service.embed_and_store")

    def test_enrich_problems_called_when_read_enabled(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_READ_ENABLED", True)
        enrich = mocker.patch("app.services.youtube_service.enrich_problems")

        youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        enrich.assert_called_once()
        assert enrich.call_args.args[0] is _LLM_RESULT

    def test_enrich_problems_called_and_response_returned(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_READ_ENABLED", True)
        enrich = mocker.patch("app.services.youtube_service.enrich_problems")

        result = youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        enrich.assert_called_once()
        assert isinstance(result, YoutubeAnalysisResponse)

    def test_retrieve_similar_called_and_result_passed_to_prompt_builder(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_READ_ENABLED", True)
        mocker.patch("app.services.youtube_service.enrich_problems")
        from app.schemas.rag import RetrievedInsight
        from datetime import datetime, timezone
        fake_insight = RetrievedInsight(
            problem="past issue",
            type="complaint",
            severity=3,
            frequency=2,
            source="youtube",
            source_url="https://example.com",
            title=None,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            similarity=0.85,
        )
        retrieve = mocker.patch(
            "app.services.youtube_service.retrieve_similar",
            return_value=[fake_insight],
        )
        build = mocker.patch(
            "app.services.youtube_service.build_youtube_prompt",
            return_value="mocked prompt",
        )

        youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        retrieve.assert_called_once()
        call_kwargs = build.call_args
        prior = call_kwargs.args[1] if len(call_kwargs.args) > 1 else call_kwargs.kwargs.get("prior_insights")
        assert prior == [fake_insight]

    def test_retrieve_similar_not_called_when_read_disabled(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_READ_ENABLED", False)
        retrieve = mocker.patch("app.services.youtube_service.retrieve_similar")

        youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        retrieve.assert_not_called()

    def test_retrieve_similar_not_called_when_cleaned_data_empty(self, mocker):
        mocker.patch("app.services.youtube_service.getVideoId", return_value="dQw4w9WgXcQ")
        mocker.patch(
            "app.services.youtube_service.get_video_metadata",
            return_value={"title": "Rick Astley"},
        )
        mocker.patch("app.services.youtube_service.getYoutubeComments", side_effect=[[], []])
        mocker.patch("app.services.youtube_service.extract_insights", return_value=None)
        mocker.patch.object(_svc_mod, "RAG_READ_ENABLED", True)
        retrieve = mocker.patch("app.services.youtube_service.retrieve_similar")

        youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        retrieve.assert_not_called()

    def test_retrieve_similar_exception_falls_back_to_empty_prior_insights(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_READ_ENABLED", True)
        mocker.patch("app.services.youtube_service.enrich_problems")
        mocker.patch(
            "app.services.youtube_service.retrieve_similar",
            side_effect=Exception("embedding service down"),
        )
        build = mocker.patch(
            "app.services.youtube_service.build_youtube_prompt",
            return_value="mocked prompt",
        )

        result = youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert isinstance(result, YoutubeAnalysisResponse)
        call_kwargs = build.call_args
        prior = call_kwargs.args[1] if len(call_kwargs.args) > 1 else call_kwargs.kwargs.get("prior_insights")
        assert prior == []

    def test_enrich_problems_not_called_when_read_disabled(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_READ_ENABLED", False)
        enrich = mocker.patch("app.services.youtube_service.enrich_problems")

        result = youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        enrich.assert_not_called()
        assert isinstance(result, YoutubeAnalysisResponse)
