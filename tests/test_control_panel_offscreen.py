"""Offscreen smoke test for the live Control Panel and Player Window.

Run with: QT_QPA_PLATFORM=offscreen python3 tests/test_control_panel_offscreen.py
(this script also sets the env var itself as a fallback).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from erm import database
from erm.control_panel import ControlPanelWindow
from erm.player_window import MUSIC_FADE_MS
from erm.widgets.lock_button import PlayerClueIcon

# Long enough for the player window's message fade animation (350ms) to finish.
MESSAGE_FADE_WAIT_MS = 500

# Long enough for the player window's background-music volume fade to finish.
MUSIC_FADE_WAIT_MS = MUSIC_FADE_MS + 150


def main():
    with tempfile.TemporaryDirectory() as tmp:
        database.DB_PATH = Path(tmp) / "test.db"
        database._connection = None
        database.init_db()

        app = QApplication.instance() or QApplication(sys.argv)

        room_id = database.create_room(
            "Test Room",
            duration_seconds=120,
            intro_video_path="/tmp/does-not-exist-intro.mp4",
            ending_video_path="/tmp/does-not-exist-ending.mp4",
        )
        database.update_room(room_id, intro_video_path_fr="/tmp/does-not-exist-intro-fr.mp4")
        obj1 = database.add_objective(
            room_id, "Find the key", checkpoint_video_path="/tmp/does-not-exist-cp.mp4"
        )
        obj2 = database.add_objective(room_id, "Open the door")
        database.add_hint(obj1, "Look in the drawer", rating=2)
        database.add_hint(
            obj1, "Use the UV light", rating=4, video_path="/tmp/does-not-exist-hint.mp4"
        )
        clue_a = database.add_clue(room_id, "Clue A")
        database.add_clue(room_id, "Clue B")

        # A real audio file so the background music actually transitions to
        # PlayingState (not just a volume-fade target).
        music_path = str(Path(__file__).resolve().parent.parent / "assets" / "sounds" / "alert.wav")
        database.update_audio_settings(room_id, game_music_path=music_path)

        panel = ControlPanelWindow(room_id)

        # Audio Mixer tab: default channel strips and page switching
        assert panel.page_stack.currentIndex() == 0
        assert set(panel.audio_strips.keys()) == {
            "alert", "game_music", "success", "fail", "video", "master"
        }
        for strip in panel.audio_strips.values():
            assert strip.slider.value() == 100
            assert strip.mute_button.isChecked() is False
            # Mixer sliders are inverted: full volume sits at the bottom of
            # the track and rises as you drag up.
            assert strip.slider.invertedAppearance() is True
        assert panel.audio_strips["alert"].status_label.text() == "No Status"
        assert panel.audio_strips["game_music"].status_label.text() == "Ready to Play"
        assert panel.audio_strips["video"].status_label.text() == "No Status"
        assert panel.audio_strips["master"].status_label.text() == "Master"

        QTest.mouseClick(panel.audio_mixer_tab, Qt.MouseButton.LeftButton)
        assert panel.page_stack.currentIndex() == 1
        QTest.mouseClick(panel.control_panel_tab, Qt.MouseButton.LeftButton)
        assert panel.page_stack.currentIndex() == 0

        # Objectives column: first objective selected by default, detail pane populated
        assert panel.objectives_list.count() == 2
        assert panel._selected_objective().id == obj1
        assert panel.detail_title_label.text() == "Find the key"
        assert panel.clues_detail_list.count() == 2

        # Selecting the second objective refreshes the detail pane
        panel.objectives_list.setCurrentRow(1)
        assert panel._selected_objective().id == obj2
        assert panel.clues_detail_list.count() == 0

        # Mark Complete toggles progress, the button label and the stat box.
        # obj1 has a checkpoint video, so this also lazily opens the player window.
        panel.objectives_list.setCurrentRow(0)
        assert panel.complete_button.text() == "Mark Complete"
        panel._toggle_objective_complete()
        assert database.get_objective(obj1).completed is True
        assert panel.complete_button.text() == "Mark Incomplete"
        assert panel.puzzles_stat[1].text() == "1/2"

        panel._toggle_objective_complete()
        assert database.get_objective(obj1).completed is False
        assert panel.puzzles_stat[1].text() == "0/2"

        # With a single (offscreen) screen, there's no secondary display to
        # auto-fullscreen the player window onto.
        assert panel._secondary_screen() is None

        player = panel._ensure_player_window()
        player.show_timer()

        # Videos sub-mixer: one strip per configured video on the room.
        expected_videos = {path for _, path in panel._list_room_videos()}
        assert set(panel.video_strips.keys()) == expected_videos
        for strip in panel.video_strips.values():
            assert strip.slider.invertedAppearance() is True

        # Audio mixer: "Game Music" volume changes fade the player window's
        # background music towards the new target volume.
        panel.audio_strips["game_music"].slider.setValue(40)
        assert database.get_audio_settings(room_id).game_music_volume == 40
        QTest.qWait(MUSIC_FADE_WAIT_MS)
        assert abs(player.music_audio_output.volume() - 0.4) < 1e-6

        panel.audio_strips["game_music"].slider.setValue(100)
        QTest.qWait(MUSIC_FADE_WAIT_MS)
        assert abs(player.music_audio_output.volume() - 1.0) < 1e-6

        # Preview buttons and lifecycle sound hooks must not raise even when
        # no custom audio files are configured for this room.
        for channel in panel.audio_strips:
            panel._on_audio_preview(channel)
        panel._play_alert_sound()
        panel._play_success_sound()
        panel._play_fail_sound()

        # Pushing a clue video for a missing file must not raise, and marks
        # it as the active video for the per-video volume sub-mixer.
        hint_video_path = "/tmp/does-not-exist-hint.mp4"
        panel._play_video(hint_video_path)
        assert panel._current_video_path == hint_video_path
        assert abs(player.audio_output.volume() - 1.0) < 1e-6

        # "Video" and "Master" channels scale the active video's volume.
        panel.audio_strips["video"].slider.setValue(50)
        assert database.get_audio_settings(room_id).video_volume == 50
        assert abs(player.audio_output.volume() - 0.5) < 1e-6

        panel.audio_strips["master"].mute_button.setChecked(True)
        assert database.get_audio_settings(room_id).master_muted is True
        assert player.audio_output.volume() == 0.0
        panel.audio_strips["master"].mute_button.setChecked(False)
        assert database.get_audio_settings(room_id).master_muted is False
        assert abs(player.audio_output.volume() - 0.5) < 1e-6

        panel.audio_strips["video"].slider.setValue(100)
        assert abs(player.audio_output.volume() - 1.0) < 1e-6

        # The active video's own strip persists independently per video and
        # applies on top of the "Video"/"Master" channels.
        hint_strip = panel.video_strips[hint_video_path]
        hint_strip.slider.setValue(60)
        assert database.get_video_volume(room_id, hint_video_path) == (60, False)
        assert abs(player.audio_output.volume() - 0.6) < 1e-6

        hint_strip.mute_button.setChecked(True)
        assert database.get_video_volume(room_id, hint_video_path) == (60, True)
        assert player.audio_output.volume() == 0.0
        hint_strip.mute_button.setChecked(False)
        assert database.get_video_volume(room_id, hint_video_path) == (60, False)
        assert abs(player.audio_output.volume() - 0.6) < 1e-6

        hint_strip.slider.setValue(100)
        assert abs(player.audio_output.volume() - 1.0) < 1e-6

        # Per-video preview buttons must not raise for missing files.
        for path in panel.video_strips:
            panel._on_video_preview(path)

        # Toggling the player window's fullscreen state must not raise, and
        # is idempotent when called twice.
        panel._on_toggle_player_fullscreen()
        panel._on_toggle_player_fullscreen()

        player.show_timer()

        base_font_px = player.message_label.font().pixelSize()

        def _max_message_width() -> int:
            view_left, _top, view_right, _bottom = player.message_view.layout().getContentsMargins()
            return max(320, player._center_container.width() - view_left - view_right)

        # The message box hugs short text instead of stretching full-width...
        player.show_message("Hi")
        QApplication.processEvents()
        max_width = _max_message_width()
        short_size = player.message_label.size()
        assert short_size.width() < max_width
        assert player.message_label.font().pixelSize() == base_font_px

        # ...but long messages wrap and grow taller to fit within the
        # available center area, without their text being clipped vertically,
        # and without growing the window itself.
        long_text = "This message is intentionally long. " * 5
        window_size_before = player.size()
        player.show_message(long_text)
        QApplication.processEvents()
        long_size = player.message_label.size()
        assert long_size.width() <= max_width
        assert long_size.height() > short_size.height()
        max_height = max(160, player._center_container.height())
        assert long_size.height() <= max_height
        assert player.size() == window_size_before

        # The compact timer badge stays within the window bounds, anchored
        # to the top-right corner (not pushed off-screen).
        badge_pos = player.compact_timer_label.pos()
        badge_size = player.compact_timer_label.size()
        assert badge_pos.x() + badge_size.width() <= player.width()
        assert badge_pos.y() + badge_size.height() <= player.height()

        # Resizing the player window re-fits the message box to the new width.
        player.resize(1600, 900)
        QApplication.processEvents()
        assert player.message_label.size().width() <= _max_message_width()

        # Extremely long messages shrink their font (instead of getting cut
        # off) so the whole message still fits within the available space.
        player.resize(960, 540)
        QApplication.processEvents()
        very_long_text = (
            "This is an extremely long message used to stress-test the "
            "wrapping and shrinking behaviour of the player window message box. "
        ) * 8
        player.show_message(very_long_text)
        QApplication.processEvents()
        very_long_size = player.message_label.size()
        max_height = max(160, player._center_container.height())
        assert very_long_size.height() <= max_height
        assert player.message_label.font().pixelSize() < base_font_px

        # Clear the test message before checking the idle state below.
        player.clear_message()
        QTest.qWait(MESSAGE_FADE_WAIT_MS)

        # Clearing the message also resets the font back to its default size.
        assert player.message_label.font().pixelSize() == base_font_px

        # Idle player window: caption + big centered timer, no message/badge
        player.show_timer()
        assert player.timer_caption_label.text() == "Time Remaining"
        assert player.center_stack.currentWidget() is player.timer_view
        assert player.compact_timer_label.isHidden() is True

        # Message feed: send updates the feed, the stat and the player banner.
        # The big timer is pushed into a small top-right badge while the
        # message becomes the centered focal point.
        panel.message_edit.setText("Hello players")
        panel._on_send_message()
        assert panel.feed_list.count() == 1
        assert panel.messages_stat[1].text() == "1"
        assert player.message_label.text() == "Hello players"
        assert player.center_stack.currentWidget() is player.message_view
        assert player.compact_timer_label.isHidden() is False

        # Clearing the player window dissipates the message (fade-out) and
        # restores the big centered timer with its caption.
        panel._on_clear_player_window()
        assert panel.feed_list.count() == 0
        QTest.qWait(MESSAGE_FADE_WAIT_MS)
        assert player.message_label.text() == ""
        assert player.center_stack.currentWidget() is player.timer_view
        assert player.compact_timer_label.isHidden() is True

        # Clue lock toggle propagates to the player window's clue strip, and
        # the corresponding icon flips from "locked" to "used" (color change)
        panel.clue_buttons[0].setChecked(True)
        assert database.get_clue_progress_map(room_id)[clue_a] is True
        assert player.clue_strip_layout.count() == 2
        clue_icon = player.clue_strip_layout.itemAt(0).widget()
        assert isinstance(clue_icon, PlayerClueIcon)
        assert clue_icon.isChecked() is True

        # "Hide clue icons on player window" toggle
        panel.hide_clue_icons_checkbox.setChecked(True)
        assert player.clue_strip.isHidden() is True
        panel.hide_clue_icons_checkbox.setChecked(False)
        assert player.clue_strip.isHidden() is False

        # The clue strip auto-hides while a video plays (so it doesn't show
        # the player background behind the lock icons) and reappears once
        # the video ends / show_timer() is called.
        player.play_video("/tmp/does-not-exist-cp.mp4")
        assert player.clue_strip.isHidden() is True
        player.show_timer()
        assert player.clue_strip.isHidden() is False

        # Start game: idle -> running, resets progress (incl. the clue we just checked)
        assert database.get_session(room_id).status == "idle"
        panel._on_start_pause()
        assert database.get_session(room_id).status == "running"
        assert panel.start_pause_button.text() == "Pause game"
        assert panel.timer.isActive()
        assert database.get_clue_progress_map(room_id).get(clue_a, False) is False

        # Tick decrements the remaining time
        panel._on_tick()
        assert database.get_session(room_id).remaining_seconds == 119

        # Add time
        panel.delta_spin.setValue(2)
        panel._on_add_time()
        session = database.get_session(room_id)
        assert session.remaining_seconds == 119 + 120
        assert panel.time_adjusted_stat[1].text() == "+2"

        # Pause
        panel._on_start_pause()
        assert database.get_session(room_id).status == "paused"
        assert panel.start_pause_button.text() == "Start game"
        assert not panel.timer.isActive()

        # Resume
        panel._on_start_pause()
        assert database.get_session(room_id).status == "running"
        assert panel.timer.isActive()

        # Simulate the timer reaching zero -> loss recorded
        database.save_session(room_id, "running", 1)
        panel._on_tick()
        assert database.get_room(room_id).losses == 1
        assert database.get_session(room_id).status == "completed"
        assert panel.start_pause_button.text() == "Start game"
        assert not panel.timer.isActive()

        # Reset game (bypassing the confirmation dialog) restores a fresh session
        panel._start_fresh_session()
        session = database.get_session(room_id)
        assert session.status == "running"
        assert session.remaining_seconds == 120
        assert session.messages_sent == 0
        assert session.time_adjusted_seconds == 0

        # _on_reset_game's reset leaves the session idle (timer not running)
        # until the game master presses "Start game"
        panel._on_tick()
        panel._start_fresh_session(status="idle")
        session = database.get_session(room_id)
        assert session.status == "idle"
        assert session.remaining_seconds == 120
        assert panel.start_pause_button.text() == "Start game"
        assert not panel.timer.isActive()

        panel._on_start_pause()
        assert database.get_session(room_id).status == "running"
        assert panel.timer.isActive()

        # Complete game records a win and pushes the ending video
        panel._on_complete_game()
        assert database.get_room(room_id).wins == 1
        assert database.get_room(room_id).losses == 1
        assert database.get_session(room_id).status == "completed"
        assert panel.start_pause_button.text() == "Start game"
        assert not panel.timer.isActive()

        # Briefing video buttons (EN/FR) are enabled and pushing them must not raise
        assert panel.briefing_video_en_button.isEnabled() is True
        assert panel.briefing_video_fr_button.isEnabled() is True
        panel._on_play_briefing_video_en()
        panel._on_play_briefing_video_fr()

        # Auto-start: when the briefing video finishes while the session is
        # still idle, the game auto-starts (idle -> running).
        panel._start_fresh_session(status="idle")
        assert database.get_session(room_id).status == "idle"
        panel._on_play_briefing_video_en()
        assert panel._current_video_path == panel.room.intro_video_path
        assert panel._video_finished_callback == panel._auto_start_after_briefing
        player._on_media_status_changed(QMediaPlayer.MediaStatus.EndOfMedia)
        assert database.get_session(room_id).status == "running"
        assert panel.timer.isActive()
        assert panel._video_finished_callback is None
        # Background music must actually start playing, not just have its
        # fade-target volume restored.
        assert player.music_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

        # Manual start is preserved: if the game master starts the game
        # themselves before the briefing video ends, the auto-start logic
        # must not undo it (e.g. by pausing) when EndOfMedia later fires.
        # It must also restore the background music volume, which
        # play_video() fades to 0 while the briefing plays.
        panel._start_fresh_session(status="idle")
        assert player.music_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState
        panel._on_play_briefing_video_en()
        QTest.qWait(MUSIC_FADE_WAIT_MS)
        assert player.music_audio_output.volume() == 0.0
        panel._on_start_pause()
        assert database.get_session(room_id).status == "running"
        assert player.music_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        QTest.qWait(MUSIC_FADE_WAIT_MS)
        assert abs(player.music_audio_output.volume() - 1.0) < 1e-6
        player._on_media_status_changed(QMediaPlayer.MediaStatus.EndOfMedia)
        assert database.get_session(room_id).status == "running"
        assert panel.timer.isActive()
        assert player.music_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        assert abs(player.music_audio_output.volume() - 1.0) < 1e-6

        # Player window background image: set via the room, applied to the
        # already-open player window on refresh, scaled to cover the window,
        # rescaled on resize, and cleared when removed.
        bg_path = str(Path(tmp) / "bg.png")
        bg_pixmap = QPixmap(200, 100)
        bg_pixmap.fill(QColor("blue"))
        bg_pixmap.save(bg_path, "PNG")

        def _covers(pixmap_size, window_size) -> bool:
            return pixmap_size.width() >= window_size.width() and pixmap_size.height() >= window_size.height()

        # No image configured: background label now shows a solid black fallback pixmap
        px = player._background_label.pixmap()
        assert px is not None and not px.isNull()
        database.update_room(room_id, background_image_path=bg_path)
        panel.refresh_all()
        QApplication.processEvents()
        bg = player._background_label.pixmap()
        assert bg is not None and not bg.isNull()
        assert _covers(bg.size(), player.size())

        player.resize(1024, 600)
        QApplication.processEvents()
        assert _covers(player._background_label.pixmap().size(), player.size())

        database.update_room(room_id, background_image_path=None)
        panel.refresh_all()
        QApplication.processEvents()
        # After clearing the image, background label reverts to the black fallback pixmap
        cleared = player._background_label.pixmap()
        assert cleared is not None and not cleared.isNull()

        # Bottom status bar reflects the recorded win/loss
        assert "Wins: 1" in panel.bottom_stats_label.text()
        assert "Losses: 1" in panel.bottom_stats_label.text()
        assert "50%" in panel.bottom_stats_label.text()

        panel.close()

    print("control_panel/player_window offscreen smoke test: OK")


if __name__ == "__main__":
    main()
