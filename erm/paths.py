"""Resolve where the app stores its persistent data (database, generated
alert sound), so things still work when packaged into a standalone
executable.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def app_data_dir() -> Path:
    """A writable, persistent directory for the app's data.

    When run from source, this is the project's `data/` directory. When
    packaged (e.g. with PyInstaller), `sys.frozen` is set and the bundle's
    own directory may be temporary or read-only, so data is stored in the
    OS's per-user app-data directory instead.
    """
    if not getattr(sys, "frozen", False):
        return PROJECT_ROOT / "data"

    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "EscapeRoomMaster"
