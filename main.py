"""
AgriHelper API - Voice + Text agricultural assistant backend
"""

import base64
import os
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Path as FastAPIPath, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

import database
import intake
import stt
import tts
from memory import SessionMemory
from models import (
    ConsultRequest,
    ConsultResponse,
    ConsultVoiceResponse,
    HealthResponse,
    SessionCreate,
    SessionResponse,
    SummaryResponse,
    TextInput,
)

ENABLE_TTS_FOR_TEXT = os.getenv("ENABLE_TTS_FOR_TEXT", "1").strip().lower() in {"1", "true", "yes", "on"}

app = FastAPI(
    title="AgriHelper API",
    description="Speech-driven agricultural assistant for farmers",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------
# Startup
# ----------------------------------------------------

@app.on_event("startup")
async def startup_event():
    database.init_database()


# ----------------------------------------------------
# Health Check
# ----------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    return {"message": "AgriHelper API running", "docs": "/docs"}


# ----------------------------------------------------
# Session Creation
# ----------------------------------------------------

@app.post("/session/new", response_model=SessionCreate)
async def create_new_session():
    try:
        session_id = database.create_session()
        return {
            "session_id": session_id,
            "message": "Session created successfully",
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={"error": "Session creation failed", "detail": str(error)},
        )


# ----------------------------------------------------
# Voice Input
# ----------------------------------------------------

@app.post("/session/{session_id}/voice", response_model=SessionResponse)
async def process_voice_input(
    session_id: str = FastAPIPath(...),
    audio: UploadFile = File(...),
):

    total_start = time.time()

    latency = {
        "stt_ms": None,
        "llm_ms": None,
        "tts_ms": None,
        "total_ms": 0.0,
    }

    if not database.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        audio_bytes = await audio.read()

        if not stt.validate_audio_format(audio_bytes):
            raise HTTPException(
                status_code=400,
                detail="Invalid WAV format (16kHz PCM recommended)"
            )

        # ---------------- STT ----------------
        stt_start = time.time()
        stt_result = stt.transcribe_audio(audio_bytes, session_id)
        latency["stt_ms"] = (time.time() - stt_start) * 1000

        if isinstance(stt_result, dict):
            transcript = stt_result.get("text", "")
            language = stt_result.get("language", "en")
        else:
            transcript = stt_result
            language = "en"

        if not transcript.strip():
            raise HTTPException(status_code=400, detail="No speech detected")

        # ---------------- LLM ----------------
        llm_start = time.time()
        result = intake.process_interaction(session_id, transcript, language_hint=language)
        latency["llm_ms"] = (time.time() - llm_start) * 1000

        # ---------------- TTS ----------------
        tts_start = time.time()
        audio_bytes = tts.generate_speech(result["response_text"], session_id, language)
        latency["tts_ms"] = (time.time() - tts_start) * 1000

        audio_base64 = None
        if audio_bytes:
            audio_base64 = base64.b64encode(audio_bytes).decode()

        latency["total_ms"] = (time.time() - total_start) * 1000

        return {
            "transcript": transcript,
            "response_text": result["response_text"],
            "audio_base64": audio_base64,
            "state": result["state"],
            "is_complete": result["is_complete"],
            "intent": result.get("intent"),
            "entities": result.get("entities"),
            "latency_breakdown": latency,
            "profile_progress": result.get("profile_progress"),
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={"error": "Voice processing failed", "detail": str(error)},
        )


# ----------------------------------------------------
# Text Input
# ----------------------------------------------------

@app.post("/session/{session_id}/text", response_model=SessionResponse)
async def process_text_input(
    input_data: TextInput,
    session_id: str = FastAPIPath(...),
):

    total_start = time.time()

    latency = {
        "stt_ms": None,
        "llm_ms": None,
        "tts_ms": None,
        "total_ms": 0.0,
    }

    if not database.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    text = input_data.text if input_data else ""

    if not text.strip() and database.get_session_state(session_id) != intake.STATES["GREETING"]:
        raise HTTPException(status_code=400, detail="Empty input")

    try:

        llm_start = time.time()
        result = intake.process_interaction(session_id, text, language_hint="en")
        latency["llm_ms"] = (time.time() - llm_start) * 1000

        audio_base64 = None

        if ENABLE_TTS_FOR_TEXT:

            tts_start = time.time()
            audio_bytes = tts.generate_speech(result["response_text"], session_id)
            latency["tts_ms"] = (time.time() - tts_start) * 1000

            if audio_bytes:
                audio_base64 = base64.b64encode(audio_bytes).decode()

        latency["total_ms"] = (time.time() - total_start) * 1000

        return {
            "transcript": text,
            "response_text": result["response_text"],
            "audio_base64": audio_base64,
            "state": result["state"],
            "is_complete": result["is_complete"],
            "intent": result.get("intent"),
            "entities": result.get("entities"),
            "latency_breakdown": latency,
            "profile_progress": result.get("profile_progress"),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={"error": "Text processing failed", "detail": str(error)},
        )


# ----------------------------------------------------
# Session Summary
# ----------------------------------------------------

@app.get("/session/{session_id}/summary", response_model=SummaryResponse)
async def get_session_summary(session_id: str):

    if not database.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    export_data = database.get_session_export_data(session_id)

    memory = SessionMemory(session_id)
    profile = memory.get_profile_data()

    return {
        "session_id": session_id,
        "state": export_data.get("state"),
        "profile": profile,
        "intent": export_data.get("intent"),
        "summary": profile.get("summary"),
        "conversation_history": export_data.get("conversation_history", []),
    }


# ----------------------------------------------------
# Consult (Text)
# ----------------------------------------------------

@app.post("/consult", response_model=ConsultResponse)
async def process_consult(request: ConsultRequest):

    session_id = request.session_id if request.session_id and database.session_exists(request.session_id) else database.create_session()

    database.save_turn(session_id, "user", request.question)

    result = intake.process_consult(request.question)

    answer = result["answer"]

    database.save_turn(session_id, "assistant", answer)

    audio_base64 = None

    if ENABLE_TTS_FOR_TEXT:
        audio_bytes = tts.generate_speech(answer, session_id)
        if audio_bytes:
            audio_base64 = base64.b64encode(audio_bytes).decode()

    return {
        "answer": answer,
        "audio_base64": audio_base64,
        "session_id": session_id,
        "intent": result.get("intent"),
    }


# ----------------------------------------------------
# Consult Voice
# ----------------------------------------------------

@app.post("/consult/voice", response_model=ConsultVoiceResponse)
async def process_consult_voice(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
):

    audio_bytes = await audio.read()

    active_session = session_id if session_id and database.session_exists(session_id) else database.create_session()

    stt_result = stt.transcribe_audio(audio_bytes, active_session)

    if isinstance(stt_result, dict):
        transcript = stt_result.get("text", "")
        language = stt_result.get("language", "en")
    else:
        transcript = stt_result
        language = "en"

    if not transcript.strip():
        return {
            "answer": "I could not hear clearly. Please repeat your farming question.",
            "transcript": "",
            "audio_base64": None,
            "session_id": active_session,
            "intent": None,
        }

    database.save_turn(active_session, "user", transcript)

    result = intake.process_consult(transcript, language_hint=language)

    answer = result["answer"]

    database.save_turn(active_session, "assistant", answer)

    audio_base64 = None

    audio_bytes = tts.generate_speech(answer, active_session)

    if audio_bytes:
        audio_base64 = base64.b64encode(audio_bytes).decode()

    return {
        "answer": answer,
        "transcript": transcript,
        "audio_base64": audio_base64,
        "session_id": active_session,
        "intent": result.get("intent"),
    }