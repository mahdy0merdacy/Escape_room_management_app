"""Vertical mixer channel strip used by the Control Panel's Audio Mixer tab."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QSlider, QVBoxLayout, QWidget


class AudioChannelStrip(QWidget):
    """One channel of the Audio Mixer: name, mute, preview, status and a
    vertical volume slider (0-100)."""

    volume_changed = pyqtSignal(int)
    mute_toggled = pyqtSignal(bool)
    preview_clicked = pyqtSignal()

    def __init__(self, name: str, show_preview: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("audioChannelStrip")
        self.setFixedWidth(110)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.setSpacing(8)

        name_label = QLabel(name)
        name_label.setObjectName("audioChannelName")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        self.mute_button = QPushButton("\U0001F50A")
        self.mute_button.setCheckable(True)
        self.mute_button.setFixedWidth(40)
        self.mute_button.toggled.connect(self._on_mute_toggled)
        layout.addWidget(self.mute_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.preview_button = QPushButton("▶")
        self.preview_button.setFixedWidth(40)
        self.preview_button.clicked.connect(self.preview_clicked)
        self.preview_button.setVisible(show_preview)
        layout.addWidget(self.preview_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.status_label = QLabel("No Status")
        self.status_label.setObjectName("audioChannelStatus")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setRange(0, 100)
        self.slider.setValue(100)
        self.slider.setInvertedAppearance(True)
        self.slider.setMinimumHeight(140)
        self.slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.slider, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.value_label = QLabel("100")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)

    def _on_slider_changed(self, value: int) -> None:
        self.value_label.setText(str(value))
        self.volume_changed.emit(value)

    def _on_mute_toggled(self, checked: bool) -> None:
        self.mute_button.setText("\U0001F507" if checked else "\U0001F50A")
        self.mute_toggled.emit(checked)

    def set_volume(self, value: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.slider.blockSignals(False)
        self.value_label.setText(str(value))

    def set_muted(self, muted: bool) -> None:
        self.mute_button.blockSignals(True)
        self.mute_button.setChecked(muted)
        self.mute_button.setText("\U0001F507" if muted else "\U0001F50A")
        self.mute_button.blockSignals(False)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)
