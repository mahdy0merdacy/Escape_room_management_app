"""Player-facing display window.

Shows a big countdown timer by default. The game master can push a video
(briefing, checkpoint or hint videos) to this window at any time; once the
video finishes it automatically returns to the timer.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QSize, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontMetrics, QPixmap
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from erm.theme import PLAYER_WINDOW_STYLE
from erm.widgets.lock_button import PlayerClueIcon

MESSAGE_FADE_MS = 350
MUSIC_FADE_MS = 600

# The message box shrinks its font (down to this size) before it accepts
# any clipping, so very long messages still fit on screen.
MESSAGE_MIN_FONT_PX = 18
MESSAGE_FONT_STEP_PX = 2


class PlayerWindow(QWidget):
    """Player-facing display: countdown timer, with on-demand video playback."""

    video_finished = pyqtSignal()

    def __init__(self, room_name: str = "", parent=None):
        super().__init__(parent)
        title = f"Player Display - {room_name}" if room_name else "Player Display"
        self.setObjectName("playerWindowRoot")
        self.setWindowTitle(title)
        self.setStyleSheet(PLAYER_WINDOW_STYLE)
        self.resize(960, 540)

        self._clue_icons_hidden = False
        self._music_path: Optional[str] = None
        self._message_padding_size: Optional[QSize] = None
        self._message_base_font: Optional[QFont] = None
        self._background_pixmap: Optional[QPixmap] = None

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.stack = QStackedLayout()

        # --- Timer page -----------------------------------------------
        self.timer_page = QWidget()
        page_layout = QVBoxLayout(self.timer_page)
        page_layout.setContentsMargins(40, 32, 40, 32)

        # Compact timer badge, top-right - shown while a message is on screen
        top_row = QHBoxLayout()
        top_row.addStretch(1)
        self.compact_timer_label = QLabel("00:00")
        self.compact_timer_label.setObjectName("playerTimerCompact")
        self.compact_timer_label.hide()
        top_row.addWidget(self.compact_timer_label)
        page_layout.addLayout(top_row)

        self.center_stack = QStackedLayout()

        # Big centered timer + caption (default/idle view)
        self.timer_view = QWidget()
        timer_view_layout = QVBoxLayout(self.timer_view)
        timer_view_layout.addStretch(1)
        self.timer_caption_label = QLabel("Time Remaining")
        self.timer_caption_label.setObjectName("playerTimerCaption")
        self.timer_caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timer_view_layout.addWidget(self.timer_caption_label)
        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("playerTimer")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timer_view_layout.addWidget(self.timer_label)
        self.time_up_label = QLabel("TIME'S UP")
        self.time_up_label.setObjectName("playerTimeUp")
        self.time_up_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_up_label.hide()
        timer_view_layout.addWidget(self.time_up_label)
        timer_view_layout.addStretch(1)

        # Big centered message (shown while a message is active)
        self.message_view = QWidget()
        message_view_layout = QVBoxLayout(self.message_view)
        message_view_layout.setContentsMargins(48, 0, 48, 0)
        message_view_layout.addStretch(1)
        self.message_label = QLabel("")
        self.message_label.setObjectName("playerMessage")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_opacity_effect = QGraphicsOpacityEffect(self.message_label)
        self._message_opacity_effect.setOpacity(1.0)
        self.message_label.setGraphicsEffect(self._message_opacity_effect)
        message_view_layout.addWidget(self.message_label, 0, Qt.AlignmentFlag.AlignHCenter)
        message_view_layout.addStretch(1)

        self.center_stack.addWidget(self.timer_view)
        self.center_stack.addWidget(self.message_view)

        center_container = QWidget()
        center_container.setLayout(self.center_stack)
        page_layout.addWidget(center_container, stretch=1)
        self._center_container = center_container

        # --- Video page --------------------------------------------------
        self.video_page = QWidget()
        self.video_page.setObjectName("playerVideoPage")
        video_layout = QVBoxLayout(self.video_page)
        video_layout.setContentsMargins(0, 0, 0, 0)
        self.video_widget = QVideoWidget()
        video_layout.addWidget(self.video_widget)

        self.stack.addWidget(self.timer_page)
        self.stack.addWidget(self.video_page)

        stack_container = QWidget()
        stack_container.setLayout(self.stack)
        root.addWidget(stack_container, stretch=1)

        # --- Clue tracker strip --------------------------------------------
        self.clue_strip = QWidget()
        self.clue_strip_layout = QHBoxLayout(self.clue_strip)
        self.clue_strip_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clue_strip_layout.setSpacing(24)
        self.clue_strip.hide()
        root.addWidget(self.clue_strip)

        # --- Background image (sits behind everything else) -----------------
        self._background_label = QLabel(self)
        self._background_label.setObjectName("playerBackgroundImage")
        self._background_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._background_label.setGeometry(self.rect())
        self._background_label.lower()

        # --- Media player ---------------------------------------------------
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)

        # --- Background music player (loops for the duration of the game) --
        self.music_player = QMediaPlayer(self)
        self.music_audio_output = QAudioOutput(self)
        self.music_player.setAudioOutput(self.music_audio_output)
        self.music_player.setLoops(QMediaPlayer.Loops.Infinite)
        self._music_should_play = False
        self.music_player.mediaStatusChanged.connect(self._on_music_status_changed)

        self._music_target_volume = 1.0
        self._music_fade_animation = QPropertyAnimation(self.music_audio_output, b"volume", self)
        self._music_fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # --- Message fade animation -----------------------------------------
        self._message_animation = QPropertyAnimation(self._message_opacity_effect, b"opacity", self)
        self._message_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._message_animation.finished.connect(self._on_message_animation_finished)

        self._update_message_geometry()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_time(self, seconds: int) -> None:
        seconds = max(0, seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            text = f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            text = f"{minutes:02d}:{secs:02d}"
        self.timer_label.setText(text)
        self.compact_timer_label.setText(text)

    def show_time_up(self) -> None:
        self.show_timer()
        self._message_animation.stop()
        self.message_label.clear()
        self._message_opacity_effect.setOpacity(1.0)
        self.compact_timer_label.hide()
        self.center_stack.setCurrentWidget(self.timer_view)
        self.time_up_label.show()

    def show_timer(self) -> None:
        if self.stack.currentWidget() is self.video_page:
            self._fade_music_to(self._music_target_volume)
        if self.media_player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
            self.media_player.stop()
        self.stack.setCurrentWidget(self.timer_page)
        self._update_clue_strip_visibility()

    def play_video(self, path: str) -> None:
        self._fade_music_to(0.0)
        self.time_up_label.hide()
        self.stack.setCurrentWidget(self.video_page)
        self._update_clue_strip_visibility()
        self.media_player.setSource(QUrl.fromLocalFile(path))
        self.media_player.play()

    def set_video_volume(self, volume: float) -> None:
        self.audio_output.setVolume(max(0.0, min(1.0, volume)))

    def set_background_image(self, path: Optional[str]) -> None:
        pixmap = None
        if path and Path(path).exists():
            loaded = QPixmap(path)
            if not loaded.isNull():
                pixmap = loaded
        self._background_pixmap = pixmap
        self._update_background_pixmap()

    def set_music(self, path: Optional[str]) -> None:
        if path == self._music_path:
            return
        self._music_path = path
        self.music_player.stop()
        if path:
            self.music_player.setSource(QUrl.fromLocalFile(path))
            if self._music_should_play:
                self.music_player.play()
        else:
            self.music_player.setSource(QUrl())

    def set_music_volume(self, volume: float) -> None:
        self._music_target_volume = max(0.0, min(1.0, volume))
        if self.stack.currentWidget() is not self.video_page:
            self._fade_music_to(self._music_target_volume)

    def play_music(self) -> None:
        self._music_should_play = True
        if self._music_path and self.music_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self.music_player.play()

    def pause_music(self) -> None:
        self._music_should_play = False
        self.music_player.pause()

    def stop_music(self) -> None:
        self._music_should_play = False
        self.music_player.stop()

    def show_message(self, text: str) -> None:
        self.message_label.setText(text)
        self.compact_timer_label.show()
        self._update_message_geometry()
        self.center_stack.setCurrentWidget(self.message_view)
        self._animate_message(1.0)

    def clear_message(self) -> None:
        if not self.message_label.text():
            return
        self._animate_message(0.0)

    def set_clue_states(self, states: list[bool]) -> None:
        while self.clue_strip_layout.count():
            item = self.clue_strip_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for state in states:
            icon = PlayerClueIcon()
            icon.setChecked(state)
            self.clue_strip_layout.addWidget(icon)
        self._update_clue_strip_visibility()

    def set_clue_icons_hidden(self, hidden: bool) -> None:
        self._clue_icons_hidden = hidden
        self._update_clue_strip_visibility()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update_clue_strip_visibility(self) -> None:
        visible = (
            self.clue_strip_layout.count() > 0
            and not self._clue_icons_hidden
            and self.stack.currentWidget() is not self.video_page
        )
        self.clue_strip.setVisible(visible)

    def _update_background_pixmap(self) -> None:
        if self._background_pixmap is None or self.size().isEmpty():
            self._background_label.clear()
            return
        scaled = self._background_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._background_label.setPixmap(scaled)

    def _fade_music_to(self, volume: float) -> None:
        self._music_fade_animation.stop()
        self._music_fade_animation.setDuration(MUSIC_FADE_MS)
        self._music_fade_animation.setStartValue(self.music_audio_output.volume())
        self._music_fade_animation.setEndValue(volume)
        self._music_fade_animation.start()

    def _update_message_geometry(self) -> None:
        """Size the message box to fit its text: short messages stay a
        single line, longer ones wrap and the box grows wider/taller to
        fit. If it still wouldn't fit at the max box size, the font is
        shrunk (down to MESSAGE_MIN_FONT_PX) so nothing gets clipped."""
        text = self.message_label.text()
        if not text:
            self.message_label.setStyleSheet("")
            self.message_label.setFixedSize(self.message_label.sizeHint())
            return

        if self._message_padding_size is None:
            self.message_label.setText("")
            self._message_padding_size = self.message_label.sizeHint()
            self._message_base_font = self.message_label.font()
            self.message_label.setText(text)

        base_font = self._message_base_font
        h_padding = self._message_padding_size.width()
        v_padding = self._message_padding_size.height() - QFontMetrics(base_font).height()
        view_left, _view_top, view_right, _view_bottom = self.message_view.layout().getContentsMargins()
        max_width = max(320, self._center_container.width() - view_left - view_right)
        max_height = max(160, self._center_container.height())

        pixel_size = base_font.pixelSize()
        while True:
            font = QFont(base_font)
            font.setPixelSize(pixel_size)
            fm = QFontMetrics(font)
            line_height = fm.height() + v_padding

            single_line_width = fm.horizontalAdvance(text) + h_padding
            if single_line_width <= max_width:
                width, height = single_line_width, line_height
            else:
                width = max_width
                text_rect = fm.boundingRect(
                    0, 0, max(1, width - h_padding), 10_000, Qt.TextFlag.TextWordWrap, text
                )
                height = text_rect.height() + v_padding

            if height <= max_height or pixel_size <= MESSAGE_MIN_FONT_PX:
                break
            pixel_size -= MESSAGE_FONT_STEP_PX

        if pixel_size == base_font.pixelSize():
            self.message_label.setStyleSheet("")
        else:
            self.message_label.setStyleSheet(f"QLabel#playerMessage {{ font-size: {pixel_size}px; }}")

        self.message_label.setFixedSize(width, min(height, max_height))

    def _animate_message(self, target_opacity: float) -> None:
        self._message_animation.stop()
        self._message_animation.setDuration(MESSAGE_FADE_MS)
        self._message_animation.setStartValue(self._message_opacity_effect.opacity())
        self._message_animation.setEndValue(target_opacity)
        self._message_animation.start()

    def _on_message_animation_finished(self) -> None:
        if self._message_opacity_effect.opacity() <= 0.0:
            self.message_label.clear()
            self._update_message_geometry()
            self.compact_timer_label.hide()
            self.center_stack.setCurrentWidget(self.timer_view)
            self._message_opacity_effect.setOpacity(1.0)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.show_timer()
            self.video_finished.emit()

    def _on_music_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        # On some platforms play() called right after setSource() is a
        # no-op until the media finishes loading - retry once it's ready.
        if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
            if self._music_should_play and self.music_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self.music_player.play()

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._background_label.setGeometry(self.rect())
        self._update_background_pixmap()
        self._update_message_geometry()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
        else:
            super().keyPressEvent(event)
