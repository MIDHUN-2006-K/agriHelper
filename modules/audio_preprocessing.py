"""
Speech Preprocessing Module
Noise reduction, silence trimming, and audio normalization
to improve ASR accuracy in noisy farm environments.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class AudioPreprocessor:
    """Cleans and normalizes audio before sending to ASR."""

    def __init__(self, target_sample_rate: int = 16_000):
        self.target_sample_rate = target_sample_rate

    def preprocess(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Full preprocessing pipeline:
        1. Load audio
        2. Resample to target rate
        3. Convert to mono
        4. Reduce noise
        5. Trim silence
        6. Normalize amplitude
        7. Save cleaned audio

        Args:
            input_path: Path to raw WAV file.
            output_path: Path for cleaned WAV. Defaults to overwriting input.

        Returns:
            Path to the preprocessed WAV file.
        """
        from scipy.io import wavfile

        output_path = output_path or input_path
        logger.info(f"Preprocessing audio: {input_path}")

        # Step 1: Load
        sample_rate, audio = wavfile.read(input_path)
        audio = audio.astype(np.float32)
        logger.info(f"Loaded: {sample_rate}Hz, {len(audio)} samples, dtype={audio.dtype}")

        # Step 2: Convert to mono if stereo
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
            logger.info("Converted stereo to mono")

        # Step 3: Resample if needed
        if sample_rate != self.target_sample_rate:
            audio = self._resample(audio, sample_rate, self.target_sample_rate)
            sample_rate = self.target_sample_rate
            logger.info(f"Resampled to {self.target_sample_rate}Hz")

        # Step 4: Noise reduction
        audio = self._reduce_noise(audio, sample_rate)

        # Step 5: Trim silence
        audio = self._trim_silence(audio, sample_rate)

        # Step 6: Normalize amplitude
        audio = self._normalize(audio)

        # Step 7: Save
        # Convert back to int16 for WAV
        audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        wavfile.write(output_path, sample_rate, audio_int16)

        logger.info(f"Preprocessed audio saved: {output_path} ({len(audio_int16)/sample_rate:.2f}s)")
        print(f"🔧 Audio preprocessed: {len(audio_int16)/sample_rate:.2f}s")

        return output_path

    def _resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Resample audio to target sample rate using linear interpolation."""
        if orig_sr == target_sr:
            return audio

        duration = len(audio) / orig_sr
        target_length = int(duration * target_sr)
        indices = np.linspace(0, len(audio) - 1, target_length)
        resampled = np.interp(indices, np.arange(len(audio)), audio)
        return resampled.astype(np.float32)

    def _reduce_noise(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Reduce background noise using spectral gating.
        Uses noisereduce library if available, otherwise applies simple spectral subtraction.
        """
        try:
            import noisereduce as nr

            # Use first 0.5s as noise profile (assumes initial silence / ambient noise)
            noise_clip_length = int(0.5 * sample_rate)
            noise_clip = audio[:noise_clip_length] if len(audio) > noise_clip_length else audio

            reduced = nr.reduce_noise(
                y=audio,
                sr=sample_rate,
                y_noise=noise_clip,
                prop_decrease=0.75,
                stationary=True,
            )
            logger.info("Noise reduction applied (noisereduce)")
            return reduced.astype(np.float32)

        except ImportError:
            logger.warning("noisereduce not installed — applying simple high-pass filter")
            return self._simple_highpass(audio, sample_rate, cutoff=80)

    def _simple_highpass(self, audio: np.ndarray, sample_rate: int, cutoff: int = 80) -> np.ndarray:
        """Simple high-pass filter to remove low-frequency rumble."""
        from scipy.signal import butter, filtfilt

        nyquist = sample_rate / 2
        normalized_cutoff = cutoff / nyquist
        b, a = butter(4, normalized_cutoff, btype="high")
        filtered = filtfilt(b, a, audio)
        return filtered.astype(np.float32)

    def _trim_silence(
        self,
        audio: np.ndarray,
        sample_rate: int,
        threshold_db: float = -40.0,
        pad_ms: int = 200,
    ) -> np.ndarray:
        """
        Trim leading and trailing silence from audio.

        Args:
            audio: Audio signal (float32, normalized or not).
            sample_rate: Sample rate.
            threshold_db: dB threshold below which audio is considered silence.
            pad_ms: Padding in milliseconds to keep around speech.

        Returns:
            Trimmed audio array.
        """
        # Convert threshold from dB to linear
        max_amp = np.max(np.abs(audio)) if np.max(np.abs(audio)) > 0 else 1.0
        threshold_linear = max_amp * (10 ** (threshold_db / 20))

        # Frame-based energy detection
        frame_length = int(0.025 * sample_rate)  # 25ms frames
        hop_length = int(0.010 * sample_rate)     # 10ms hop

        energies = []
        for start in range(0, len(audio) - frame_length, hop_length):
            frame = audio[start : start + frame_length]
            rms = np.sqrt(np.mean(frame ** 2))
            energies.append(rms)

        energies = np.array(energies)

        # Find first and last frame above threshold
        above = np.where(energies > threshold_linear)[0]

        if len(above) == 0:
            logger.warning("All audio below silence threshold — returning original")
            return audio

        first_frame = above[0]
        last_frame = above[-1]

        pad_samples = int(pad_ms / 1000 * sample_rate)
        start_sample = max(0, first_frame * hop_length - pad_samples)
        end_sample = min(len(audio), (last_frame + 1) * hop_length + frame_length + pad_samples)

        trimmed = audio[start_sample:end_sample]
        logger.info(f"Trimmed silence: {len(audio)/sample_rate:.2f}s → {len(trimmed)/sample_rate:.2f}s")
        return trimmed

    def _normalize(self, audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
        """Normalize audio to target peak amplitude."""
        max_val = np.max(np.abs(audio))
        if max_val == 0:
            logger.warning("Audio is completely silent")
            return audio
        normalized = audio * (target_peak / max_val)
        return normalized

    def get_audio_quality_report(self, path: str) -> dict:
        """Generate a quality report for an audio file."""
        from scipy.io import wavfile

        sr, audio = wavfile.read(path)
        audio_f = audio.astype(np.float32)
        if audio_f.ndim > 1:
            audio_f = np.mean(audio_f, axis=1)

        max_amp = np.max(np.abs(audio_f))
        rms = np.sqrt(np.mean(audio_f ** 2))

        # Estimate SNR (rough)
        noise_floor = np.percentile(np.abs(audio_f), 10)
        snr_estimate = 20 * np.log10(rms / (noise_floor + 1e-10))

        return {
            "sample_rate": sr,
            "duration_seconds": round(len(audio_f) / sr, 2),
            "max_amplitude": round(float(max_amp), 2),
            "rms_energy": round(float(rms), 2),
            "estimated_snr_db": round(float(snr_estimate), 1),
            "is_clipping": bool(max_amp >= 32000 if audio.dtype == np.int16 else max_amp >= 0.99),
            "is_too_quiet": bool(rms < 500 if audio.dtype == np.int16 else rms < 0.02),
        }
