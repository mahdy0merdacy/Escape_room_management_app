"""Shared colors and Qt stylesheets for the dashboard (light) and the live
Control Panel (dark)."""

# ---------------------------------------------------------------------------
# Colors used by custom-painted widgets (rating dots, lock buttons, etc.)
# ---------------------------------------------------------------------------

RATING_FILLED_COLOR = "#F5C518"
RATING_EMPTY_COLOR = "#3A4257"

LOCK_UNLOCKED_BG = "#2A3245"   # used/revealed → grey
LOCK_UNLOCKED_FG = "#8B93A7"
LOCK_LOCKED_BG = "#1F4D34"    # available/not yet sent → green
LOCK_LOCKED_FG = "#3DDC84"

# Player window clue tracker: bright gold while a clue is still locked
# (catches the eye), grayed out once the game master ticks it (used/revealed).
PLAYER_LOCK_PENDING_COLOR = "#F5C518"
PLAYER_LOCK_USED_COLOR = "#8B93A7"


# ---------------------------------------------------------------------------
# Dashboard (light theme)
# ---------------------------------------------------------------------------

DASHBOARD_STYLE = """
QMainWindow, QWidget#dashboardCentral, QWidget#dashboardScrollContent {
    background-color: #FFFFFF;
}

QLabel#pageTitle {
    font-size: 28px;
    font-weight: 700;
    color: #1A2744;
}

QLabel#sectionLabel {
    color: #6B7280;
    font-size: 13px;
}

QPushButton#primaryButton {
    background-color: #3D5AFE;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background-color: #2F46D6;
}

QPushButton#secondaryButton {
    background-color: #FFFFFF;
    color: #1A2744;
    border: 1px solid #D7DBE6;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: 600;
}
QPushButton#secondaryButton:hover {
    background-color: #F5F6FA;
}

QFrame#roomCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E5EC;
    border-radius: 8px;
}

QLabel#cardTitle {
    font-size: 18px;
    font-weight: 700;
    color: #1A2744;
}

QLabel#statLabel {
    color: #6B7280;
    font-size: 12px;
}

QLabel#statValue {
    color: #1A2744;
    font-weight: 700;
    font-size: 14px;
}

QPushButton#cardPrimaryButton {
    background-color: #3D5AFE;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#cardPrimaryButton:hover {
    background-color: #2F46D6;
}

QPushButton#cardSecondaryButton {
    background-color: #EEF0F6;
    color: #3D5AFE;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#cardSecondaryButton:hover {
    background-color: #E2E6F5;
}

QPushButton#cardMenuButton {
    background-color: transparent;
    border: none;
    color: #6B7280;
    font-size: 18px;
    font-weight: 700;
}
QPushButton#cardMenuButton:hover {
    color: #1A2744;
}

QFrame#newRoomCard {
    border: 2px dashed #D7DBE6;
    border-radius: 8px;
    background-color: #FFFFFF;
}

QPushButton#createRoomCardButton {
    background-color: #11151F;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-weight: 600;
}
QPushButton#createRoomCardButton:hover {
    background-color: #2A3245;
}

QComboBox {
    border: 1px solid #D7DBE6;
    border-radius: 6px;
    padding: 6px 10px;
    background-color: #FFFFFF;
    color: #1A2744;
}

QTableWidget {
    border: 1px solid #E2E5EC;
    gridline-color: #E2E5EC;
    background-color: #FFFFFF;
    color: #1A2744;
}
QHeaderView::section {
    background-color: #F5F6FA;
    color: #6B7280;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #E2E5EC;
    font-weight: 600;
}
"""


# ---------------------------------------------------------------------------
# Control Panel (dark theme)
# ---------------------------------------------------------------------------

