-- ═══════════════════════════════════════════════════════════════
-- AgriHelper Database Schema
-- Multilingual AI Voice Assistant for Farmers
-- ═══════════════════════════════════════════════════════════════

-- Stores every conversation turn in the voice assistant pipeline
CREATE TABLE IF NOT EXISTS conversations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL DEFAULT 'default_farmer',
    session_id      TEXT NOT NULL,
    timestamp       DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
    language        TEXT NOT NULL DEFAULT 'en',          -- ta / hi / en
    spoken_text     TEXT NOT NULL,                       -- Transcribed speech
    intent          TEXT,                                -- Classified intent
    entities        TEXT,                                -- JSON: extracted entities
    knowledge_data  TEXT,                                -- JSON: retrieved knowledge
    response_text   TEXT,                                -- Generated response
    audio_input     TEXT,                                -- Path to input WAV
    audio_output    TEXT,                                -- Path to response WAV
    processing_time REAL,                                -- Seconds
    success         BOOLEAN DEFAULT 1,
    error_message   TEXT
);

-- Farmer profiles for personalization
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id         TEXT PRIMARY KEY,
    name            TEXT,
    preferred_lang  TEXT DEFAULT 'en',
    location        TEXT,
    primary_crops   TEXT,                                -- JSON array
    soil_type       TEXT,
    farm_size_acres REAL,
    created_at      DATETIME DEFAULT (datetime('now','localtime')),
    updated_at      DATETIME DEFAULT (datetime('now','localtime'))
);

-- User feedback on responses
CREATE TABLE IF NOT EXISTS feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER REFERENCES conversations(id),
    user_id         TEXT NOT NULL,
    rating          INTEGER CHECK(rating BETWEEN 1 AND 5),
    comment         TEXT,
    timestamp       DATETIME DEFAULT (datetime('now','localtime'))
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_conv_user      ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_intent    ON conversations(intent);
CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp);
CREATE INDEX IF NOT EXISTS idx_conv_session   ON conversations(session_id);
