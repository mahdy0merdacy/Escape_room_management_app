"""Room Setup dialog: name/duration, puzzles (objectives + hints), clue
counter slots, and all media files.  All edits write straight through to the
database — nothing is lost if the dialog is just closed.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from erm import database
from erm.constants import AUDIO_FILE_FILTER, IMAGE_FILE_FILTER, MEDIA_FILE_FILTER, RATING_MAX, VIDEO_FILE_FILTER
from erm.paths import to_portable_path
from erm.theme import CONTROL_PANEL_STYLE
from erm.widgets.rating import RatingDots


def _filename(path: Optional[str]) -> str:
    return Path(path).name if path else "No file selected"


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "font-size: 11px; font-weight: 700; letter-spacing: 1.2px; "
        "color: #6B6A80; text-transform: uppercase; padding-top: 6px;"
    )
    return lbl


def _caption(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet("color: #6B6A80; font-size: 12px;")
    return lbl


def _file_row(label: str, file_filter: str, on_browse, on_clear) -> tuple[QHBoxLayout, QLabel]:
    """Return a (layout, file_label) for a single browse/clear file row."""
    row = QHBoxLayout()
    row.setSpacing(6)
    name_lbl = QLabel("No file selected")
    name_lbl.setStyleSheet(
        "background: #060607; border: 1px solid #2A2A34; border-radius: 6px; "
        "padding: 6px 10px; color: #8A8896; font-size: 12px;"
    )
    name_lbl.setMinimumWidth(160)
    row.addWidget(name_lbl, stretch=1)
    browse_btn = QPushButton("Browse…")
    browse_btn.setFixedWidth(80)
    browse_btn.clicked.connect(on_browse)
    row.addWidget(browse_btn)
    clear_btn = QPushButton("Clear")
    clear_btn.setFixedWidth(56)
    clear_btn.clicked.connect(on_clear)
    row.addWidget(clear_btn)
    return row, name_lbl


def _set_file_label(lbl: QLabel, path: Optional[str]) -> None:
    if path:
        lbl.setText(Path(path).name)
        lbl.setToolTip(path)
        lbl.setStyleSheet(
            "background: #060607; border: 1px solid #2A2A34; border-radius: 6px; "
            "padding: 6px 10px; color: #C8C6D0; font-size: 12px;"
        )
    else:
        lbl.setText("No file selected")
        lbl.setToolTip("")
        lbl.setStyleSheet(
            "background: #060607; border: 1px solid #2A2A34; border-radius: 6px; "
            "padding: 6px 10px; color: #8A8896; font-size: 12px;"
        )


# ---------------------------------------------------------------------------
# Hint editor
# ---------------------------------------------------------------------------

class HintEditorDialog(QDialog):
    """Add or edit a single prepared hint: text, difficulty, and an optional
    video that plays in the player window when the hint is given."""

    def __init__(self, parent=None, text: str = "", rating: int = 0,
                 video_path: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Hint" if text else "Add Hint")
        self.setMinimumWidth(460)
        self._video_path = video_path
        self._build_ui()
        self.text_edit.setPlainText(text)
        self.rating_spin.setValue(rating)
        self._on_rating_changed(rating)
        _set_file_label(self._video_lbl, video_path)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        layout.addWidget(_section_label("What to say to the players"))
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Type the hint text here…")
        self.text_edit.setFixedHeight(90)
        layout.addWidget(self.text_edit)

        diff_row = QHBoxLayout()
        diff_row.addWidget(_section_label("Difficulty"))
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(0, RATING_MAX)
        self.rating_spin.setFixedWidth(52)
        self.rating_spin.valueChanged.connect(self._on_rating_changed)
        diff_row.addWidget(self.rating_spin)
        self.rating_preview = RatingDots(0)
        diff_row.addWidget(self.rating_preview)
        diff_row.addWidget(_caption("0 = easy   •   5 = hardest"))
        diff_row.addStretch(1)
        layout.addLayout(diff_row)

        layout.addWidget(_section_label("Video / Audio (optional)"))
        layout.addWidget(_caption("Plays in the player window when you give this hint."))
        vid_row, self._video_lbl = _file_row(
            "Video", MEDIA_FILE_FILTER, self._browse_video, self._clear_video
        )
        layout.addLayout(vid_row)

        layout.addSpacing(4)
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
            path = to_portable_path(path)
            self._video_path = path
            _set_file_label(self._video_lbl, path)

    def _clear_video(self) -> None:
        self._video_path = None
        _set_file_label(self._video_lbl, None)

    def values(self) -> tuple[str, int, Optional[str]]:
        return self.text_edit.toPlainText().strip(), self.rating_spin.value(), self._video_path


# ---------------------------------------------------------------------------
# Collapsible hint card
# ---------------------------------------------------------------------------

class _HintCard(QFrame):
    """A compact card for one hint. Shows text + rating always; expands to
    reveal edit / delete / reorder controls when the header is clicked."""

    def __init__(self, hint, on_edit, on_delete, on_up, on_down, parent=None):
        super().__init__(parent)
        self._expanded = False
        self.setObjectName("hintCard")
        self.setStyleSheet("""
            QFrame#hintCard {
                background: #1A1A20;
                border: 1px solid #2A2A34;
                border-radius: 8px;
            }
            QFrame#hintCardDetail {
                background: #131316;
                border: none;
                border-top: 1px solid #2A2A34;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header (always visible) ────────────────────────────────────────
        header = QWidget()
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(12, 10, 12, 10)
        header_row.setSpacing(10)

        self._arrow = QLabel("▶")
        self._arrow.setFixedWidth(14)
        self._arrow.setStyleSheet("color: #55546A; font-size: 11px; background: transparent;")
        header_row.addWidget(self._arrow)

        text_lbl = QLabel(hint.text)
        text_lbl.setWordWrap(False)
        text_lbl.setStyleSheet("color: #C8C6D0; font-size: 13px; background: transparent;")
        header_row.addWidget(text_lbl, stretch=1)

        header_row.addWidget(RatingDots(hint.rating))

        if hint.video_path:
            vid_lbl = QLabel("▶ video")
            vid_lbl.setStyleSheet("color: #94A8C4; font-size: 11px; background: transparent;")
            vid_lbl.setToolTip(hint.video_path)
            header_row.addWidget(vid_lbl)

        outer.addWidget(header)

        # ── Detail panel (hidden until expanded) ──────────────────────────
        self._detail = QFrame()
        self._detail.setObjectName("hintCardDetail")
        detail_row = QHBoxLayout(self._detail)
        detail_row.setContentsMargins(38, 8, 12, 10)
        detail_row.setSpacing(8)

        full_lbl = QLabel(hint.text)
        full_lbl.setWordWrap(True)
        full_lbl.setStyleSheet("color: #A8A6B0; font-size: 12px; background: transparent;")
        detail_row.addWidget(full_lbl, stretch=1)

        for label, callback, style in (
            ("Edit",   on_edit,   ""),
            ("Delete", on_delete, "color: #F87171; border-color: #3D2020;"),
        ):
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setMinimumWidth(64)
            if style:
                btn.setStyleSheet(f"QPushButton {{ {style} }}")
            btn.clicked.connect(callback)
            detail_row.addWidget(btn)

        up_btn = QPushButton("↑")
        up_btn.setFixedSize(30, 30)
        up_btn.clicked.connect(on_up)
        detail_row.addWidget(up_btn)

        down_btn = QPushButton("↓")
        down_btn.setFixedSize(30, 30)
        down_btn.clicked.connect(on_down)
        detail_row.addWidget(down_btn)

        self._detail.setVisible(False)
        outer.addWidget(self._detail)

        header.mousePressEvent = lambda _: self._toggle()

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._detail.setVisible(self._expanded)
        self._arrow.setText("▼" if self._expanded else "▶")


