"""Live game-master Control Panel: objectives, clue cards, message feed,
timer and session controls, plus the player-facing display window."""

from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from erm import audio, database
from erm.constants import APP_VERSION
from erm.player_window import PlayerWindow
from erm.room_editor import RoomEditorDialog
from erm.theme import CONTROL_PANEL_STYLE
from erm.widgets.channel_strip import AudioChannelStrip
from erm.widgets.lock_button import ClueLockButton
from erm.widgets.rating import RatingDots


def _format_time(seconds: int) -> str:
    seconds = max(0, seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class ControlPanelWindow(QMainWindow):
    """Live session window for the game master."""

    back_to_dashboard = pyqtSignal()

    def __init__(self, room_id: int, parent=None):
        super().__init__(parent)
        self.room_id = room_id
        self.setStyleSheet(CONTROL_PANEL_STYLE)
        self.resize(1400, 800)

        self.player_window: Optional[PlayerWindow] = None
        self.objectives: list = []
        self.clue_buttons: list[ClueLockButton] = []
        self.audio_settings = database.get_audio_settings(room_id)
        self.video_strips: dict[str, AudioChannelStrip] = {}
        self._current_video_path: Optional[str] = None
        self._video_finished_callback: Optional[Callable[[], None]] = None

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)

        self._build_ui()
        self.refresh_all()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())

        main_area = QWidget()
        main_layout = QHBoxLayout(main_area)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(16)

        self.page_stack = QStackedLayout()
        self.page_stack.addWidget(self._build_session_page())
        self.page_stack.addWidget(self._build_audio_mixer_page())
        page_container = QWidget()
        page_container.setLayout(self.page_stack)
        main_layout.addWidget(page_container, stretch=1)

        main_layout.addWidget(self._build_separator())
        main_layout.addWidget(self._build_controls_column())
        root.addWidget(main_area, stretch=1)

        root.addWidget(self._build_bottom_bar())

        self.setCentralWidget(central)
        self.control_panel_tab.setChecked(True)

    def _build_session_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._build_objectives_column())
        layout.addWidget(self._build_separator())
        layout.addWidget(self._build_detail_column())
        layout.addWidget(self._build_separator())
        layout.addWidget(self._build_feed_column(), stretch=1)
        return page

    def _build_separator(self) -> QFrame:
        line = QFrame()
        line.setObjectName("columnSeparator")
        line.setFrameShape(QFrame.Shape.NoFrame)
        line.setFixedWidth(2)
        return line

    def _build_section_separator(self) -> QFrame:
        line = QFrame()
        line.setObjectName("sectionSeparator")
        line.setFrameShape(QFrame.Shape.NoFrame)
        line.setFixedHeight(2)
        return line

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)

        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)

        self.control_panel_tab = QPushButton("⚡ Control Panel")
        self.control_panel_tab.setObjectName("tabButton")
        self.control_panel_tab.setCheckable(True)
        self.tab_group.addButton(self.control_panel_tab, 0)
        layout.addWidget(self.control_panel_tab)

        self.audio_mixer_tab = QPushButton("🎚 Audio Mixer")
        self.audio_mixer_tab.setObjectName("tabButton")
        self.audio_mixer_tab.setCheckable(True)
        self.tab_group.addButton(self.audio_mixer_tab, 1)
        layout.addWidget(self.audio_mixer_tab)

        self.tab_group.idClicked.connect(self._on_tab_clicked)

        layout.addStretch(1)
        self.room_name_label = QLabel("")
        self.room_name_label.setObjectName("roomNameLabel")
        layout.addWidget(self.room_name_label)
        layout.addStretch(1)

        self.edit_room_button = QPushButton("✏ Edit Objectives & Clues")
        self.edit_room_button.clicked.connect(self._open_room_editor)
        layout.addWidget(self.edit_room_button)

        self.fullscreen_button = QPushButton("Fullscreen")
        self.fullscreen_button.setCheckable(True)
        self.fullscreen_button.toggled.connect(self._toggle_fullscreen)
        layout.addWidget(self.fullscreen_button)

        return bar

    def _build_objectives_column(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("columnPanel")
        panel.setFixedWidth(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("Objectives")
        header.setObjectName("columnHeader")
        layout.addWidget(header)

        self.objectives_list = QListWidget()
        self.objectives_list.currentItemChanged.connect(lambda *_: self._refresh_detail())
        layout.addWidget(self.objectives_list)

        return panel

    def _build_detail_column(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("columnPanel")
        panel.setFixedWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("Objective")
        header.setObjectName("columnHeader")
        layout.addWidget(header)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)

        self.complete_button = QPushButton("Mark Complete")
        self.complete_button.setObjectName("primaryButton")
        self.complete_button.clicked.connect(self._toggle_objective_complete)
        content_layout.addWidget(self.complete_button)

        self.detail_title_label = QLabel("")
        self.detail_title_label.setObjectName("objectiveTitle")
        self.detail_title_label.setWordWrap(True)
        content_layout.addWidget(self.detail_title_label)

        self.detail_code_label = QLabel("")
        self.detail_code_label.setObjectName("objectiveCode")
        content_layout.addWidget(self.detail_code_label)

        self.detail_description_label = QLabel("")
        self.detail_description_label.setObjectName("objectiveDescription")
        self.detail_description_label.setWordWrap(True)
        content_layout.addWidget(self.detail_description_label)

        content_layout.addSpacing(8)
        content_layout.addWidget(self._build_section_separator())
        content_layout.addSpacing(4)

        clues_header = QLabel("Clues")
        clues_header.setObjectName("sectionHeader")
        content_layout.addWidget(clues_header)
        self.clues_detail_list = QListWidget()
        self.clues_detail_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.clues_detail_list.model().rowsMoved.connect(self._on_hints_reordered)
        self.clues_detail_list.itemClicked.connect(self._on_clue_card_clicked)
        content_layout.addWidget(self.clues_detail_list, stretch=1)

        layout.addWidget(content, stretch=1)
        return panel

    def _build_feed_column(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("columnPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("Message Feed")
        header.setObjectName("columnHeader")
        layout.addWidget(header)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)

        self.feed_list = QListWidget()
        content_layout.addWidget(self.feed_list, stretch=1)

        clear_button = QPushButton("Clear player window")
        clear_button.clicked.connect(self._on_clear_player_window)
        content_layout.addWidget(clear_button)

        send_row = QHBoxLayout()
        self.message_edit = QLineEdit()
        self.message_edit.setPlaceholderText("Type a message to send to players...")
        self.message_edit.returnPressed.connect(self._on_send_message)
        send_row.addWidget(self.message_edit, stretch=1)

        alert_button = QPushButton("Alert Tone")
        alert_button.clicked.connect(self._play_alert_sound)
        send_row.addWidget(alert_button)

        send_button = QPushButton("Send")
        send_button.setObjectName("primaryButton")
        send_button.clicked.connect(self._on_send_message)
        send_row.addWidget(send_button)

        content_layout.addLayout(send_row)

        layout.addWidget(content, stretch=1)
        return panel

    def _build_audio_mixer_page(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("columnPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("Audio")
        header.setObjectName("columnHeader")
        layout.addWidget(header)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)

        strips_row = QHBoxLayout()
        strips_row.setSpacing(24)
        self.audio_strips: dict[str, AudioChannelStrip] = {}
        for channel, label, show_preview in (
            ("alert", "Alert", True),
            ("game_music", "Game Music", True),
            ("success", "Success", True),
            ("fail", "Fail", True),
            ("video", "Video", False),
            ("master", "Master", False),
        ):
            strip = AudioChannelStrip(label, show_preview=show_preview)
            strip.volume_changed.connect(
                lambda value, ch=channel: self._on_audio_volume_changed(ch, value)
            )
            strip.mute_toggled.connect(
                lambda checked, ch=channel: self._on_audio_mute_toggled(ch, checked)
            )
            strip.preview_clicked.connect(lambda ch=channel: self._on_audio_preview(ch))
            self.audio_strips[channel] = strip
            strips_row.addWidget(strip)
        strips_row.addStretch(1)
        content_layout.addLayout(strips_row)

        videos_header = QLabel("Videos")
        videos_header.setObjectName("sectionHeader")
        content_layout.addWidget(videos_header)

        self.video_strips_container = QWidget()
        self.video_strips_layout = QHBoxLayout(self.video_strips_container)
        self.video_strips_layout.setContentsMargins(0, 0, 0, 0)
        self.video_strips_layout.setSpacing(24)
        self.video_strips_layout.addStretch(1)

        self.video_strips_scroll = QScrollArea()
        self.video_strips_scroll.setWidgetResizable(True)
        self.video_strips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.video_strips_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.video_strips_scroll.setFixedHeight(260)
        self.video_strips_scroll.setWidget(self.video_strips_container)
        content_layout.addWidget(self.video_strips_scroll)

        self.no_videos_label = QLabel("No videos configured for this room yet.")
        self.no_videos_label.setObjectName("audioMixerCaption")
        content_layout.addWidget(self.no_videos_label)

        content_layout.addStretch(1)

        caption = QLabel("You can upload custom audio in the game settings.")
        caption.setObjectName("audioMixerCaption")
        content_layout.addWidget(caption)

        layout.addWidget(content, stretch=1)
        return panel

    def _build_controls_column(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("columnPanel")
        panel.setFixedWidth(280)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("Controls")
        header.setObjectName("columnHeader")
        layout.addWidget(header)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)

        self.complete_game_button = QPushButton("Complete game")
        self.complete_game_button.setObjectName("primaryButton")
        self.complete_game_button.clicked.connect(self._on_complete_game)
        content_layout.addWidget(self.complete_game_button)

        stats_row = QHBoxLayout()
        self.puzzles_stat = self._build_stat_box("Puzzles Done")
        self.messages_stat = self._build_stat_box("Messages Sent")
        self.time_adjusted_stat = self._build_stat_box("Time Adjusted")
        for box, _ in (self.puzzles_stat, self.messages_stat, self.time_adjusted_stat):
            stats_row.addWidget(box)
        content_layout.addLayout(stats_row)

        content_layout.addWidget(self._build_section_separator())

        self.open_player_button = QPushButton("Open player window")
        self.open_player_button.clicked.connect(self._on_open_player_window)
        content_layout.addWidget(self.open_player_button)

        self.fullscreen_player_button = QPushButton("⛶ Fullscreen Player Window")
        self.fullscreen_player_button.clicked.connect(self._on_toggle_player_fullscreen)
        content_layout.addWidget(self.fullscreen_player_button)

        self.briefing_video_en_button = QPushButton("▶ Briefing Video (English)")
        self.briefing_video_en_button.setObjectName("playVideoButton")
        self.briefing_video_en_button.clicked.connect(self._on_play_briefing_video_en)
        content_layout.addWidget(self.briefing_video_en_button)

        self.briefing_video_fr_button = QPushButton("▶ Briefing Video (French)")
        self.briefing_video_fr_button.setObjectName("playVideoButton")
        self.briefing_video_fr_button.clicked.connect(self._on_play_briefing_video_fr)
        content_layout.addWidget(self.briefing_video_fr_button)

        content_layout.addWidget(self._build_section_separator())

        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("timerLabel")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(self.timer_label)

        adjust_row = QHBoxLayout()
        minus_button = QPushButton("-")
        minus_button.setFixedWidth(32)
        minus_button.clicked.connect(self._decrement_delta)
        adjust_row.addWidget(minus_button)
        self.delta_spin = QSpinBox()
        self.delta_spin.setRange(-10, 10)
        self.delta_spin.setValue(1)
        self.delta_spin.setSuffix(" min")
        adjust_row.addWidget(self.delta_spin, stretch=1)
        plus_button = QPushButton("+")
        plus_button.setFixedWidth(32)
        plus_button.clicked.connect(self._increment_delta)
        adjust_row.addWidget(plus_button)
        content_layout.addLayout(adjust_row)

        add_time_button = QPushButton("Add time")
        add_time_button.clicked.connect(self._on_add_time)
        content_layout.addWidget(add_time_button)

        self.start_pause_button = QPushButton("Start game")
        self.start_pause_button.setObjectName("primaryButton")
        self.start_pause_button.clicked.connect(self._on_start_pause)
        content_layout.addWidget(self.start_pause_button)

        self.reset_button = QPushButton("Reset game")
        self.reset_button.setObjectName("dangerButton")
        self.reset_button.clicked.connect(self._on_reset_game)
        content_layout.addWidget(self.reset_button)

        content_layout.addWidget(self._build_section_separator())

        clue_tracker_header = QLabel("Clues")
        clue_tracker_header.setObjectName("sectionHeader")
        content_layout.addWidget(clue_tracker_header)
        self.clue_buttons_layout = QHBoxLayout()
        clue_buttons_container = QWidget()
        clue_buttons_container.setLayout(self.clue_buttons_layout)
        content_layout.addWidget(clue_buttons_container)

        self.hide_clue_icons_checkbox = QCheckBox("Hide clue icons on player window")
        self.hide_clue_icons_checkbox.toggled.connect(self._on_hide_clue_icons_toggled)
        content_layout.addWidget(self.hide_clue_icons_checkbox)

        content_layout.addStretch(1)

        layout.addWidget(content, stretch=1)
        return panel

    def _build_stat_box(self, label_text: str) -> tuple[QWidget, QLabel]:
        box = QFrame()
        box.setObjectName("columnPanel")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        value_label = QLabel("0")
        value_label.setObjectName("statBoxValue")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)
        caption = QLabel(label_text)
        caption.setObjectName("statBoxLabel")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption.setWordWrap(True)
        layout.addWidget(caption)
        return box, value_label

    def _build_bottom_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("bottomBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)

        exit_button = QPushButton("Exit to Dashboard")
        exit_button.clicked.connect(self.back_to_dashboard.emit)
        layout.addWidget(exit_button)

        layout.addStretch(1)

        self.bottom_room_label = QLabel("")
        self.bottom_room_label.setObjectName("statusBarText")
        layout.addWidget(self.bottom_room_label)

        layout.addSpacing(20)

        self.bottom_stats_label = QLabel("")
        self.bottom_stats_label.setObjectName("statusBarText")
        layout.addWidget(self.bottom_stats_label)

        layout.addStretch(1)

        version_label = QLabel(f"VERSION {APP_VERSION}")
        version_label.setObjectName("statusBarText")
        layout.addWidget(version_label)

        return bar

    # ------------------------------------------------------------------
    # Refresh helpers
    # ------------------------------------------------------------------

    def refresh_all(self) -> None:
        room = database.get_room(self.room_id)
        if room is None:
            return
        self.room = room
        self.audio_settings = database.get_audio_settings(self.room_id)
        self.room_name_label.setText(room.name)
        self._refresh_objectives()
        self._refresh_clue_buttons()
        self._refresh_session_display()
        self._refresh_stats()
        self._refresh_briefing_buttons()
        self._refresh_audio_mixer()
        self._refresh_video_strips()
        self._apply_audio_settings()
        if self.player_window is not None:
            self.player_window.set_background_image(self.room.background_image_path)
        self._update_bottom_bar()

    def _refresh_briefing_buttons(self) -> None:
        self._refresh_briefing_button(self.briefing_video_en_button, self.room.intro_video_path)
        self._refresh_briefing_button(self.briefing_video_fr_button, self.room.intro_video_path_fr)

    def _refresh_briefing_button(self, button: QPushButton, path: Optional[str]) -> None:
        button.setEnabled(bool(path))
        if path:
            button.setToolTip(f"Plays: {Path(path).name}\n{path}")
        else:
            button.setToolTip(
                "No briefing video set. Add one via ✏ Edit Objectives & Clues → Videos."
            )

    def _update_bottom_bar(self) -> None:
        room = self.room
        self.bottom_room_label.setText(room.name)
        total = room.wins + room.losses
        rate = (room.wins / total * 100) if total else 0.0
        self.bottom_stats_label.setText(
            f"Success Rate: {rate:.0f}%   Wins: {room.wins}   Losses: {room.losses}"
        )

    def _refresh_stats(self) -> None:
        objectives = database.list_objectives(self.room_id)
        done = sum(1 for o in objectives if o.completed)
        total = len(objectives)
        self._set_stat(self.puzzles_stat, f"{done}/{total}")
        session = database.get_session(self.room_id)
        self._set_stat(self.messages_stat, str(session.messages_sent))
        adjusted_minutes = session.time_adjusted_seconds // 60
        sign = "+" if adjusted_minutes > 0 else ""
        self._set_stat(self.time_adjusted_stat, f"{sign}{adjusted_minutes}")

    def _set_stat(self, stat: tuple[QWidget, QLabel], value: str) -> None:
        stat[1].setText(value)

    def _refresh_session_display(self) -> None:
        session = database.get_session(self.room_id)
        self.timer_label.setText(_format_time(session.remaining_seconds))
        if self.player_window is not None:
            self.player_window.set_time(session.remaining_seconds)
            if session.status == "running":
                self.player_window.play_music()
            else:
                self.player_window.pause_music()
        if session.status == "running":
            self.start_pause_button.setText("Pause game")
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.start_pause_button.setText("Start game")
            if self.timer.isActive():
                self.timer.stop()

    # ------------------------------------------------------------------
    # Objectives column
    # ------------------------------------------------------------------

    def _refresh_objectives(self, select_id: Optional[int] = None) -> None:
        if select_id is None:
            current = self.objectives_list.currentItem()
            if current is not None:
                select_id = current.data(Qt.ItemDataRole.UserRole)
        self.objectives_list.clear()
        self.objectives = database.list_objectives(self.room_id)
        if not self.objectives:
            placeholder = QListWidgetItem(
                "No objectives yet.\nClick ✏ Edit Objectives & Clues above to add one."
            )
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.objectives_list.addItem(placeholder)
            self._refresh_detail()
            return
        selected_item = None
        for objective in self.objectives:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, objective.id)
            self.objectives_list.addItem(item)
            widget = self._build_objective_item_widget(objective)
            item.setSizeHint(widget.sizeHint())
            self.objectives_list.setItemWidget(item, widget)
            if objective.id == select_id:
                selected_item = item
        if selected_item is None and self.objectives_list.count() > 0:
            selected_item = self.objectives_list.item(0)
        if selected_item is not None:
            self.objectives_list.setCurrentItem(selected_item)
        else:
            self._refresh_detail()

    def _build_objective_item_widget(self, objective) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        icon = QLabel("✅" if objective.completed else "\U0001F511")
        layout.addWidget(icon)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title_label = QLabel(objective.title)
        title_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        title_label.setWordWrap(True)
        text_layout.addWidget(title_label)
        if objective.code:
            code_label = QLabel(f"CODE: {objective.code}")
            code_label.setObjectName("objectiveCode")
            text_layout.addWidget(code_label)
        layout.addLayout(text_layout, 1)
        return widget

    def _selected_objective(self):
        item = self.objectives_list.currentItem()
        if item is None:
            return None
        objective_id = item.data(Qt.ItemDataRole.UserRole)
        return next((o for o in self.objectives if o.id == objective_id), None)

    # ------------------------------------------------------------------
    # Objective detail column
    # ------------------------------------------------------------------

    def _refresh_detail(self, *_args) -> None:
        objective = self._selected_objective()
        if objective is None:
            self.complete_button.setEnabled(False)
            self.complete_button.setText("Mark Complete")
            self.detail_title_label.setText("")
            self.detail_code_label.setText("")
            self.detail_description_label.setText("")
            self.clues_detail_list.clear()
            return
        self.complete_button.setEnabled(True)
        self.complete_button.setText(
            "Mark Incomplete" if objective.completed else "Mark Complete"
        )
        self.detail_title_label.setText(objective.title)
        self.detail_code_label.setText(f"CODE: {objective.code}" if objective.code else "")
        self.detail_description_label.setText(objective.description or "")
        self._refresh_clue_cards(objective)

    def _refresh_clue_cards(self, objective) -> None:
        self.clues_detail_list.blockSignals(True)
        self.clues_detail_list.clear()
        for hint in database.list_hints(objective.id):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, hint.id)
            item.setData(Qt.ItemDataRole.UserRole + 1, hint.text)
            widget = self._build_clue_card_widget(hint, objective)
            item.setSizeHint(widget.sizeHint())
            self.clues_detail_list.addItem(item)
            self.clues_detail_list.setItemWidget(item, widget)
        self.clues_detail_list.blockSignals(False)

    def _build_clue_card_widget(self, hint, objective) -> QWidget:
        widget = QWidget()
        widget.setToolTip("Click to put this clue's text in the message box below")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)

        top_row = QHBoxLayout()
        text_label = QLabel(hint.text)
        text_label.setWordWrap(True)
        top_row.addWidget(text_label, stretch=1)
        if hint.video_path:
            play_button = QPushButton("▶")
            play_button.setObjectName("playVideoButton")
            play_button.setFixedWidth(32)
            play_button.clicked.connect(lambda _, path=hint.video_path: self._play_video(path))
            top_row.addWidget(play_button)
        layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        tag_label = QLabel(objective.title)
        tag_label.setObjectName("clueTag")
        bottom_row.addWidget(tag_label)
        bottom_row.addStretch(1)
        bottom_row.addWidget(RatingDots(hint.rating))
        layout.addLayout(bottom_row)

        return widget

    def _on_hints_reordered(self, *_args) -> None:
        objective = self._selected_objective()
        if objective is None:
            return
        ordered_ids = [
            self.clues_detail_list.item(row).data(Qt.ItemDataRole.UserRole)
            for row in range(self.clues_detail_list.count())
        ]
        database.reorder_hints(objective.id, ordered_ids)

    def _on_clue_card_clicked(self, item: QListWidgetItem) -> None:
        text = item.data(Qt.ItemDataRole.UserRole + 1)
        if not text:
            return
        self.message_edit.setText(text)
        self.message_edit.setFocus()
        self.message_edit.selectAll()

    def _toggle_objective_complete(self) -> None:
        objective = self._selected_objective()
        if objective is None:
            return
        new_state = not objective.completed
        database.set_objective_progress(self.room_id, objective.id, new_state)
        if new_state and objective.checkpoint_video_path:
            self._play_video(objective.checkpoint_video_path)
        self._refresh_objectives(select_id=objective.id)
        self._refresh_stats()

    # ------------------------------------------------------------------
    # Message feed
    # ------------------------------------------------------------------

    def _on_send_message(self) -> None:
        text = self.message_edit.text().strip()
        if not text:
            return
        self.feed_list.addItem(text)
        self.feed_list.scrollToBottom()
        self.message_edit.clear()
        new_count = database.increment_session_messages(self.room_id)
        self._set_stat(self.messages_stat, str(new_count))
        self._play_alert_sound()
        if self.player_window is not None:
            self.player_window.show_message(text)

    def _on_clear_player_window(self) -> None:
        if self.player_window is not None:
            self.player_window.clear_message()
        self.feed_list.clear()

    # ------------------------------------------------------------------
    # Player window
    # ------------------------------------------------------------------

    def _ensure_player_window(self) -> PlayerWindow:
        if self.player_window is None:
            self.player_window = PlayerWindow(room_name=self.room.name)
            self.player_window.video_finished.connect(self._on_video_finished)
            self.player_window.set_clue_icons_hidden(self.hide_clue_icons_checkbox.isChecked())
            self._sync_player_clue_states()
            session = database.get_session(self.room_id)
            self.player_window.set_time(session.remaining_seconds)
            self.player_window.set_background_image(self.room.background_image_path)
            self._apply_audio_settings()
            if session.status == "running":
                self.player_window.play_music()

            secondary_screen = self._secondary_screen()
            if secondary_screen is not None:
                self.player_window.move(secondary_screen.geometry().topLeft())
                self.player_window.showFullScreen()
        self.player_window.show()
        self.player_window.raise_()
        return self.player_window

    def _secondary_screen(self):
        """Return a screen other than the one this control panel is on, if
        a second display is attached, so the player window can be opened
        there directly in fullscreen."""
        current_screen = self.screen()
        for screen in QGuiApplication.screens():
            if screen is not current_screen:
                return screen
        return None

    def _play_video(self, path: str, on_finished: Optional[Callable[[], None]] = None) -> None:
        player = self._ensure_player_window()
        self._current_video_path = path
        self._video_finished_callback = on_finished
        player.play_video(path)
        self._apply_video_volume()

    def _on_video_finished(self) -> None:
        callback = self._video_finished_callback
        self._video_finished_callback = None
        if callback is not None:
            callback()

    def _on_open_player_window(self) -> None:
        self._ensure_player_window()

    def _on_toggle_player_fullscreen(self) -> None:
        self._ensure_player_window().toggle_fullscreen()

    def _on_play_briefing_video_en(self) -> None:
        if self.room.intro_video_path:
            self._play_video(self.room.intro_video_path, on_finished=self._auto_start_after_briefing)

    def _on_play_briefing_video_fr(self) -> None:
        if self.room.intro_video_path_fr:
            self._play_video(self.room.intro_video_path_fr, on_finished=self._auto_start_after_briefing)

    def _auto_start_after_briefing(self) -> None:
        if database.get_session(self.room_id).status == "idle":
            self._on_start_pause()

    # ------------------------------------------------------------------
    # Audio mixer
    # ------------------------------------------------------------------

    def _on_tab_clicked(self, button_id: int) -> None:
        self.page_stack.setCurrentIndex(button_id)

    def _refresh_audio_mixer(self) -> None:
        settings = self.audio_settings
        for channel, strip in self.audio_strips.items():
            strip.set_volume(getattr(settings, f"{channel}_volume"))
            strip.set_muted(getattr(settings, f"{channel}_muted"))
        for channel in ("alert", "game_music", "success", "fail"):
            path = getattr(settings, f"{channel}_path")
            self.audio_strips[channel].set_status("Ready to Play" if path else "No Status")
        self.audio_strips["video"].set_status("No Status")
        self.audio_strips["master"].set_status("Master")

    def _apply_audio_settings(self) -> None:
        if self.player_window is None:
            return
        settings = self.audio_settings
        self.player_window.set_music(settings.game_music_path)
        music_volume = audio.effective_volume(
            settings.game_music_volume,
            settings.game_music_muted,
            settings.master_volume,
            settings.master_muted,
        )
        self.player_window.set_music_volume(music_volume)
        self._apply_video_volume()

    def _on_audio_volume_changed(self, channel: str, value: int) -> None:
        database.update_audio_settings(self.room_id, **{f"{channel}_volume": value})
        self.audio_settings = database.get_audio_settings(self.room_id)
        self._apply_audio_settings()

    def _on_audio_mute_toggled(self, channel: str, checked: bool) -> None:
        database.update_audio_settings(self.room_id, **{f"{channel}_muted": checked})
        self.audio_settings = database.get_audio_settings(self.room_id)
        self._apply_audio_settings()

    def _on_audio_preview(self, channel: str) -> None:
        settings = self.audio_settings
        if channel == "alert":
            self._play_alert_sound()
        elif channel == "success":
            self._play_success_sound()
        elif channel == "fail":
            self._play_fail_sound()
        elif channel == "game_music" and settings.game_music_path:
            volume = audio.effective_volume(
                settings.game_music_volume,
                settings.game_music_muted,
                settings.master_volume,
                settings.master_muted,
            )
            audio.play_file(settings.game_music_path, volume)

    def _play_alert_sound(self) -> None:
        settings = self.audio_settings
        volume = audio.effective_volume(
            settings.alert_volume, settings.alert_muted, settings.master_volume, settings.master_muted
        )
        audio.play_alert(settings.alert_path, volume)

    def _play_success_sound(self) -> None:
        settings = self.audio_settings
        volume = audio.effective_volume(
            settings.success_volume,
            settings.success_muted,
            settings.master_volume,
            settings.master_muted,
        )
        audio.play_success(settings.success_path, volume)

    def _play_fail_sound(self) -> None:
        settings = self.audio_settings
        volume = audio.effective_volume(
            settings.fail_volume, settings.fail_muted, settings.master_volume, settings.master_muted
        )
        if settings.fail_path:
            audio.play_fail(settings.fail_path, volume)
        else:
            audio.play_alert(None, volume)

    # ------------------------------------------------------------------
    # Per-video volume sub-mixer
    # ------------------------------------------------------------------

    def _list_room_videos(self) -> list[tuple[str, str]]:
        videos: list[tuple[str, str]] = []
        room = self.room
        if room.intro_video_path:
            videos.append(("Briefing (EN)", room.intro_video_path))
        if room.intro_video_path_fr:
            videos.append(("Briefing (FR)", room.intro_video_path_fr))
        if room.ending_video_path:
            videos.append(("Ending", room.ending_video_path))
        for objective in database.list_objectives(self.room_id):
            if objective.checkpoint_video_path:
                videos.append((f"Checkpoint: {objective.title}", objective.checkpoint_video_path))
            for hint in database.list_hints(objective.id):
                if hint.video_path:
                    videos.append((f"Hint: {hint.text}", hint.video_path))
        return videos

    def _refresh_video_strips(self) -> None:
        while self.video_strips_layout.count() > 1:
            item = self.video_strips_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.video_strips = {}

        videos = self._list_room_videos()
        for label, path in videos:
            strip = AudioChannelStrip(label, show_preview=True)
            volume, muted = database.get_video_volume(self.room_id, path)
            strip.set_volume(volume)
            strip.set_muted(muted)
            strip.set_status(Path(path).name)
            strip.volume_changed.connect(
                lambda value, p=path: self._on_video_volume_changed(p, value)
            )
            strip.mute_toggled.connect(
                lambda checked, p=path: self._on_video_mute_toggled(p, checked)
            )
            strip.preview_clicked.connect(lambda p=path: self._on_video_preview(p))
            self.video_strips[path] = strip
            self.video_strips_layout.insertWidget(self.video_strips_layout.count() - 1, strip)

        self.video_strips_scroll.setVisible(bool(videos))
        self.no_videos_label.setVisible(not videos)

    def _on_video_volume_changed(self, path: str, value: int) -> None:
        database.update_video_volume(self.room_id, path, volume=value)
        self._apply_video_volume()

    def _on_video_mute_toggled(self, path: str, checked: bool) -> None:
        database.update_video_volume(self.room_id, path, muted=checked)
        self._apply_video_volume()

    def _on_video_preview(self, path: str) -> None:
        volume, muted = database.get_video_volume(self.room_id, path)
        settings = self.audio_settings
        effective = audio.effective_video_volume(
            volume, muted,
            settings.video_volume, settings.video_muted,
            settings.master_volume, settings.master_muted,
        )
        audio.play_file(path, effective)

    def _apply_video_volume(self) -> None:
        if self.player_window is None or self._current_video_path is None:
            return
        volume, muted = database.get_video_volume(self.room_id, self._current_video_path)
        settings = self.audio_settings
        effective = audio.effective_video_volume(
            volume, muted,
            settings.video_volume, settings.video_muted,
            settings.master_volume, settings.master_muted,
        )
        self.player_window.set_video_volume(effective)

    # ------------------------------------------------------------------
    # Clue tracker
    # ------------------------------------------------------------------

    def _refresh_clue_buttons(self) -> None:
        while self.clue_buttons_layout.count():
            item = self.clue_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.clue_buttons = []
        for clue in database.list_clues(self.room_id):
            button = ClueLockButton(label=clue.label)
            button.setChecked(clue.checked)
            button.toggled.connect(
                lambda checked, clue_id=clue.id: self._on_clue_toggled(clue_id, checked)
            )
            self.clue_buttons_layout.addWidget(button)
            self.clue_buttons.append(button)
        self._sync_player_clue_states()

    def _on_clue_toggled(self, clue_id: int, checked: bool) -> None:
        database.set_clue_progress(self.room_id, clue_id, checked)
        self._sync_player_clue_states()

    def _sync_player_clue_states(self) -> None:
        if self.player_window is not None:
            self.player_window.set_clue_states([btn.isChecked() for btn in self.clue_buttons])

    def _on_hide_clue_icons_toggled(self, checked: bool) -> None:
        if self.player_window is not None:
            self.player_window.set_clue_icons_hidden(checked)

    # ------------------------------------------------------------------
    # Timer / session lifecycle
    # ------------------------------------------------------------------

    def _decrement_delta(self) -> None:
        self.delta_spin.setValue(self.delta_spin.value() - 1)

    def _increment_delta(self) -> None:
        self.delta_spin.setValue(self.delta_spin.value() + 1)

    def _on_add_time(self) -> None:
        delta_seconds = self.delta_spin.value() * 60
        if delta_seconds == 0:
            return
        session = database.adjust_session_time(self.room_id, delta_seconds)
        self.timer_label.setText(_format_time(session.remaining_seconds))
        if self.player_window is not None:
            self.player_window.set_time(session.remaining_seconds)
        self._refresh_stats()

    def _on_tick(self) -> None:
        session = database.get_session(self.room_id)
        remaining = max(0, session.remaining_seconds - 1)
        if remaining <= 0:
            self.timer.stop()
            database.record_result(self.room_id, won=False)
            database.save_session(self.room_id, "completed", 0)
            if self.player_window is not None:
                self.player_window.show_time_up()
            self._play_fail_sound()
            self.refresh_all()
        else:
            database.save_session(self.room_id, "running", remaining)
            self.timer_label.setText(_format_time(remaining))
            if self.player_window is not None:
                self.player_window.set_time(remaining)

    def _start_fresh_session(self, status: str = "running") -> None:
        database.start_session(self.room_id, status=status)
        self.feed_list.clear()
        if status == "running":
            self._ensure_player_window()
        if self.player_window is not None:
            self.player_window.clear_message()
            self.player_window.show_timer()
        self.refresh_all()

    def _on_start_pause(self) -> None:
        session = database.get_session(self.room_id)
        if session.status == "running":
            self.timer.stop()
            database.save_session(self.room_id, "paused", session.remaining_seconds)
            self.refresh_all()
        elif session.status in ("idle", "completed"):
            self._start_fresh_session()
        else:
            database.save_session(self.room_id, "running", session.remaining_seconds)
            self._ensure_player_window()
            self.refresh_all()

    def _on_complete_game(self) -> None:
        self.timer.stop()
        session = database.get_session(self.room_id)
        database.record_result(self.room_id, won=True)
        database.save_session(self.room_id, "completed", session.remaining_seconds)
        self._play_success_sound()
        if self.room.ending_video_path:
            self._play_video(self.room.ending_video_path)
        self.refresh_all()

    def _on_reset_game(self) -> None:
        if (
            QMessageBox.question(
                self, "Reset Game", "Reset the timer and all progress for this room?"
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.timer.stop()
        self._start_fresh_session(status="idle")

    # ------------------------------------------------------------------
    # Room editor
    # ------------------------------------------------------------------

    def _open_room_editor(self) -> None:
        dialog = RoomEditorDialog(self.room_id, parent=self)
        dialog.exec()
        self.refresh_all()

    # ------------------------------------------------------------------
    # Window chrome
    # ------------------------------------------------------------------

    def _toggle_fullscreen(self, checked: bool) -> None:
        if checked:
            self.showFullScreen()
            self.fullscreen_button.setText("Exit Fullscreen")
        else:
            self.showNormal()
            self.fullscreen_button.setText("Fullscreen")

    def closeEvent(self, event) -> None:
        if self.timer.isActive():
            self.timer.stop()
            session = database.get_session(self.room_id)
            database.save_session(self.room_id, "paused", session.remaining_seconds)
        if self.player_window is not None:
            self.player_window.close()
        super().closeEvent(event)
