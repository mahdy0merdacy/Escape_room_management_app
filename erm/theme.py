"""Shared colors and Qt stylesheets for the dashboard (light) and the live
Control Panel (dark)."""

# ---------------------------------------------------------------------------
# Colors used by custom-painted widgets (rating dots, lock buttons, etc.)
# ---------------------------------------------------------------------------

RATING_FILLED_COLOR = "#F5C518"
RATING_EMPTY_COLOR = "#3A4257"

LOCK_UNLOCKED_BG = "#1F4D34"
LOCK_UNLOCKED_FG = "#3DDC84"
LOCK_LOCKED_BG = "#2A3245"
LOCK_LOCKED_FG = "#8B93A7"

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
}

QWidget#topBar, QWidget#bottomBar {
    background-color: #0D1019;
    border: none;
}

QLabel#topBarTitle {
    font-weight: 700;
    font-size: 15px;
    color: #F5F6FA;
}

QLabel#roomNameLabel {
    font-weight: 600;
    font-size: 15px;
    color: #C7CCDA;
}

QLabel#statusBarText {
    color: #8B93A7;
    font-size: 12px;
}

QWidget#columnPanel {
    background-color: #1B2230;
    border: 1px solid #2E3648;
    border-radius: 6px;
}

QLabel#columnHeader {
    background-color: #252C3D;
    font-weight: 700;
    font-size: 13px;
    padding: 10px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QLabel#objectiveTitle {
    font-size: 18px;
    font-weight: 700;
}

QLabel#objectiveCode, QLabel#clueTag {
    color: #8B93A7;
    font-size: 12px;
}

QLabel#objectiveDescription {
    color: #C7CCDA;
    font-size: 13px;
}

QLabel#sectionHeader {
    color: #8B93A7;
    font-weight: 700;
    font-size: 12px;
}

QFrame#columnSeparator {
    background-color: #3A4257;
    border: none;
}

QFrame#sectionSeparator {
    background-color: #2E3648;
    border: none;
}

QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    border-bottom: 1px solid #2E3648;
}
QListWidget::item:selected {
    background-color: #252C3D;
    border-left: 4px solid #F5C518;
}

QPushButton {
    background-color: #2A3245;
    color: #F5F6FA;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
}
QPushButton:hover {
    background-color: #37415A;
}
QPushButton:disabled {
    color: #5A6178;
    background-color: #1B2230;
}
QPushButton:checked {
    background-color: #37415A;
}

QPushButton#primaryButton {
    background-color: #3D5AFE;
    font-weight: 700;
    font-size: 14px;
    padding: 12px 14px;
}
QPushButton#primaryButton:hover {
    background-color: #5470FF;
}

QPushButton#dangerButton {
    color: #FF8A8A;
}

QPushButton#playVideoButton {
    background-color: #2F3A52;
    color: #9FC3FF;
    font-weight: 700;
}
QPushButton#playVideoButton:hover {
    background-color: #3D4D6E;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0D1019;
    border: 1px solid #2E3648;
    border-radius: 6px;
    padding: 8px;
    color: #F5F6FA;
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
}
QLabel#statBoxLabel {
    color: #8B93A7;
    font-size: 11px;
}

QSpinBox {
    background-color: #0D1019;
    border: 1px solid #2E3648;
    border-radius: 6px;
    padding: 4px;
    color: #F5F6FA;
}

QCheckBox {
    color: #C7CCDA;
    font-size: 12px;
}

QPushButton#tabButton {
    background-color: transparent;
    color: #8B93A7;
    font-weight: 700;
    font-size: 14px;
    padding: 10px 16px;
    border-radius: 0;
    border-bottom: 3px solid transparent;
}
QPushButton#tabButton:hover {
    color: #F5F6FA;
}
QPushButton#tabButton:checked {
    color: #F5F6FA;
    border-bottom: 3px solid #3D5AFE;
}

QWidget#audioChannelStrip {
    background-color: #1B2230;
    border: 1px solid #2E3648;
    border-radius: 6px;
}

QLabel#audioChannelName {
    font-weight: 700;
    font-size: 13px;
}

QLabel#audioChannelStatus {
    color: #8B93A7;
    font-size: 11px;
}

QLabel#audioMixerCaption {
    color: #8B93A7;
    font-size: 12px;
}

QSlider::groove:vertical {
    background-color: #0D1019;
    border: 1px solid #2E3648;
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
    background-color: #3D5AFE;
    border-radius: 3px;
}
QSlider::add-page:vertical {
    background-color: #37415A;
    border-radius: 3px;
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

QLabel#playerTimer {
    font-size: 120px;
    font-weight: 700;
    font-family: "DejaVu Sans Mono", "Consolas", monospace;
    color: #F5F6FA;
}

QLabel#playerTimerCaption {
    font-size: 28px;
    font-weight: 500;
    letter-spacing: 4px;
    color: #9AA3B8;
}

QLabel#playerTimerCompact {
    background-color: rgba(40, 46, 64, 230);
    color: #F5F6FA;
    font-size: 40px;
    font-weight: 700;
    font-family: "DejaVu Sans Mono", "Consolas", monospace;
    padding: 10px 26px;
    border-radius: 14px;
}

QLabel#playerTimeUp {
    font-size: 64px;
    font-weight: 700;
    color: #FF5C5C;
}

QLabel#playerMessage {
    background-color: rgba(27, 34, 48, 235);
    color: #FFFFFF;
    font-size: 44px;
    font-weight: 700;
    padding: 32px 44px;
    border-radius: 20px;
    border: 3px solid #E5484D;
}
"""
