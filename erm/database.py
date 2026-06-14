"""SQLite persistence layer for the Escape Room Master Console.

All GUI code should go through the functions in this module instead of
running raw SQL. Paths are resolved relative to the project root so the
app works the same regardless of the current working directory or OS.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from erm.models import Clue, Hint, Objective, Room, RoomAudioSettings, SessionState
from erm.paths import app_data_dir

DATA_DIR = app_data_dir()
DB_PATH = DATA_DIR / "escape_rooms.db"

_connection: Optional[sqlite3.Connection] = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 3600,
    intro_video_path TEXT,
    ending_video_path TEXT,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    intro_video_path_fr TEXT
);

CREATE TABLE IF NOT EXISTS objectives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0,
    checkpoint_video_path TEXT,
    code TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS hints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objective_id INTEGER NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0,
    rating INTEGER NOT NULL DEFAULT 0,
    video_path TEXT
);

CREATE TABLE IF NOT EXISTS clues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    room_id INTEGER PRIMARY KEY REFERENCES rooms(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'idle',
    remaining_seconds INTEGER NOT NULL DEFAULT 0,
    messages_sent INTEGER NOT NULL DEFAULT 0,
    time_adjusted_seconds INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS objective_progress (
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    objective_id INTEGER NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
    completed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (room_id, objective_id)
);

CREATE TABLE IF NOT EXISTS clue_progress (
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    clue_id INTEGER NOT NULL REFERENCES clues(id) ON DELETE CASCADE,
    checked INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (room_id, clue_id)
);

CREATE TABLE IF NOT EXISTS room_audio_settings (
    room_id INTEGER PRIMARY KEY REFERENCES rooms(id) ON DELETE CASCADE,
    alert_volume INTEGER NOT NULL DEFAULT 100,
    alert_muted INTEGER NOT NULL DEFAULT 0,
    alert_path TEXT,
    game_music_volume INTEGER NOT NULL DEFAULT 100,
    game_music_muted INTEGER NOT NULL DEFAULT 0,
    game_music_path TEXT,
    success_volume INTEGER NOT NULL DEFAULT 100,
    success_muted INTEGER NOT NULL DEFAULT 0,
    success_path TEXT,
    fail_volume INTEGER NOT NULL DEFAULT 100,
    fail_muted INTEGER NOT NULL DEFAULT 0,
    fail_path TEXT,
    video_volume INTEGER NOT NULL DEFAULT 100,
    video_muted INTEGER NOT NULL DEFAULT 0,
    master_volume INTEGER NOT NULL DEFAULT 100,
    master_muted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS room_video_volumes (
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    video_path TEXT NOT NULL,
    volume INTEGER NOT NULL DEFAULT 100,
    muted INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (room_id, video_path)
);
"""


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(DB_PATH)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA foreign_keys = ON")
    return _connection


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    """Add `column` to `table` via ALTER TABLE if it doesn't already exist.

    `ddl` is the full column definition passed to ADD COLUMN, e.g.
    "wins INTEGER NOT NULL DEFAULT 0".
    """
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Bring an existing database up to date with newly added columns."""
    _ensure_column(conn, "rooms", "wins", "wins INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "rooms", "losses", "losses INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "objectives", "code", "code TEXT")
    _ensure_column(conn, "objectives", "description", "description TEXT")
    _ensure_column(conn, "hints", "rating", "rating INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "hints", "video_path", "video_path TEXT")
    _ensure_column(conn, "sessions", "messages_sent", "messages_sent INTEGER NOT NULL DEFAULT 0")
    _ensure_column(
        conn, "sessions", "time_adjusted_seconds", "time_adjusted_seconds INTEGER NOT NULL DEFAULT 0"
    )
    _ensure_column(conn, "rooms", "intro_video_path_fr", "intro_video_path_fr TEXT")


def init_db() -> None:
    conn = get_connection()
    conn.executescript(SCHEMA)
    _migrate_schema(conn)
    conn.commit()


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------

def _row_to_room(row: sqlite3.Row) -> Room:
    return Room(
        id=row["id"],
        name=row["name"],
        duration_seconds=row["duration_seconds"],
        intro_video_path=row["intro_video_path"],
        ending_video_path=row["ending_video_path"],
        wins=row["wins"],
        losses=row["losses"],
        intro_video_path_fr=row["intro_video_path_fr"],
    )


def list_rooms() -> list[Room]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM rooms ORDER BY name").fetchall()
    return [_row_to_room(row) for row in rows]


def get_room(room_id: int) -> Optional[Room]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    return _row_to_room(row) if row else None


def create_room(
    name: str,
    duration_seconds: int = 3600,
    intro_video_path: Optional[str] = None,
    ending_video_path: Optional[str] = None,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO rooms (name, duration_seconds, intro_video_path, ending_video_path) "
        "VALUES (?, ?, ?, ?)",
        (name, duration_seconds, intro_video_path, ending_video_path),
    )
    conn.commit()
    return cur.lastrowid


def update_room(room_id: int, **fields) -> None:
    if not fields:
        return
    allowed = {"name", "duration_seconds", "intro_video_path", "ending_video_path", "intro_video_path_fr"}
    columns = [key for key in fields if key in allowed]
    if not columns:
        return
    assignments = ", ".join(f"{col} = ?" for col in columns)
    values = [fields[col] for col in columns]
    conn = get_connection()
    conn.execute(f"UPDATE rooms SET {assignments} WHERE id = ?", (*values, room_id))
    conn.commit()


def delete_room(room_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    conn.commit()


def record_result(room_id: int, won: bool) -> None:
    """Increment the room's win or loss counter."""
    column = "wins" if won else "losses"
    conn = get_connection()
    conn.execute(f"UPDATE rooms SET {column} = {column} + 1 WHERE id = ?", (room_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Objectives
# ---------------------------------------------------------------------------

def _row_to_objective(row: sqlite3.Row, completed: bool = False) -> Objective:
    return Objective(
        id=row["id"],
        room_id=row["room_id"],
        title=row["title"],
        order_index=row["order_index"],
        checkpoint_video_path=row["checkpoint_video_path"],
        completed=completed,
        code=row["code"],
        description=row["description"],
    )


def get_objective_progress_map(room_id: int) -> dict[int, bool]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT objective_id, completed FROM objective_progress WHERE room_id = ?",
        (room_id,),
    ).fetchall()
    return {row["objective_id"]: bool(row["completed"]) for row in rows}


def list_objectives(room_id: int) -> list[Objective]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM objectives WHERE room_id = ? ORDER BY order_index", (room_id,)
    ).fetchall()
    progress = get_objective_progress_map(room_id)
    return [_row_to_objective(row, progress.get(row["id"], False)) for row in rows]


