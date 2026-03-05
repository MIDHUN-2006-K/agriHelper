"""
Configuration module for ClinAssist
Loads environment variables and defines system constants
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()


def _clean_env(value: str) -> str:
    if value is None:
        return ""
    return value.strip().strip('"').strip("'")

# Nexus API Configuration
NEXUS_API_KEY = _clean_env(os.getenv("NEXUS_API_KEY") or os.getenv("API_KEY"))
NEXUS_BASE_URL = _clean_env(os.getenv("NEXUS_BASE_URL") or os.getenv("BASE_URL", "")).rstrip("/")

# Endpoint paths (override in .env if Nexus uses non-standard routes)
NEXUS_CHAT_COMPLETIONS_PATH = os.getenv("NEXUS_CHAT_COMPLETIONS_PATH", "/v1/chat/completions")
NEXUS_TTS_PATH = os.getenv("NEXUS_TTS_PATH", "/v1/audio/speech")
NEXUS_STT_PATH = os.getenv("NEXUS_STT_PATH", "/v1/audio/transcriptions")


def _normalize_path(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


NEXUS_CHAT_COMPLETIONS_PATH = _normalize_path(NEXUS_CHAT_COMPLETIONS_PATH)
NEXUS_TTS_PATH = _normalize_path(NEXUS_TTS_PATH)
NEXUS_STT_PATH = _normalize_path(NEXUS_STT_PATH)

if not NEXUS_API_KEY or not NEXUS_BASE_URL:
    print("Warning: STT/LLM/TTS credentials are missing. Set NEXUS_API_KEY + NEXUS_BASE_URL (or API_KEY + BASE_URL) in .env.")

# API Headers for Nexus
NEXUS_HEADERS = {
    "Authorization": f"Bearer {NEXUS_API_KEY}",
    "Content-Type": "application/json"
}

# Model Configuration
STT_MODEL = "whisper-1"
LLM_MODEL = "gpt-4.1-nano"
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "alloy"

# STT request behavior
# auto: try multipart then json fallback
# multipart: only multipart (fastest when gateway is OpenAI-compatible)
# json: only json/base64 (fastest when gateway expects JSON)
STT_REQUEST_MODE = os.getenv("STT_REQUEST_MODE", "auto").strip().lower()
if STT_REQUEST_MODE not in {"auto", "multipart", "json"}:
    STT_REQUEST_MODE = "auto"

STT_TIMEOUT_SECONDS = int(os.getenv("STT_TIMEOUT_SECONDS", "30"))

# LLM and TTS timeout tuning
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "25"))
TTS_TIMEOUT_SECONDS = int(os.getenv("TTS_TIMEOUT_SECONDS", "20"))

# Latency optimization: for text endpoint, skip TTS by default (does not affect extraction/risk accuracy)
ENABLE_TTS_FOR_TEXT = os.getenv("ENABLE_TTS_FOR_TEXT", "0").strip().lower() in {"1", "true", "yes", "on"}

# LLM Parameters
LLM_TEMPERATURE = 0.2
LLM_MAX_RETRIES = 2

# Required Crop Issue Fields (9 attributes)
REQUIRED_FIELDS = [
    "primary_concern",
    "duration",
    "severity",
    "progression",
    "associated_issues",
    "affected_crop",
    "onset_type",
    "environmental_factors",
    "farm_management_history"
]

# Critical Issues Configuration
EMERGENCY_CONTEXTS = ["crop_disease", "pest_infestation", "drought", "nutrient_deficiency"]
EMERGENCY_FIELDS = ["duration", "severity"]

# Keywords for LLM Prompt Injection per Context
CONTEXT_FIELD_KEYWORDS = {
    "pest_infestation": {
        "duration": ["when did you first notice the pests", "how long have they been present", "time of first detection"],
        "severity": ["infestation level 1 to 10", "how widespread"],
        "progression": ["getting worse", "pest population growing", "spreading to other areas"],
        "associated_issues": ["leaf damage", "wilting", "reduced yield", "other crop problems"],
        "affected_crop": ["which crop", "what plant"],
        "onset_type": ["happened suddenly", "gradually increased"],
    },
    "crop_disease": {
        "duration": ["when did the disease first appear", "how many days since symptoms"],
        "severity": ["disease severity scale 1 to 10"],
        "progression": ["disease spreading", "getting worse over time"],
        "associated_issues": ["leaf discoloration", "stem rot", "blight", "wilting"],
        "affected_crop": ["which crop", "affected plant type"],
        "onset_type": ["started suddenly", "came on gradually"],
    },
    "drought": {
        "duration": ["how long since last significant rainfall"],
        "severity": ["drought stress level 1-10"],
        "progression": ["soil moisture decreasing", "plant stress worsening"],
        "associated_issues": ["wilting", "reduced growth", "increased pest vulnerability"],
        "affected_crop": ["which crop is affected", "what field"],
        "onset_type": ["sudden dry spell", "gradual water deficit"],
    },
    "nutrient_deficiency": {
        "duration": ["when did you notice the symptoms"],
        "severity": ["deficiency level 1-10", "how noticeable is it"],
        "progression": ["symptoms spreading", "more plants affected"],
        "associated_issues": ["yellowing leaves", "stunted growth", "poor productivity"],
        "affected_crop": ["which crop", "what section of field"],
        "onset_type": ["sudden appearance", "gradual decline"],
    },
    "soil_health": {
        "duration": ["how long has this issue been present"],
        "severity": ["soil quality score 1-10"],
        "progression": ["degradation worsening", "compaction increasing"],
        "associated_issues": ["poor drainage", "low fertility", "erosion"],
        "affected_crop": ["which field", "which crop"],
        "onset_type": ["sudden event", "long-term degradation"],
    },
    "weather_damage": {
        "duration": ["when did the damage occur"],
        "severity": ["damage level 1-10"],
        "progression": ["damage extent", "affected area growing"],
        "associated_issues": ["lodging", "broken stems", "leaf shredding"],
        "affected_crop": ["which crop affected", "what area"],
        "onset_type": ["sudden storm", "gradual environmental stress"],
    },
    "irrigation_issues": {
        "duration": ["when did the irrigation problem start"],
        "severity": ["water availability impact 1-10"],
        "progression": ["water stress increasing"],
        "associated_issues": ["uneven water distribution", "plant stress", "reduced yield"],
        "affected_crop": ["which field", "which crop type"],
        "onset_type": ["equipment failure", "gradual system degradation"],
    },
    "weed_pressure": {
        "duration": ["when did weed problems start"],
        "severity": ["weed coverage percentage 1-10 scale"],
        "progression": ["weed population growing", "coverage expanding"],
        "associated_issues": ["competition for nutrients", "reduced crop yield"],
        "affected_crop": ["which field", "which crop"],
        "onset_type": ["sudden outbreak", "gradual buildup"],
    },
    "seed_quality": {
        "duration": ["when did germination issues appear"],
        "severity": ["germination failure rate 1-10 scale"],
        "progression": ["more seeds failing", "emergence rate declining"],
        "associated_issues": ["poor plant stand", "stunted growth"],
        "affected_crop": ["which crop variety", "which field"],
        "onset_type": ["noticed at emergence", "gradual decline"],
    },
    "post_harvest": {
        "duration": ["how long have post-harvest issues been occurring"],
        "severity": ["crop loss percentage 1-10 scale"],
        "progression": ["deterioration worsening", "losses increasing"],
        "associated_issues": ["mold", "pest damage", "improper storage"],
        "affected_crop": ["which crop", "storage location"],
        "onset_type": ["immediate after harvest", "gradual onset"],
    }
}

# Generic Keywords fallback for fields not defined in specific context
GENERIC_FIELD_KEYWORDS = {
    "duration": ["how long", "when did it start"],
    "severity": ["how bad", "scale 1 to 10"],
    "progression": ["getting better or worse", "changing"],
    "associated_issues": ["any other problems", "besides the main issue"],
    "affected_crop": ["which crop", "field location"],
    "onset_type": ["sudden", "gradual"],
    "environmental_factors": ["weather conditions", "recent rainfall", "temperature"],
    "farm_management_history": ["farming practices", "recent treatments", "field history"]
}

# Field Priority for Clarification Questions
FIELD_PRIORITY = {
    "primary_concern": 1,
    "severity": 2,
    "duration": 3,
    "progression": 4,
    "onset_type": 5,
    "affected_crop": 6,
    "associated_issues": 7,
    "environmental_factors": 8,
    "farm_management_history": 9
}

# Valid Enum Values
VALID_PROGRESSIONS = ["improving", "worsening", "stable"]
VALID_ONSET_TYPES = ["sudden", "gradual"]

# Database Configuration
BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / "agriassist.db"

# Audio Output Configuration
AUDIO_OUTPUT_DIR = BASE_DIR / "audio_output"
AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)

# Evaluation Configuration
EVALUATION_SAMPLES_DIR = BASE_DIR / "evaluation_samples"
EVALUATION_SAMPLES_DIR.mkdir(exist_ok=True)

# System States
STATES = {
    "GREETING": "greeting",
    "COLLECTING": "collecting",
    "CLARIFYING": "clarifying",
    "SUMMARIZING": "summarizing",
    "COMPLETE": "complete",
    "QA": "qa"
}

# Safety Disclaimers
SAFETY_DISCLAIMER = (
    "AgriAssist is a structured farm assessment support tool and does not provide "
    "professional agronomic advice. This system does not replace an agronomist or agricultural extension service."
)

LLM_SAFETY_INSTRUCTIONS = """
CRITICAL SAFETY RULES:
- Do NOT claim certainty or provide guaranteed outcomes.
- You MAY provide practical, general agronomic recommendations (including fertilizer type categories and integrated pest management options).
- Do NOT give hazardous chemical handling instructions, illegal use guidance, or unsafe dosage claims.
- Present recommendations as "likely suitable" or "commonly used" and include a brief caution to validate with local soil tests and label/regional rules.
- Only extract structured crop issue attributes.
- Only summarize provided information.
- This system does not replace an agronomist.
"""