CONTROL_PANEL_STYLE = """
QMainWindow, QWidget {
    background-color: #11151F;
    color: #F5F6FA;
    font-size: 13px;
}

QWidget#topBar, QWidget#bottomBar {
    background-color: #0A0D14;
    border: none;
}

QLabel#topBarTitle {
    font-weight: 700;
    font-size: 15px;
    color: #F5F6FA;
    letter-spacing: 1px;
}

QLabel#roomNameLabel {
    font-weight: 600;
    font-size: 15px;
    color: #C7CCDA;
}

QLabel#statusBarText {
    color: #6B7589;
    font-size: 12px;
}

QWidget#columnPanel {
    background-color: #181E2C;
    border: 1px solid #252E44;
    border-radius: 8px;
}

QLabel#columnHeader {
    background-color: #1F2739;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 1px;
    padding: 10px 12px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    color: #9AA3B8;
}

QLabel#objectiveTitle {
    font-size: 17px;
    font-weight: 700;
    color: #F5F6FA;
}

QLabel#objectiveCode, QLabel#clueTag {
    color: #6B7589;
    font-size: 12px;
}

QLabel#objectiveDescription {
    color: #B4BBCC;
    font-size: 13px;
}

QLabel#sectionHeader {
    color: #6B7589;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 1px;
}

QFrame#columnSeparator {
    background-color: #252E44;
    border: none;
}

QFrame#sectionSeparator {
    background-color: #1F2739;
    border: none;
}

QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    border-bottom: 1px solid #1F2739;
    padding: 2px 0;
    border-radius: 0;
}
QListWidget::item:hover {
    background-color: #1F2739;
}
QListWidget::item:selected {
    background-color: #232C40;
    border-left: 3px solid #F5C518;
}

/* Item widgets inside lists must be transparent so the list's hover/selected
   background shows through without dark rectangles behind each label. */
QWidget#objectiveItemWidget,
QWidget#objectiveItemWidget QLabel,
QWidget#clueCardWidget,
QWidget#clueCardWidget QLabel {
    background-color: transparent;
}

QPushButton {
    background-color: #232C40;
    color: #D4D8E5;
    border: 1px solid #2E3852;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #2E3852;
    color: #F5F6FA;
    border-color: #3D4D6E;
}
QPushButton:pressed {
    background-color: #1B2230;
    border-color: #252E44;
    color: #C7CCDA;
}
QPushButton:disabled {
    color: #4A5268;
    background-color: #161C28;
    border-color: #1F2739;
}
QPushButton:checked {
    background-color: #2E3852;
    border-color: #3D4D6E;
    color: #F5F6FA;
}

QPushButton#primaryButton {
    background-color: #3D5AFE;
    color: #FFFFFF;
    border: none;
    font-weight: 700;
    font-size: 14px;
    padding: 12px 14px;
}
QPushButton#primaryButton:hover {
    background-color: #5470FF;
}
QPushButton#primaryButton:pressed {
    background-color: #2A3FD6;
    border: none;
}

QPushButton#dangerButton {
    color: #FF8A8A;
    border-color: #4A2A2A;
}
QPushButton#dangerButton:hover {
    background-color: #3A1E1E;
    color: #FFB3B3;
}

QPushButton#playVideoButton {
    background-color: #1E2B3F;
    color: #7BAEE8;
    border: 1px solid #2A3D5C;
    font-weight: 700;
}
QPushButton#playVideoButton:hover {
    background-color: #263347;
    color: #9FC3FF;
}

QPushButton#sfxButton {
    background-color: #1E2E26;
    color: #5ECBA1;
    border: 1px solid #2A4036;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#sfxButton:hover {
    background-color: #263A2E;
    color: #7FDBBA;
    border-color: #3A5848;
}
QPushButton#sfxButton:pressed {
    background-color: #162219;
}

QPushButton#linkGroupButton {
    background-color: #2D2310;
    color: #F5A623;
    border: 1px solid #4A3A18;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#linkGroupButton:hover {
    background-color: #3A2E14;
    color: #FFB84D;
    border-color: #6A5428;
}
QPushButton#linkGroupButton:pressed {
    background-color: #1E1708;
}
QPushButton#linkGroupButton[linked="true"] {
    background-color: #1E2E26;
    color: #5ECBA1;
    border-color: #2A4036;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0D1019;
    border: 1px solid #252E44;
    border-radius: 6px;
    padding: 8px;
    color: #F5F6FA;
    selection-background-color: #2E3852;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #4A5A7E;
}

QLabel#timerLabel {
    font-size: 48px;
    font-weight: 700;
    font-family: "DejaVu Sans Mono", "Consolas", monospace;
    color: #E5E8F0;
}

QLabel#statBoxValue {
    font-size: 20px;
    font-weight: 700;
    color: #F5F6FA;
}
QLabel#statBoxLabel {
    color: #6B7589;
    font-size: 11px;
    letter-spacing: 1px;
}

QSpinBox {
    background-color: #0D1019;
    border: 1px solid #252E44;
    border-radius: 6px;
    padding: 4px;
    color: #F5F6FA;
}
QSpinBox:focus {
    border-color: #4A5A7E;
}

QCheckBox {
    color: #B4BBCC;
    font-size: 12px;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #3A4257;
    border-radius: 3px;
    background-color: #0D1019;
}
QCheckBox::indicator:checked {
    background-color: #3D5AFE;
    border-color: #5470FF;
}

QPushButton#tabButton {
    background-color: transparent;
    color: #6B7589;
    font-weight: 700;
    font-size: 14px;
    padding: 10px 16px;
    border-radius: 0;
    border: none;
    border-bottom: 3px solid transparent;
}
QPushButton#tabButton:hover {
    color: #C7CCDA;
    background-color: #161C28;
}
QPushButton#tabButton:checked {
    color: #F5F6FA;
    border-bottom: 3px solid #3D5AFE;
    background-color: transparent;
}

QWidget#mixerSectionCard {
    background-color: #181E2C;
    border: 1px solid #252E44;
    border-radius: 8px;
}

QLabel#mixerSectionTitle {
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 1px;
    color: #9AA3B8;
    padding-bottom: 2px;
}

QWidget#audioChannelStrip {
    background-color: #1F2739;
    border: 1px solid #2A3448;
    border-radius: 6px;
}

QLabel#audioChannelName {
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.5px;
    color: #C7CCDA;
}

QLabel#audioChannelStatus {
    color: #6B7589;
    font-size: 11px;
}

/* Mute toggle: "Off" (checked = muted) gets a red tint */
QWidget#audioChannelStrip QPushButton:checked {
    background-color: #4A1E1E;
    color: #FF8A8A;
    border-color: #6A2E2E;
}

QLabel#audioMixerCaption {
    color: #6B7589;
    font-size: 12px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:horizontal {
    background-color: #0D1019;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background-color: #3A4257;
    border-radius: 3px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #4A5268;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QScrollBar:vertical {
    background-color: #0D1019;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background-color: #3A4257;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background-color: #4A5268;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QSlider::groove:vertical {
    background-color: #0D1019;
    border: 1px solid #252E44;
    width: 6px;
    border-radius: 3px;
}
QSlider::handle:vertical {
    background-color: #3D5AFE;
    height: 16px;
    margin: 0 -6px;
    border-radius: 8px;
}
QSlider::handle:vertical:hover {
    background-color: #5470FF;
}
QSlider::sub-page:vertical {
    background-color: #252E44;
    border-radius: 3px;
}
QSlider::add-page:vertical {
    background-color: #3D5AFE;
    border-radius: 3px;
}

QMenu {
    background-color: #1B2230;
    border: 1px solid #2E3852;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 7px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #2E3852;
    color: #F5F6FA;
}
QMenu::separator {
    height: 1px;
    background-color: #2E3852;
    margin: 4px 8px;
}

QToolTip {
    background-color: #1B2230;
    color: #C7CCDA;
    border: 1px solid #2E3852;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
}
"""


