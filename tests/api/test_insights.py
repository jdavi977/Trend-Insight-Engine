"""TestClient tests for GET /insights/similar with rag_service.similar mocked."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.rag import RetrievedInsight, SimilarInsightsResponse


@pytest.fixture
def client():
    return TestClient(app)


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


def test_get_similar_returns_results(client, mocker):
    mocker.patch(
        "app.api.insights.similar",
        return_value=SimilarInsightsResponse(query="crash", results=[_INSIGHT]),
    )
    response = client.get("/insights/similar", params={"query": "crash", "k": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "crash"
    assert len(payload["results"]) == 1
    assert payload["results"][0]["problem"] == "app crashes on launch"
    assert payload["results"][0]["similarity"] == 0.91


def test_get_similar_returns_empty_list_when_no_matches(client, mocker):
    mocker.patch(
        "app.api.insights.similar",
        return_value=SimilarInsightsResponse(query="nothing", results=[]),
    )
    response = client.get("/insights/similar", params={"query": "nothing"})

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_get_similar_uses_default_k(client, mocker):
    service = mocker.patch(
        "app.api.insights.similar",
        return_value=SimilarInsightsResponse(query="test", results=[]),
    )
    client.get("/insights/similar", params={"query": "test"})

    call_k = service.call_args.args[1]
    assert call_k == 5


def test_get_similar_missing_query_returns_422(client):
    response = client.get("/insights/similar")
    assert response.status_code == 422


def test_get_similar_empty_query_returns_422(client):
    response = client.get("/insights/similar", params={"query": ""})
    assert response.status_code == 422
