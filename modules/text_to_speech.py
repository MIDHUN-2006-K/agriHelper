"""
Text-to-Speech Module
Converts response text to speech using the Nexus TTS API (GPT-4o-mini-tts).
Outputs WAV audio file for playback.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Voice configuration per language ──────────────────────────────────────────
VOICE_CONFIG = {
    "en": {"voice": "alloy", "speed": 1.0},
    "ta": {"voice": "nova", "speed": 0.95},   # Slightly slower for Tamil
    "hi": {"voice": "shimmer", "speed": 0.95}, # Slightly slower for Hindi
}

DEFAULT_VOICE = {"voice": "alloy", "speed": 1.0}


class TextToSpeech:
    """Synthesizes speech from text using GPT-4o-mini-tts via Nexus API."""

    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4o-mini-tts"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def synthesize(
        self,
        text: str,
        language: str = "en",
        output_path: Optional[str] = None,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> str:
        """
        Convert text to speech and save as audio file.

        Args:
            text: Text to synthesize.
            language: Language code ('en', 'ta', 'hi').
            output_path: Output file path. Auto-generated if None.
            voice: Override voice selection.
            speed: Override speech speed.

        Returns:
            Path to the generated audio file.
        """
        if not text or not text.strip():
            raise ValueError("Cannot synthesize empty text")

        output_path = output_path or str(Path("data") / "response.wav")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Get voice config for language
        config = VOICE_CONFIG.get(language, DEFAULT_VOICE)
        selected_voice = voice or config["voice"]
        selected_speed = speed or config["speed"]

        logger.info(f"TTS: '{text[:60]}...' → {output_path} (voice={selected_voice}, lang={language})")
        print(f"🔊 Synthesizing speech ({language})...")

        try:
            response = self.client.audio.speech.create(
                model=self.model,
                voice=selected_voice,
                input=text,
                speed=selected_speed,
                response_format="wav",
            )

            # Write complete audio to file — use .content for full bytes
            # (iter_bytes can truncate if generator is not fully consumed)
            try:
                # Preferred: write_to_file gets the complete response
                response.write_to_file(output_path)
            except AttributeError:
                # Fallback: read .content (all bytes at once)
                try:
                    audio_bytes = response.content
                    with open(output_path, "wb") as f:
                        f.write(audio_bytes)
                except AttributeError:
                    # Last resort: iter_bytes with explicit full read
                    with open(output_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)

            file_size = Path(output_path).stat().st_size
            logger.info(f"TTS output saved: {output_path} ({file_size} bytes)")
            print(f"✅ Speech generated: {output_path} ({file_size / 1024:.1f} KB)")

            return output_path

        except Exception as e:
            logger.error(f"TTS failed: {e}")
            # Try fallback with simpler parameters
            return self._fallback_tts(text, output_path, language)

    def _fallback_tts(self, text: str, output_path: str, language: str) -> str:
        """Fallback TTS using pyttsx3 (offline) if API fails."""
        logger.info("Attempting fallback TTS with pyttsx3...")
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", 150)

            # Try to set language-appropriate voice
            voices = engine.getProperty("voices")
            for v in voices:
                if language == "hi" and "hindi" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
                elif language == "ta" and "tamil" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break

            engine.save_to_file(text, output_path)
            engine.runAndWait()
            print(f"⚠️ Used offline TTS fallback: {output_path}")
            return output_path

        except Exception as fallback_error:
            logger.error(f"Fallback TTS also failed: {fallback_error}")
            raise RuntimeError(
                f"TTS failed with both API and fallback. "
                f"API error: Primary TTS unavailable. Fallback error: {fallback_error}"
            )

    def list_voices(self) -> list:
        """List available TTS voices."""
        return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
