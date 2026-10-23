"""Platform-appropriate location for the local SQLite file."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def default_database_path() -> Path:
    """Return the user data path, or honor FOODLUCK_DB for testing/portability."""

    override = os.environ.get("FOODLUCK_DB")
    if override:
        return Path(override).expanduser()

    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "FoodLuck"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "FoodLuck"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "foodluck"
    return base / "foodluck.sqlite3"
