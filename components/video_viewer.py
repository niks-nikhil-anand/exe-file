from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget
from config.styles import MEDIA_BUTTON_STYLE


class VideoViewer(QWidget):
    """Self-contained video player and playback controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #121212;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #000;")
        layout.addWidget(self.video_widget)

        self.controls_widget = QWidget()
        self.controls_widget.setFixedHeight(50)
        self.controls_widget.setStyleSheet("background-color: #1e1e1e; border-top: 1px solid #333;")
        self.controls_widget.hide()  # Hidden by default
        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(15, 5, 15, 5)
        controls_layout.setSpacing(10)

        self.play_button = QPushButton("▶")
        self.play_button.setFixedSize(40, 30)
        self.play_button.clicked.connect(self.toggle_play)
        controls_layout.addWidget(self.play_button)

        self.stop_button = QPushButton("⏹")
        self.stop_button.setFixedSize(40, 30)
        self.stop_button.clicked.connect(self.stop_playback)
        controls_layout.addWidget(self.stop_button)

        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)
        controls_layout.addWidget(self.position_slider)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #a0a0a0; font-family: monospace;")
        controls_layout.addWidget(self.time_label)

        self.speed_button = QPushButton("1.0x")
        self.speed_button.setFixedSize(50, 30)
        self.speed_button.clicked.connect(self.cycle_speed)
        controls_layout.addWidget(self.speed_button)

        self.mute_button = QPushButton("🔊")
        self.mute_button.setFixedSize(40, 30)
        self.mute_button.clicked.connect(self.toggle_mute)
        controls_layout.addWidget(self.mute_button)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self.set_volume)
        controls_layout.addWidget(self.volume_slider)
        layout.addWidget(self.controls_widget)

        for button in (self.play_button, self.stop_button, self.speed_button, self.mute_button):
            button.setStyleSheet(MEDIA_BUTTON_STYLE)

        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.positionChanged.connect(self._position_changed)
        self.media_player.durationChanged.connect(self._duration_changed)
        self.media_player.stateChanged.connect(self._state_changed)
        self.media_player.setVolume(70)
        self.last_volume = 70
        self.playback_speeds = [0.5, 1.0, 1.5, 2.0]
        self.current_speed_index = 1

    def set_fullscreen_mode(self, is_full):
        self.controls_widget.setVisible(is_full)

    def load_media(self, filepath):
        self.stop()
        self.play_button.setText("▶")
        self.time_label.setText("00:00 / 00:00")
        self.position_slider.setValue(0)
        self.current_speed_index = 1
        self.speed_button.setText("1.0x")
        self.media_player.setPlaybackRate(1.0)
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(filepath)))
        self.media_player.play()

    def stop(self):
        self.media_player.stop()
        
    def stop_playback(self):
        self.stop()
        self.position_slider.setValue(0)
        self.play_button.setText("▶")

    def cycle_speed(self):
        self.current_speed_index = (self.current_speed_index + 1) % len(self.playback_speeds)
        speed = self.playback_speeds[self.current_speed_index]
        self.media_player.setPlaybackRate(speed)
        self.speed_button.setText(f"{speed}x")

    def toggle_play(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def toggle_mute(self):
        muted = not self.media_player.isMuted()
        if muted:
            self.last_volume = self.volume_slider.value()
        self.media_player.setMuted(muted)
        self.mute_button.setText("🔇" if muted else "🔊")
        if not muted and self.volume_slider.value() == 0:
            self.volume_slider.setValue(self.last_volume)

    def set_volume(self, value):
        self.media_player.setVolume(value)
        self.media_player.setMuted(value == 0)
        self.mute_button.setText("🔇" if value == 0 else "🔊")

    def set_position(self, position):
        self.media_player.setPosition(position)

    def _position_changed(self, position):
        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(position)
        self._update_time(position, self.media_player.duration())

    def _duration_changed(self, duration):
        self.position_slider.setRange(0, duration)
        self._update_time(self.media_player.position(), duration)

    def _state_changed(self, state):
        self.play_button.setText("❚❚" if state == QMediaPlayer.PlayingState else "▶")

    def _update_time(self, position, duration):
        pos_seconds = position // 1000
        duration_seconds = duration // 1000
        self.time_label.setText(
            f"{pos_seconds // 60:02d}:{pos_seconds % 60:02d} / "
            f"{duration_seconds // 60:02d}:{duration_seconds % 60:02d}"
        )
