"""
Speech-to-text adapter for AgriHelper API.
"""

import os
import time
import uuid
from typing import Dict

from config.settings import DATA_DIR, NEXUS_API_KEY, NEXUS_BASE_URL, NEXUS_MODEL_STT
from database import log_latency
from modules.speech_to_text import SpeechToText


STT_ENGINE = SpeechToText(
    api_key=NEXUS_API_KEY,
    base_url=NEXUS_BASE_URL,
    model=NEXUS_MODEL_STT,
)


def validate_audio_format(audio_bytes: bytes) -> bool:
    if len(audio_bytes) < 44:
        return False
    return audio_bytes[0:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE"


def transcribe_audio(audio_bytes: bytes, session_id: str) -> Dict[str, str]:
    start_time = time.time()
    temp_path = DATA_DIR / f"stt_{session_id}_{uuid.uuid4().hex[:8]}.wav"
    if not validate_audio_format(audio_bytes):
       print("Invalid WAV format")
       return null
    try:
        with open(temp_path, "wb") as file_handle:
            file_handle.write(audio_bytes)

        result = STT_ENGINE.transcribe_with_retry(str(temp_path))
        latency_ms = (time.time() - start_time) * 1000

        if "error" in result:
            log_latency(session_id, "stt_error", latency_ms)
            return {"text": "", "language": "en"}

        log_latency(session_id, "stt", latency_ms)
        return {
            "text": result.get("text", "").strip(),
            "language": result.get("language", "en"),
        }
    except Exception:
        log_latency(session_id, "stt_error", (time.time() - start_time) * 1000)
        return {"text": "", "language": "en"}
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
    print("Received audio size:", len(audio_bytes))
