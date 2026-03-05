"""
Audio Playback Module
Plays synthesized speech audio to the farmer.
Supports WAV playback in Jupyter Notebook and terminal environments.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Plays audio files with multiple backend support."""

    def play(self, audio_path: str) -> bool:
        """
        Play an audio file.
        Tries multiple playback backends in order of preference.

        Args:
            audio_path: Path to the audio file.

        Returns:
            True if playback succeeded, False otherwise.
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            print(f"❌ Audio file not found: {audio_path}")
            return False

        logger.info(f"Playing audio: {audio_path}")

        # Try backends in order
        backends = [
            ("IPython.display", self._play_ipython),
            ("sounddevice", self._play_sounddevice),
            ("playsound", self._play_playsound),
            ("system", self._play_system),
        ]

        for name, player in backends:
            try:
                player(str(audio_path))
                logger.info(f"Playback successful via {name}")
                return True
            except Exception as e:
                logger.debug(f"{name} playback failed: {e}")
                continue

        logger.error("All playback backends failed")
        print(f"⚠️ Could not play audio. File saved at: {audio_path}")
        return False

    def play_in_notebook(self, audio_path: str):
        """
        Display audio player widget in Jupyter Notebook.
        Returns the IPython Audio widget for inline playback.
        """
        try:
            from IPython.display import Audio, display
            audio_widget = Audio(filename=str(audio_path), autoplay=True)
            display(audio_widget)
            print(f"🔊 Playing audio response...")
            return audio_widget
        except ImportError:
            logger.warning("IPython not available. Falling back to other playback methods.")
            self.play(audio_path)
            return None

    def _play_ipython(self, path: str):
        """Play using IPython (Jupyter Notebook)."""
        from IPython.display import Audio, display
        display(Audio(filename=path, autoplay=True))
        print("🔊 Playing audio response...")

    def _play_sounddevice(self, path: str):
        """Play using sounddevice."""
        import sounddevice as sd
        from scipy.io import wavfile

        sr, data = wavfile.read(path)
        print(f"🔊 Playing audio ({len(data)/sr:.1f}s)...")
        sd.play(data, sr)
        sd.wait()
        print("✅ Playback complete.")

    def _play_playsound(self, path: str):
        """Play using playsound library."""
        from playsound import playsound
        print(f"🔊 Playing audio...")
        playsound(path)
        print("✅ Playback complete.")

    def _play_system(self, path: str):
        """Play using system default player."""
        import subprocess
        import platform

        system = platform.system()
        print(f"🔊 Opening audio in system player...")

        if system == "Windows":
            subprocess.Popen(["start", "", path], shell=True)
        elif system == "Darwin":
            subprocess.Popen(["afplay", path])
        elif system == "Linux":
            subprocess.Popen(["aplay", path])
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

    @staticmethod
    def get_audio_duration(path: str) -> float:
        """Get duration of an audio file in seconds."""
        from scipy.io import wavfile
        sr, data = wavfile.read(path)
        return len(data) / sr
