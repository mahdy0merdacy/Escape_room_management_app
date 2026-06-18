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


class ClueLockButton(QPushButton):
    """Checkable padlock button for the Control Panel's clue tracker.

    Checked = unlocked (open green padlock), unchecked = locked (closed
    gray padlock).  The icon is painted via QPainter so it renders on all
    platforms without relying on emoji fonts.
    """

    def __init__(self, label: str = "", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setToolTip(label)
        self.setFixedSize(40, 40)
        self._refresh_style()
        self.toggled.connect(self._refresh_style)

    def _refresh_style(self) -> None:
        bg, fg = (LOCK_UNLOCKED_BG, LOCK_UNLOCKED_FG) if self.isChecked() else (LOCK_LOCKED_BG, LOCK_LOCKED_FG)
        self.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; border-radius: 8px; }}"
        )
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(LOCK_UNLOCKED_FG if self.isChecked() else LOCK_LOCKED_FG)
        w, h = self.width(), self.height()

        pen = QPen(color)
        pen.setWidthF(w * 0.12)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self.isChecked():
            # Open lock: shackle swung up and to the right
            shackle = QRectF(w * 0.36, h * 0.02, w * 0.48, h * 0.48)
            painter.drawArc(shackle, 0, 200 * 16)
        else:
            # Closed lock: centered semicircle sitting on the body
            shackle = QRectF(w * 0.24, h * 0.05, w * 0.48, h * 0.48)
            painter.drawArc(shackle, 0, 180 * 16)

        # Lock body
        body = QRectF(w * 0.13, h * 0.44, w * 0.68, h * 0.44)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(body, w * 0.10, w * 0.10)
        painter.end()


class PlayerClueIcon(QWidget):
    """Read-only flat padlock icon for the player window's clue tracker.

    Dim olive while a clue hasn't been revealed yet; once the game master
    ticks it, it switches to bright gold to look "used"/found.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(112, 112)
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
