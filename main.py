"""
AgriHelper API - ClinAssist-style backend adapted for agriculture domain.
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


@app.on_event("startup")
async def startup_event() -> None:
    database.init_database()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/")
async def root():
    return {"message": "AgriHelper API is running", "docs": "/docs"}


@app.post("/session/new", response_model=SessionCreate)
async def create_new_session():
    try:
        session_id = database.create_session()
        return {"session_id": session_id, "message": "Session created successfully"}
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Session creation failed", "detail": str(error)},
        )


@app.post("/session/{session_id}/voice", response_model=SessionResponse)
async def process_voice_input(
    session_id: str = FastAPIPath(..., description="Session ID"),
    audio: UploadFile = File(..., description="Audio file (WAV format)"),
):
    total_start = time.time()
    latency = {"stt_ms": None, "llm_ms": None, "tts_ms": None, "total_ms": 0.0}

    if not database.session_exists(session_id):
        raise HTTPException(status_code=404, detail={"error": "Session not found", "detail": session_id})

    try:
        audio_bytes = await audio.read()
        if not stt.validate_audio_format(audio_bytes):
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid audio format", "detail": "Provide WAV audio (16-bit PCM preferred)."},
            )

        stt_start = time.time()
        transcribed = stt.transcribe_audio(audio_bytes, session_id)
        latency["stt_ms"] = (time.time() - stt_start) * 1000

        transcript = transcribed.get("text", "")
        language = transcribed.get("language", "en")
        if not transcript.strip():
            raise HTTPException(status_code=400, detail={"error": "Transcription failed", "detail": "No speech detected"})

        llm_start = time.time()
        result = intake.process_interaction(session_id, transcript, language_hint=language)
        latency["llm_ms"] = (time.time() - llm_start) * 1000

        tts_start = time.time()
        audio_response = tts.generate_speech(result["response_text"], session_id, language=language)
        latency["tts_ms"] = (time.time() - tts_start) * 1000
        audio_b64 = base64.b64encode(audio_response).decode("utf-8") if audio_response else None

        latency["total_ms"] = (time.time() - total_start) * 1000

        return {
            "transcript": transcript,
            "response_text": result["response_text"],
            "audio_base64": audio_b64,
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
        raise HTTPException(status_code=500, detail={"error": "Voice processing failed", "detail": str(error)})


@app.post("/session/{session_id}/text", response_model=SessionResponse)
async def process_text_input(
    input_data: TextInput,
    session_id: str = FastAPIPath(..., description="Session ID"),
):
    total_start = time.time()
    latency = {"stt_ms": None, "llm_ms": None, "tts_ms": None, "total_ms": 0.0}

    if not database.session_exists(session_id):
        raise HTTPException(status_code=404, detail={"error": "Session not found", "detail": session_id})

    text = input_data.text if input_data else ""
    if not text.strip() and database.get_session_state(session_id) != intake.STATES["GREETING"]:
        raise HTTPException(status_code=400, detail={"error": "Empty input", "detail": "Text input cannot be empty"})

    try:
        llm_start = time.time()
        result = intake.process_interaction(session_id, text, language_hint="en")
        latency["llm_ms"] = (time.time() - llm_start) * 1000

        audio_b64 = None
        if ENABLE_TTS_FOR_TEXT:
            tts_start = time.time()
            audio_response = tts.generate_speech(result["response_text"], session_id, language="en")
            latency["tts_ms"] = (time.time() - tts_start) * 1000
            if audio_response:
                audio_b64 = base64.b64encode(audio_response).decode("utf-8")
        else:
            latency["tts_ms"] = 0.0

        latency["total_ms"] = (time.time() - total_start) * 1000

        return {
            "transcript": text,
            "response_text": result["response_text"],
            "audio_base64": audio_b64,
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
        raise HTTPException(status_code=500, detail={"error": "Text processing failed", "detail": str(error)})


@app.get("/session/{session_id}/summary", response_model=SummaryResponse)
async def get_session_summary(session_id: str = FastAPIPath(..., description="Session ID")):
    if not database.session_exists(session_id):
        raise HTTPException(status_code=404, detail={"error": "Session not found", "detail": session_id})

    export_data = database.get_session_export_data(session_id)
    if not export_data:
        raise HTTPException(status_code=404, detail={"error": "Summary not found", "detail": session_id})

    memory = SessionMemory(session_id)
    profile = memory.get_profile_data()
    return {
        "session_id": session_id,
        "state": export_data.get("state", "unknown"),
        "profile": {
            "primary_problem": profile.get("primary_problem"),
            "crop_name": profile.get("crop_name"),
            "location": profile.get("location"),
            "season": profile.get("season"),
            "soil_type": profile.get("soil_type"),
            "farm_size_acres": profile.get("farm_size_acres"),
        },
        "intent": export_data.get("intent"),
        "summary": profile.get("summary"),
        "conversation_history": export_data.get("conversation_history", []),
    }


@app.post("/consult", response_model=ConsultResponse)
async def process_standalone_consult(request: ConsultRequest):
    try:
        session_id = request.session_id if request.session_id and database.session_exists(request.session_id) else database.create_session()
        database.save_turn(session_id, "user", request.question)

        result = intake.process_consult(request.question, language_hint="en")
        answer = result["answer"]
        database.save_turn(session_id, "assistant", answer)

        audio_b64 = None
        if ENABLE_TTS_FOR_TEXT:
            audio_response = tts.generate_speech(answer, session_id, language="en")
            if audio_response:
                audio_b64 = base64.b64encode(audio_response).decode("utf-8")

        return {
            "answer": answer,
            "audio_base64": audio_b64,
            "session_id": session_id,
            "intent": result.get("intent"),
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail={"error": "Consult processing failed", "detail": str(error)})


@app.post("/consult/voice", response_model=ConsultVoiceResponse)
async def process_standalone_voice_consult(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
):
    try:
        audio_content = await audio.read()
        if not audio_content:
            raise HTTPException(status_code=400, detail="Empty audio file")

        active_session = session_id if session_id and database.session_exists(session_id) else database.create_session()

        transcribed = stt.transcribe_audio(audio_content, active_session)
        transcript = transcribed.get("text", "").strip()
        language = transcribed.get("language", "en")
        if not transcript:
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

        audio_b64 = None
        audio_response = tts.generate_speech(answer, active_session, language=language)
        if audio_response:
            audio_b64 = base64.b64encode(audio_response).decode("utf-8")

        return {
            "answer": answer,
            "transcript": transcript,
            "audio_base64": audio_b64,
            "session_id": active_session,
            "intent": result.get("intent"),
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail={"error": "Voice consult failed", "detail": str(error)})
