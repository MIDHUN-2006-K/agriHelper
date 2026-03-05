"""
Session memory management for AgriHelper.
"""

from typing import Any, Dict, List, Set

from database import (
    get_profile_record,
    get_session_history,
    get_asked_fields,
    set_asked_fields,
    update_profile_record,
)


REQUIRED_FIELDS = [
    "primary_problem",
    "crop_name",
    "location",
    "season",
    "soil_type",
]


class SessionMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.profile_data: Dict[str, Any] = {}
        self.asked_fields: Set[str] = set()
        self.conversation_history: List[Dict[str, str]] = []
        self.load_state()

    def load_state(self) -> None:
        profile = get_profile_record(self.session_id)
        if profile:
            for field in REQUIRED_FIELDS + ["farm_size_acres", "summary"]:
                value = profile.get(field)
                if value is not None:
                    self.profile_data[field] = value

        self.conversation_history = get_session_history(self.session_id)
        self.asked_fields = set(get_asked_fields(self.session_id))

    def update_fields(self, new_data: Dict[str, Any]) -> None:
        updated = False
        for field, new_value in new_data.items():
            if new_value is None:
                continue

            if isinstance(new_value, str) and not new_value.strip():
                continue

            current_value = self.profile_data.get(field)
            if current_value is None or (isinstance(current_value, str) and not current_value.strip()):
                self.profile_data[field] = new_value
                updated = True

        if updated:
            self.persist()

    def get_missing_fields(self) -> List[str]:
        missing: List[str] = []
        for field in REQUIRED_FIELDS:
            value = self.profile_data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)
        return missing

    def mark_field_asked(self, field_name: str) -> None:
        self.asked_fields.add(field_name)
        set_asked_fields(self.session_id, sorted(self.asked_fields))

    def persist(self) -> None:
        update_profile_record(self.session_id, self.profile_data)

    def get_profile_data(self) -> Dict[str, Any]:
        return self.profile_data.copy()

    def get_progress(self) -> Dict[str, bool]:
        progress: Dict[str, bool] = {}
        for field in REQUIRED_FIELDS:
            value = self.profile_data.get(field)
            progress[field] = bool(value and (not isinstance(value, str) or value.strip()))
        return progress