def get_objective(objective_id: int) -> Optional[Objective]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM objectives WHERE id = ?", (objective_id,)
    ).fetchone()
    if not row:
        return None
    progress = get_objective_progress_map(row["room_id"])
    return _row_to_objective(row, progress.get(row["id"], False))


def add_objective(
    room_id: int, title: str, checkpoint_video_path: Optional[str] = None
) -> int:
    conn = get_connection()
    next_index = conn.execute(
        "SELECT COALESCE(MAX(order_index) + 1, 0) FROM objectives WHERE room_id = ?",
        (room_id,),
    ).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO objectives (room_id, title, order_index, checkpoint_video_path) "
        "VALUES (?, ?, ?, ?)",
        (room_id, title, next_index, checkpoint_video_path),
    )
    conn.commit()
    return cur.lastrowid


def update_objective(objective_id: int, **fields) -> None:
    if not fields:
        return
    allowed = {"title", "checkpoint_video_path", "order_index", "code", "description"}
    columns = [key for key in fields if key in allowed]
    if not columns:
        return
    assignments = ", ".join(f"{col} = ?" for col in columns)
    values = [fields[col] for col in columns]
    conn = get_connection()
    conn.execute(
        f"UPDATE objectives SET {assignments} WHERE id = ?", (*values, objective_id)
    )
    conn.commit()


