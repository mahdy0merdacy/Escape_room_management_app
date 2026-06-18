"""Alert sound generation and playback.

A short beep is synthesized once with the stdlib `wave` module so the
project doesn't need to ship or download any binary assets.
"""

import math
import struct
import sys
import wave
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect

from erm.paths import PROJECT_ROOT, app_data_dir

if getattr(sys, "frozen", False):
    ALERT_SOUND_PATH = app_data_dir() / "alert.wav"
else:
    ALERT_SOUND_PATH = PROJECT_ROOT / "assets" / "sounds" / "alert.wav"

_effect: Optional[QSoundEffect] = None
_file_player: Optional[QMediaPlayer] = None
_file_audio_output: Optional[QAudioOutput] = None
_sfx_player: Optional[QMediaPlayer] = None
_sfx_audio_output: Optional[QAudioOutput] = None
_sfx_should_play: bool = False
_sfx_on_finished: list = [None]  # mutable slot so the status handler can read/clear it


def ensure_alert_sound(path: Path = ALERT_SOUND_PATH) -> None:
    """Create a short sine-wave beep at `path` if it doesn't already exist."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)

    sample_rate = 44100
    duration_seconds = 0.2
    frequency_hz = 880.0
    amplitude = 0.5
    fade_seconds = 0.05
    n_samples = int(sample_rate * duration_seconds)

    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(n_samples):
            value = amplitude * math.sin(2 * math.pi * frequency_hz * i / sample_rate)
            fade = min(1.0, (n_samples - i) / (sample_rate * fade_seconds))
            sample = int(value * fade * 32767)
            wav_file.writeframes(struct.pack("<h", sample))


def effective_volume(
    channel_volume: int, channel_muted: bool, master_volume: int, master_muted: bool
) -> float:
    """Combine a channel's volume/mute with the master volume/mute into a
    single 0.0-1.0 value suitable for `QAudioOutput.setVolume()`."""
    if channel_muted or master_muted:
        return 0.0
    return (channel_volume / 100.0) * (master_volume / 100.0)


def effective_video_volume(
    video_volume: int,
    video_muted: bool,
    channel_volume: int,
    channel_muted: bool,
    master_volume: int,
    master_muted: bool,
) -> float:
    """Combine a per-video volume/mute with the "Video" channel and master
    volume/mute into a single 0.0-1.0 value."""
    if video_muted or channel_muted or master_muted:
        return 0.0
    return (video_volume / 100.0) * (channel_volume / 100.0) * (master_volume / 100.0)


def _on_sfx_status(status: QMediaPlayer.MediaStatus) -> None:
    global _sfx_should_play
    if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
        if _sfx_should_play and _sfx_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            _sfx_player.play()
    elif status == QMediaPlayer.MediaStatus.EndOfMedia:
        _sfx_should_play = False
        cb = _sfx_on_finished[0]
        _sfx_on_finished[0] = None
        if cb:
            cb()


def play_sfx(path: Optional[str], volume: float, on_finished=None) -> None:
    """Play a one-shot SFX file at `volume` (0.0–1.0).

    Handles Windows WMF load-before-play and calls `on_finished` when the
    clip ends.  Uses a dedicated player so it never conflicts with alert /
    success / fail one-shots.
    """
    global _sfx_player, _sfx_audio_output, _sfx_should_play
    if not path or not Path(path).exists():
        return
    if _sfx_player is None:
        _sfx_player = QMediaPlayer()
        _sfx_audio_output = QAudioOutput()
        _sfx_player.setAudioOutput(_sfx_audio_output)
        _sfx_player.mediaStatusChanged.connect(_on_sfx_status)
    _sfx_on_finished[0] = on_finished
    _sfx_audio_output.setVolume(max(0.0, min(1.0, volume)))
    _sfx_should_play = True
    _sfx_player.setSource(QUrl.fromLocalFile(path))
    _sfx_player.play()


def play_file(path: Optional[str], volume: float) -> None:
    """Play a one-shot custom audio file at `volume` (0.0-1.0).

    Requires a QApplication to already exist. No-ops if `path` is empty or
    doesn't exist.
    """
    global _file_player, _file_audio_output
    if not path or not Path(path).exists():
        return
    if _file_player is None:
        _file_player = QMediaPlayer()
        _file_audio_output = QAudioOutput()
        _file_player.setAudioOutput(_file_audio_output)
    _file_audio_output.setVolume(max(0.0, min(1.0, volume)))
    _file_player.setSource(QUrl.fromLocalFile(path))
    _file_player.play()


def play_alert(path: Optional[str] = None, volume: float = 0.6) -> None:
    """Play the alert sound. Requires a QApplication to already exist.

    If `path` is given, plays that custom audio file instead of the
    synthesized beep.
    """
    if path:
        play_file(path, volume)
        return

    global _effect
    ensure_alert_sound()
    if _effect is None:
        _effect = QSoundEffect()
        _effect.setSource(QUrl.fromLocalFile(str(ALERT_SOUND_PATH)))
    _effect.setVolume(max(0.0, min(1.0, volume)))
    _effect.play()


def play_success(path: Optional[str], volume: float) -> None:
    """Play a custom "success" sound, if one is configured."""
    if path:
        play_file(path, volume)


def play_fail(path: Optional[str], volume: float) -> None:
    """Play a custom "fail" sound, if one is configured."""
    if path:
        play_file(path, volume)