# ---------------------------------------------------------------------------
# Player window (player-facing display)
# ---------------------------------------------------------------------------

PLAYER_WINDOW_STYLE = """
QWidget {
    color: #F5F6FA;
}

QWidget#playerWindowRoot {
    background-color: #000000;
}

QWidget#playerVideoPage {
    background-color: #000000;
}

QWidget#playerTimerPage,
QWidget#playerStackContainer,
QWidget#playerCenterContainer,
QWidget#playerTimerView,
QWidget#playerMessageView,
QWidget#playerClueStrip {
    background-color: transparent;
}

QLabel#playerTimer {
    font-size: 138px;
    font-weight: 700;
    font-family: "Impact", "DejaVu Sans Mono", "Consolas", monospace;
    color: #F5F6FA;
}

QLabel#playerTimerCaption {
    font-size: 32px;
    font-weight: 500;
    letter-spacing: 4px;
    color: #9AA3B8;
}

QLabel#playerTimerCompact {
    background-color: rgba(40, 46, 64, 230);
    color: #F5F6FA;
    font-size: 46px;
    font-weight: 700;
    font-family: "Impact", "DejaVu Sans Mono", "Consolas", monospace;
    padding: 10px 26px;
    border-radius: 14px;
}

QLabel#playerTimeUp {
    font-size: 74px;
    font-weight: 700;
    color: #FF5C5C;
}

QLabel#playerMessage {
    background-color: rgba(27, 34, 48, 235);
    color: #FFFFFF;
    font-size: 46px;
    font-weight: 700;
    font-family: "Segoe UI", "Arial", sans-serif;
    padding: 32px 44px;
    border-radius: 20px;
}
"""
