"""Headless smoke test for erm.database. Run with plain python3."""

import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from erm import database

OLD_SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 3600,
    intro_video_path TEXT,
    ending_video_path TEXT
);

CREATE TABLE IF NOT EXISTS objectives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0,
    checkpoint_video_path TEXT
);

CREATE TABLE IF NOT EXISTS hints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    objective_id INTEGER NOT NULL REFERENCES objectives(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0
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
"""


def test_migration(tmp: str) -> None:
    db_path = Path(tmp) / "old.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(OLD_SCHEMA)
    conn.execute(
        "INSERT INTO rooms (name, duration_seconds) VALUES (?, ?)", ("Old Room", 1800)
    )
    conn.commit()
    conn.close()

    database.DB_PATH = db_path
    database._connection = None
    database.init_db()

    room = database.list_rooms()[0]
    assert room.wins == 0
    assert room.losses == 0
    assert room.intro_video_path_fr is None
    assert room.background_image_path is None

    database.update_room(room.id, intro_video_path_fr="/videos/intro_fr.mp4")
    assert database.get_room(room.id).intro_video_path_fr == "/videos/intro_fr.mp4"

    database.update_room(room.id, background_image_path="/images/bg.png")
    assert database.get_room(room.id).background_image_path == "/images/bg.png"

    obj_id = database.add_objective(room.id, "Legacy objective")
    objective = database.get_objective(obj_id)
    assert objective.code is None
    assert objective.description is None

    hint_id = database.add_hint(obj_id, "Legacy hint")
    hint = database.list_hints(obj_id)[0]
    assert hint.rating == 0
    assert hint.video_path is None

    session = database.get_session(room.id)
    assert session.messages_sent == 0
    assert session.time_adjusted_seconds == 0

    print("database.py migration test: OK")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        database.DB_PATH = Path(tmp) / "test.db"
        database._connection = None
        database.init_db()

        # Rooms
        room_id = database.create_room(
            "Pharaoh's Tomb", duration_seconds=3000, intro_video_path="/videos/intro.mp4"
        )
        rooms = database.list_rooms()
        assert len(rooms) == 1 and rooms[0].name == "Pharaoh's Tomb"
        assert rooms[0].wins == 0 and rooms[0].losses == 0
        assert rooms[0].intro_video_path_fr is None
        assert rooms[0].background_image_path is None

        database.update_room(
            room_id, name="Pharaoh's Tomb (Hard)", duration_seconds=3600,
            intro_video_path_fr="/videos/intro_fr.mp4",
            background_image_path="/images/tomb_bg.png",
        )
        room = database.get_room(room_id)
        assert room.name == "Pharaoh's Tomb (Hard)"
        assert room.duration_seconds == 3600
        assert room.intro_video_path_fr == "/videos/intro_fr.mp4"
        assert room.background_image_path == "/images/tomb_bg.png"

        database.update_room(room_id, background_image_path=None)
        assert database.get_room(room_id).background_image_path is None

        # Win/loss recording
        database.record_result(room_id, won=True)
        database.record_result(room_id, won=False)
        database.record_result(room_id, won=True)
        room = database.get_room(room_id)
        assert room.wins == 2 and room.losses == 1

        # Objectives + code/description
        obj1 = database.add_objective(
            room_id, "Find the amulet", checkpoint_video_path="/videos/cp1.mp4"
        )
        obj2 = database.add_objective(room_id, "Open the sarcophagus")
        objectives = database.list_objectives(room_id)
        assert [o.title for o in objectives] == ["Find the amulet", "Open the sarcophagus"]
        assert all(o.completed is False for o in objectives)

        database.update_objective(obj1, code="1279", description="A golden amulet.")
        objective = database.get_objective(obj1)
        assert objective.code == "1279"
        assert objective.description == "A golden amulet."

        # Hints: rating, video_path, update, move, reorder
        hint1 = database.add_hint(obj1, "Look under the rug", rating=2)
        hint2 = database.add_hint(obj1, "Check behind the painting", video_path="/videos/h2.mp4")
        hint3 = database.add_hint(obj1, "Ask the guard")
        hints = database.list_hints(obj1)
        assert [h.text for h in hints] == [
            "Look under the rug",
            "Check behind the painting",
            "Ask the guard",
        ]
        assert hints[0].rating == 2
        assert hints[1].video_path == "/videos/h2.mp4"

        database.update_hint(hint1, text="Look under the red rug", rating=4)
        hint = database.list_hints(obj1)[0]
        assert hint.text == "Look under the red rug"
        assert hint.rating == 4

        database.move_hint(hint2, -1)  # move "Check behind the painting" up
        hints = database.list_hints(obj1)
        assert [h.id for h in hints] == [hint2, hint1, hint3]

        database.reorder_hints(obj1, [hint3, hint1, hint2])
        hints = database.list_hints(obj1)
        assert [h.id for h in hints] == [hint3, hint1, hint2]

        database.delete_hint(hint3)
        assert len(database.list_hints(obj1)) == 2

        # Clues (dynamic, unlimited)
        clue_ids = [database.add_clue(room_id, f"Clue {i}") for i in range(1, 5)]
        clues = database.list_clues(room_id)
        assert [c.label for c in clues] == ["Clue 1", "Clue 2", "Clue 3", "Clue 4"]
        assert all(c.checked is False for c in clues)

        database.move_clue(clue_ids[1], -1)  # move "Clue 2" up
        clues = database.list_clues(room_id)
        assert [c.label for c in clues] == ["Clue 2", "Clue 1", "Clue 3", "Clue 4"]

        # Session lifecycle
        session = database.get_session(room_id)
        assert session.status == "idle"
        assert session.remaining_seconds == 3600
        assert session.messages_sent == 0
        assert session.time_adjusted_seconds == 0

        session = database.start_session(room_id)
        assert session.status == "running"
        assert session.remaining_seconds == 3600

        database.save_session(room_id, "paused", 1800)
        session = database.get_session(room_id)
        assert session.status == "paused"
        assert session.remaining_seconds == 1800

        # Messages-sent counter
        count = database.increment_session_messages(room_id)
        assert count == 1
        count = database.increment_session_messages(room_id)
        assert count == 2
        session = database.get_session(room_id)
        assert session.messages_sent == 2

        # Time adjustment, including clamping at zero
        session = database.adjust_session_time(room_id, 120)
        assert session.remaining_seconds == 1920
        assert session.time_adjusted_seconds == 120

        session = database.adjust_session_time(room_id, -10000)
        assert session.remaining_seconds == 0
        assert session.time_adjusted_seconds == -9880

        # Progress tracking
        database.set_objective_progress(room_id, obj1, True)
        objectives = database.list_objectives(room_id)
        progress = {o.id: o.completed for o in objectives}
        assert progress[obj1] is True
        assert progress[obj2] is False

        database.set_clue_progress(room_id, clue_ids[0], True)
        clues = database.list_clues(room_id)
        checked = {c.id: c.checked for c in clues}
        assert checked[clue_ids[0]] is True

        # start_session should clear progress and per-session stats
        session = database.start_session(room_id)
        assert session.remaining_seconds == 3600
        objectives = database.list_objectives(room_id)
        assert all(o.completed is False for o in objectives)
        clues = database.list_clues(room_id)
        assert all(c.checked is False for c in clues)
        session = database.get_session(room_id)
        assert session.messages_sent == 0
        assert session.time_adjusted_seconds == 0

        # Audio settings: get-or-create defaults
        audio_settings = database.get_audio_settings(room_id)
        assert audio_settings.room_id == room_id
        assert audio_settings.alert_volume == 100
        assert audio_settings.alert_muted is False
        assert audio_settings.alert_path is None
        assert audio_settings.game_music_volume == 100
        assert audio_settings.game_music_muted is False
        assert audio_settings.game_music_path is None
        assert audio_settings.success_volume == 100
        assert audio_settings.fail_volume == 100
        assert audio_settings.video_volume == 100
        assert audio_settings.video_muted is False
        assert audio_settings.master_volume == 100
        assert audio_settings.master_muted is False

        # Audio settings: persisted updates
        database.update_audio_settings(
            room_id,
            alert_volume=60,
            alert_muted=True,
            alert_path="/sounds/alert.wav",
            game_music_path="/sounds/music.mp3",
            master_volume=80,
        )
        audio_settings = database.get_audio_settings(room_id)
        assert audio_settings.alert_volume == 60
        assert audio_settings.alert_muted is True
        assert audio_settings.alert_path == "/sounds/alert.wav"
        assert audio_settings.game_music_path == "/sounds/music.mp3"
        assert audio_settings.master_volume == 80

        # Per-video volume overrides: get-or-create defaults
        assert database.get_video_volume(room_id, "/videos/cp1.mp4") == (100, False)

        # Persisted updates, independent per field
        database.update_video_volume(room_id, "/videos/cp1.mp4", volume=50)
        assert database.get_video_volume(room_id, "/videos/cp1.mp4") == (50, False)

        database.update_video_volume(room_id, "/videos/cp1.mp4", muted=True)
        assert database.get_video_volume(room_id, "/videos/cp1.mp4") == (50, True)

        # Persisted updates are independent per video path
        assert database.get_video_volume(room_id, "/videos/h2.mp4") == (100, False)
        database.update_video_volume(room_id, "/videos/h2.mp4", volume=75, muted=True)
        assert database.get_video_volume(room_id, "/videos/h2.mp4") == (75, True)
        assert database.get_video_volume(room_id, "/videos/cp1.mp4") == (50, True)

        # Cascading deletes
        database.delete_objective(obj1)
        assert database.get_objective(obj1) is None
        assert database.list_hints(obj1) == []

        database.delete_room(room_id)
        assert database.list_rooms() == []

    print("database.py smoke test: OK")

    with tempfile.TemporaryDirectory() as tmp:
        test_migration(tmp)


if __name__ == "__main__":
    main()
