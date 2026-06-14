"""Offscreen smoke test for the dashboard and room editor dialogs.

Run with: QT_QPA_PLATFORM=offscreen python3 tests/test_dashboard_offscreen.py
(this script also sets the env var itself as a fallback).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QPushButton

from erm import database
from erm.dashboard import MainDashboardWindow, NewRoomDialog, RoomCard
from erm.room_editor import HintEditorDialog, ObjectiveEditorDialog, RoomEditorDialog


def main():
    with tempfile.TemporaryDirectory() as tmp:
        database.DB_PATH = Path(tmp) / "test.db"
        database._connection = None
        database.init_db()

        app = QApplication.instance() or QApplication(sys.argv)

        room_id = database.create_room("Test Room", duration_seconds=1800)
        obj_id = database.add_objective(
            room_id, "Find the key", checkpoint_video_path="/tmp/cp.mp4"
        )
        database.add_hint(obj_id, "Look in the drawer", rating=3)
        database.add_clue(room_id, "Clue A")
        database.add_clue(room_id, "Clue B")

        # Dashboard: card grid view
        dashboard = MainDashboardWindow()
        assert len(dashboard._rooms_cache) == 1
        assert dashboard._rooms_cache[0].id == room_id

        card = dashboard.grid_layout.itemAt(0).widget()
        assert isinstance(card, RoomCard)
        assert card.room.id == room_id

        # Table view toggle
        dashboard._toggle_view()
        assert dashboard.stack.currentWidget() is dashboard.table
        assert dashboard.table.rowCount() == 1
        assert dashboard.table.item(0, 0).text() == "Test Room"
        dashboard._toggle_view()
        assert dashboard.stack.currentWidget() is dashboard.scroll_area

        # New Room dialog
        new_room_dialog = NewRoomDialog()
        new_room_dialog.name_edit.setText("Second Room")
        idx = new_room_dialog.duration_combo.findData(45)
        new_room_dialog.duration_combo.setCurrentIndex(idx)
        name, minutes = new_room_dialog.values()
        assert name == "Second Room"
        assert minutes == 45
        new_room_dialog.close()

        # Win/loss stats reflected on the card after a refresh
        database.record_result(room_id, won=True)
        dashboard.refresh_rooms()
        card = dashboard.grid_layout.itemAt(0).widget()
        assert card.room.wins == 1

        # Room editor dialog (constructed but not exec'd, to avoid a blocking modal loop)
        editor = RoomEditorDialog(room_id)
        assert editor.name_edit.text() == "Test Room"
        assert editor.duration_spin.value() == 30
        assert editor.objectives_list.count() == 1
        assert editor.clues_list.count() == 2

        # "OK" button (no separate "Close" with unsaved-changes ambiguity)
        ok_button = editor.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
        assert ok_button is not None

        # Field-edit handlers (none of these pop a dialog)
        editor.name_edit.setText("Renamed Room")
        editor._on_name_edited()
        assert database.get_room(room_id).name == "Renamed Room"

        editor.duration_spin.setValue(45)
        editor._on_duration_changed()
        assert database.get_room(room_id).duration_seconds == 45 * 60

        editor._clear_intro_video()
        assert database.get_room(room_id).intro_video_path is None

        # French briefing video (separate from the English one)
        assert editor.intro_fr_label.text() == "(none)"
        database.update_room(room_id, intro_video_path_fr="/tmp/intro_fr.mp4")
        editor._load()
        assert editor.intro_fr_label.text() == "intro_fr.mp4"

        editor._clear_intro_video_fr()
        assert database.get_room(room_id).intro_video_path_fr is None
        assert editor.intro_fr_label.text() == "(none)"

        # Objective editor dialog: code, description, hints
        obj_editor = ObjectiveEditorDialog(obj_id)
        assert obj_editor.title_edit.text() == "Find the key"
        assert obj_editor.hints_list.count() == 1

        obj_ok_button = obj_editor.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
        assert obj_ok_button is not None

        obj_editor.code_edit.setText("4242")
        obj_editor._on_code_edited()
        assert database.get_objective(obj_id).code == "4242"

        obj_editor.description_edit.setPlainText("It's hidden somewhere clever.")
        obj_editor._on_description_edited()
        assert database.get_objective(obj_id).description == "It's hidden somewhere clever."

        obj_editor._clear_checkpoint_video()
        assert database.get_objective(obj_id).checkpoint_video_path is None

        # Hint editor dialog: text, rating and an optional video
        hint_dialog = HintEditorDialog(text="Use the UV light", rating=5, video_path="/tmp/h.mp4")
        text, rating, video_path = hint_dialog.values()
        assert text == "Use the UV light"
        assert rating == 5
        assert video_path == "/tmp/h.mp4"
        hint_dialog.close()

        new_hint_id = database.add_hint(obj_id, text, rating=rating, video_path=video_path)
        obj_editor._refresh_hints()
        assert obj_editor.hints_list.count() == 2

        database.move_hint(new_hint_id, -1)
        hints = database.list_hints(obj_id)
        assert hints[0].id == new_hint_id

        database.delete_hint(new_hint_id)
        obj_editor._refresh_hints()
        assert obj_editor.hints_list.count() == 1

        # Per-objective "+ Cue" quick-add button on the RoomEditorDialog's
        # objectives list opens HintEditorDialog directly and adds the hint
        editor._refresh_objectives(select_id=obj_id)
        item = editor.objectives_list.item(0)
        item_widget = editor.objectives_list.itemWidget(item)
        add_cue_buttons = [
            b for b in item_widget.findChildren(QPushButton) if b.text() == "+ Cue"
        ]
        assert len(add_cue_buttons) == 1

        original_hint_exec = HintEditorDialog.exec

        def _fake_hint_exec(self):
            self.text_edit.setText("Quick cue")
            self.rating_spin.setValue(2)
            return QDialog.DialogCode.Accepted

        HintEditorDialog.exec = _fake_hint_exec
        try:
            editor._quick_add_cue(obj_id)
        finally:
            HintEditorDialog.exec = original_hint_exec

        hints = database.list_hints(obj_id)
        assert any(h.text == "Quick cue" and h.rating == 2 for h in hints)

        obj_editor._refresh_hints()
        assert obj_editor.hints_list.count() == 2

        # Control Panel wiring from the dashboard (lazy construction + cleanup)
        dashboard.open_control_panel(room_id)
        assert room_id in dashboard.active_control_panels
        dashboard._on_control_panel_closed(room_id)
        assert room_id not in dashboard.active_control_panels

        editor.close()
        obj_editor.close()
        dashboard.close()

    print("dashboard/room_editor offscreen smoke test: OK")


if __name__ == "__main__":
    main()
