"""
Database layer for AgriHelper API.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

from config.settings import DATABASE_PATH


@contextmanager
def get_db_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database() -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'greeting',
                asked_fields_json TEXT NOT NULL DEFAULT '[]',
                intent TEXT,
                last_query TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_records (
                session_id TEXT PRIMARY KEY,
                primary_problem TEXT,
                crop_name TEXT,
                location TEXT,
                season TEXT,
                soil_type TEXT,
                farm_size_acres REAL,
                summary TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS latency_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
            """
        )


def create_session(session_id: Optional[str] = None) -> str:
    if not session_id:
        session_id = str(uuid.uuid4())

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, created_at, state, asked_fields_json) VALUES (?, ?, ?, ?)",
            (session_id, datetime.utcnow().isoformat(), "greeting", json.dumps([])),
        )
        cursor.execute("INSERT INTO profile_records (session_id) VALUES (?)", (session_id,))

    return session_id


def session_exists(session_id: str) -> bool:
    with get_db_connection() as conn:
        row = conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return row is not None


def update_session_state(session_id: str, state: str) -> None:
    with get_db_connection() as conn:
        conn.execute("UPDATE sessions SET state = ? WHERE id = ?", (state, session_id))


def get_session_state(session_id: str) -> Optional[str]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT state FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return row["state"] if row else None


def update_session_metadata(session_id: str, intent: Optional[str], last_query: Optional[str]) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE sessions SET intent = ?, last_query = ? WHERE id = ?",
            (intent, last_query, session_id),
        )


def get_asked_fields(session_id: str) -> List[str]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT asked_fields_json FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row or not row["asked_fields_json"]:
            return []
        try:
            return json.loads(row["asked_fields_json"])
        except json.JSONDecodeError:
            return []


def set_asked_fields(session_id: str, asked_fields: List[str]) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE sessions SET asked_fields_json = ? WHERE id = ?",
            (json.dumps(asked_fields), session_id),
        )


def save_turn(session_id: str, role: str, content: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO conversation_turns (session_id, timestamp, role, content) VALUES (?, ?, ?, ?)",
            (session_id, datetime.utcnow().isoformat(), role, content),
        )


def get_session_history(session_id: str) -> List[Dict[str, str]]:
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversation_turns WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,),
        ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]


def update_profile_record(session_id: str, fields: Dict[str, Any]) -> None:
    allowed_fields = {
        "primary_problem",
        "crop_name",
        "location",
        "season",
        "soil_type",
        "farm_size_acres",
        "summary",
    }
    filtered = {key: value for key, value in fields.items() if key in allowed_fields}
    if not filtered:
        return

    set_clause = ", ".join([f"{field} = ?" for field in filtered.keys()])
    values = list(filtered.values())
    values.append(session_id)

    with get_db_connection() as conn:
        conn.execute(f"UPDATE profile_records SET {set_clause} WHERE session_id = ?", values)


def get_profile_record(session_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM profile_records WHERE session_id = ?", (session_id,)).fetchone()
        return dict(row) if row else None


def get_session_export_data(session_id: str) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not session:
            return None
        profile = conn.execute("SELECT * FROM profile_records WHERE session_id = ?", (session_id,)).fetchone()

    return {
        "session_id": session_id,
        "created_at": session["created_at"],
        "state": session["state"],
        "intent": session["intent"],
        "profile": dict(profile) if profile else {},
        "conversation_history": get_session_history(session_id),
    }


def log_latency(session_id: str, operation_type: str, latency_ms: float) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO latency_logs (session_id, timestamp, operation_type, latency_ms) VALUES (?, ?, ?, ?)",
            (session_id, datetime.utcnow().isoformat(), operation_type, latency_ms),
        )
