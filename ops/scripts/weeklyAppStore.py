import os
import sys
import traceback

from app.config.keywords import APPLE_KEYWORDS
from app.config.prompts import appStoreGamesSystemPrompt, appStoreSocialSystemPrompt, appStoreUtilitiesSystemPrompt
from app.config.constants import (
    APPLE_COUNTRY,
    APPLE_GAMES_GENRE_ID,
    APPLE_TOP_APPS_LIMIT,
    APPLE_UTILITIES_GENRE_ID,
    APPLE_SOCIAL_GENRE_ID, 
    APPLE_UTILITIES_GENRE_ID
)
from app.clients.appstore import list_top_apps
from app.jobs.automaticAppStore import appstore_automatic

# 5/genre cap is enforced upstream by list_top_apps (limit=APPLE_TOP_APPS_LIMIT).
GENRES = [
    ("Games", APPLE_GAMES_GENRE_ID, appStoreGamesSystemPrompt, APPLE_KEYWORDS),
    ("Social Networking", APPLE_SOCIAL_GENRE_ID, appStoreSocialSystemPrompt, APPLE_KEYWORDS),
    ("Utilities", APPLE_UTILITIES_GENRE_ID, appStoreUtilitiesSystemPrompt, APPLE_KEYWORDS),
]


def run_genre(genre_id, prompt, keywords):
    apps = list_top_apps(genre_id, country=APPLE_COUNTRY, limit=APPLE_TOP_APPS_LIMIT)
    rows = appstore_automatic(apps, genre_id, prompt, keywords) or []
    return len(apps), len(rows)


def write_summary(results):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a") as f:
        f.write("# Weekly App Store Pipeline\n\n")
        f.write("| Genre | Status | Apps | Rows | Error |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for name, ok, apps, rows, err in results:
            status = "OK" if ok else "FAIL"
            err_text = err.replace("|", "\\|") if err else ""
            f.write(f"| {name} | {status} | {apps} | {rows} | {err_text} |\n")


def main():
    results = []
    for name, genre_id, prompt, keywords in GENRES:
        print(f"=== Running genre: {name} ({genre_id}) ===")
        try:
            app_count, row_count = run_genre(genre_id, prompt, keywords)
            results.append((name, True, app_count, row_count, None))
            print(f"=== {name}: ok ({app_count} apps, {row_count} rows) ===")
        except Exception as exc:
            traceback.print_exc()
            results.append((name, False, 0, 0, repr(exc)))
            print(f"=== {name}: FAILED ===")

    write_summary(results)

    failed = [r for r in results if not r[1]]
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
