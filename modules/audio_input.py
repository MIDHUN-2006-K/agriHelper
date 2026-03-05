"""
Audio Input Module
Records farmer voice from microphone and saves as WAV file.
Handles noisy environments with configurable recording parameters.
"""

import wave
import struct
import math
import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Records audio from microphone with silence-based stop detection."""

    def __init__(
        self,
        sample_rate: int = 16_000,
        channels: int = 1,
        dtype: str = "int16",
        max_duration: int = 30,
        silence_threshold: float = 0.01,
        silence_duration: float = 2.0,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.max_duration = max_duration
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration

    def record(self, output_path: Optional[str] = None, duration: Optional[int] = None) -> str:
        """
        Record audio from microphone.

        Args:
            output_path: Path to save the WAV file. Auto-generated if None.
            duration: Fixed recording duration in seconds. If None, uses silence detection.

        Returns:
            Path to the saved WAV file.
        """
        import sounddevice as sd

        rec_duration = duration or self.max_duration
        output_path = output_path or str(Path("data") / "input.wav")

        logger.info(f"🎙️ Recording for up to {rec_duration}s at {self.sample_rate}Hz...")
        print(f"🎙️ Recording... (max {rec_duration}s — speak now)")

        # Record full block (non-streaming)
        audio_data = sd.rec(
            int(rec_duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
        )
        sd.wait()  # Block until recording finishes

        # If no fixed duration, trim trailing silence
        if duration is None:
            audio_data = self._trim_trailing_silence(audio_data)

        print(f"✅ Recording complete — {len(audio_data) / self.sample_rate:.1f}s captured")

        # Save to WAV
        self._save_wav(audio_data, output_path)
        logger.info(f"Audio saved to {output_path}")

        return output_path

    def record_with_auto_stop(self, output_path: Optional[str] = None) -> str:
        """
        Record with automatic stop on extended silence.
        Falls back to fixed-duration recording if sounddevice callback mode unavailable.
        """
        import sounddevice as sd

        output_path = output_path or str(Path("data") / "input.wav")
        frames = []
        silence_counter = 0
        max_silence_frames = int(self.silence_duration * self.sample_rate / 1024)

        print("🎙️ Recording with auto-stop (silence detection)... Speak now!")

        def callback(indata, frame_count, time_info, status):
            nonlocal silence_counter
            if status:
                logger.warning(f"Audio status: {status}")
            frames.append(indata.copy())

            # Check RMS energy
            rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
            normalized_rms = rms / 32768.0 if self.dtype == "int16" else rms

            if normalized_rms < self.silence_threshold:
                silence_counter += 1
            else:
                silence_counter = 0

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=1024,
                callback=callback,
            ):
                import time
                start = time.time()
                while True:
                    time.sleep(0.1)
                    elapsed = time.time() - start
                    if silence_counter >= max_silence_frames and elapsed > 1.0:
                        print("🔇 Silence detected — stopping.")
                        break
                    if elapsed >= self.max_duration:
                        print("⏱️ Maximum duration reached — stopping.")
                        break
        except Exception as e:
            logger.error(f"Auto-stop recording failed: {e}. Falling back to fixed recording.")
            return self.record(output_path, duration=10)

        if not frames:
            raise RuntimeError("No audio frames captured.")

        audio_data = np.concatenate(frames, axis=0)
        print(f"✅ Captured {len(audio_data) / self.sample_rate:.1f}s of audio")

        self._save_wav(audio_data, output_path)
        return output_path

    def _trim_trailing_silence(self, audio: np.ndarray, frame_size: int = 1024) -> np.ndarray:
        """Remove trailing silence from recorded audio."""
        if audio.ndim > 1:
            mono = audio[:, 0]
        else:
            mono = audio

        # Find last non-silent frame
        last_voice = 0
        for i in range(0, len(mono) - frame_size, frame_size):
            chunk = mono[i : i + frame_size].astype(np.float32)
            rms = np.sqrt(np.mean(chunk ** 2))
            normalized = rms / 32768.0 if self.dtype == "int16" else rms
            if normalized > self.silence_threshold:
                last_voice = i + frame_size

        # Keep a small tail buffer (0.5s)
        tail = int(0.5 * self.sample_rate)
        end_idx = min(last_voice + tail, len(audio))
        return audio[:end_idx] if end_idx > self.sample_rate else audio  # min 1s

    def _save_wav(self, audio_data: np.ndarray, path: str) -> None:
        """Save numpy audio array to WAV file."""
        from scipy.io import wavfile

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        if audio_data.ndim > 1 and self.channels == 1:
            audio_data = audio_data[:, 0]

        wavfile.write(path, self.sample_rate, audio_data)
        logger.info(f"WAV saved: {path} ({len(audio_data)} samples)")

    @staticmethod
    def load_wav(path: str) -> tuple:
        """
        Load a WAV file and return (sample_rate, audio_data).
        """
        from scipy.io import wavfile
        sample_rate, data = wavfile.read(path)
        return sample_rate, data

    @staticmethod
    def get_audio_info(path: str) -> dict:
        """Return metadata about a WAV file."""
        from scipy.io import wavfile
        sr, data = wavfile.read(path)
        return {
            "path": path,
            "sample_rate": sr,
            "channels": 1 if data.ndim == 1 else data.shape[1],
            "duration_seconds": round(len(data) / sr, 2),
            "samples": len(data),
            "dtype": str(data.dtype),
        }
