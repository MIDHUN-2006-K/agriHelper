"""
Speech-to-Text (ASR) Module
Uses Whisper via the Nexus API for multilingual transcription.
Detects spoken language and returns structured output.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Language code mapping for Whisper output normalization
LANGUAGE_MAP = {
    "tamil": "ta",
    "hindi": "hi",
    "english": "en",
    "ta": "ta",
    "hi": "hi",
    "en": "en",
}

SUPPORTED_LANGUAGES = {"ta", "hi", "en"}


class SpeechToText:
    """Transcribes audio to text using Whisper (via Nexus OpenAI-compatible API)."""

    def __init__(self, api_key: str, base_url: str, model: str = "whisper-1"):
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

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> dict:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to WAV audio file.
            language: Optional ISO 639-1 language hint (e.g., 'ta', 'hi', 'en').

        Returns:
            {
                "language": "ta/hi/en",
                "text": "transcribed text",
                "confidence": float or None,
                "raw_response": dict
            }
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing: {audio_path} (model={self.model})")
        print(f"🗣️ Transcribing audio with Whisper ({self.model})...")

        try:
            with open(audio_path, "rb") as audio_file:
                # Build API parameters
                params = {
                    "model": self.model,
                    "file": audio_file,
                    "response_format": "verbose_json",
                }
                if language:
                    params["language"] = language

                response = self.client.audio.transcriptions.create(**params)

            # Parse response
            result = self._parse_response(response)
            logger.info(f"Transcription result: lang={result['language']}, text={result['text'][:80]}...")
            print(f"📝 Detected language: {result['language']} | Text: {result['text'][:100]}")
            return result

        except Exception as e:
            logger.error(f"ASR failed: {e}")
            return self._error_response(str(e))

    def _parse_response(self, response) -> dict:
        """Parse the Whisper API response into structured output."""
        # Handle different response formats
        if hasattr(response, "text"):
            text = response.text
        elif isinstance(response, dict):
            text = response.get("text", "")
        else:
            text = str(response)

        # Detect language from response
        detected_lang = None
        if hasattr(response, "language"):
            detected_lang = response.language
        elif isinstance(response, dict) and "language" in response:
            detected_lang = response["language"]

        # Normalize language code
        lang_code = self._normalize_language(detected_lang, text)

        return {
            "language": lang_code,
            "text": text.strip(),
            "confidence": getattr(response, "confidence", None),
            "raw_response": response if isinstance(response, dict) else str(response),
        }

    def _normalize_language(self, detected_lang: Optional[str], text: str) -> str:
        """Normalize language code to ta/hi/en."""
        if detected_lang:
            normalized = LANGUAGE_MAP.get(detected_lang.lower(), None)
            if normalized:
                return normalized

        # Fallback: detect from text script
        return self._detect_language_from_text(text)

    def _detect_language_from_text(self, text: str) -> str:
        """Detect language from text using Unicode script analysis."""
        tamil_chars = 0
        devanagari_chars = 0
        latin_chars = 0

        for char in text:
            code = ord(char)
            if 0x0B80 <= code <= 0x0BFF:  # Tamil block
                tamil_chars += 1
            elif 0x0900 <= code <= 0x097F:  # Devanagari block
                devanagari_chars += 1
            elif (0x0041 <= code <= 0x005A) or (0x0061 <= code <= 0x007A):  # Latin
                latin_chars += 1

        total = tamil_chars + devanagari_chars + latin_chars
        if total == 0:
            return "en"  # Default

        if tamil_chars / total > 0.3:
            return "ta"
        elif devanagari_chars / total > 0.3:
            return "hi"
        else:
            return "en"

    def _error_response(self, error_msg: str) -> dict:
        """Return a structured error response."""
        return {
            "language": "en",
            "text": "",
            "confidence": None,
            "error": error_msg,
            "raw_response": None,
        }

    def transcribe_with_retry(
        self,
        audio_path: str,
        language: Optional[str] = None,
        max_retries: int = 3,
    ) -> dict:
        """Transcribe with automatic retry on failure."""
        import time

        for attempt in range(1, max_retries + 1):
            result = self.transcribe(audio_path, language)
            if "error" not in result:
                return result
            logger.warning(f"Attempt {attempt}/{max_retries} failed: {result.get('error')}")
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.info(f"Retrying in {wait}s...")
                time.sleep(wait)

        logger.error("All transcription attempts failed")
        return result  # Return last error
