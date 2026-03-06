"""
Speech-to-Text module for AgriAssist
Primary: Nexus API (whisper-1) when NEXUS_API_KEY is set.
Fallback: Local openai-whisper model when API key is missing.
"""
import time
import tempfile
import os
import requests
import base64
import io
from requests.adapters import HTTPAdapter
from typing import Optional
from config import (
    NEXUS_BASE_URL,
    NEXUS_API_KEY,
    NEXUS_STT_PATH,
    STT_MODEL,
    STT_REQUEST_MODE,
    STT_TIMEOUT_SECONDS,
)
from database import log_latency


HTTP_SESSION = requests.Session()
HTTP_ADAPTER = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=0)
HTTP_SESSION.mount("http://", HTTP_ADAPTER)
HTTP_SESSION.mount("https://", HTTP_ADAPTER)

# Lazily loaded local Whisper model
_local_whisper_model = None


def _get_local_whisper():
    """Load local Whisper model (cached after first load)."""
    global _local_whisper_model
    if _local_whisper_model is None:
        try:
            import whisper
            print("Loading local Whisper model (base)... this may take a moment on first run.")
            _local_whisper_model = whisper.load_model("base")
            print("Local Whisper model loaded successfully.")
        except ImportError:
            print("ERROR: openai-whisper not installed. Run: pip install openai-whisper")
            return None
        except Exception as e:
            print(f"ERROR: Failed to load local Whisper model: {e}")
            return None
    return _local_whisper_model


def _transcribe_local_whisper(audio_bytes: bytes) -> str:
    """Transcribe using local Whisper model (no API key required)."""
    model = _get_local_whisper()
    if model is None:
        return ""

    try:
        import whisper
        import numpy as np

        # Write audio to a temp WAV file so Whisper can read it
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            result = model.transcribe(tmp_path, language="en", fp16=False)
            transcript = result.get("text", "").strip()
            return transcript
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    except Exception as e:
        print(f"Local Whisper transcription error: {e}")
        return ""


def transcribe_audio(audio_bytes: bytes, session_id: str) -> str:
    """
    Transcribe audio to text.

    Primary:  Nexus whisper-1 API (when NEXUS_API_KEY + NEXUS_BASE_URL are set).
    Fallback: Local openai-whisper model (works with no API key).

    Args:
        audio_bytes: Raw audio bytes (WAV format)
        session_id: Session ID for latency logging

    Returns:
        Transcribed text string (empty string on error)
    """
    start_time = time.time()

    # ── Path A: Nexus cloud API ──────────────────────────────────────────────
    if NEXUS_API_KEY and NEXUS_BASE_URL:

        def _extract_text(response: requests.Response) -> str:
            try:
                result = response.json()
                if isinstance(result, dict):
                    return (result.get("text") or result.get("transcript") or "").strip()
                if isinstance(result, str):
                    return result.strip()
                return ""
            except Exception:
                raw = response.text.strip()
                return raw if raw else ""

        # Attempt 1: multipart upload
        if STT_REQUEST_MODE in {"auto", "multipart"}:
            try:
                headers = {"Authorization": f"Bearer {NEXUS_API_KEY}"}
                data = {"model": STT_MODEL, "response_format": "json", "language": "en"}
                wav_stream = io.BytesIO(audio_bytes)
                files = {"file": ("audio.wav", wav_stream, "audio/wav")}
                response = HTTP_SESSION.post(
                    f"{NEXUS_BASE_URL}{NEXUS_STT_PATH}",
                    data=data, files=files, headers=headers,
                    timeout=STT_TIMEOUT_SECONDS
                )
                response.raise_for_status()
                transcript = _extract_text(response)
                latency_ms = (time.time() - start_time) * 1000
                log_latency(session_id, "stt", latency_ms)
                if transcript:
                    return transcript
            except requests.exceptions.RequestException as e:
                resp = getattr(e, "response", None)
                body = resp.text if resp is not None else ""
                print(f"STT API Error (multipart): {e} | Response: {body}")
                if STT_REQUEST_MODE == "multipart":
                    log_latency(session_id, "stt_error", (time.time() - start_time) * 1000)
                    return ""
            except Exception as e:
                print(f"STT Error (multipart): {e}")
                if STT_REQUEST_MODE == "multipart":
                    log_latency(session_id, "stt_error", (time.time() - start_time) * 1000)
                    return ""

        # Attempt 2: JSON/base64 fallback
        if STT_REQUEST_MODE in {"auto", "json"}:
            try:
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                payload = {"model": STT_MODEL, "audio": audio_b64, "response_format": "json", "language": "en"}
                headers = {"Authorization": f"Bearer {NEXUS_API_KEY}", "Content-Type": "application/json"}
                response = HTTP_SESSION.post(
                    f"{NEXUS_BASE_URL}{NEXUS_STT_PATH}",
                    json=payload, headers=headers,
                    timeout=STT_TIMEOUT_SECONDS
                )
                response.raise_for_status()
                transcript = _extract_text(response)
                latency_ms = (time.time() - start_time) * 1000
                log_latency(session_id, "stt", latency_ms)
                if transcript:
                    return transcript
            except requests.exceptions.RequestException as e:
                resp = getattr(e, "response", None)
                body = resp.text if resp is not None else ""
                print(f"STT API Error (json fallback): {e} | Response: {body}")
            except Exception as e:
                print(f"STT Error (json fallback): {e}")

        log_latency(session_id, "stt_error", (time.time() - start_time) * 1000)
        return ""

    # ── Path B: Local Whisper fallback (no API key) ──────────────────────────
    print("NEXUS_API_KEY not set — using local Whisper model for transcription.")
    transcript = _transcribe_local_whisper(audio_bytes)
    latency_ms = (time.time() - start_time) * 1000
    log_latency(session_id, "stt_local" if transcript else "stt_error", latency_ms)
    return transcript


def validate_audio_format(audio_bytes: bytes) -> bool:
    """
    Validate that audio is in WAV format.

    Args:
        audio_bytes: Raw audio bytes

    Returns:
        True if valid WAV format, False otherwise
    """
    if len(audio_bytes) < 44:
        return False
    if audio_bytes[0:4] != b'RIFF':
        return False
    if audio_bytes[8:12] != b'WAVE':
        return False
    return True
