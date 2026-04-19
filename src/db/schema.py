"""Database schema definitions for x-bookmarked-posts.

D-03: Phase 1 creates minimal schema: users and tokens tables only.
Posts table deferred to Phase 2.

STOR-01: WAL mode enabled (applied in connection.py)
STOR-02: Foreign key constraints (applied in connection.py)
"""

# Schema version 1: Phase 1 - Authentication foundation
SCHEMA_V1 = """
-- Users table: stores X user information
-- Created in Phase 1 as part of authentication foundation
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    x_user_id TEXT UNIQUE NOT NULL,      -- X platform user ID (from GET /2/users/me)
    username TEXT NOT NULL,              -- X username (handle)
    display_name TEXT,                   -- Display name (nullable)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tokens table: stores OAuth 2.0 tokens for each user
-- Required for token persistence and refresh
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    access_token TEXT NOT NULL,          -- OAuth 2.0 access token
    refresh_token TEXT NOT NULL,         -- OAuth 2.0 refresh token
    expires_at TIMESTAMP,                 -- Token expiration time (nullable, ~2 hours)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Index for fast token lookup by user
-- Essential for: "get tokens for user X"
CREATE INDEX IF NOT EXISTS idx_tokens_user_id ON tokens(user_id);
"""

# Future schemas will be added as SCHEMA_V2, SCHEMA_V3, etc.
# Schema migration strategy will be defined in Phase 2+


def get_schema_version() -> str:
    """Get the current schema version identifier.

    Returns:
        Schema version string (e.g., "v1", "v2")
    """
    return "v1"


__all__ = ["SCHEMA_V1", "get_schema_version"]