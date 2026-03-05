"""
Conversation Memory Module
SQLite-based persistent storage for conversation history.
Enables personalization and future recommendations.
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

# ── Database Schema ──────────────────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL DEFAULT 'default_farmer',
    session_id      TEXT NOT NULL,
    timestamp       DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
    language        TEXT NOT NULL DEFAULT 'en',
    spoken_text     TEXT NOT NULL,
    intent          TEXT,
    entities        TEXT,      -- JSON string
    knowledge_data  TEXT,      -- JSON string
    response_text   TEXT,
    audio_input     TEXT,      -- Path to input audio file
    audio_output    TEXT,      -- Path to output audio file
    processing_time REAL,      -- Seconds
    success         BOOLEAN DEFAULT 1,
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id         TEXT PRIMARY KEY,
    name            TEXT,
    preferred_lang  TEXT DEFAULT 'en',
    location        TEXT,
    primary_crops   TEXT,      -- JSON array
    soil_type       TEXT,
    farm_size_acres REAL,
    created_at      DATETIME DEFAULT (datetime('now','localtime')),
    updated_at      DATETIME DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER REFERENCES conversations(id),
    user_id         TEXT NOT NULL,
    rating          INTEGER CHECK(rating BETWEEN 1 AND 5),
    comment         TEXT,
    timestamp       DATETIME DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_intent ON conversations(intent);
CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp);
CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
"""


class ConversationMemory:
    """Manages conversation history and user profiles using SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(SCHEMA_SQL)
            logger.info(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Conversation CRUD ────────────────────────────────────────────────────
    def save_conversation(
        self,
        user_id: str,
        session_id: str,
        language: str,
        spoken_text: str,
        intent: str,
        entities: dict,
        knowledge_data: dict,
        response_text: str,
        audio_input: Optional[str] = None,
        audio_output: Optional[str] = None,
        processing_time: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> int:
        """Save a conversation turn to the database."""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO conversations
                        (user_id, session_id, language, spoken_text, intent, entities,
                         knowledge_data, response_text, audio_input, audio_output,
                         processing_time, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        session_id,
                        language,
                        spoken_text,
                        intent,
                        json.dumps(entities, ensure_ascii=False),
                        json.dumps(knowledge_data, ensure_ascii=False),
                        response_text,
                        audio_input,
                        audio_output,
                        processing_time,
                        success,
                        error_message,
                    ),
                )
                conv_id = cursor.lastrowid
                logger.info(f"Conversation saved: id={conv_id}, user={user_id}")
                return conv_id

        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            return -1

    def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10,
        intent_filter: Optional[str] = None,
    ) -> List[dict]:
        """Retrieve conversation history for a user."""
        try:
            with self._get_conn() as conn:
                query = "SELECT * FROM conversations WHERE user_id = ?"
                params = [user_id]

                if intent_filter:
                    query += " AND intent = ?"
                    params.append(intent_filter)

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                rows = conn.execute(query, params).fetchall()

                return [
                    {
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "language": row["language"],
                        "spoken_text": row["spoken_text"],
                        "intent": row["intent"],
                        "entities": json.loads(row["entities"]) if row["entities"] else {},
                        "response_text": row["response_text"],
                        "success": bool(row["success"]),
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to retrieve history: {e}")
            return []

    def get_session_history(self, session_id: str) -> List[dict]:
        """Get all conversations in a session."""
        try:
            with self._get_conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM conversations WHERE session_id = ? ORDER BY timestamp ASC",
                    (session_id,),
                ).fetchall()

                return [
                    {
                        "id": row["id"],
                        "timestamp": row["timestamp"],
                        "spoken_text": row["spoken_text"],
                        "intent": row["intent"],
                        "response_text": row["response_text"],
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to retrieve session history: {e}")
            return []

    # ── User Profile ─────────────────────────────────────────────────────────
    def save_user_profile(
        self,
        user_id: str,
        name: Optional[str] = None,
        preferred_lang: str = "en",
        location: Optional[str] = None,
        primary_crops: Optional[list] = None,
        soil_type: Optional[str] = None,
        farm_size_acres: Optional[float] = None,
    ) -> bool:
        """Create or update a user profile."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO user_profiles
                        (user_id, name, preferred_lang, location, primary_crops,
                         soil_type, farm_size_acres)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        name = COALESCE(excluded.name, name),
                        preferred_lang = excluded.preferred_lang,
                        location = COALESCE(excluded.location, location),
                        primary_crops = COALESCE(excluded.primary_crops, primary_crops),
                        soil_type = COALESCE(excluded.soil_type, soil_type),
                        farm_size_acres = COALESCE(excluded.farm_size_acres, farm_size_acres),
                        updated_at = datetime('now','localtime')
                    """,
                    (
                        user_id,
                        name,
                        preferred_lang,
                        location,
                        json.dumps(primary_crops) if primary_crops else None,
                        soil_type,
                        farm_size_acres,
                    ),
                )
                logger.info(f"User profile saved: {user_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")
            return False

    def get_user_profile(self, user_id: str) -> Optional[dict]:
        """Retrieve a user profile."""
        try:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
                ).fetchone()

                if row is None:
                    return None

                return {
                    "user_id": row["user_id"],
                    "name": row["name"],
                    "preferred_lang": row["preferred_lang"],
                    "location": row["location"],
                    "primary_crops": json.loads(row["primary_crops"]) if row["primary_crops"] else [],
                    "soil_type": row["soil_type"],
                    "farm_size_acres": row["farm_size_acres"],
                }

        except Exception as e:
            logger.error(f"Failed to retrieve user profile: {e}")
            return None

    # ── Analytics ─────────────────────────────────────────────────────────────
    def get_stats(self, user_id: Optional[str] = None) -> dict:
        """Get usage statistics."""
        try:
            with self._get_conn() as conn:
                where = "WHERE user_id = ?" if user_id else ""
                params = [user_id] if user_id else []

                total = conn.execute(
                    f"SELECT COUNT(*) FROM conversations {where}", params
                ).fetchone()[0]

                intent_counts = conn.execute(
                    f"""SELECT intent, COUNT(*) as cnt
                        FROM conversations {where}
                        GROUP BY intent ORDER BY cnt DESC""",
                    params,
                ).fetchall()

                lang_counts = conn.execute(
                    f"""SELECT language, COUNT(*) as cnt
                        FROM conversations {where}
                        GROUP BY language ORDER BY cnt DESC""",
                    params,
                ).fetchall()

                avg_time = conn.execute(
                    f"""SELECT AVG(processing_time)
                        FROM conversations {where} AND processing_time IS NOT NULL""" 
                    if where else
                    "SELECT AVG(processing_time) FROM conversations WHERE processing_time IS NOT NULL",
                    params,
                ).fetchone()[0]

                return {
                    "total_conversations": total,
                    "intents": {row["intent"]: row["cnt"] for row in intent_counts},
                    "languages": {row["language"]: row["cnt"] for row in lang_counts},
                    "avg_processing_time_sec": round(avg_time, 2) if avg_time else None,
                }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}

    # ── Feedback ──────────────────────────────────────────────────────────────
    def save_feedback(
        self, conversation_id: int, user_id: str, rating: int, comment: Optional[str] = None
    ) -> bool:
        """Save user feedback for a conversation."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO feedback (conversation_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
                    (conversation_id, user_id, rating, comment),
                )
                return True
        except Exception as e:
            logger.error(f"Failed to save feedback: {e}")
            return False
