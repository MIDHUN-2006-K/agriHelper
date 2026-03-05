"""
Assessment state machine for AgriAssist
Manages conversation flow: GREETING -> COLLECTING -> CLARIFYING -> SUMMARIZING -> COMPLETE
"""
from typing import Dict, Any, Optional, List
import re
from config import STATES, FIELD_PRIORITY
from memory import SessionMemory
from database import save_turn, update_session_state, get_session_state, update_symptom_record
import llm
import risk


def process_interaction(session_id: str, user_input: str) -> Dict[str, Any]:
    """
    Process user interaction through the farm assessment state machine
    
    Args:
        session_id: Current session ID
        user_input: User's text input
    
    Returns:
        Dictionary with response_text, state, is_complete, and optional crop_health_assessment
    """
    # Load session memory
    memory = SessionMemory(session_id)
    current_state = get_session_state(session_id)
    
    # Save user input
    if user_input and user_input.strip():
        save_turn(session_id, "user", user_input)
    
    response_text = ""
    crop_health_assessment = None
    farm_tip = None

    def _extract_severity_value(text: str) -> Optional[int]:
        if not text:
            return None

        lowered = text.lower()
        word_to_num = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }

        range_match = re.search(r"\b(10|[1-9])\s*(?:to|-|–)\s*(10|[1-9])\b", lowered)
        if range_match:
            left = int(range_match.group(1))
            right = int(range_match.group(2))
            return max(1, min(10, round((left + right) / 2)))

        word_range_match = re.search(
            r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:to|-|–)\s*"
            r"(one|two|three|four|five|six|seven|eight|nine|ten)\b",
            lowered,
        )
        if word_range_match:
            left = word_to_num[word_range_match.group(1)]
            right = word_to_num[word_range_match.group(2)]
            return max(1, min(10, round((left + right) / 2)))

        single_num = re.search(r"\b(10|[1-9])\b", lowered)
        if single_num:
            return int(single_num.group(1))

        for word, value in word_to_num.items():
            if re.search(rf"\b{word}\b", lowered):
                return value

        return None

    def _extract_associated_issues(text: str) -> Optional[List[str]]:
        if not text:
            return None

        lowered = text.lower()

        negative_markers = [
            "no other issues",
            "no additional problems",
            "no more issues",
            "none",
            "nothing else",
            "just that",
            "only the",
        ]
        if any(marker in lowered for marker in negative_markers):
            return ["none reported"]

        issue_aliases = [
            ("wilting", ["wilting", "wilt"]),
            ("leaf yellowing", ["yellowing", "yellow leaves", "chlorosis"]),
            ("pest damage", ["pest", "insect damage", "bug damage"]),
            ("leaf spots", ["spots", "leaf spots", "lesions"]),
            ("powdery mildew", ["powdery", "mildew", "white coating"]),
            ("root rot", ["root rot", "rotting roots"]),
            ("stunted growth", ["stunted", "short", "dwarf"]),
            ("nutrient deficiency", ["nutrient deficiency", "nutrient", "deficient"]),
            ("mosaic virus", ["mosaic", "virus", "viral"]),
            ("fungal disease", ["fungal", "fungus", "mold"]),
        ]

        found: List[str] = []
        for canonical, aliases in issue_aliases:
            if any(alias in lowered for alias in aliases):
                found.append(canonical)

        if not found:
            return None

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for issue in found:
            if issue not in seen:
                deduped.append(issue)
                seen.add(issue)

        return deduped

    def _finalize_intake(crop_data: Dict[str, Any], partial: bool = False):
        nonlocal crop_health_assessment, response_text, farm_tip

        update_session_state(session_id, STATES["SUMMARIZING"])

        # Categorize crop health (deterministic)
        health_result = risk.categorize_risk(crop_data)
        crop_health_assessment = health_result

        # Save crop health assessment
        update_symptom_record(session_id, {
            "health_level": health_result["health_level"],
            "health_reason": health_result["reason"],
            "recommended_action": health_result["recommended_action"]
        })

        # Generate and save summary
        summary = llm.generate_summary(crop_data, session_id)
        update_symptom_record(session_id, {"summary": summary})

        # ALWAYS get a tip/recommendation for the separate UI block
        if health_result['health_level'] in ["LOW", "MODERATE"]:
            farm_tip = llm.generate_farm_advice(crop_data, session_id)
        else:
            # For HIGH/CRITICAL, give a strong warning tip
            farm_tip = f"Immediate action required. {health_result['recommended_action']}"

        # Move straight to complete
        response_text = "I've completed your crop assessment based on the details provided. Your farm summary is now ready."
        update_session_state(session_id, STATES["COMPLETE"])
    
    # State machine logic
    if current_state == STATES["GREETING"]:
        # Welcome and ask for primary concern
        response_text = (
            "Hi, I'm AgriAssist. I'll ask a few simple questions about your crop issue. "
            "What primary concern are you seeing today?"
        )
        update_session_state(session_id, STATES["COLLECTING"])
    
    elif current_state == STATES["COLLECTING"] or current_state == STATES["CLARIFYING"]:
        # Immediate stop for critical issues: do not continue seven-question intake
        critical_detected = risk.detect_urgent_keyword(user_input or "")
        if critical_detected:
            health_result = risk.build_urgent_assessment(critical_detected, user_input or "")
            crop_health_assessment = health_result

            existing_data = memory.get_crop_data()
            primary_concern = existing_data.get("primary_concern") or (user_input or "")
            urgent_summary = (
                f"Primary Concern: {primary_concern}\n"
                f"Duration: Not reported\n"
                f"Severity (1-10): Not reported\n"
                f"Progression: Not reported\n"
                f"Affected Crop: Not reported\n"
                f"Onset Type: Not reported\n"
                f"Associated Issues: Not reported\n"
                f"Farm Note: Critical keyword trigger ('{critical_detected['keyword']}'). Assessment stopped for immediate action."
            )

            update_symptom_record(session_id, {
                "primary_concern": primary_concern,
                "health_level": health_result["health_level"],
                "health_reason": health_result["reason"],
                "recommended_action": health_result["recommended_action"],
                "summary": urgent_summary,
            })

            response_text = (
                "Important: this crop issue requires urgent action. "
                f"{health_result['recommended_action']}"
            )
            update_session_state(session_id, STATES["COMPLETE"])

        else:
            # Extract crop issue details from user input
            extracted = llm.extract_symptoms(
                memory.conversation_history,
                user_input,
                session_id
            )

            # Update memory with extracted data
            if extracted:
                memory.update_fields(extracted)

            # Deterministic fallback extraction for short/natural replies that LLM may miss
            fallback_updates: Dict[str, Any] = {}
            currently_missing = memory.get_missing_fields()

            if "severity" in currently_missing:
                severity_value = _extract_severity_value(user_input or "")
                if severity_value is not None:
                    fallback_updates["severity"] = severity_value

            if "associated_issues" in currently_missing:
                associated = _extract_associated_issues(user_input or "")
                if associated is not None:
                    fallback_updates["associated_issues"] = associated

            if fallback_updates:
                memory.update_fields(fallback_updates)

            from config import EMERGENCY_CONTEXTS, EMERGENCY_FIELDS
            context_name = llm._detect_symptom_context(memory.conversation_history)
            is_emergency = context_name in EMERGENCY_CONTEXTS

            if is_emergency:
                missing_fields = [f for f in EMERGENCY_FIELDS if f in memory.get_missing_fields()]
            else:
                missing_fields = memory.get_missing_fields()

            # Check if intake is complete for the current context
            if not missing_fields:
                symptom_data = memory.get_symptom_data()
                # If it's an emergency, it's considered a partial record compared to the 7 generic fields
                _finalize_intake(symptom_data, partial=(is_emergency or not memory.is_intake_complete()))

            else:
                # Ask clarification questions for the remaining fields
                # CRITICAL: If primary_concern is missing, STAY on it.
                if "primary_concern" in missing_fields:
                    # Only mark primary_concern as asked if it wasn't already.
                    # But we'll keep asking it until we get it.
                    if "primary_concern" not in memory.asked_fields:
                        memory.mark_field_asked("primary_concern")
                    
                    response_text = llm.generate_clarification_question(
                        ["primary_concern"],
                        memory.conversation_history,
                        session_id
                    )
                    update_session_state(session_id, STATES["CLARIFYING"])
                
                else:
                    # Primary concern is present, look for other UNASKED fields
                    unasked_missing = [f for f in missing_fields if f not in memory.asked_fields]

                    if unasked_missing:
                        # Pick ONLY the highest priority unasked field to mark as asked
                        # Sort by priority and pick the first
                        next_field = sorted(unasked_missing, key=lambda x: FIELD_PRIORITY.get(x, 99))[0]
                        memory.mark_field_asked(next_field)
                        
                        # Generate clarification question for only the next targeted field
                        response_text = llm.generate_clarification_question(
                            [next_field],
                            memory.conversation_history,
                            session_id
                        )
                        update_session_state(session_id, STATES["CLARIFYING"])
                    else:
                        # All missing fields were asked before, but still not filled.
                        # Re-ask the highest-priority missing field instead of finalizing.
                        next_missing = sorted(missing_fields, key=lambda x: FIELD_PRIORITY.get(x, 99))[0]
                        response_text = llm.generate_clarification_question(
                            [next_missing],
                            memory.conversation_history,
                            session_id
                        )
                        update_session_state(session_id, STATES["CLARIFYING"])
    
    elif current_state == STATES["COMPLETE"]:
        # Session already complete
        user_lower = (user_input or "").lower().strip().strip('.,!?')
        affirmatives = ["yes", "yep", "y", "ok", "okay", "sure", "show", "report", "please"]
        if any(word in user_lower for word in affirmatives):
            symptom_data = memory.get_symptom_data()
            summary = symptom_data.get("summary", "Summary not available.")
            response_text = f"Here is your summary report:\n\n{summary}\n\nYou can view the full report using the 'Farm Report' button."
        else:
            response_text = "Your crop assessment is complete. You can view your report or switch to the Farm Consult tab."
    
    else:
        # Unknown state, reset to greeting
        response_text = "Sorry, something went wrong. Let's start again. What primary crop concern are you having today?"
        update_session_state(session_id, STATES["COLLECTING"])
    
    # Save assistant response
    if response_text:
        save_turn(session_id, "assistant", response_text)
    
    # Get updated state
    final_state = get_session_state(session_id)
    is_complete = (final_state == STATES["COMPLETE"])

    # If in COMPLETE but we don't have crop health assessment in memory (subsequent turn), load them
    if (is_complete) and crop_health_assessment is None:
        symptom_data = memory.get_symptom_data()
        crop_health_assessment = risk.categorize_risk(symptom_data)
        # For farm tips, we can re-generate if LOW/MODERATE
        if crop_health_assessment['health_level'] in ["LOW", "MODERATE"]:
             farm_tip = llm.generate_farm_advice(symptom_data, session_id)
        else:
             farm_tip = f"Immediate action required. {crop_health_assessment['recommended_action']}"
    
    return {
        "response_text": response_text,
        "state": final_state,
        "is_complete": is_complete,
        "crop_health_assessment": crop_health_assessment,
        "farm_tip": farm_tip
    }