def delete_objective(objective_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM objectives WHERE id = ?", (objective_id,))
    conn.commit()


def move_objective(objective_id: int, direction: int) -> None:
    """Swap order_index with the neighboring objective. direction: -1 (up) or +1 (down)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT room_id, order_index FROM objectives WHERE id = ?", (objective_id,)
    ).fetchone()
    if not row:
        return
    room_id, order_index = row["room_id"], row["order_index"]
    if direction < 0:
        neighbor = conn.execute(
            "SELECT id, order_index FROM objectives WHERE room_id = ? AND order_index < ? "
            "ORDER BY order_index DESC LIMIT 1",
            (room_id, order_index),
        ).fetchone()
    else:
        neighbor = conn.execute(
            "SELECT id, order_index FROM objectives WHERE room_id = ? AND order_index > ? "
            "ORDER BY order_index ASC LIMIT 1",
            (room_id, order_index),
        ).fetchone()
    if not neighbor:
        return
    conn.execute(
        "UPDATE objectives SET order_index = ? WHERE id = ?",
        (neighbor["order_index"], objective_id),
    )
    conn.execute(
        "UPDATE objectives SET order_index = ? WHERE id = ?",
        (order_index, neighbor["id"]),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Hints
# ---------------------------------------------------------------------------

def _row_to_hint(row: sqlite3.Row) -> Hint:
    return Hint(
        id=row["id"],
        objective_id=row["objective_id"],
        text=row["text"],
        order_index=row["order_index"],
        rating=row["rating"],
        video_path=row["video_path"],
    )


def list_hints(objective_id: int) -> list[Hint]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM hints WHERE objective_id = ? ORDER BY order_index",
        (objective_id,),
    ).fetchall()
    return [_row_to_hint(row) for row in rows]


def add_hint(
    objective_id: int,
    text: str,
    rating: int = 0,
    video_path: Optional[str] = None,
) -> int:
    conn = get_connection()
    next_index = conn.execute(
        "SELECT COALESCE(MAX(order_index) + 1, 0) FROM hints WHERE objective_id = ?",
        (objective_id,),
    ).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO hints (objective_id, text, order_index, rating, video_path) "
        "VALUES (?, ?, ?, ?, ?)",
        (objective_id, text, next_index, rating, video_path),
    )
    conn.commit()
    return cur.lastrowid


def update_hint(hint_id: int, **fields) -> None:
    if not fields:
        return
    allowed = {"text", "rating", "video_path", "order_index"}
    columns = [key for key in fields if key in allowed]
    if not columns:
        return
    assignments = ", ".join(f"{col} = ?" for col in columns)
    values = [fields[col] for col in columns]
    conn = get_connection()
    conn.execute(f"UPDATE hints SET {assignments} WHERE id = ?", (*values, hint_id))
    conn.commit()


def delete_hint(hint_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM hints WHERE id = ?", (hint_id,))
    conn.commit()


def move_hint(hint_id: int, direction: int) -> None:
    """Swap order_index with the neighboring hint. direction: -1 (up) or +1 (down)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT objective_id, order_index FROM hints WHERE id = ?", (hint_id,)
    ).fetchone()
    if not row:
        return
    objective_id, order_index = row["objective_id"], row["order_index"]
    if direction < 0:
        neighbor = conn.execute(
            "SELECT id, order_index FROM hints WHERE objective_id = ? AND order_index < ? "
            "ORDER BY order_index DESC LIMIT 1",
            (objective_id, order_index),
        ).fetchone()
    else:
        neighbor = conn.execute(
            "SELECT id, order_index FROM hints WHERE objective_id = ? AND order_index > ? "
            "ORDER BY order_index ASC LIMIT 1",
            (objective_id, order_index),
        ).fetchone()
    if not neighbor:
        return
    conn.execute(
        "UPDATE hints SET order_index = ? WHERE id = ?",
        (neighbor["order_index"], hint_id),
    )
    conn.execute(
        "UPDATE hints SET order_index = ? WHERE id = ?",
        (order_index, neighbor["id"]),
    )
    conn.commit()


def reorder_hints(objective_id: int, ordered_ids: list[int]) -> None:
    """Set order_index for each hint id in `ordered_ids` to its position."""
    conn = get_connection()
    for index, hint_id in enumerate(ordered_ids):
        conn.execute(
            "UPDATE hints SET order_index = ? WHERE id = ? AND objective_id = ?",
            (index, hint_id, objective_id),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Clues
# ---------------------------------------------------------------------------

def _row_to_clue(row: sqlite3.Row, checked: bool = False) -> Clue:
    return Clue(
        id=row["id"],
        room_id=row["room_id"],
        label=row["label"],
        order_index=row["order_index"],
        checked=checked,
    )


def get_clue_progress_map(room_id: int) -> dict[int, bool]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT clue_id, checked FROM clue_progress WHERE room_id = ?", (room_id,)
    ).fetchall()
    return {row["clue_id"]: bool(row["checked"]) for row in rows}


def list_clues(room_id: int) -> list[Clue]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM clues WHERE room_id = ? ORDER BY order_index", (room_id,)
    ).fetchall()
    progress = get_clue_progress_map(room_id)
    return [_row_to_clue(row, progress.get(row["id"], False)) for row in rows]


def add_clue(room_id: int, label: str) -> int:
    conn = get_connection()
    next_index = conn.execute(
        "SELECT COALESCE(MAX(order_index) + 1, 0) FROM clues WHERE room_id = ?",
        (room_id,),
    ).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO clues (room_id, label, order_index) VALUES (?, ?, ?)",
        (room_id, label, next_index),
    )
    conn.commit()
    return cur.lastrowid


