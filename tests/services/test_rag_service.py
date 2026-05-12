"""Tests that rag_service.similar delegates correctly to rag.retrieve_similar."""
from app.services.rag_service import similar
from app.schemas.rag import RetrievedInsight, SimilarInsightsResponse


_INSIGHT = RetrievedInsight(
    problem="app crashes on launch",
    type="complaint",
    severity=5,
    frequency=4,
    source="app_store",
    source_url="https://apps.apple.com/us/app/example/id123",
    title="Example App",
    extracted_at="2026-01-01T00:00:00+00:00",
    similarity=0.91,
)


def test_similar_returns_response_with_query_and_results(mocker):
    retrieve = mocker.patch(
        "app.services.rag_service.retrieve_similar",
        return_value=[_INSIGHT],
    )

    response = similar("crash on launch", 5)

    retrieve.assert_called_once_with("crash on launch", 5)
    assert isinstance(response, SimilarInsightsResponse)
    assert response.query == "crash on launch"
    assert len(response.results) == 1
    assert response.results[0].problem == "app crashes on launch"
    assert response.results[0].similarity == 0.91


def test_similar_returns_empty_results_when_retrieve_returns_nothing(mocker):
    mocker.patch("app.services.rag_service.retrieve_similar", return_value=[])

    response = similar("no match", 5)

    assert response.query == "no match"
    assert response.results == []


def test_similar_passes_k_to_retrieve(mocker):
    retrieve = mocker.patch(
        "app.services.rag_service.retrieve_similar",
        return_value=[],
    )

    similar("some query", 3)

    retrieve.assert_called_once_with("some query", 3)
