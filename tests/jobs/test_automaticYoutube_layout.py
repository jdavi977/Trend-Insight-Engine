"""Layout test for PR 6: scripts/ → jobs/.

The job entrypoint is a thin shell — its orchestration is exercised via
service tests. This test only guards the move itself: the cron entrypoint
must reach `youtube_automatic` through `app.jobs`, and the legacy
`app.scripts` package must be gone.
"""

import importlib


def test_youtube_automatic_importable_from_jobs():
    module = importlib.import_module("app.jobs.automaticYoutube")
    assert callable(module.youtube_automatic)


def test_weekly_cron_entrypoint_imports_cleanly():
    module = importlib.import_module("ops.scripts.weeklyYoutube")
    assert callable(module.main)
    assert callable(module.run_category)


def test_legacy_scripts_package_removed():
    try:
        importlib.import_module("app.scripts")
    except ModuleNotFoundError:
        return
    raise AssertionError("app.scripts should be removed in PR 6")
