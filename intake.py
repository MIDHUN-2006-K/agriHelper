"""
Agricultural advisory intake state machine for AgriHelper.
"""

import re
from typing import Any, Dict, List, Optional

import database
from config.settings import NEXUS_API_KEY, NEXUS_BASE_URL, NEXUS_MODEL_LLM
from memory import SessionMemory
from modules.nlp_pipeline import NLPPipeline
from modules.response_generator import ResponseGenerator
from modules.knowledge.weather_service import WeatherService
from modules.knowledge.fertilizer_service import FertilizerService
from modules.knowledge.market_service import MarketService
from modules.knowledge.scheme_service import SchemeService


STATES = {
    "GREETING": "greeting",
    "COLLECTING": "collecting",
    "CLARIFYING": "clarifying",
    "COMPLETE": "complete",
}


FIELD_PRIORITY = {
    "primary_problem": 1,
    "crop_name": 2,
    "location": 3,
    "season": 4,
    "soil_type": 5,
}


FIELD_QUESTIONS = {
    "primary_problem": "Please describe your main farming problem in one line.",
    "crop_name": "Which crop is this about?",
    "location": "Which village/district/state are you farming in?",
    "season": "Which season is this for (kharif, rabi, zaid)?",
    "soil_type": "What soil type do you have (red, black, alluvial, clay, sandy)?",
}


NLP = NLPPipeline(NEXUS_API_KEY, NEXUS_BASE_URL, NEXUS_MODEL_LLM)
RESPONDER = ResponseGenerator(NEXUS_API_KEY, NEXUS_BASE_URL, NEXUS_MODEL_LLM)

SERVICES = {
    "weather_query": WeatherService(),
    "fertilizer_query": FertilizerService(),
    "market_price_query": MarketService(),
    "government_scheme_query": SchemeService(),
}


def _extract_profile_updates(user_input: str, entities: Dict[str, Any]) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}

    if user_input and user_input.strip():
        updates["primary_problem"] = user_input.strip()

    for field in ["crop_name", "location", "season", "soil_type"]:
        value = entities.get(field)
        if value:
            updates[field] = value

    farm_size_match = re.search(r"(\d+(?:\.\d+)?)\s*(acre|acres)", (user_input or "").lower())
    if farm_size_match:
        updates["farm_size_acres"] = float(farm_size_match.group(1))

    return updates


def _required_fields_for_intent(intent: str) -> List[str]:
    intent_requirements = {
        "weather_query": ["location"],
        "fertilizer_query": ["crop_name", "soil_type"],
        "market_price_query": ["crop_name", "location"],
        "government_scheme_query": ["location"],
        "crop_disease_query": ["crop_name"],
        "general_question": ["primary_problem"],
    }
    return intent_requirements.get(intent, ["primary_problem"])


def _retrieve_knowledge(intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if intent == "weather_query":
            return SERVICES["weather_query"].get_weather(
                location=entities.get("location"),
                date=entities.get("date"),
            )

        if intent == "fertilizer_query":
            return SERVICES["fertilizer_query"].get_recommendation(
                crop_name=entities.get("crop_name"),
                soil_type=entities.get("soil_type"),
                location=entities.get("location"),
            )

        if intent == "market_price_query":
            return SERVICES["market_price_query"].get_prices(
                crop_name=entities.get("crop_name"),
                location=entities.get("location"),
            )

        if intent == "government_scheme_query":
            return SERVICES["government_scheme_query"].search_schemes(
                query=entities.get("crop_name") or entities.get("season"),
                category=None,
                location=entities.get("location"),
            )

        if intent == "crop_disease_query":
            return {
                "type": "crop_disease_guidance",
                "crop": entities.get("crop_name", "unknown"),
                "disease": entities.get("disease_name", "unknown"),
                "note": "Disease diagnosis may need local extension officer verification.",
            }

        return {"type": "general_knowledge", "note": "General agriculture guidance response."}
    except Exception as error:
        return {"error": str(error), "fallback": True}


def _next_missing_field(required_fields: List[str], memory: SessionMemory) -> Optional[str]:
    missing = [field for field in required_fields if field in memory.get_missing_fields()]
    if not missing:
        return None

    unasked = [field for field in missing if field not in memory.asked_fields]
    if unasked:
        return sorted(unasked, key=lambda field: FIELD_PRIORITY.get(field, 99))[0]

    return sorted(missing, key=lambda field: FIELD_PRIORITY.get(field, 99))[0]


def process_interaction(session_id: str, user_input: str, language_hint: str = "en") -> Dict[str, Any]:
    memory = SessionMemory(session_id)
    current_state = database.get_session_state(session_id) or STATES["GREETING"]

    if user_input and user_input.strip():
        database.save_turn(session_id, "user", user_input)

    if current_state == STATES["GREETING"]:
        response_text = (
            "Hi, I am AgriHelper. I can help with weather, fertilizer, diseases, market prices, and schemes. "
            "What farming issue do you want help with today?"
        )
        database.update_session_state(session_id, STATES["COLLECTING"])
        database.save_turn(session_id, "assistant", response_text)
        return {
            "response_text": response_text,
            "state": STATES["COLLECTING"],
            "is_complete": False,
            "intent": None,
            "entities": {},
            "profile_progress": memory.get_progress(),
        }

    analysis = NLP.process(user_input or "", language_hint)
    intent = analysis.get("intent", "general_question")
    entities = analysis.get("entities", {}) or {}

    updates = _extract_profile_updates(user_input, entities)
    memory.update_fields(updates)
    database.update_session_metadata(session_id, intent=intent, last_query=user_input)

    required_fields = _required_fields_for_intent(intent)
    next_field = _next_missing_field(required_fields, memory)

    if next_field:
        memory.mark_field_asked(next_field)
        response_text = FIELD_QUESTIONS[next_field]
        database.update_session_state(session_id, STATES["CLARIFYING"])
        state = STATES["CLARIFYING"]
        is_complete = False
    else:
        profile_data = memory.get_profile_data()
        merged_entities = {**entities, **{k: v for k, v in profile_data.items() if v is not None}}
        knowledge_data = _retrieve_knowledge(intent, merged_entities)
        response_text = RESPONDER.generate(
            intent=intent,
            entities=merged_entities,
            knowledge_data=knowledge_data,
            language=language_hint,
            original_query=user_input,
        )
        summary = f"Intent: {intent}; Crop: {merged_entities.get('crop_name')}; Location: {merged_entities.get('location')}"
        database.update_profile_record(session_id, {"summary": summary})
        database.update_session_state(session_id, STATES["COMPLETE"])
        state = STATES["COMPLETE"]
        is_complete = True

    database.save_turn(session_id, "assistant", response_text)

    return {
        "response_text": response_text,
        "state": state,
        "is_complete": is_complete,
        "intent": intent,
        "entities": entities,
        "profile_progress": memory.get_progress(),
    }


def process_consult(question: str, language_hint: str = "en") -> Dict[str, Any]:
    analysis = NLP.process(question, language_hint)
    intent = analysis.get("intent", "general_question")
    entities = analysis.get("entities", {}) or {}
    knowledge_data = _retrieve_knowledge(intent, entities)
    answer = RESPONDER.generate(
        intent=intent,
        entities=entities,
        knowledge_data=knowledge_data,
        language=language_hint,
        original_query=question,
    )
    return {
        "answer": answer,
        "intent": intent,
        "entities": entities,
    }
