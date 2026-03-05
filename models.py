"""
Pydantic models and schemas for AgriHelper API.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    session_id: str
    message: str


class TextInput(BaseModel):
    text: str = Field(..., min_length=0, max_length=1000)


class FarmerProfile(BaseModel):
    primary_problem: Optional[str] = None
    crop_name: Optional[str] = None
    location: Optional[str] = None
    season: Optional[str] = None
    soil_type: Optional[str] = None
    farm_size_acres: Optional[float] = None


class LatencyBreakdown(BaseModel):
    stt_ms: Optional[float] = None
    llm_ms: Optional[float] = None
    tts_ms: Optional[float] = None
    total_ms: float


class SessionResponse(BaseModel):
    transcript: Optional[str] = None
    response_text: str
    audio_base64: Optional[str] = None
    state: str
    is_complete: bool
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    latency_breakdown: LatencyBreakdown
    profile_progress: Optional[Dict[str, bool]] = None


class SummaryResponse(BaseModel):
    session_id: str
    state: str
    profile: FarmerProfile
    intent: Optional[str] = None
    summary: Optional[str] = None
    conversation_history: List[Dict[str, str]]


class ConsultRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None


class ConsultResponse(BaseModel):
    answer: str
    audio_base64: Optional[str] = None
    session_id: str
    intent: Optional[str] = None


class ConsultVoiceResponse(BaseModel):
    answer: str
    transcript: str
    audio_base64: Optional[str] = None
    session_id: str
    intent: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
