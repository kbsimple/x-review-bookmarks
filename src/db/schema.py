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

# Schema version 2: Phase 2 - Posts and sync_state tables
SCHEMA_V2 = """
-- Posts table: stores bookmarked posts from X API
-- D-01: Full content storage per DATA-02, DATA-03
CREATE TABLE IF NOT EXISTS posts (
    x_post_id TEXT PRIMARY KEY,        -- Tweet ID from X API
    created_at TIMESTAMP NOT NULL,     -- Publication date (DATA-03)
    text TEXT NOT NULL,                 -- Tweet text content
    author_id TEXT NOT NULL,            -- X user ID
    author_username TEXT NOT NULL,     -- @handle
    author_display_name TEXT,          -- Display name
    media_urls TEXT,                   -- JSON array of media URLs
    link_urls TEXT,                     -- JSON array of link URLs from entities
    bookmarked_at TIMESTAMP,           -- When user bookmarked (from API if available)
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_version INTEGER DEFAULT 1
);

-- Index for incremental sync lookup (DATA-03: publication date for scheduling)
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);

-- Sync state table: tracks sync progress for incremental sync
-- D-02: Incremental sync via bookmark ID comparison
CREATE TABLE IF NOT EXISTS sync_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Single-row table
    last_sync_bookmark_id TEXT,              -- Highest bookmark ID seen
    last_sync_at TIMESTAMP,                  -- Timestamp of last successful sync
    pagination_token TEXT,                   -- Resume point if interrupted (DATA-04)
    total_bookmarks INTEGER DEFAULT 0,       -- Total count for 800 limit tracking (DATA-05)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_schema_version() -> str:
    """Get the current schema version identifier.

    Returns:
        Schema version string (e.g., "v1", "v2")
    """
    return "v2"


__all__ = ["SCHEMA_V1", "get_schema_version"]