"""Orchestration tests for the YouTube manual service."""
from app.services.youtube_service import youtube_manual
from app.schemas.llm import LLMExtraction, YoutubeProblemItem


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
        "app.services.youtube_service.getYoutubeComments",
        side_effect=[[], []],
    )
    mocker.patch("app.services.youtube_service.extract_insights", return_value=None)

    result = youtube_manual("https://www.youtube.com/watch?v=abc123")

    assert result is None
