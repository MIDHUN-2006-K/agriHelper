"""
Text-to-speech adapter for AgriHelper API.
"""

import os
import time
import uuid
from typing import Optional

from config.settings import DATA_DIR, NEXUS_API_KEY, NEXUS_BASE_URL, NEXUS_MODEL_TTS
from database import log_latency
from modules.text_to_speech import TextToSpeech


TTS_ENGINE = TextToSpeech(
    api_key=NEXUS_API_KEY,
    base_url=NEXUS_BASE_URL,
    model=NEXUS_MODEL_TTS,
)


def generate_speech(text: str, session_id: str, language: str = "en") -> Optional[bytes]:
    start_time = time.time()
    output_path = DATA_DIR / f"tts_{session_id}_{uuid.uuid4().hex[:8]}.wav"
    try:
        path = TTS_ENGINE.synthesize(text=text, language=language, output_path=str(output_path))
        with open(path, "rb") as file_handle:
            audio_bytes = file_handle.read()
        log_latency(session_id, "tts", (time.time() - start_time) * 1000)
        return audio_bytes
    except Exception:
        log_latency(session_id, "tts_error", (time.time() - start_time) * 1000)
        return None
    finally:
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except OSError:
            pass
