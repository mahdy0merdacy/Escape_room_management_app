"""Room template editor: rooms, objectives, hints, clues and the
intro/checkpoint/ending video paths. All edits write straight through to
the database, so nothing is lost if the dialog is just closed.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from erm import database
from erm.constants import AUDIO_FILE_FILTER, IMAGE_FILE_FILTER, MEDIA_FILE_FILTER, RATING_MAX, VIDEO_FILE_FILTER
from erm.widgets.rating import RatingDots


def _video_label_text(path: Optional[str]) -> str:
    return Path(path).name if path else "(none)"


class HintEditorDialog(QDialog):
    """Add/edit a single hint: its text, a 0-N rating, and an optional video
    the game master can play in the player window when giving this hint."""

    def __init__(
        self,
        parent=None,
        text: str = "",
        rating: int = 0,
        video_path: Optional[str] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Clue / Hint")
        self._video_path = video_path
        self._build_ui()
        self.text_edit.setText(text)
        self.rating_spin.setValue(rating)
        self._update_video_label()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Text:"))
        self.text_edit = QLineEdit()
        layout.addWidget(self.text_edit)

        rating_row = QHBoxLayout()
        rating_row.addWidget(QLabel("Rating:"))
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, RATING_MAX)
        self.rating_spin.valueChanged.connect(self._on_rating_changed)
        rating_row.addWidget(self.rating_spin)
        self.rating_preview = RatingDots(0)
        rating_row.addWidget(self.rating_preview)
        rating_row.addStretch(1)
        layout.addLayout(rating_row)

        video_group = QGroupBox("Video (optional, played in the player window)")
        video_layout = QHBoxLayout(video_group)
        self.video_label = QLabel("(none)")
        video_layout.addWidget(self.video_label, stretch=1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_video)
        video_layout.addWidget(browse_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_video)
        video_layout.addWidget(clear_btn)
        layout.addWidget(video_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_rating_changed(self, value: int) -> None:
        self.rating_preview.set_rating(value)

    def _browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Hint Video / Audio", "", MEDIA_FILE_FILTER)
        if path:
            self._video_path = path
            self._update_video_label()

    def _clear_video(self) -> None:
        self._video_path = None
        self._update_video_label()

    def _update_video_label(self) -> None:
        self.video_label.setText(_video_label_text(self._video_path))
        self.video_label.setToolTip(self._video_path or "")

    def values(self) -> tuple[str, int, Optional[str]]:
        return self.text_edit.text().strip(), self.rating_spin.value(), self._video_path


class ObjectiveEditorDialog(QDialog):
    """Edit a single objective: title, code, description, checkpoint video,
    and its rated clue/hint cards."""

    def __init__(self, objective_id: int, parent=None):
        super().__init__(parent)
        self.objective_id = objective_id
        self.setWindowTitle("Edit Objective")
        self.resize(560, 620)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.editingFinished.connect(self._on_title_edited)
        title_row.addWidget(self.title_edit, stretch=1)
        title_row.addWidget(QLabel("Code:"))
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g. 1279")
        self.code_edit.setMaximumWidth(120)
        self.code_edit.editingFinished.connect(self._on_code_edited)
        title_row.addWidget(self.code_edit)
        layout.addLayout(title_row)

        layout.addWidget(QLabel("Description (shown to the game master in the Control Panel):"))
        self.description_edit = QPlainTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.textChanged.connect(self._on_description_edited)
        layout.addWidget(self.description_edit)

        video_group = QGroupBox("Checkpoint Video (reward shown when this objective is solved)")
        video_layout = QHBoxLayout(video_group)
        self.video_label = QLabel("(none)")
        video_layout.addWidget(self.video_label, stretch=1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_checkpoint_video)
        video_layout.addWidget(browse_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_checkpoint_video)
        video_layout.addWidget(clear_btn)
        layout.addWidget(video_group)

        hints_group = QGroupBox(
            "Clues / Hints (rating + optional video, shown live in the Control Panel)"
        )
        hints_layout = QVBoxLayout(hints_group)
        self.hints_list = QListWidget()
        self.hints_list.itemDoubleClicked.connect(lambda _: self._edit_hint())
        hints_layout.addWidget(self.hints_list)
        hint_btn_row = QHBoxLayout()
        for label, handler in (
            ("Add", self._add_hint),
            ("Edit", self._edit_hint),
            ("Delete", self._delete_hint),
            ("Up", self._move_hint_up),
            ("Down", self._move_hint_down),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            hint_btn_row.addWidget(btn)
        hints_layout.addLayout(hint_btn_row)
        layout.addWidget(hints_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _load(self) -> None:
        objective = database.get_objective(self.objective_id)
        if objective is None:
            return
        self.title_edit.setText(objective.title)
        self.code_edit.setText(objective.code or "")
        self.description_edit.blockSignals(True)
        self.description_edit.setPlainText(objective.description or "")
        self.description_edit.blockSignals(False)
        self.video_label.setText(_video_label_text(objective.checkpoint_video_path))
        self.video_label.setToolTip(objective.checkpoint_video_path or "")
        self._refresh_hints()

    def _on_title_edited(self) -> None:
        title = self.title_edit.text().strip()
        if title:
            database.update_objective(self.objective_id, title=title)

    def _on_code_edited(self) -> None:
        database.update_objective(self.objective_id, code=self.code_edit.text().strip() or None)

    def _on_description_edited(self) -> None:
        database.update_objective(
            self.objective_id, description=self.description_edit.toPlainText().strip() or None
        )

    def _browse_checkpoint_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Checkpoint Video / Audio", "", MEDIA_FILE_FILTER)
        if path:
            database.update_objective(self.objective_id, checkpoint_video_path=path)
            self.video_label.setText(_video_label_text(path))
            self.video_label.setToolTip(path)

    def _clear_checkpoint_video(self) -> None:
        database.update_objective(self.objective_id, checkpoint_video_path=None)
        self.video_label.setText("(none)")
        self.video_label.setToolTip("")

    # ------------------------------------------------------------------
    # Hints / clue cards
    # ------------------------------------------------------------------

    def _build_hint_item_widget(self, hint) -> QWidget:
        widget = QWidget()
        item_layout = QHBoxLayout(widget)
        item_layout.setContentsMargins(6, 4, 6, 4)
        text_label = QLabel(hint.text)
        text_label.setWordWrap(True)
        item_layout.addWidget(text_label, stretch=1)
        item_layout.addWidget(RatingDots(hint.rating))
        if hint.video_path:
            video_label = QLabel("[vid]")
            video_label.setToolTip(hint.video_path)
            item_layout.addWidget(video_label)
        return widget

    def _refresh_hints(self, select_id: Optional[int] = None) -> None:
        self.hints_list.clear()
        for hint in database.list_hints(self.objective_id):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, hint.id)
            self.hints_list.addItem(item)
            widget = self._build_hint_item_widget(hint)
            item.setSizeHint(widget.sizeHint())
            self.hints_list.setItemWidget(item, widget)
            if hint.id == select_id:
                self.hints_list.setCurrentItem(item)

    def _selected_hint_id(self) -> Optional[int]:
        item = self.hints_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add_hint(self) -> None:
        dialog = HintEditorDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text, rating, video_path = dialog.values()
            if text:
                new_id = database.add_hint(self.objective_id, text, rating=rating, video_path=video_path)
                self._refresh_hints(select_id=new_id)

    def _edit_hint(self) -> None:
        hint_id = self._selected_hint_id()
        if hint_id is None:
            return
        hint = next((h for h in database.list_hints(self.objective_id) if h.id == hint_id), None)
        if hint is None:
            return
        dialog = HintEditorDialog(
            parent=self, text=hint.text, rating=hint.rating, video_path=hint.video_path
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text, rating, video_path = dialog.values()
            if text:
                database.update_hint(hint_id, text=text, rating=rating, video_path=video_path)
                self._refresh_hints(select_id=hint_id)

    def _delete_hint(self) -> None:
        hint_id = self._selected_hint_id()
        if hint_id is None:
            return
        database.delete_hint(hint_id)
        self._refresh_hints()

    def _move_hint_up(self) -> None:
        hint_id = self._selected_hint_id()
        if hint_id is None:
            return
        database.move_hint(hint_id, -1)
        self._refresh_hints(select_id=hint_id)

    def _move_hint_down(self) -> None:
        hint_id = self._selected_hint_id()
        if hint_id is None:
            return
        database.move_hint(hint_id, 1)
        self._refresh_hints(select_id=hint_id)


class RoomEditorDialog(QDialog):
    """Edit a room template: name, duration, briefing/ending videos,
    objectives (with code, description, hints + checkpoint video) and the
    clue tracker list.
    """

    def __init__(self, room_id: int, parent=None):
        super().__init__(parent)
        self.room_id = room_id
        self.setWindowTitle("Edit Room")
        self.resize(800, 650)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Room name:"))
        self.name_edit = QLineEdit()
        self.name_edit.editingFinished.connect(self._on_name_edited)
        name_row.addWidget(self.name_edit)
        name_row.addWidget(QLabel("Duration (minutes):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 600)
        self.duration_spin.editingFinished.connect(self._on_duration_changed)
        name_row.addWidget(self.duration_spin)
        layout.addLayout(name_row)

        video_group = QGroupBox("Videos")
        video_layout = QVBoxLayout(video_group)

        intro_row = QHBoxLayout()
        intro_row.addWidget(QLabel("Briefing video (English):"))
        self.intro_label = QLabel("(none)")
        intro_row.addWidget(self.intro_label, stretch=1)
        intro_browse = QPushButton("Browse...")
        intro_browse.clicked.connect(self._browse_intro_video)
        intro_row.addWidget(intro_browse)
        intro_clear = QPushButton("Clear")
        intro_clear.clicked.connect(self._clear_intro_video)
        intro_row.addWidget(intro_clear)
        video_layout.addLayout(intro_row)

        intro_fr_row = QHBoxLayout()
        intro_fr_row.addWidget(QLabel("Briefing video (French):"))
        self.intro_fr_label = QLabel("(none)")
        intro_fr_row.addWidget(self.intro_fr_label, stretch=1)
        intro_fr_browse = QPushButton("Browse...")
        intro_fr_browse.clicked.connect(self._browse_intro_video_fr)
        intro_fr_row.addWidget(intro_fr_browse)
        intro_fr_clear = QPushButton("Clear")
        intro_fr_clear.clicked.connect(self._clear_intro_video_fr)
        intro_fr_row.addWidget(intro_fr_clear)
        video_layout.addLayout(intro_fr_row)

        ending_row = QHBoxLayout()
        ending_row.addWidget(QLabel("Ending video:"))
        self.ending_label = QLabel("(none)")
        ending_row.addWidget(self.ending_label, stretch=1)
        ending_browse = QPushButton("Browse...")
        ending_browse.clicked.connect(self._browse_ending_video)
        ending_row.addWidget(ending_browse)
        ending_clear = QPushButton("Clear")
        ending_clear.clicked.connect(self._clear_ending_video)
        ending_row.addWidget(ending_clear)
        video_layout.addLayout(ending_row)

        layout.addWidget(video_group)

        player_window_group = QGroupBox("Player Window")
        player_window_layout = QVBoxLayout(player_window_group)

        background_row = QHBoxLayout()
        background_row.addWidget(QLabel("Background image:"))
        self.background_image_label = QLabel("(none)")
        background_row.addWidget(self.background_image_label, stretch=1)
        background_browse = QPushButton("Browse...")
        background_browse.clicked.connect(self._browse_background_image)
        background_row.addWidget(background_browse)
        background_clear = QPushButton("Clear")
        background_clear.clicked.connect(self._clear_background_image)
        background_row.addWidget(background_clear)
        player_window_layout.addLayout(background_row)

        layout.addWidget(player_window_group)

        audio_group = QGroupBox("Audio")
        audio_layout = QVBoxLayout(audio_group)

        alert_row = QHBoxLayout()
        alert_row.addWidget(QLabel("Custom alert sound:"))
        self.alert_sound_label = QLabel("(none)")
        alert_row.addWidget(self.alert_sound_label, stretch=1)
        alert_browse = QPushButton("Browse...")
        alert_browse.clicked.connect(self._browse_alert_sound)
        alert_row.addWidget(alert_browse)
        alert_clear = QPushButton("Clear")
        alert_clear.clicked.connect(self._clear_alert_sound)
        alert_row.addWidget(alert_clear)
        audio_layout.addLayout(alert_row)

        game_music_row = QHBoxLayout()
        game_music_row.addWidget(QLabel("Background music (player window):"))
        self.game_music_label = QLabel("(none)")
        game_music_row.addWidget(self.game_music_label, stretch=1)
        game_music_browse = QPushButton("Browse...")
        game_music_browse.clicked.connect(self._browse_game_music)
        game_music_row.addWidget(game_music_browse)
        game_music_clear = QPushButton("Clear")
        game_music_clear.clicked.connect(self._clear_game_music)
        game_music_row.addWidget(game_music_clear)
        audio_layout.addLayout(game_music_row)

        success_row = QHBoxLayout()
        success_row.addWidget(QLabel("Success sound:"))
        self.success_sound_label = QLabel("(none)")
        success_row.addWidget(self.success_sound_label, stretch=1)
        success_browse = QPushButton("Browse...")
        success_browse.clicked.connect(self._browse_success_sound)
        success_row.addWidget(success_browse)
        success_clear = QPushButton("Clear")
        success_clear.clicked.connect(self._clear_success_sound)
        success_row.addWidget(success_clear)
        audio_layout.addLayout(success_row)

        fail_row = QHBoxLayout()
        fail_row.addWidget(QLabel("Fail sound:"))
        self.fail_sound_label = QLabel("(none)")
        fail_row.addWidget(self.fail_sound_label, stretch=1)
        fail_browse = QPushButton("Browse...")
        fail_browse.clicked.connect(self._browse_fail_sound)
        fail_row.addWidget(fail_browse)
        fail_clear = QPushButton("Clear")
        fail_clear.clicked.connect(self._clear_fail_sound)
        fail_row.addWidget(fail_clear)
        audio_layout.addLayout(fail_row)

        layout.addWidget(audio_group)

        columns = QHBoxLayout()

        objectives_group = QGroupBox("Objectives")
        objectives_layout = QVBoxLayout(objectives_group)
        self.objectives_list = QListWidget()
        self.objectives_list.itemDoubleClicked.connect(lambda _: self._manage_objective())
        objectives_layout.addWidget(self.objectives_list)
        obj_btn_row = QHBoxLayout()
        for label, handler in (
            ("Add", self._add_objective),
            ("Manage...", self._manage_objective),
            ("Delete", self._delete_objective),
            ("Up", self._move_objective_up),
            ("Down", self._move_objective_down),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            obj_btn_row.addWidget(btn)
        objectives_layout.addLayout(obj_btn_row)
        columns.addWidget(objectives_group)

        clues_group = QGroupBox("Clue Tracker (any number of slots)")
        clues_layout = QVBoxLayout(clues_group)
        self.clues_list = QListWidget()
        self.clues_list.itemDoubleClicked.connect(lambda _: self._rename_clue())
        clues_layout.addWidget(self.clues_list)
        clue_btn_row = QHBoxLayout()
        for label, handler in (
            ("Add", self._add_clue),
            ("Rename", self._rename_clue),
            ("Delete", self._delete_clue),
            ("Up", self._move_clue_up),
            ("Down", self._move_clue_down),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            clue_btn_row.addWidget(btn)
        clues_layout.addLayout(clue_btn_row)
        columns.addWidget(clues_group)

        layout.addLayout(columns)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        room = database.get_room(self.room_id)
        if room is None:
            return
        self.name_edit.setText(room.name)
        self.duration_spin.setValue(max(1, room.duration_seconds // 60))
        self.intro_label.setText(_video_label_text(room.intro_video_path))
        self.intro_label.setToolTip(room.intro_video_path or "")
        self.intro_fr_label.setText(_video_label_text(room.intro_video_path_fr))
        self.intro_fr_label.setToolTip(room.intro_video_path_fr or "")
        self.ending_label.setText(_video_label_text(room.ending_video_path))
        self.ending_label.setToolTip(room.ending_video_path or "")
        self.background_image_label.setText(_video_label_text(room.background_image_path))
        self.background_image_label.setToolTip(room.background_image_path or "")
        audio_settings = database.get_audio_settings(self.room_id)
        self.alert_sound_label.setText(_video_label_text(audio_settings.alert_path))
        self.alert_sound_label.setToolTip(audio_settings.alert_path or "")
        self.game_music_label.setText(_video_label_text(audio_settings.game_music_path))
        self.game_music_label.setToolTip(audio_settings.game_music_path or "")
        self.success_sound_label.setText(_video_label_text(audio_settings.success_path))
        self.success_sound_label.setToolTip(audio_settings.success_path or "")
        self.fail_sound_label.setText(_video_label_text(audio_settings.fail_path))
        self.fail_sound_label.setToolTip(audio_settings.fail_path or "")
        self._refresh_objectives()
        self._refresh_clues()

    # ------------------------------------------------------------------
    # Room fields
    # ------------------------------------------------------------------

    def _on_name_edited(self) -> None:
        name = self.name_edit.text().strip()
        if name:
            database.update_room(self.room_id, name=name)
            self.setWindowTitle(f"Edit Room: {name}")

    def _on_duration_changed(self) -> None:
        minutes = self.duration_spin.value()
        database.update_room(self.room_id, duration_seconds=minutes * 60)

    def _browse_intro_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Briefing Video", "", VIDEO_FILE_FILTER)
        if path:
            database.update_room(self.room_id, intro_video_path=path)
            self.intro_label.setText(_video_label_text(path))
            self.intro_label.setToolTip(path)

    def _clear_intro_video(self) -> None:
        database.update_room(self.room_id, intro_video_path=None)
        self.intro_label.setText("(none)")
        self.intro_label.setToolTip("")

    def _browse_intro_video_fr(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Briefing Video (French)", "", VIDEO_FILE_FILTER
        )
        if path:
            database.update_room(self.room_id, intro_video_path_fr=path)
            self.intro_fr_label.setText(_video_label_text(path))
            self.intro_fr_label.setToolTip(path)

    def _clear_intro_video_fr(self) -> None:
        database.update_room(self.room_id, intro_video_path_fr=None)
        self.intro_fr_label.setText("(none)")
        self.intro_fr_label.setToolTip("")

    def _browse_ending_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Ending Video", "", VIDEO_FILE_FILTER)
        if path:
            database.update_room(self.room_id, ending_video_path=path)
            self.ending_label.setText(_video_label_text(path))
            self.ending_label.setToolTip(path)

    def _clear_ending_video(self) -> None:
        database.update_room(self.room_id, ending_video_path=None)
        self.ending_label.setText("(none)")
        self.ending_label.setToolTip("")

    def _browse_background_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "", IMAGE_FILE_FILTER
        )
        if path:
            database.update_room(self.room_id, background_image_path=path)
            self.background_image_label.setText(_video_label_text(path))
            self.background_image_label.setToolTip(path)

    def _clear_background_image(self) -> None:
        database.update_room(self.room_id, background_image_path=None)
        self.background_image_label.setText("(none)")
        self.background_image_label.setToolTip("")

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    def _browse_alert_sound(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Alert Sound", "", AUDIO_FILE_FILTER)
        if path:
            database.update_audio_settings(self.room_id, alert_path=path)
            self.alert_sound_label.setText(_video_label_text(path))
            self.alert_sound_label.setToolTip(path)

    def _clear_alert_sound(self) -> None:
        database.update_audio_settings(self.room_id, alert_path=None)
        self.alert_sound_label.setText("(none)")
        self.alert_sound_label.setToolTip("")

    def _browse_game_music(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Music", "", AUDIO_FILE_FILTER
        )
        if path:
            database.update_audio_settings(self.room_id, game_music_path=path)
            self.game_music_label.setText(_video_label_text(path))
            self.game_music_label.setToolTip(path)

    def _clear_game_music(self) -> None:
        database.update_audio_settings(self.room_id, game_music_path=None)
        self.game_music_label.setText("(none)")
        self.game_music_label.setToolTip("")

    def _browse_success_sound(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Success Sound", "", AUDIO_FILE_FILTER)
        if path:
            database.update_audio_settings(self.room_id, success_path=path)
            self.success_sound_label.setText(_video_label_text(path))
            self.success_sound_label.setToolTip(path)

    def _clear_success_sound(self) -> None:
        database.update_audio_settings(self.room_id, success_path=None)
        self.success_sound_label.setText("(none)")
        self.success_sound_label.setToolTip("")

    def _browse_fail_sound(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Fail Sound", "", AUDIO_FILE_FILTER)
        if path:
            database.update_audio_settings(self.room_id, fail_path=path)
            self.fail_sound_label.setText(_video_label_text(path))
            self.fail_sound_label.setToolTip(path)

    def _clear_fail_sound(self) -> None:
        database.update_audio_settings(self.room_id, fail_path=None)
        self.fail_sound_label.setText("(none)")
        self.fail_sound_label.setToolTip("")

    # ------------------------------------------------------------------
    # Objectives
    # ------------------------------------------------------------------

    def _refresh_objectives(self, select_id: Optional[int] = None) -> None:
        self.objectives_list.clear()
        for objective in database.list_objectives(self.room_id):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, objective.id)
            widget = self._build_objective_item_widget(objective)
            item.setSizeHint(widget.sizeHint())
            self.objectives_list.addItem(item)
            self.objectives_list.setItemWidget(item, widget)
            if objective.id == select_id:
                self.objectives_list.setCurrentItem(item)

    def _build_objective_item_widget(self, objective) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 4, 6, 4)
        text = objective.title
        if objective.code:
            text += f"  (CODE: {objective.code})"
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label, stretch=1)
        add_cue_button = QPushButton("+ Cue")
        add_cue_button.setToolTip("Add a clue/hint to this objective")
        add_cue_button.clicked.connect(lambda _, oid=objective.id: self._quick_add_cue(oid))
        layout.addWidget(add_cue_button)
        return widget

    def _quick_add_cue(self, objective_id: int) -> None:
        dialog = HintEditorDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text, rating, video_path = dialog.values()
            if text:
                database.add_hint(objective_id, text, rating=rating, video_path=video_path)

    def _selected_objective_id(self) -> Optional[int]:
        item = self.objectives_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add_objective(self) -> None:
        title, ok = QInputDialog.getText(self, "Add Objective", "Objective title:")
        if ok and title.strip():
            new_id = database.add_objective(self.room_id, title.strip())
            self._refresh_objectives(select_id=new_id)
            self._manage_objective()

    def _manage_objective(self) -> None:
        objective_id = self._selected_objective_id()
        if objective_id is None:
            return
        dialog = ObjectiveEditorDialog(objective_id, parent=self)
        dialog.exec()
        self._refresh_objectives(select_id=objective_id)

    def _delete_objective(self) -> None:
        objective_id = self._selected_objective_id()
        if objective_id is None:
            return
        if QMessageBox.question(self, "Delete Objective", "Delete this objective and its hints?") \
                != QMessageBox.StandardButton.Yes:
            return
        database.delete_objective(objective_id)
        self._refresh_objectives()

    def _move_objective_up(self) -> None:
        objective_id = self._selected_objective_id()
        if objective_id is None:
            return
        database.move_objective(objective_id, -1)
        self._refresh_objectives(select_id=objective_id)

    def _move_objective_down(self) -> None:
        objective_id = self._selected_objective_id()
        if objective_id is None:
            return
        database.move_objective(objective_id, 1)
        self._refresh_objectives(select_id=objective_id)

    # ------------------------------------------------------------------
    # Clues
    # ------------------------------------------------------------------

    def _refresh_clues(self, select_id: Optional[int] = None) -> None:
        self.clues_list.clear()
        for clue in database.list_clues(self.room_id):
            item = QListWidgetItem(clue.label)
            item.setData(Qt.ItemDataRole.UserRole, clue.id)
            self.clues_list.addItem(item)
            if clue.id == select_id:
                self.clues_list.setCurrentItem(item)

    def _selected_clue_id(self) -> Optional[int]:
        item = self.clues_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add_clue(self) -> None:
        label, ok = QInputDialog.getText(self, "Add Clue", "Clue label:")
        if ok and label.strip():
            new_id = database.add_clue(self.room_id, label.strip())
            self._refresh_clues(select_id=new_id)

    def _rename_clue(self) -> None:
        item = self.clues_list.currentItem()
        if item is None:
            return
        clue_id = item.data(Qt.ItemDataRole.UserRole)
        label, ok = QInputDialog.getText(self, "Rename Clue", "Clue label:", text=item.text())
        if ok and label.strip():
            database.update_clue(clue_id, label.strip())
            self._refresh_clues(select_id=clue_id)

    def _delete_clue(self) -> None:
        clue_id = self._selected_clue_id()
        if clue_id is None:
            return
        database.delete_clue(clue_id)
        self._refresh_clues()

    def _move_clue_up(self) -> None:
        clue_id = self._selected_clue_id()
        if clue_id is None:
            return
        database.move_clue(clue_id, -1)
        self._refresh_clues(select_id=clue_id)

    def _move_clue_down(self) -> None:
        clue_id = self._selected_clue_id()
        if clue_id is None:
            return
        database.move_clue(clue_id, 1)
        self._refresh_clues(select_id=clue_id)
