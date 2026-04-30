import os
import sys
import traceback

from app.config.keywords import (
    GAME_KEYWORDS,
    HOWTO_STYLE_KEYWORDS,
    SCIENCE_TECH_KEYWORDS,
)
from app.config.prompts import (
    youtubeGameSystemPrompt,
    youtubeHowtoStyleSystemPrompt,
    youtubeScienceTechSystemPrompt,
)
from app.config.settings import (
    GAME_CATEGORY_ID,
    HOW_TO_STYLE_ID,
    SCIENCE_TECH_ID,
)
from app.ingestion.youtubeComments import getMostPopularVideos
from app.scripts.automaticYoutube import youtube_automatic

# 5/category cap is enforced upstream by getMostPopularVideos (maxResults=5).
CATEGORIES = [
    ("Games", GAME_CATEGORY_ID, youtubeGameSystemPrompt, GAME_KEYWORDS),
    ("Science & Tech", SCIENCE_TECH_ID, youtubeScienceTechSystemPrompt, SCIENCE_TECH_KEYWORDS),
    ("How-to & Style", HOW_TO_STYLE_ID, youtubeHowtoStyleSystemPrompt, HOWTO_STYLE_KEYWORDS),
]


def run_category(category_id, prompt, keywords):
    videos = getMostPopularVideos(category_id)
    rows = youtube_automatic(videos, category_id, prompt, keywords) or []
    return len(videos), len(rows)


def write_summary(results):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a") as f:
        f.write("# Weekly YouTube Pipeline\n\n")
        f.write("| Category | Status | Videos | Rows | Error |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for name, ok, videos, rows, err in results:
            status = "OK" if ok else "FAIL"
            err_text = err.replace("|", "\\|") if err else ""
            f.write(f"| {name} | {status} | {videos} | {rows} | {err_text} |\n")


def main():
    results = []
    for name, category_id, prompt, keywords in CATEGORIES:
        print(f"=== Running category: {name} ({category_id}) ===")
        try:
            video_count, row_count = run_category(category_id, prompt, keywords)
            results.append((name, True, video_count, row_count, None))
            print(f"=== {name}: ok ({video_count} videos, {row_count} rows) ===")
        except Exception as exc:
            traceback.print_exc()
            results.append((name, False, 0, 0, repr(exc)))
            print(f"=== {name}: FAILED ===")

    write_summary(results)

    failed = [r for r in results if not r[1]]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
