"""
Database layer for AgriAssist
Handles SQLite operations for sessions, crop issue records, conversation turns, and latency logs
"""
import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Iterator
from contextlib import contextmanager
from config import DATABASE_PATH, STATES


@contextmanager
def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Context manager for database connections"""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """Initialize database with all required tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'greeting',
                asked_fields_json TEXT NOT NULL DEFAULT '[]'
            )
        """)

        # Migration for existing databases without asked_fields_json
        cursor.execute("PRAGMA table_info(sessions)")
        session_columns = [row[1] for row in cursor.fetchall()]
        if "asked_fields_json" not in session_columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN asked_fields_json TEXT NOT NULL DEFAULT '[]'")
        
        # Crop issue records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crop_issue_records (
                session_id TEXT PRIMARY KEY,
                primary_concern TEXT,
                duration TEXT,
                severity INTEGER,
                progression TEXT,
                associated_issues_json TEXT,
                affected_crop TEXT,
                onset_type TEXT,
                environmental_factors TEXT,
                farm_management_history TEXT,
                health_level TEXT,
                health_reason TEXT,
                recommended_action TEXT,
                summary TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        # Migration for existing databases
        cursor.execute("PRAGMA table_info(crop_issue_records)")
        crop_columns = [row[1] for row in cursor.fetchall()]
        if "environmental_factors" not in crop_columns:
            cursor.execute("ALTER TABLE crop_issue_records ADD COLUMN environmental_factors TEXT")
        if "farm_management_history" not in crop_columns:
            cursor.execute("ALTER TABLE crop_issue_records ADD COLUMN farm_management_history TEXT")
        
        # Conversation turns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        # Latency logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS latency_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        conn.commit()


def create_session(session_id: str = None) -> str:
    """Create a new session and return session ID"""
    if not session_id:
        session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, created_at, state, asked_fields_json) VALUES (?, ?, ?, ?)",
            (session_id, timestamp, STATES["GREETING"], json.dumps([]))
        )
        
        # Initialize empty crop issue record
        cursor.execute(
            "INSERT INTO crop_issue_records (session_id) VALUES (?)",
            (session_id,)
        )
    
    return session_id


def update_session_state(session_id: str, state: str):
    """Update session state"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET state = ? WHERE id = ?",
            (state, session_id)
        )


def get_session_state(session_id: str) -> Optional[str]:
    """Get current session state"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT state FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return row["state"] if row else None


def get_asked_fields(session_id: str) -> List[str]:
    """Get list of fields already asked for this session"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT asked_fields_json FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if not row or not row["asked_fields_json"]:
            return []
        try:
            return json.loads(row["asked_fields_json"])
        except json.JSONDecodeError:
            return []


def set_asked_fields(session_id: str, asked_fields: List[str]):
    """Persist asked fields list for a session"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET asked_fields_json = ? WHERE id = ?",
            (json.dumps(asked_fields), session_id)
        )


def save_turn(session_id: str, role: str, content: str):
    """Save a conversation turn"""
    timestamp = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversation_turns (session_id, timestamp, role, content) VALUES (?, ?, ?, ?)",
            (session_id, timestamp, role, content)
        )


def get_session_history(session_id: str) -> List[Dict[str, str]]:
    """Retrieve conversation history for a session"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM conversation_turns WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]


def update_symptom_record(session_id: str, fields: Dict[str, Any]):
    """Update crop issue record with new fields"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Build dynamic UPDATE query
        update_parts = []
        values = []
        
        for key, value in fields.items():
            if key in ["associated_issues", "associated_symptoms"]:
                update_parts.append("associated_issues_json = ?")
                values.append(json.dumps(value) if value else None)
            elif key == "risk_level":
                update_parts.append("health_level = ?")
                values.append(value)
            elif key == "risk_reason":
                update_parts.append("health_reason = ?")
                values.append(value)
            elif key in ["health_level", "health_reason", "recommended_action", "summary"]:
                update_parts.append(f"{key} = ?")
                values.append(value)
            elif key in ["primary_concern", "duration", "severity", "progression", "affected_crop", "onset_type", "environmental_factors", "farm_management_history"]:
                update_parts.append(f"{key} = ?")
                values.append(value)
        
        if update_parts:
            query = f"UPDATE crop_issue_records SET {', '.join(update_parts)} WHERE session_id = ?"
            values.append(session_id)
            cursor.execute(query, values)


def get_symptom_record(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve crop issue record for a session"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM crop_issue_records WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Convert row to dictionary
        record = dict(row)
        
        # Parse associated issues JSON
        if record.get("associated_issues_json"):
            record["associated_issues"] = json.loads(record["associated_issues_json"])
        else:
            record["associated_issues"] = None

        # Backward-compatible alias used by some legacy code paths
        record["associated_symptoms"] = record["associated_issues"]
        
        del record["associated_issues_json"]
        
        return record


def log_latency(session_id: str, operation_type: str, latency_ms: float):
    """Log latency for an operation"""
    timestamp = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO latency_logs (session_id, timestamp, operation_type, latency_ms) VALUES (?, ?, ?, ?)",
            (session_id, timestamp, operation_type, latency_ms)
        )


def session_exists(session_id: str) -> bool:
    """Check if a session exists"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,))
        return cursor.fetchone() is not None


def get_session_export_data(session_id: str) -> Optional[Dict[str, Any]]:
    """Get all data for session export"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get session info
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session = cursor.fetchone()
        if not session:
            return None
        
        # Get conversation history
        history = get_session_history(session_id)
        
        # Get crop issue record
        crop_issue_record = get_symptom_record(session_id)
        
        return {
            "session_id": session_id,
            "created_at": session["created_at"],
            "state": session["state"],
            "conversation_history": history,
            "crop_issue_record": crop_issue_record,
            "symptom_record": crop_issue_record
        }


def get_recent_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve a list of recent sessions for history management"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT s.id, s.created_at, s.state, sr.primary_concern, sr.health_level
            FROM sessions s
            LEFT JOIN crop_issue_records sr ON s.id = sr.session_id
            ORDER BY s.created_at DESC
            LIMIT ?
        """
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