# ---------------------------------------------------------------------------
# Objective (puzzle) editor
# ---------------------------------------------------------------------------

class ObjectiveEditorDialog(QDialog):
    """Set up a single puzzle: its title, answer code, GM notes,
    a checkpoint video that plays when it's solved, and its prepared hints."""

    def __init__(self, objective_id: int, parent=None):
        super().__init__(parent)
        self.objective_id = objective_id
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.Window)
        self.setStyleSheet(CONTROL_PANEL_STYLE)
        self.setMinimumWidth(580)
        self.resize(640, 640)
        self._build_ui()
        self._load()
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(
            screen.x() + (screen.width() - self.width()) // 2,
            screen.y() + max(10, (screen.height() - self.height()) // 2),
        )

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        # Title + code on one row
        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        title_col = QVBoxLayout()
        title_col.addWidget(_section_label("Puzzle Name"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("e.g. Find the hidden key")
        self.title_edit.editingFinished.connect(self._on_title_edited)
        title_col.addWidget(self.title_edit)
        top_row.addLayout(title_col, stretch=3)

        code_col = QVBoxLayout()
        code_col.addWidget(_section_label("Answer Code"))
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g. 1279")
        self.code_edit.setToolTip("The code or answer players need to find for this puzzle")
        self.code_edit.editingFinished.connect(self._on_code_edited)
        code_col.addWidget(self.code_edit)
        top_row.addLayout(code_col, stretch=1)
        layout.addLayout(top_row)

        # GM notes
        layout.addWidget(_section_label("Game Master Notes"))
        layout.addWidget(_caption("Private notes only you see in the Control Panel."))
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText("Optional notes for the game master…")
        self.description_edit.setFixedHeight(60)
        self.description_edit.textChanged.connect(self._on_description_edited)
        layout.addWidget(self.description_edit)

        # Checkpoint video
        layout.addWidget(_section_label("Checkpoint Video"))
        layout.addWidget(_caption("Plays automatically in the player window when you mark this puzzle solved."))
        vid_row, self._video_lbl = _file_row(
            "Video", MEDIA_FILE_FILTER, self._browse_checkpoint_video, self._clear_checkpoint_video
        )
        layout.addLayout(vid_row)

        # Hints — collapsible cards
        layout.addSpacing(6)
        hints_header_row = QHBoxLayout()
        hints_header_row.addWidget(_section_label("Prepared Hints"))
        hints_header_row.addStretch(1)
        add_btn = QPushButton("+ Add Hint")
        add_btn.setMinimumHeight(32)
        add_btn.setMinimumWidth(100)
        add_btn.clicked.connect(self._add_hint)
        hints_header_row.addWidget(add_btn)
        layout.addLayout(hints_header_row)
        layout.addWidget(_caption("Click a hint to expand it and edit or delete it."))

        self._hints_scroll = QScrollArea()
        self._hints_scroll.setWidgetResizable(True)
        self._hints_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._hints_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._hints_container = QWidget()
        self._hints_container.setStyleSheet("background: transparent;")
        self._hints_layout = QVBoxLayout(self._hints_container)
        self._hints_layout.setContentsMargins(0, 0, 0, 0)
        self._hints_layout.setSpacing(6)
        self._hints_layout.addStretch(1)

        self._hints_scroll.setWidget(self._hints_container)
        layout.addWidget(self._hints_scroll, stretch=1)

        layout.addSpacing(4)
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primaryButton")
        close_btn.setMinimumHeight(38)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _load(self) -> None:
        obj = database.get_objective(self.objective_id)
        if obj is None:
            return
        self.setWindowTitle(f"Puzzle Setup — {obj.title}")
        self.title_edit.setText(obj.title)
        self.code_edit.setText(obj.code or "")
        self.description_edit.blockSignals(True)
        self.description_edit.setPlainText(obj.description or "")
        self.description_edit.blockSignals(False)
        _set_file_label(self._video_lbl, obj.checkpoint_video_path)
        self._refresh_hints()

    def _on_title_edited(self) -> None:
        title = self.title_edit.text().strip()
        if title:
            database.update_objective(self.objective_id, title=title)
            self.setWindowTitle(f"Puzzle Setup — {title}")

    def _on_code_edited(self) -> None:
        database.update_objective(self.objective_id, code=self.code_edit.text().strip() or None)

    def _on_description_edited(self) -> None:
        database.update_objective(
            self.objective_id, description=self.description_edit.toPlainText().strip() or None
        )

    def _browse_checkpoint_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Checkpoint Video", "", MEDIA_FILE_FILTER)
        if path:
            path = to_portable_path(path)
            database.update_objective(self.objective_id, checkpoint_video_path=path)
            _set_file_label(self._video_lbl, path)

    def _clear_checkpoint_video(self) -> None:
        database.update_objective(self.objective_id, checkpoint_video_path=None)
        _set_file_label(self._video_lbl, None)

    def _refresh_hints(self) -> None:
        # Remove all cards but keep the trailing stretch
        while self._hints_layout.count() > 1:
            item = self._hints_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for hint in database.list_hints(self.objective_id):
            card = _HintCard(
                hint,
                on_edit=lambda _, h=hint: self._edit_hint(h.id),
                on_delete=lambda _, h=hint: self._delete_hint(h.id),
                on_up=lambda _, h=hint: self._move_hint(h.id, -1),
                on_down=lambda _, h=hint: self._move_hint(h.id, 1),
            )
            self._hints_layout.insertWidget(self._hints_layout.count() - 1, card)

        if self._hints_layout.count() == 1:
            empty = QLabel("No hints yet — click + Add Hint to get started.")
            empty.setStyleSheet("color: #55546A; font-size: 12px; padding: 12px;")
            self._hints_layout.insertWidget(0, empty)

    def _add_hint(self) -> None:
        dlg = HintEditorDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            text, rating, video_path = dlg.values()
            if text:
                database.add_hint(self.objective_id, text, rating=rating, video_path=video_path)
                self._refresh_hints()

    def _edit_hint(self, hint_id: int) -> None:
        hint = next((h for h in database.list_hints(self.objective_id) if h.id == hint_id), None)
        if hint is None:
            return
        dlg = HintEditorDialog(parent=self, text=hint.text, rating=hint.rating, video_path=hint.video_path)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            text, rating, video_path = dlg.values()
            if text:
                database.update_hint(hint_id, text=text, rating=rating, video_path=video_path)
                self._refresh_hints()

    def _delete_hint(self, hint_id: int) -> None:
        database.delete_hint(hint_id)
        self._refresh_hints()

    def _move_hint(self, hint_id: int, direction: int) -> None:
        database.move_hint(hint_id, direction)
        self._refresh_hints()


# ---------------------------------------------------------------------------
# Main room setup dialog
# ---------------------------------------------------------------------------

class RoomEditorDialog(QDialog):
    """Room Setup — all configuration for a room in one tabbed dialog."""

    def __init__(self, room_id: int, parent=None):
        super().__init__(parent)
        self.room_id = room_id
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.Window)
        self.setStyleSheet(CONTROL_PANEL_STYLE)
        self.setMinimumSize(720, 520)
        self.resize(800, 580)
        self._build_ui()
        self._load()
        self._center_on_screen()

    def _center_on_screen(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = screen.x() + (screen.width() - self.width()) // 2
        y = screen.y() + max(10, (screen.height() - self.height()) // 2)
        self.move(x, y)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_puzzles_tab(),      "  Puzzles  ")
        self.tabs.addTab(self._build_clue_counter_tab(), "  Clue Counter  ")
        self.tabs.addTab(self._build_media_tab(),        "  Media  ")
        self.tabs.addTab(self._build_general_tab(),      "  Settings  ")
        root.addWidget(self.tabs, stretch=1)

        footer = QWidget()
        footer.setObjectName("roomEditorFooter")
        footer.setStyleSheet(
            "QWidget#roomEditorFooter { background: #0A0A0B; border-top: 1px solid #2A2A34; }"
        )
        footer_row = QHBoxLayout(footer)
        footer_row.setContentsMargins(16, 10, 16, 10)
        footer_row.addStretch(1)
        done_btn = QPushButton("Done")
        done_btn.setObjectName("primaryButton")
        done_btn.setMinimumWidth(100)
        done_btn.setMinimumHeight(38)
        done_btn.clicked.connect(self.accept)
        footer_row.addWidget(done_btn)
        root.addWidget(footer)

    # -----------------------------------------------------------------------
    # Tab 1 — General
    # -----------------------------------------------------------------------

    def _build_general_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        layout.addWidget(_section_label("Room Name"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Stranger Things")
        self.name_edit.editingFinished.connect(self._on_name_edited)
        layout.addWidget(self.name_edit)

        dur_row = QHBoxLayout()
        dur_col = QVBoxLayout()
        dur_col.addWidget(_section_label("Session Duration (minutes)"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 600)
        self.duration_spin.setFixedWidth(100)
        self.duration_spin.editingFinished.connect(self._on_duration_changed)
        dur_col.addWidget(self.duration_spin)
        dur_row.addLayout(dur_col)
        dur_row.addSpacing(24)

        slug_col = QVBoxLayout()
        slug_col.addWidget(_section_label("Website Room ID"))
        slug_col.addWidget(_caption("Links this room to your online booking system for leaderboard tracking."))
        self.slug_combo = QComboBox()
        self.slug_combo.addItems(["(none)", "annabelle", "stranger-things", "breaking-bad"])
        self.slug_combo.currentTextChanged.connect(self._on_slug_changed)
        slug_col.addWidget(self.slug_combo)
        dur_row.addLayout(slug_col, stretch=1)
        layout.addLayout(dur_row)

        layout.addStretch(1)
        return page

    # -----------------------------------------------------------------------
    # Tab 2 — Puzzles
    # -----------------------------------------------------------------------

    def _build_puzzles_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        layout.addWidget(_section_label("Puzzles / Stages"))
        layout.addWidget(_caption(
            "Each puzzle is a stage of your room. Add prepared hints that you can send "
            "to players from the Control Panel. Double-click a puzzle to edit its hints."
        ))

        self.objectives_list = QListWidget()
        self.objectives_list.itemDoubleClicked.connect(lambda _: self._manage_objective())
        layout.addWidget(self.objectives_list, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        for label, slot in (
            ("+ Add Puzzle", self._add_objective),
            ("Edit Hints…",  self._manage_objective),
            ("Delete",       self._delete_objective),
        ):
            b = QPushButton(label)
            b.setMinimumHeight(34)
            b.setMinimumWidth(96)
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        btn_row.addStretch(1)
        for label, slot in (("↑", self._move_objective_up), ("↓", self._move_objective_down)):
            b = QPushButton(label)
            b.setFixedSize(34, 34)
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        return page

    # -----------------------------------------------------------------------
    # Tab 3 — Clue Counter
    # -----------------------------------------------------------------------

    def _build_clue_counter_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        layout.addWidget(_section_label("Number of Clues"))
        layout.addWidget(_caption(
            "How many clues the team is allowed to ask for during the session. "
            "Each one appears as a button in the Control Panel — click it when a clue is used."
        ))

        count_row = QHBoxLayout()
        count_row.setSpacing(12)
        self.clue_count_spin = QSpinBox()
        self.clue_count_spin.setRange(0, 20)
        self.clue_count_spin.setFixedWidth(80)
        self.clue_count_spin.setMinimumHeight(36)
        self.clue_count_spin.editingFinished.connect(self._on_clue_count_changed)
        self.clue_count_spin.valueChanged.connect(self._on_clue_count_changed)
        count_row.addWidget(self.clue_count_spin)
        count_row.addWidget(_caption("Set to 0 to disable the clue counter."))
        count_row.addStretch(1)
        layout.addLayout(count_row)

        layout.addStretch(1)
        return page

    # -----------------------------------------------------------------------
    # Tab 4 — Media
    # -----------------------------------------------------------------------

    def _build_media_tab(self) -> QWidget:
        # Outer page is just a container for the scroll area
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(0)

        def _row_block(caption_text, lbl_attr, file_filter, browse_fn, clear_fn):
            layout.addWidget(_caption(caption_text))
            row, lbl = _file_row("", file_filter, browse_fn, clear_fn)
            setattr(self, lbl_attr, lbl)
            layout.addLayout(row)
            layout.addSpacing(10)

        # --- Videos --------------------------------------------------------
        layout.addWidget(_section_label("Videos"))
        layout.addSpacing(6)
        _row_block("Briefing — English  (plays before the game starts)",
                   "intro_lbl", VIDEO_FILE_FILTER, self._browse_intro_video, self._clear_intro_video)
        _row_block("Briefing — French  (optional second language)",
                   "intro_fr_lbl", VIDEO_FILE_FILTER, self._browse_intro_video_fr, self._clear_intro_video_fr)
        _row_block("Ending video  (plays after the team escapes)",
                   "ending_lbl", VIDEO_FILE_FILTER, self._browse_ending_video, self._clear_ending_video)

        layout.addSpacing(6)

        # --- Player screen -------------------------------------------------
        layout.addWidget(_section_label("Player Screen"))
        layout.addSpacing(6)
        _row_block("Background image shown behind the timer on the player screen.",
                   "bg_lbl", IMAGE_FILE_FILTER, self._browse_background_image, self._clear_background_image)

        layout.addSpacing(6)

        # --- Audio ---------------------------------------------------------
        layout.addWidget(_section_label("Audio"))
        layout.addSpacing(6)
        _row_block("Alert sound  (plays when you send a message to players)",
                   "alert_lbl", AUDIO_FILE_FILTER, self._browse_alert_sound, self._clear_alert_sound)
        _row_block("Background music  (looped on the player screen during the game)",
                   "music_lbl", AUDIO_FILE_FILTER, self._browse_game_music, self._clear_game_music)
        _row_block("Success sound  (plays when the team escapes)",
                   "success_lbl", AUDIO_FILE_FILTER, self._browse_success_sound, self._clear_success_sound)
        _row_block("Fail / time-up sound  (plays when time runs out)",
                   "fail_lbl", AUDIO_FILE_FILTER, self._browse_fail_sound, self._clear_fail_sound)

        layout.addStretch(1)

        scroll.setWidget(inner)
        outer_layout.addWidget(scroll)
        return outer

    # -----------------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------------

    def _load(self) -> None:
        room = database.get_room(self.room_id)
        if room is None:
            return
        self.setWindowTitle(f"Room Setup — {room.name}")
        self.name_edit.setText(room.name)
        self.duration_spin.setValue(max(1, room.duration_seconds // 60))
        idx = self.slug_combo.findText(room.slug or "(none)")
        self.slug_combo.setCurrentIndex(max(0, idx))

        _set_file_label(self.intro_lbl,    room.intro_video_path)
        _set_file_label(self.intro_fr_lbl, room.intro_video_path_fr)
        _set_file_label(self.ending_lbl,   room.ending_video_path)
        _set_file_label(self.bg_lbl,       room.background_image_path)

        audio = database.get_audio_settings(self.room_id)
        _set_file_label(self.alert_lbl,   audio.alert_path)
        _set_file_label(self.music_lbl,   audio.game_music_path)
        _set_file_label(self.success_lbl, audio.success_path)
        _set_file_label(self.fail_lbl,    audio.fail_path)

        self._refresh_objectives()
        room = database.get_room(self.room_id)
        if room:
            self.clue_count_spin.blockSignals(True)
            self.clue_count_spin.setValue(room.clue_count)
            self.clue_count_spin.blockSignals(False)

    # -----------------------------------------------------------------------
    # General tab handlers
    # -----------------------------------------------------------------------

    def _on_name_edited(self) -> None:
        name = self.name_edit.text().strip()
        if name:
            database.update_room(self.room_id, name=name)
            self.setWindowTitle(f"Room Setup — {name}")

    def _on_duration_changed(self) -> None:
        database.update_room(self.room_id, duration_seconds=self.duration_spin.value() * 60)

    def _on_slug_changed(self, text: str) -> None:
        database.update_room(self.room_id, slug=text if text != "(none)" else None)

    # -----------------------------------------------------------------------
    # Puzzles tab
    # -----------------------------------------------------------------------

    def _build_objective_item_widget(self, objective) -> QWidget:
        widget = QWidget()
        row = QHBoxLayout(widget)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(10)

        col = QVBoxLayout()
        col.setSpacing(2)
        title_lbl = QLabel(objective.title)
        title_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        col.addWidget(title_lbl)

        meta_parts = []
        if objective.code:
            meta_parts.append(f"Code: {objective.code}")
        hint_count = len(database.list_hints(objective.id))
        meta_parts.append(f"{hint_count} hint{'s' if hint_count != 1 else ''}")
        meta_lbl = QLabel("  •  ".join(meta_parts))
        meta_lbl.setStyleSheet("color: #6B6A80; font-size: 11px;")
        col.addWidget(meta_lbl)
        row.addLayout(col, stretch=1)

        edit_btn = QPushButton("Edit Hints…")
        edit_btn.setMinimumWidth(100)
        edit_btn.setMinimumHeight(32)
        edit_btn.clicked.connect(lambda _, oid=objective.id: self._manage_objective_by_id(oid))
        row.addWidget(edit_btn)
        return widget

    def _refresh_objectives(self, select_id: Optional[int] = None) -> None:
        self.objectives_list.clear()
        for obj in database.list_objectives(self.room_id):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, obj.id)
            widget = self._build_objective_item_widget(obj)
            item.setSizeHint(widget.sizeHint())
            self.objectives_list.addItem(item)
            self.objectives_list.setItemWidget(item, widget)
            if obj.id == select_id:
                self.objectives_list.setCurrentItem(item)

    def _selected_objective_id(self) -> Optional[int]:
        item = self.objectives_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add_objective(self) -> None:
        title, ok = QInputDialog.getText(self, "Add Puzzle", "Puzzle name:")
        if ok and title.strip():
            new_id = database.add_objective(self.room_id, title.strip())
            self._refresh_objectives(select_id=new_id)
            self._manage_objective_by_id(new_id)

    def _manage_objective(self) -> None:
        obj_id = self._selected_objective_id()
        if obj_id:
            self._manage_objective_by_id(obj_id)

    def _manage_objective_by_id(self, objective_id: int) -> None:
        dlg = ObjectiveEditorDialog(objective_id, parent=self)
        dlg.exec()
        self._refresh_objectives(select_id=objective_id)

    def _delete_objective(self) -> None:
        obj_id = self._selected_objective_id()
        if obj_id is None:
            return
        if QMessageBox.question(self, "Delete Puzzle", "Delete this puzzle and all its hints?") \
                != QMessageBox.StandardButton.Yes:
            return
        database.delete_objective(obj_id)
        self._refresh_objectives()

    def _move_objective_up(self) -> None:
        obj_id = self._selected_objective_id()
        if obj_id:
            database.move_objective(obj_id, -1)
            self._refresh_objectives(select_id=obj_id)

    def _move_objective_down(self) -> None:
        obj_id = self._selected_objective_id()
        if obj_id:
            database.move_objective(obj_id, 1)
            self._refresh_objectives(select_id=obj_id)

    # -----------------------------------------------------------------------
    # Clue counter tab
    # -----------------------------------------------------------------------

    def _on_clue_count_changed(self) -> None:
        database.update_room(self.room_id, clue_count=self.clue_count_spin.value())

    # -----------------------------------------------------------------------
    # Media tab — videos
    # -----------------------------------------------------------------------

    def _browse_intro_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Briefing Video (English)", "", VIDEO_FILE_FILTER)
        if path:
            path = to_portable_path(path)
            database.update_room(self.room_id, intro_video_path=path)
            _set_file_label(self.intro_lbl, path)

    def _clear_intro_video(self) -> None:
        database.update_room(self.room_id, intro_video_path=None)
        _set_file_label(self.intro_lbl, None)

    def _browse_intro_video_fr(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Briefing Video (French)", "", VIDEO_FILE_FILTER)
        if path:
            path = to_portable_path(path)
            database.update_room(self.room_id, intro_video_path_fr=path)
            _set_file_label(self.intro_fr_lbl, path)

    def _clear_intro_video_fr(self) -> None:
        database.update_room(self.room_id, intro_video_path_fr=None)
        _set_file_label(self.intro_fr_lbl, None)

    def _browse_ending_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Ending Video", "", VIDEO_FILE_FILTER)
        if path:
            path = to_portable_path(path)
            database.update_room(self.room_id, ending_video_path=path)
            _set_file_label(self.ending_lbl, path)

    def _clear_ending_video(self) -> None:
        database.update_room(self.room_id, ending_video_path=None)
        _set_file_label(self.ending_lbl, None)

    def _browse_background_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Background Image", "", IMAGE_FILE_FILTER)
        if path:
            path = to_portable_path(path)
            database.update_room(self.room_id, background_image_path=path)
            _set_file_label(self.bg_lbl, path)

    def _clear_background_image(self) -> None:
        database.update_room(self.room_id, background_image_path=None)
        _set_file_label(self.bg_lbl, None)

    # -----------------------------------------------------------------------
    # Media tab — audio
    # -----------------------------------------------------------------------

    def _browse_alert_sound(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Alert Sound", "", AUDIO_FILE_FILTER)
        if path:
            path = to_portable_path(path)
            database.update_audio_settings(self.room_id, alert_path=path)
            _set_file_label(self.alert_lbl, path)

    def _clear_alert_sound(self) -> None:
        database.update_audio_settings(self.room_id, alert_path=None)
        _set_file_label(self.alert_lbl, None)

    def _browse_game_music(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Background Music", "", AUDIO_FILE_FILTER)
        if path:
            path = to_portable_path(path)
            database.update_audio_settings(self.room_id, game_music_path=path)
            _set_file_label(self.music_lbl, path)

    def _clear_game_music(self) -> None:
        database.update_audio_settings(self.room_id, game_music_path=None)
        _set_file_label(self.music_lbl, None)

    def _browse_success_sound(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Success Sound", "", AUDIO_FILE_FILTER)
        if path:
            path = to_portable_path(path)
            database.update_audio_settings(self.room_id, success_path=path)
            _set_file_label(self.success_lbl, path)

    def _clear_success_sound(self) -> None:
        database.update_audio_settings(self.room_id, success_path=None)
        _set_file_label(self.success_lbl, None)

    def _browse_fail_sound(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Fail Sound", "", AUDIO_FILE_FILTER)
        if path:
            path = to_portable_path(path)
            database.update_audio_settings(self.room_id, fail_path=path)
            _set_file_label(self.fail_lbl, path)

    def _clear_fail_sound(self) -> None:
        database.update_audio_settings(self.room_id, fail_path=None)
        _set_file_label(self.fail_lbl, None)
