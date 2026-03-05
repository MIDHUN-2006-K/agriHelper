"""
AgriHelper Configuration Module
Loads environment variables and provides centralized settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Resolve project root (two levels up from this file) ──────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# ── API Configuration ────────────────────────────────────────────────────────
NEXUS_API_KEY: str = os.getenv("NEXUS_API_KEY", "")
NEXUS_BASE_URL: str = os.getenv("NEXUS_BASE_URL", "https://apidev.navigatelabsai.com/")
NEXUS_MODEL_LLM: str = os.getenv("NEXUS_MODEL_LLM", "gemini-2.5-flash")
NEXUS_MODEL_STT: str = os.getenv("NEXUS_MODEL_STT", "whisper-1")
NEXUS_MODEL_TTS: str = os.getenv("NEXUS_MODEL_TTS", "gpt-4o-mini-tts")

# ── Audio Settings ────────────────────────────────────────────────────────────
AUDIO_SAMPLE_RATE: int = 16_000       # 16 kHz – optimal for Whisper
AUDIO_CHANNELS: int = 1               # Mono
AUDIO_DTYPE: str = "int16"
MAX_RECORD_SECONDS: int = 30          # Maximum recording duration
SILENCE_THRESHOLD: float = 0.01       # RMS threshold for silence detection
SILENCE_DURATION: float = 2.0         # Seconds of silence to stop recording

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = PROJECT_ROOT / "database" / "agrihelper.db"
AUDIO_INPUT_PATH = DATA_DIR / "input.wav"
AUDIO_OUTPUT_PATH = DATA_DIR / "response.wav"

# ── Supported Languages ──────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "ta": "Tamil",
    "hi": "Hindi",
    "en": "English",
}

# ── Ensure directories exist ─────────────────────────────────────────────────
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_openai_client():
    """Return an OpenAI-compatible client pointed at the Nexus API."""
    from openai import OpenAI
    return OpenAI(
        api_key=NEXUS_API_KEY,
        base_url=NEXUS_BASE_URL,
    )


def validate_config() -> dict:
    """Validate configuration and return a status dict."""
    issues = []
    if not NEXUS_API_KEY or NEXUS_API_KEY == "sk-":
        issues.append("NEXUS_API_KEY is not set or still default")
    if not NEXUS_BASE_URL:
        issues.append("NEXUS_BASE_URL is not set")
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "api_key_set": bool(NEXUS_API_KEY and NEXUS_API_KEY != "sk-"),
        "base_url": NEXUS_BASE_URL,
        "models": {
            "llm": NEXUS_MODEL_LLM,
            "stt": NEXUS_MODEL_STT,
            "tts": NEXUS_MODEL_TTS,
        },
    }