def update_clue(clue_id: int, label: str) -> None:
    conn = get_connection()
    conn.execute("UPDATE clues SET label = ? WHERE id = ?", (label, clue_id))
    conn.commit()


def delete_clue(clue_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM clues WHERE id = ?", (clue_id,))
    conn.commit()


def move_clue(clue_id: int, direction: int) -> None:
    """Swap order_index with the neighboring clue. direction: -1 (up) or +1 (down)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT room_id, order_index FROM clues WHERE id = ?", (clue_id,)
    ).fetchone()
    if not row:
        return
    room_id, order_index = row["room_id"], row["order_index"]
    if direction < 0:
        neighbor = conn.execute(
            "SELECT id, order_index FROM clues WHERE room_id = ? AND order_index < ? "
            "ORDER BY order_index DESC LIMIT 1",
            (room_id, order_index),
        ).fetchone()
    else:
        neighbor = conn.execute(
            "SELECT id, order_index FROM clues WHERE room_id = ? AND order_index > ? "
            "ORDER BY order_index ASC LIMIT 1",
            (room_id, order_index),
        ).fetchone()
    if not neighbor:
        return
    conn.execute(
        "UPDATE clues SET order_index = ? WHERE id = ?",
        (neighbor["order_index"], clue_id),
    )
    conn.execute(
        "UPDATE clues SET order_index = ? WHERE id = ?",
        (order_index, neighbor["id"]),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Sessions / live progress
# ---------------------------------------------------------------------------

def _row_to_session(row: sqlite3.Row) -> SessionState:
    return SessionState(
        room_id=row["room_id"],
        status=row["status"],
        remaining_seconds=row["remaining_seconds"],
        messages_sent=row["messages_sent"],
        time_adjusted_seconds=row["time_adjusted_seconds"],
        updated_at=row["updated_at"],
    )


def get_session(room_id: int) -> SessionState:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM sessions WHERE room_id = ?", (room_id,)
    ).fetchone()
    if row:
        return _row_to_session(row)

    room = get_room(room_id)
    remaining = room.duration_seconds if room else 0
    save_session(room_id, "idle", remaining)
    return SessionState(room_id=room_id, status="idle", remaining_seconds=remaining)


def save_session(
    room_id: int,
    status: str,
    remaining_seconds: int,
    messages_sent: Optional[int] = None,
    time_adjusted_seconds: Optional[int] = None,
) -> None:
    conn = get_connection()
    if messages_sent is None or time_adjusted_seconds is None:
        existing = conn.execute(
            "SELECT messages_sent, time_adjusted_seconds FROM sessions WHERE room_id = ?",
            (room_id,),
        ).fetchone()
        if messages_sent is None:
            messages_sent = existing["messages_sent"] if existing else 0
        if time_adjusted_seconds is None:
            time_adjusted_seconds = existing["time_adjusted_seconds"] if existing else 0
    conn.execute(
        "INSERT INTO sessions (room_id, status, remaining_seconds, messages_sent, "
        "time_adjusted_seconds, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(room_id) DO UPDATE SET status = excluded.status, "
        "remaining_seconds = excluded.remaining_seconds, "
        "messages_sent = excluded.messages_sent, "
        "time_adjusted_seconds = excluded.time_adjusted_seconds, "
        "updated_at = excluded.updated_at",
        (room_id, status, remaining_seconds, messages_sent, time_adjusted_seconds, datetime.now().isoformat()),
    )
    conn.commit()


def start_session(room_id: int, status: str = "running") -> SessionState:
    """Reset the session for a fresh game: full duration, and clear all
    objective/clue progress ticks and per-session stats. `status` controls
    whether the timer starts immediately ("running") or waits for the game
    master to press "Start game" ("idle")."""
    room = get_room(room_id)
    duration = room.duration_seconds if room else 0
    conn = get_connection()
    conn.execute("DELETE FROM objective_progress WHERE room_id = ?", (room_id,))
    conn.execute("DELETE FROM clue_progress WHERE room_id = ?", (room_id,))
    conn.commit()
    save_session(room_id, status, duration, messages_sent=0, time_adjusted_seconds=0)
    return SessionState(room_id=room_id, status=status, remaining_seconds=duration)


def increment_session_messages(room_id: int) -> int:
    """Increment and persist the session's messages-sent counter, returning the new count."""
    session = get_session(room_id)
    new_count = session.messages_sent + 1
    save_session(room_id, session.status, session.remaining_seconds, messages_sent=new_count)
    return new_count


def adjust_session_time(room_id: int, delta_seconds: int) -> SessionState:
    """Apply a +/- adjustment to the session's remaining time (clamped to >= 0)
    and accumulate the net adjustment for the "Time Adjusted" stat."""
    session = get_session(room_id)
    remaining = max(0, session.remaining_seconds + delta_seconds)
    time_adjusted = session.time_adjusted_seconds + delta_seconds
    save_session(room_id, session.status, remaining, time_adjusted_seconds=time_adjusted)
    return SessionState(
        room_id=room_id,
        status=session.status,
        remaining_seconds=remaining,
        messages_sent=session.messages_sent,
        time_adjusted_seconds=time_adjusted,
    )


def set_objective_progress(room_id: int, objective_id: int, completed: bool) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO objective_progress (room_id, objective_id, completed) "
        "VALUES (?, ?, ?) "
        "ON CONFLICT(room_id, objective_id) DO UPDATE SET completed = excluded.completed",
        (room_id, objective_id, int(completed)),
    )
    conn.commit()


