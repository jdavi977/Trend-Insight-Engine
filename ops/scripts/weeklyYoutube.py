import os
import sys
import traceback

from app.config.genres import YOUTUBE_GENRES
from app.ingestion.youtubeComments import getMostPopularVideos
from app.jobs.automaticYoutube import youtube_automatic


def run_category(category_id, genre, keywords):
    # Get most popular videos for the category
    videos = getMostPopularVideos(category_id)
    rows = youtube_automatic(videos, category_id, genre, keywords) or []
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
    for genre in YOUTUBE_GENRES:
        print(f"=== Running category: {genre.name} ({genre.id}) ===")
        try:
            video_count, row_count = run_category(genre.id, genre, genre.keywords)
            results.append((genre.name, True, video_count, row_count, None))
            print(f"=== {genre.name}: ok ({video_count} videos, {row_count} rows) ===")
        except Exception as exc:
            traceback.print_exc()
            results.append((genre.name, False, 0, 0, repr(exc)))
            print(f"=== {genre.name}: FAILED ===")

    write_summary(results)

    failed = [r for r in results if not r[1]]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
