"""Qt-based audio playback shell for later player-window wiring."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class AudioPlaybackController:
    """Wrap a Qt media player behind a small, app-specific API."""

    def __init__(self) -> None:
        self._audio_output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        self._loaded_audio_path: Path | None = None

    @property
    def player(self) -> QMediaPlayer:
        """Expose the underlying player for later signal wiring."""

        return self._player

    @property
    def audio_output(self) -> QAudioOutput:
        """Expose the underlying audio output for later configuration."""

        return self._audio_output

    @property
    def loaded_audio_path(self) -> Path | None:
        """Return the currently loaded local audio path, if any."""

        return self._loaded_audio_path

    def load_audio(self, audio_path: str | Path) -> Path:
        """Load a local audio file into the Qt media player."""

        resolved_path = Path(audio_path).expanduser().resolve()
        self._player.setSource(QUrl.fromLocalFile(str(resolved_path)))
        self._loaded_audio_path = resolved_path
        return resolved_path

    def play(self) -> None:
        """Start or resume playback."""

        self._player.play()

    def pause(self) -> None:
        """Pause playback."""

        self._player.pause()

    def stop(self) -> None:
        """Stop playback and reset position to the start."""

        self._player.stop()

    def clear_audio(self) -> None:
        """Stop playback and unload the current media source."""

        self.stop()
        self._player.setSource(QUrl())
        self._loaded_audio_path = None

    def seek_to_ms(self, position_ms: int) -> int:
        """Seek to a clamped position in milliseconds."""

        clamped_position = self._clamp_position(position_ms)
        self._player.setPosition(clamped_position)
        return clamped_position

    def jump_by_ms(self, delta_ms: int) -> int:
        """Move playback position by a signed delta in milliseconds."""

        return self.seek_to_ms(self.position_ms() + delta_ms)

    def has_loaded_audio(self) -> bool:
        """Return whether a local audio file has been loaded."""

        return self._loaded_audio_path is not None

    def is_playing(self) -> bool:
        """Return whether playback is currently active."""

        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def is_paused(self) -> bool:
        """Return whether playback is currently paused."""

        return self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState

    def is_stopped(self) -> bool:
        """Return whether playback is currently stopped."""

        return self._player.playbackState() == QMediaPlayer.PlaybackState.StoppedState

    def can_seek(self) -> bool:
        """Return whether the current media supports seeking."""

        return self._player.isSeekable()

    def duration_ms(self) -> int:
        """Return the known media duration in milliseconds."""

        return max(0, self._player.duration())

    def position_ms(self) -> int:
        """Return the current playback position in milliseconds."""

        return max(0, self._player.position())

    def playback_state_name(self) -> str:
        """Return a stable string form of the Qt playback state."""

        state = self._player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            return "playing"
        if state == QMediaPlayer.PlaybackState.PausedState:
            return "paused"
        return "stopped"

    def set_volume(self, volume: float) -> float:
        """Set output volume using Qt's 0.0-1.0 floating range."""

        clamped_volume = min(max(volume, 0.0), 1.0)
        self._audio_output.setVolume(clamped_volume)
        return clamped_volume

    def volume(self) -> float:
        """Return the current output volume."""

        return self._audio_output.volume()

    def _clamp_position(self, position_ms: int) -> int:
        duration = self.duration_ms()
        if duration <= 0:
            return max(0, position_ms)
        return min(max(0, position_ms), duration)
