"""
Crop health categorization module for AgriAssist
Uses deterministic rule-based logic (NO LLM involvement)
"""
from typing import Dict, Any, List
import json


# Critical crop issue keywords
CRITICAL_KEYWORDS = [
    "crop failure",
    "complete crop loss",
    "widespread crop death",
    "severe pest infestation",
    "total crop destruction",
    "uncontrolled blight",
    "field wilt",
    "root rot",
    "sudden leaf drop",
    "yellow mosaic virus",
    "fungal outbreak",
    "severe drought",
    "total field failure",
    "equipment failure",
    "toxic contamination",
]


HIGH_PRIORITY_KEYWORDS = [
    "severe disease",
    "major pest damage",
    "crop lodging",
    "extensive wilting",
    "yellowing leaves",
    "fungal spreading",
    "significant yield loss",
    "extreme weather damage",
]


def detect_urgent_keyword(text: str) -> Dict[str, str] | None:
    lowered = (text or "").lower()

    for keyword in CRITICAL_KEYWORDS:
        if keyword in lowered:
            return {"health_level": "CRITICAL", "keyword": keyword}

    for keyword in HIGH_PRIORITY_KEYWORDS:
        if keyword in lowered:
            return {"health_level": "HIGH", "keyword": keyword}

    return None


def build_urgent_assessment(detected: Dict[str, str], source_text: str) -> Dict[str, str]:
    """Build a deterministic urgent crop health assessment from detected keyword."""
    health_level = detected["health_level"]
    keyword = detected["keyword"]
    concern = (source_text or "").strip()

    if health_level == "CRITICAL":
        return {
            "health_level": "CRITICAL",
            "reason": f"Severe crop issue detected: '{keyword}' in concern '{concern}'.",
            "recommended_action": "Immediate action needed. Consult with an agronomist or agricultural extension service urgently."
        }

    return {
        "health_level": "HIGH",
        "reason": f"High-priority crop issue detected: '{keyword}' in concern '{concern}'.",
        "recommended_action": "Please consult with an agronomist for evaluation and treatment recommendations."
    }


def categorize_risk(crop_record: Dict[str, Any]) -> Dict[str, str]:
    """
    Categorize crop health level using deterministic rules
    
    Rules (in priority order):
    CRITICAL: severity >= 9 OR primary_concern contains critical keywords
    HIGH: severity >= 7 OR (progression == "worsening" AND duration <= 2 days)
    MODERATE: severity >= 4 OR associated_issues count >= 3
    LOW: everything else
    
    Args:
        crop_record: Dictionary containing all crop issue attributes
    
    Returns:
        Dictionary with health_level, reason, and recommended_action
    """
    severity = crop_record.get("severity")
    primary_concern = (crop_record.get("primary_concern") or "").lower()
    progression = crop_record.get("progression")
    duration = crop_record.get("duration") or ""
    associated_issues = crop_record.get("associated_issues") or []
    
    # Parse associated issues if stored as JSON string
    if isinstance(associated_issues, str):
        try:
            associated_issues = json.loads(associated_issues)
        except:
            associated_issues = []
    
    # CRITICAL: Check severity >= 9
    if severity is not None and severity >= 9:
        return {
            "health_level": "CRITICAL",
            "reason": f"Severity level {severity}/10 indicates critical crop damage",
            "recommended_action": "Immediate intervention required. Contact an agronomist or agricultural extension service immediately."
        }
    
    # CRITICAL: Check for critical keywords in primary concern
    for keyword in CRITICAL_KEYWORDS:
        if keyword in primary_concern:
            return {
                "health_level": "CRITICAL",
                "reason": f"Concern '{primary_concern}' contains critical issue: '{keyword}'",
                "recommended_action": "Immediate action required. Consult with an agronomist or agricultural extension service urgently."
            }

    # HIGH: Check for high-priority keywords in primary concern
    for keyword in HIGH_PRIORITY_KEYWORDS:
        if keyword in primary_concern:
            return {
                "health_level": "HIGH",
                "reason": f"Concern '{primary_concern}' contains high-priority issue: '{keyword}'",
                "recommended_action": "Schedule urgent consultation with an agronomist within 24-48 hours."
            }
    
    # HIGH: Check severity >= 7
    if severity is not None and severity >= 7:
        return {
            "health_level": "HIGH",
            "reason": f"Severity level {severity}/10 indicates significant crop stress",
            "recommended_action": "Contact an agronomist or extension service for urgent consultation and treatment options."
        }
    
    # HIGH: Check for worsening condition with short duration
    if progression == "worsening" and duration:
        duration_lower = duration.lower()
        # Check if duration mentions hours, 1 day, or 2 days
        if ("hour" in duration_lower or 
            "1 day" in duration_lower or 
            "2 day" in duration_lower or
            "today" in duration_lower or
            "yesterday" in duration_lower):
            return {
                "health_level": "HIGH",
                "reason": f"Crop condition worsening over short duration ({duration}) requires prompt evaluation",
                "recommended_action": "Schedule urgent consultation with an agronomist within 24 hours."
            }
    
    # MODERATE: Check severity >= 4
    if severity is not None and severity >= 4:
        return {
            "health_level": "MODERATE",
            "reason": f"Severity level {severity}/10 indicates moderate crop issues",
            "recommended_action": "Consult with an agronomist within 2-3 days for assessment and management plan."
        }
    
    # MODERATE: Check for multiple associated issues
    if len(associated_issues) >= 3:
        return {
            "health_level": "MODERATE",
            "reason": f"Multiple crop issues ({len(associated_issues)}) present",
            "recommended_action": "Consult with an agronomist within 2-3 days for assessment and management plan."
        }
    
    # LOW: Default case
    return {
        "health_level": "LOW",
        "reason": "Crop appears manageable with low severity indicators",
        "recommended_action": "Monitor crop status. Schedule routine agronomist consultation if issues persist or worsen."
    }
