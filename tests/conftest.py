"""Point profile loading at the small committed fixture; avoid S3 and user_profiles.json."""

from __future__ import annotations

import os
from pathlib import Path

_TEST_PROFILES = Path(__file__).resolve().parent.parent / "app" / "data" / "user_profiles_test.json"


def pytest_configure(config):
    """Runs before collection and test setup so ``User()`` always sees the test file."""
    os.environ["USER_PROFILES_JSON_PATH"] = str(_TEST_PROFILES)
    for key in ("USER_PROFILES_BUCKET", "S3_BUCKET", "AWS_S3_BUCKET"):
        os.environ.pop(key, None)


def pytest_sessionstart(session):
    try:
        import app.models as models

        models._profiles_by_id = None
    except ImportError:
        pass