def set_clue_progress(room_id: int, clue_id: int, checked: bool) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO clue_progress (room_id, clue_id, checked) "
        "VALUES (?, ?, ?) "
        "ON CONFLICT(room_id, clue_id) DO UPDATE SET checked = excluded.checked",
        (room_id, clue_id, int(checked)),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Per-room audio mixer settings
# ---------------------------------------------------------------------------

def _row_to_audio_settings(row: sqlite3.Row) -> RoomAudioSettings:
    return RoomAudioSettings(
        room_id=row["room_id"],
        alert_volume=row["alert_volume"],
        alert_muted=bool(row["alert_muted"]),
        alert_path=row["alert_path"],
        game_music_volume=row["game_music_volume"],
        game_music_muted=bool(row["game_music_muted"]),
        game_music_path=row["game_music_path"],
        success_volume=row["success_volume"],
        success_muted=bool(row["success_muted"]),
        success_path=row["success_path"],
        fail_volume=row["fail_volume"],
        fail_muted=bool(row["fail_muted"]),
        fail_path=row["fail_path"],
        video_volume=row["video_volume"],
        video_muted=bool(row["video_muted"]),
        master_volume=row["master_volume"],
        master_muted=bool(row["master_muted"]),
    )


def get_audio_settings(room_id: int) -> RoomAudioSettings:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM room_audio_settings WHERE room_id = ?", (room_id,)
    ).fetchone()
    if row:
        return _row_to_audio_settings(row)
    conn.execute("INSERT INTO room_audio_settings (room_id) VALUES (?)", (room_id,))
    conn.commit()
    return RoomAudioSettings(room_id=room_id)


def update_audio_settings(room_id: int, **fields) -> None:
    if not fields:
        return
    allowed = {
        "alert_volume", "alert_muted", "alert_path",
        "game_music_volume", "game_music_muted", "game_music_path",
        "success_volume", "success_muted", "success_path",
        "fail_volume", "fail_muted", "fail_path",
        "video_volume", "video_muted",
        "master_volume", "master_muted",
    }
    columns = [key for key in fields if key in allowed]
    if not columns:
        return
    get_audio_settings(room_id)
    values = [int(fields[col]) if col.endswith("_muted") else fields[col] for col in columns]
    assignments = ", ".join(f"{col} = ?" for col in columns)
    conn = get_connection()
    conn.execute(
        f"UPDATE room_audio_settings SET {assignments} WHERE room_id = ?", (*values, room_id)
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Per-video volume overrides
# ---------------------------------------------------------------------------

def get_video_volume(room_id: int, video_path: str) -> tuple[int, bool]:
    conn = get_connection()
    row = conn.execute(
        "SELECT volume, muted FROM room_video_volumes WHERE room_id = ? AND video_path = ?",
        (room_id, video_path),
    ).fetchone()
    if row:
        return row["volume"], bool(row["muted"])
    return 100, False


def update_video_volume(room_id: int, video_path: str, **fields) -> None:
    allowed = {"volume", "muted"}
    columns = [key for key in fields if key in allowed]
    if not columns:
        return
    volume, muted = get_video_volume(room_id, video_path)
    if "volume" in fields:
        volume = int(fields["volume"])
    if "muted" in fields:
        muted = bool(fields["muted"])
    conn = get_connection()
    conn.execute(
        "INSERT INTO room_video_volumes (room_id, video_path, volume, muted) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(room_id, video_path) DO UPDATE SET volume = excluded.volume, muted = excluded.muted",
        (room_id, video_path, volume, int(muted)),
    )
    conn.commit()
