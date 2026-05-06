from app.config.preprocessing import YOUTUBE_PREPROCESS
from app.ingestion.youtubeComments import getVideoId, getYoutubeComments
from app.preprocessing.reviewPipeline import clean
from app.llm.extractInsights import extractInsights
from app.llm.validateOutput import validateOutput
from app.config.promptTemplates import build_youtube_prompt, youtubePromptOutput
from app.config.genres import get_default_genre


def youtube_manual(link: str):
    default = get_default_genre("youtube")
    id = getVideoId(link)
    relevance = getYoutubeComments(id, "relevance")
    time = getYoutubeComments(id, "time")
    all_items = relevance + time
    rows = [{**item, "Content": item["Text"]} for item in all_items]
    cleaned_data = clean(rows, **YOUTUBE_PREPROCESS)
    insights = extractInsights(cleaned_data, build_youtube_prompt(default), youtubePromptOutput)
    validated_data = validateOutput(insights)
    return validated_data
