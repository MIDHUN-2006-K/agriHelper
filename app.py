"""
🌾 AgriHelper — Multilingual AI Voice Assistant for Farmers
Streamlit Web Application
"""

import os
import sys
import json
import time
import logging
import base64
from pathlib import Path

import streamlit as st
import requests

# ── Project root on sys.path ─────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ── API Configuration ────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("AGRIHELPER_API_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 30

from config.settings import (
    NEXUS_API_KEY, NEXUS_BASE_URL,
    NEXUS_MODEL_LLM, NEXUS_MODEL_STT, NEXUS_MODEL_TTS,
    DATABASE_PATH, DATA_DIR, SUPPORTED_LANGUAGES,
    validate_config,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AgriHelper")

# ═════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AgriHelper 🌾",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═════════════════════════════════════════════════════════════════════════════
#  CUSTOM CSS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2e7d32;
        text-align: center;
        padding: 0.5rem 0 0.2rem 0;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
    }
    .stage-card {
        background: #f8f9fa;
        border-left: 4px solid #2e7d32;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .response-box {
        background: linear-gradient(135deg, #e8f5e9, #f1f8e9);
        border: 1px solid #a5d6a7;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        font-size: 1.05rem;
        line-height: 1.7;
    }
    .metric-card {
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .intent-badge {
        display: inline-block;
        background: #2e7d32;
        color: white;
        padding: 0.25rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    div[data-testid="stAudio"] { margin-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
#  API SESSION MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════
def get_or_create_session() -> str:
    """Get or create an API session."""
    if "api_session_id" not in st.session_state:
        try:
            resp = requests.post(f"{API_BASE_URL}/session/new", timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            st.session_state.api_session_id = resp.json()["session_id"]
        except Exception as e:
            st.error(f"Failed to create session: {e}")
            st.session_state.api_session_id = None
    return st.session_state.get("api_session_id")


def api_health_check() -> bool:
    """Check if API is running."""
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


# ═════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════
def autoplay_audio(file_path: str):
    """Render an HTML audio player with autoplay."""
    if not Path(file_path).exists():
        return
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    st.audio(data, format="audio/wav")


INTENT_ICONS = {
    "weather_query": "🌦️",
    "fertilizer_query": "🧪",
    "crop_disease_query": "🌿",
    "market_price_query": "💰",
    "government_scheme_query": "🏛️",
    "general_question": "❓",
}

SAMPLE_QUERIES = {
    "en": [
        "What is the weather forecast for Tamil Nadu?",
        "What fertilizer should I use for wheat in red soil?",
        "What is the current market price of rice in Punjab?",
        "Tell me about government schemes for farmers",
        "My tomato plants have yellow leaves, what disease is this?",
    ],
    "ta": [
        "தமிழ்நாட்டின் வானிலை நிலை என்ன?",
        "சிவப்பு மண்ணில் கோதுமைக்கு என்ன உரம் பயன்படுத்த வேண்டும்?",
        "அரிசியின் தற்போதைய சந்தை விலை என்ன?",
        "விவசாயிகளுக்கான அரசு திட்டங்கள் என்ன?",
    ],
    "hi": [
        "तमिलनाडु का मौसम कैसा रहेगा?",
        "लाल मिट्टी में गेहूं के लिए कौन सा उर्वरक इस्तेमाल करें?",
        "चावल का बाजार भाव क्या है?",
        "किसानों के लिए सरकारी योजनाएं बताइए",
    ],
}


# ═════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🌾 AgriHelper")
        st.caption("Multilingual AI Voice Assistant for Farmers")

        st.divider()

        # Config status
        config = validate_config()
        if config["valid"]:
            st.success("✅ API Connected", icon="🔗")
        else:
            st.error("❌ API Not Configured")
            for issue in config["issues"]:
                st.caption(f"• {issue}")

        st.divider()

        # Mode selector
        mode = st.radio(
            "Interaction Mode",
            ["💬 Text Query", "🎙️ Voice Query", "📊 Dashboard"],
            index=0,
        )

        st.divider()

        # Language
        lang_options = {"English 🇬🇧": "en", "Tamil 🇮🇳": "ta", "Hindi 🇮🇳": "hi"}
        selected_lang_label = st.selectbox("🌐 Language", list(lang_options.keys()))
        language = lang_options[selected_lang_label]

        st.divider()

        # Model info
        with st.expander("⚙️ Models", expanded=False):
            st.caption(f"**LLM:** {NEXUS_MODEL_LLM}")
            st.caption(f"**STT:** {NEXUS_MODEL_STT}")
            st.caption(f"**TTS:** {NEXUS_MODEL_TTS}")

        # Architecture
        with st.expander("🏗️ Architecture", expanded=False):
            st.markdown("""
            ```
            Audio Input
              ↓
            Preprocessing
              ↓
            STT (Whisper)
              ↓
            Language Detection
              ↓
            NLP (Intent + Entities)
              ↓
            Knowledge Retrieval
              ↓
            Response Generation
              ↓
            TTS (GPT-4o-mini)
              ↓
            Audio Playback
              ↓
            Memory (SQLite)
            ```
            """)

        return mode, language


# ═════════════════════════════════════════════════════════════════════════════
#  TEXT QUERY PAGE
# ═════════════════════════════════════════════════════════════════════════════
def render_text_query(language: str):
    st.markdown('<div class="main-header">🌾 AgriHelper</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Ask any agricultural question — get answers in your language</div>', unsafe_allow_html=True)

    session_id = get_or_create_session()
    if not session_id:
        st.error("Cannot connect to API. Is the server running at " + API_BASE_URL + "?")
        return

    # ── Sample queries ───────────────────────────────────────────────────
    samples = SAMPLE_QUERIES.get(language, SAMPLE_QUERIES["en"])
    st.markdown("##### 💡 Try a sample query:")
    cols = st.columns(min(len(samples), 3))
    selected_sample = None
    for i, sample in enumerate(samples):
        with cols[i % 3]:
            if st.button(sample[:50] + ("…" if len(sample) > 50 else ""), key=f"sample_{i}", use_container_width=True):
                selected_sample = sample

    st.divider()

    # ── Query input ──────────────────────────────────────────────────────
    query = st.text_area(
        "🌾 Your Question",
        value=selected_sample or "",
        height=100,
        placeholder="Type your agricultural question here…",
    )

    col_go, col_tts = st.columns([3, 1])
    with col_tts:
        enable_tts = st.checkbox("🔊 Voice Response", value=True)
    with col_go:
        submit = st.button("🚀 Get Answer", type="primary", use_container_width=True)

    # ── Process ──────────────────────────────────────────────────────────
    if submit and query.strip():
        _process_text_via_api(session_id, query, language, enable_tts)
    elif submit:
        st.warning("Please enter a question first.")


# ═════════════════════════════════════════════════════════════════════════════
#  VOICE QUERY PAGE
# ═════════════════════════════════════════════════════════════════════════════
def render_voice_query(language: str):
    st.markdown('<div class="main-header">🎙️ Voice Query</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Record from your microphone or upload an audio file</div>', unsafe_allow_html=True)

    session_id = get_or_create_session()
    if not session_id:
        st.error("Cannot connect to API. Is the server running at " + API_BASE_URL + "?")
        return

    enable_tts = st.checkbox("🔊 Voice Response", value=True, key="voice_tts")

    # ── Two input methods: Mic + File Upload ────────────────────────────
    tab_mic, tab_upload = st.tabs(["🎤 Record from Microphone", "📁 Upload Audio File"])

    input_path = None

    with tab_mic:
        st.info("Click the microphone button below to record your question. "
                "Press stop when done speaking.")
        mic_audio = st.audio_input(
            "🎤 Record your question",
            key="mic_input",
        )
        if mic_audio is not None:
            input_path = str(DATA_DIR / "mic_input.wav")
            with open(input_path, "wb") as f:
                f.write(mic_audio.read())
            st.audio(input_path, format="audio/wav")
            file_kb = Path(input_path).stat().st_size / 1024
            st.success(f"✅ Recorded ({file_kb:.1f} KB)")
            if st.button("🚀 Process Mic Recording", type="primary",
                         use_container_width=True, key="process_mic"):
                _process_voice_via_api(session_id, input_path, language, enable_tts)

    with tab_upload:
        uploaded = st.file_uploader(
            "Upload audio file",
            type=["wav", "mp3", "m4a", "ogg"],
            help="Record your question externally and upload the audio file here.",
        )
        if uploaded is not None:
            input_path = str(DATA_DIR / "uploaded_input.wav")
            with open(input_path, "wb") as f:
                f.write(uploaded.read())
            st.audio(input_path, format="audio/wav")
            file_kb = Path(input_path).stat().st_size / 1024
            st.success(f"✅ Audio uploaded ({file_kb:.1f} KB)")
            if st.button("🚀 Process Uploaded Audio", type="primary",
                         use_container_width=True, key="process_upload"):
                _process_voice_via_api(session_id, input_path, language, enable_tts)


# ═════════════════════════════════════════════════════════════════════════════
#  DASHBOARD PAGE
# ═════════════════════════════════════════════════════════════════════════════
def render_dashboard():
    st.markdown('<div class="main-header">📊 Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Session summary and conversation history</div>', unsafe_allow_html=True)

    session_id = get_or_create_session()
    if not session_id:
        st.error("Cannot connect to API. Is the server running at " + API_BASE_URL + "?")
        return

    # ── Summary ──────────────────────────────────────────────────────────
    try:
        resp = requests.get(f"{API_BASE_URL}/session/{session_id}/summary", timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            summary = resp.json()
            st.markdown(f"**Session ID:** `{session_id}`")
            st.markdown(f"**State:** {summary.get('state', 'unknown')}")

            if summary.get("profile"):
                st.markdown("##### 🌾 Farmer Profile")
                for key, val in summary["profile"].items():
                    if val:
                        st.markdown(f"  • **{key.replace('_', ' ').title()}:** {val}")

            if summary.get("conversation_history"):
                st.markdown("##### 📜 Conversation History")
                for i, turn in enumerate(summary["conversation_history"]):
                    role = "👤" if turn["role"] == "user" else "🤖"
                    with st.expander(f"{role} {turn['role'].title()}", expanded=(i == len(summary.get('conversation_history', [])) - 1)):
                        st.markdown(turn["content"])
        else:
            st.info("No session summary available yet. Start by asking a question!")
    except Exception as e:
        st.warning(f"Could not load summary: {e}")


# ═════════════════════════════════════════════════════════════════════════════
#  API-BASED PROCESSING FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════
def _process_text_via_api(session_id: str, query: str, language: str, enable_tts: bool):
    """Process a text query via API."""
    status = st.status("🌾 Processing your query…", expanded=True)

    try:
        with status:
            st.write("📤 Sending query to AgriHelper API…")
            payload = {"text": query}
            resp = requests.post(
                f"{API_BASE_URL}/session/{session_id}/text",
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            result = resp.json()

        status.update(label="✅ Processed", state="complete", expanded=False)

        # Render results
        st.markdown("---")
        response_text = result.get("response_text", "No response")
        intent = result.get("intent", "general_question")
        entities = result.get("entities", {})
        latency = result.get("latency_breakdown", {})

        # Intent & entities
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            icon = INTENT_ICONS.get(intent, "📌")
            st.markdown(f"### {icon} {intent.replace('_', ' ').title()}")
        with col2:
            if entities:
                entity_tags = "  ".join([f"`{k}: {v}`" for k, v in entities.items()])
                st.markdown(f"**Entities:** {entity_tags}")
        with col3:
            total_ms = latency.get("total_ms", 0)
            st.markdown(f"⏱️ **{total_ms/1000:.2f}s** | 🌐 **{language.upper()}**")

        # Response
        st.markdown(f'<div class="response-box">{response_text}</div>', unsafe_allow_html=True)

        # Audio
        if enable_tts and result.get("audio_base64"):
            audio_bytes = base64.b64decode(result["audio_base64"])
            st.audio(audio_bytes, format="audio/wav")

        # Details
        with st.expander("⏱️ Latency Breakdown"):
            st.json(latency)
        with st.expander("🧠 Entities & Intent"):
            st.json({"intent": intent, "entities": entities})

    except Exception as e:
        status.update(label=f"❌ Error", state="error")
        st.error(f"Processing failed: {e}")


def _process_voice_via_api(session_id: str, audio_path: str, language: str, enable_tts: bool):
    """Process a voice query via API."""
    status = st.status("🎙️ Processing voice query…", expanded=True)

    try:
        with status:
            st.write("📤 Uploading audio to AgriHelper API…")
            with open(audio_path, "rb") as f:
                files = {"audio": ("audio.wav", f, "audio/wav")}
                resp = requests.post(
                    f"{API_BASE_URL}/session/{session_id}/voice",
                    files=files,
                    timeout=REQUEST_TIMEOUT,
                )
            resp.raise_for_status()
            result = resp.json()

        status.update(label="✅ Processed", state="complete", expanded=False)

        # Render results
        st.markdown("---")
        transcript = result.get("transcript", "")
        response_text = result.get("response_text", "No response")
        intent = result.get("intent", "general_question")
        entities = result.get("entities", {})
        latency = result.get("latency_breakdown", {})

        st.markdown(f"**Transcription:** {transcript}")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            icon = INTENT_ICONS.get(intent, "📌")
            st.markdown(f"### {icon} {intent.replace('_', ' ').title()}")
        with col2:
            if entities:
                entity_tags = "  ".join([f"`{k}: {v}`" for k, v in entities.items()])
                st.markdown(f"**Entities:** {entity_tags}")
        with col3:
            total_ms = latency.get("total_ms", 0)
            st.markdown(f"⏱️ **{total_ms/1000:.2f}s** | 🌐 **{language.upper()}**")

        st.markdown(f'<div class="response-box">{response_text}</div>', unsafe_allow_html=True)

        if enable_tts and result.get("audio_base64"):
            audio_bytes = base64.b64decode(result["audio_base64"])
            st.audio(audio_bytes, format="audio/wav")

        with st.expander("⏱️ Latency Breakdown"):
            st.json(latency)
        with st.expander("🧠 Entities & Intent"):
            st.json({"intent": intent, "entities": entities})

    except Exception as e:
        status.update(label=f"❌ Error", state="error")
        st.error(f"Voice processing failed: {e}")


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════
def main():
    mode, language = render_sidebar()

    if mode == "💬 Text Query":
        render_text_query(language)
    elif mode == "🎙️ Voice Query":
        render_voice_query(language)
    elif mode == "📊 Dashboard":
        render_dashboard()

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#999; font-size:0.85rem;'>"
        "🌾 AgriHelper — Multilingual AI Voice Assistant for Farmers "
        "| Built with Streamlit + Whisper + LLM + TTS"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
