"""Happy-path orchestration test for the YouTube service.

Imports `app.scripts.youtubePipeline` for now. PR 3 moves this to
`app.services.youtube_service`; updating the import here is the regression
check for that PR.
"""
import json

from app.scripts.youtubePipeline import youtube_manual
from app.schemas.llm_insights import LLMExtraction


def test_youtube_manual_returns_validated_insights_for_real_pipeline(mocker):
    mocker.patch(
        "app.scripts.youtubePipeline.getVideoId",
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
        "app.scripts.youtubePipeline.getYoutubeComments",
        side_effect=[relevance_comments, time_comments],
    )

    llm_response = json.dumps({
        "source": "youtube",
        "title": "Vid",
        "problems": [
            {
                "problem": "battery dies quickly",
                "type": "complaint",
                "total_likes": 200,
                "severity": 4,
                "frequency": 3,
            }
        ],
    })
    extract = mocker.patch(
        "app.scripts.youtubePipeline.extractInsights",
        return_value=llm_response,
    )

    result = youtube_manual("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert isinstance(result, LLMExtraction)
    assert result.source == "youtube"
    assert len(result.problems) == 1
    assert result.problems[0]["problem"] == "battery dies quickly"

    assert fetch.call_count == 2
    assert fetch.call_args_list[0].args == ("dQw4w9WgXcQ", "relevance")
    assert fetch.call_args_list[1].args == ("dQw4w9WgXcQ", "time")

    cleaned_passed_to_llm = extract.call_args.args[0]
    contents = [row["Content"] for row in cleaned_passed_to_llm]
    assert "battery problem on the device" in contents
    assert "the bug ruined this " in contents
    assert all("below threshold" not in c for c in contents)
