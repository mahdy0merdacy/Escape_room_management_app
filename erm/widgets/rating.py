"""Small custom-painted widget for showing a 0-N "rating" as a row of dots."""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

from erm.constants import RATING_MAX
from erm.theme import RATING_EMPTY_COLOR, RATING_FILLED_COLOR


class RatingDots(QWidget):
    """Draws `max_rating` dots, filling the first `rating` of them.

    Used to show how "strong" a clue/hint is, e.g. ()()()()() for a rating
    of 0 up to a fully filled row for `max_rating`.
    """

    def __init__(self, rating: int = 0, max_rating: int = RATING_MAX, parent=None):
        super().__init__(parent)
        self._max_rating = max_rating
        self._rating = max(0, min(rating, max_rating))
        self._dot_size = 10
        self._spacing = 4

    def set_rating(self, rating: int) -> None:
        self._rating = max(0, min(rating, self._max_rating))
        self.update()

    def rating(self) -> int:
        return self._rating

    def sizeHint(self) -> QSize:
        width = self._max_rating * self._dot_size + (self._max_rating - 1) * self._spacing
        return QSize(width, self._dot_size)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(self._max_rating):
            x = i * (self._dot_size + self._spacing)
            color = RATING_FILLED_COLOR if i < self._rating else RATING_EMPTY_COLOR
            painter.setBrush(QColor(color))
            painter.drawEllipse(x, 0, self._dot_size, self._dot_size)
        painter.end()
