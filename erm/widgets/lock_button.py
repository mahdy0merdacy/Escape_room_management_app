"""Padlock-styled widgets used for the clue tracker."""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QPushButton, QWidget

from erm.theme import (
    LOCK_LOCKED_BG,
    LOCK_LOCKED_FG,
    LOCK_UNLOCKED_BG,
    LOCK_UNLOCKED_FG,
    PLAYER_LOCK_PENDING_COLOR,
    PLAYER_LOCK_USED_COLOR,
)

OPEN_LOCK = "\U0001F513"
CLOSED_LOCK = "\U0001F512"


class ClueLockButton(QPushButton):
    """Checkable padlock button for the Control Panel's clue tracker.

    Checked = unlocked (open green padlock), unchecked = locked (closed
    gray padlock).
    """

    def __init__(self, label: str = "", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setToolTip(label)
        self.setFixedSize(40, 40)
        self._refresh_style()
        self.toggled.connect(self._refresh_style)

    def _refresh_style(self) -> None:
        if self.isChecked():
            self.setText(OPEN_LOCK)
            bg, fg = LOCK_UNLOCKED_BG, LOCK_UNLOCKED_FG
        else:
            self.setText(CLOSED_LOCK)
            bg, fg = LOCK_LOCKED_BG, LOCK_LOCKED_FG
        self.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; color: {fg}; "
            f"border-radius: 8px; font-size: 18px; }}"
        )


class PlayerClueIcon(QWidget):
    """Read-only flat padlock icon for the player window's clue tracker.

    Dim olive while a clue hasn't been revealed yet; once the game master
    ticks it, it switches to bright gold to look "used"/found.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(56, 56)
        self._checked = False

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        if checked == self._checked:
            return
        self._checked = checked
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(PLAYER_LOCK_USED_COLOR if self._checked else PLAYER_LOCK_PENDING_COLOR)

        w, h = self.width(), self.height()
        shackle = QRectF(w * 0.28, h * 0.06, w * 0.44, h * 0.52)
        body = QRectF(w * 0.18, h * 0.42, w * 0.64, h * 0.46)

        pen = QPen(color)
        pen.setWidthF(w * 0.1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(shackle, 0, 180 * 16)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(body, w * 0.08, w * 0.08)
