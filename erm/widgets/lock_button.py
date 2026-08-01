"""Clue-counter widgets used in the Control Panel and player window."""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import QPushButton, QWidget

from erm.theme import PLAYER_LOCK_PENDING_COLOR, PLAYER_LOCK_USED_COLOR


def _draw_bulb(painter: QPainter, cx: float, cy: float, w: float, color: QColor, glow: bool) -> None:
    """Draw a simple lightbulb centred at (cx, cy) within a square of width w."""
    # Proportions relative to w
    bulb_r   = w * 0.30
    cap_w    = w * 0.38
    cap_h    = w * 0.14
    base_w   = w * 0.28
    base_h   = w * 0.08
    # Vertical layout: bulb centre at top third, cap below, base below that
    bulb_cy  = cy - w * 0.10
    cap_top  = bulb_cy + bulb_r * 0.68
    base_top = cap_top + cap_h + w * 0.01

    if glow:
        halo = QColor(color)
        halo.setAlpha(35)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(QRectF(cx - bulb_r * 1.55, bulb_cy - bulb_r * 1.55,
                                   bulb_r * 3.1, bulb_r * 3.1))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)

    # Bulb (circle)
    painter.drawEllipse(QRectF(cx - bulb_r, bulb_cy - bulb_r, bulb_r * 2, bulb_r * 2))

    # Cap (trapezoid base of the bulb)
    painter.drawRoundedRect(
        QRectF(cx - cap_w / 2, cap_top, cap_w, cap_h),
        w * 0.04, w * 0.04,
    )

    # Base tip
    painter.drawRoundedRect(
        QRectF(cx - base_w / 2, base_top, base_w, base_h),
        w * 0.03, w * 0.03,
    )


class ClueLockButton(QPushButton):
    """Checkable lightbulb button for the Control Panel's clue tracker.

    Unchecked = clue available (amber glow).
    Checked   = clue used / given out (dim gray).
    """

    def __init__(self, number: int = 1, parent=None):
        super().__init__("", parent)
        self._number = number
        self.setCheckable(True)
        self.setFixedSize(46, 46)
        self.setToolTip(f"Clue {number} — click when used")
        self._refresh_style()
        self.toggled.connect(self._refresh_style)

    def _refresh_style(self) -> None:
        if self.isChecked():
            self.setStyleSheet("""
                QPushButton {
                    background-color: #111114;
                    border: 1px solid #1E1E26;
                    border-radius: 10px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1C1408;
                    border: 1px solid #3D2E10;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #26190A;
                    border-color: #5A4418;
                }
            """)
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        color = QColor("#C9952A") if not self.isChecked() else QColor("#2A2A38")

        _draw_bulb(painter, w / 2, h / 2, min(w, h) * 0.92,
                   color, glow=not self.isChecked())
        painter.end()


class PlayerClueIcon(QWidget):
    """Lightbulb icon for the player window's clue tracker.

    Amber while available; dim gray once the clue has been given out.
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

        w, h = self.width(), self.height()
        color = QColor(PLAYER_LOCK_USED_COLOR if self._checked else PLAYER_LOCK_PENDING_COLOR)

        _draw_bulb(painter, w / 2, h / 2, min(w, h) * 0.88,
                   color, glow=not self._checked)
        painter.end()
