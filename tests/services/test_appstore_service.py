"""Orchestration tests for the App Store manual service."""
import app.services.appstore_service as _svc_mod
from app.services.appstore_service import app_store_manual
from app.schemas.llm import LLMExtraction, AppStoreProblemItem


_LLM_RESULT = LLMExtraction(
    source="app_store",
    title="Cool App",
    problems=[
        AppStoreProblemItem(
            problem="notifications never arrive",
            type="complaint",
            average_rating=2.1,
            severity=4,
            frequency=3,
            example_reviews=["never gets notifs", "push broken for months"],
        )
    ],
)


def test_app_store_manual_returns_validated_insights(mocker):
    mocker.patch("app.services.appstore_service.getAppId", return_value="12345")

    most_recent = [{"title": "Cool App", "vote_count": 1, "content": "notifications broken"}]
    most_helpful = [{"title": "Cool App", "vote_count": 2, "content": "push never works"}]
    fetch = mocker.patch(
        "app.services.appstore_service.getAppReviews",
        side_effect=[most_recent, most_helpful],
    )

    extract = mocker.patch(
        "app.services.appstore_service.extract_insights",
        return_value=_LLM_RESULT,
    )

    result = app_store_manual("https://apps.apple.com/app/cool-app/id12345")

    assert isinstance(result, LLMExtraction)
    assert result.source == "app_store"
    assert len(result.problems) == 1
    assert isinstance(result.problems[0], AppStoreProblemItem)
    assert result.problems[0].problem == "notifications never arrive"

    assert fetch.call_count == 2
    assert extract.call_count == 1


def test_app_store_manual_returns_none_when_extract_insights_returns_none(mocker):
    mocker.patch("app.services.appstore_service.getAppId", return_value="99999")
    mocker.patch("app.services.appstore_service.getAppReviews", side_effect=[[], []])
    mocker.patch("app.services.appstore_service.extract_insights", return_value=None)

    result = app_store_manual("https://apps.apple.com/app/dead-app/id99999")

    assert result is None


class TestAppStoreManualRAGWritePath:
    def _setup(self, mocker):
        mocker.patch("app.services.appstore_service.getAppId", return_value="12345")
        mocker.patch(
            "app.services.appstore_service.getAppReviews",
            side_effect=[[{"title": "App", "vote_count": 1, "content": "great"}], []],
        )
        mocker.patch("app.services.appstore_service.extract_insights", return_value=_LLM_RESULT)

    def test_embed_and_store_called_when_write_enabled(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_WRITE_ENABLED", True)
        embed = mocker.patch("app.services.appstore_service.embed_and_store")

        app_store_manual("https://apps.apple.com/app/cool-app/id12345")

        embed.assert_called_once()
        call_args = embed.call_args
        assert call_args.args[0] is _LLM_RESULT
        assert "12345" in call_args.args[1]

    def test_embed_and_store_not_called_when_write_disabled(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_WRITE_ENABLED", False)
        embed = mocker.patch("app.services.appstore_service.embed_and_store")

        app_store_manual("https://apps.apple.com/app/cool-app/id12345")

        embed.assert_not_called()

    def test_retrieve_similar_not_called(self, mocker):
        self._setup(mocker)
        mocker.patch.object(_svc_mod, "RAG_WRITE_ENABLED", False)
        mocker.patch("app.services.appstore_service.embed_and_store")
        retrieve = mocker.patch("app.rag.rag.retrieve_similar")

        app_store_manual("https://apps.apple.com/app/cool-app/id12345")

        retrieve.assert_not_called()

    def test_embed_and_store_not_called_when_extract_returns_none(self, mocker):
        mocker.patch("app.services.appstore_service.getAppId", return_value="99")
        mocker.patch("app.services.appstore_service.getAppReviews", side_effect=[[], []])
        mocker.patch("app.services.appstore_service.extract_insights", return_value=None)
        mocker.patch.object(_svc_mod, "RAG_WRITE_ENABLED", True)
        embed = mocker.patch("app.services.appstore_service.embed_and_store")

        app_store_manual("https://apps.apple.com/app/dead-app/id99")

        embed.assert_not_called()
