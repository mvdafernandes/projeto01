"""Build metadata helpers for runtime display."""

from __future__ import annotations

import os
import pathlib
import subprocess
from functools import lru_cache


_BUILD_ENV_KEYS = ("STREAMLIT_BUILD_ID", "GITHUB_SHA", "CI_COMMIT_SHA", "RENDER_GIT_COMMIT")


@lru_cache(maxsize=1)
def get_build_id() -> str:
    """Return a short build identifier for the current deployed revision."""
    for key in _BUILD_ENV_KEYS:
        value = str(os.getenv(key, "")).strip()
        if value:
            return value[:8]

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=_project_root(),
        )
        value = result.stdout.strip()
        if value:
            return value
    except Exception:
        pass

    return "unknown"


def _project_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent
