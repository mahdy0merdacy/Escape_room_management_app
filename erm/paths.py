"""Resolve where the app stores its persistent data and how to handle
portable (relative) media paths so the entire app folder can be moved
between machines without re-linking every video or audio file.

Portability model
-----------------
* The app folder is the *root* (exe directory when packaged, project root
  when run from source).
* The SQLite database lives in  <root>/data/
* Media files should ideally live somewhere inside <root>/ so that paths
  stored in the DB can be *relative* (e.g. "media/videos/briefing.mp4").
* When a user picks a file that is outside the root (e.g. on a different
  drive), the absolute path is kept as-is — it works on this machine but
  will need re-linking if moved to a new PC.
* `resolve_path()` turns any stored path (relative or absolute) into an
  absolute path so the rest of the app can open/play it normally.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# The project root when running from source (parent of this file's package)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def app_root() -> Path:
    """The directory that contains the running app.

    * Packaged (PyInstaller / cx_Freeze): the folder holding the .exe
    * Source: the project root directory

    Everything – database, media files – should live inside this tree so
    the whole folder can be copied to another machine and just work.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return PROJECT_ROOT


def app_data_dir() -> Path:
    """Writable directory for the SQLite database and other generated data."""
    return app_root() / "data"


def to_portable_path(abs_path: str) -> str:
    """Convert an absolute path to one relative to app_root(), if possible.

    If the file lives inside the app folder the returned path is relative
    (e.g. ``media\\videos\\briefing.mp4``), so it stays valid after the
    folder is moved or copied.  If the file is outside the app folder
    (different drive, arbitrary location) the original absolute path is
    returned unchanged.
    """
    try:
        return str(Path(abs_path).relative_to(app_root()))
    except ValueError:
        return abs_path


def resolve_path(path: Optional[str]) -> Optional[str]:
    """Resolve a stored path (possibly relative) to an absolute path.

    Relative paths are resolved against app_root().  Absolute paths are
    returned as-is.  ``None`` / empty string are passed through unchanged.
    """
    if not path:
        return path
    p = Path(path)
    if p.is_absolute():
        return str(p)
    return str(app_root() / p)
