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


# Schema version 3: Phase 3 - FTS5 full-text search, notes, link status
# Migration from v2 to v3 (not a standalone schema, but migration statements)
# Note: SQLite doesn't support ALTER TABLE IF NOT EXISTS, so migration handles idempotency
SCHEMA_V3_MIGRATION = """
-- D-02: Add note column for personal notes on posts
-- NOTE-01: User can add personal notes to bookmarked posts
-- NOTE-02: Notes displayed when post is resurfaced for review
-- ALTER TABLE posts ADD COLUMN note TEXT;  -- Run in migration with try/except

-- D-04: Add link_status column for dead link detection
-- MAINT-01: Application detects and flags dead links
-- MAINT-02: Application can filter dead links from review queue
-- ALTER TABLE posts ADD COLUMN link_status TEXT DEFAULT 'unchecked';  -- Run in migration

-- D-01: FTS5 virtual table for full-text search
-- SRCH-01: Full-text search within stored post content
-- SRCH-02: Search by author name or username
-- SRCH-03: Search results with context display (snippet/highlight)
CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
    text,                    -- Full-text indexed content
    author_username,         -- Searchable username
    author_display_name,     -- Searchable display name
    content='posts',        -- External content table
    content_rowid='rowid'   -- Use SQLite's built-in rowid
);

-- CRITICAL: Triggers to keep FTS5 index synchronized with posts table
-- See: https://sqlite.org/fts5.html - external content tables
-- Pitfall #1: FTS5 index goes stale without triggers

CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
    INSERT INTO posts_fts(rowid, text, author_username, author_display_name)
    VALUES (new.rowid, new.text, new.author_username, new.author_display_name);
END;

CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, text, author_username, author_display_name)
    VALUES ('delete', old.rowid, old.text, old.author_username, old.author_display_name);
END;

CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, text, author_username, author_display_name)
    VALUES ('delete', old.rowid, old.text, old.author_username, old.author_display_name);
    INSERT INTO posts_fts(rowid, text, author_username, author_display_name)
    VALUES (new.rowid, new.text, new.author_username, new.author_display_name);
END;
"""


# Schema version 4: Phase 4 - Tags, topics, and embeddings for topic organization
# ORG-01: User can assign tags to bookmarked posts
# ORG-02: User can create and manage a predefined topic taxonomy
# ORG-03: Application clusters posts into topics using hybrid approach
# ORG-04: User can review and approve AI-suggested topic assignments
SCHEMA_V4_MIGRATION = """
-- Tags table: User-defined tags for posts
-- ORG-01: User can assign tags to bookmarked posts
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,           -- Tag name (e.g., "python", "ml", "career")
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Post-Tags junction table: Many-to-many relationship
CREATE TABLE IF NOT EXISTS post_tags (
    post_id TEXT NOT NULL,               -- References posts.x_post_id
    tag_id INTEGER NOT NULL,             -- References tags.id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(x_post_id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Index for finding all tags on a post
CREATE INDEX IF NOT EXISTS idx_post_tags_post ON post_tags(post_id);
-- Index for finding all posts with a tag
CREATE INDEX IF NOT EXISTS idx_post_tags_tag ON post_tags(tag_id);

-- Topics table: Predefined topic taxonomy
-- ORG-02: User can create and manage a predefined topic taxonomy
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,           -- Topic name (e.g., "Programming", "Machine Learning")
    description TEXT,                    -- Optional description
    parent_id INTEGER,                   -- Optional parent topic for hierarchy
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES topics(id) ON DELETE SET NULL
);

-- Post-Topics table: Post-to-topic assignments (user-approved)
CREATE TABLE IF NOT EXISTS post_topics (
    post_id TEXT NOT NULL,
    topic_id INTEGER NOT NULL,
    confidence REAL,                     -- AI confidence score (0.0-1.0)
    source TEXT DEFAULT 'user',          -- 'user' or 'ai-approved'
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (post_id, topic_id),
    FOREIGN KEY (post_id) REFERENCES posts(x_post_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

-- Index for finding posts by topic
CREATE INDEX IF NOT EXISTS idx_post_topics_topic ON post_topics(topic_id);

-- Pending topic assignments: AI suggestions awaiting review
-- ORG-04: User can review and approve AI-suggested topic assignments
CREATE TABLE IF NOT EXISTS pending_topic_assignments (
    id INTEGER PRIMARY KEY,
    post_id TEXT NOT NULL,
    topic_id INTEGER NOT NULL,
    confidence REAL NOT NULL,            -- AI confidence score
    suggested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(x_post_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

-- Index for finding pending assignments
CREATE INDEX IF NOT EXISTS idx_pending_topic_assignments_post ON pending_topic_assignments(post_id);

-- Post embeddings cache: Store embeddings to avoid recomputation
-- ORG-03: Application clusters posts into topics using embeddings
CREATE TABLE IF NOT EXISTS post_embeddings (
    post_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,             -- 384 floats as binary (1536 bytes for float32)
    model_name TEXT DEFAULT 'all-MiniLM-L6-v2',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(x_post_id) ON DELETE CASCADE
);
"""


# Schema version 5: Phase 5 - Post review state for spaced repetition scheduling
# SPAC-01: Review state table for spaced repetition scheduling
# SPAC-02: get_due_posts query returns posts where scheduled_for <= NOW
# SPAC-04: Themed reviews filter by topic via post_topics join
SCHEMA_V5_MIGRATION = """
-- Post review state: Track FSRS scheduling state for each post
-- SPAC-01: Database schema V5 includes post_review_state table
-- D-14: FSRS Card state serialization in fsrs_data column
-- D-15: Initial scheduled_for seeded from posts.created_at
CREATE TABLE IF NOT EXISTS post_review_state (
    post_id TEXT PRIMARY KEY,              -- References posts.x_post_id
    scheduled_for TIMESTAMP NOT NULL,      -- Next review date (D-15: seeded from created_at)
    last_reviewed TIMESTAMP,               -- When last reviewed
    review_count INTEGER DEFAULT 0,        -- Number of times reviewed
    user_preference TEXT,                  -- Last user choice: 'fresh', 'soon', 'later'
    stability REAL,                        -- FSRS parameter
    difficulty REAL,                       -- FSRS parameter
    state INTEGER DEFAULT 0,                -- FSRS state: 0=new, 1=learning, 2=review, 3=relearning
    step INTEGER,                           -- FSRS learning step (nullable)
    fsrs_data TEXT,                         -- FSRS Card JSON serialization (D-14)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(x_post_id) ON DELETE CASCADE
);

-- Index for due posts query (SPAC-02)
CREATE INDEX IF NOT EXISTS idx_review_state_scheduled ON post_review_state(scheduled_for);

-- Index for themed reviews join (SPAC-04)
CREATE INDEX IF NOT EXISTS idx_review_state_post ON post_review_state(post_id);
"""


# Schema version 6: Phase 8 - Embedded posts for retweets and quote tweets
# STR-01: Embedded posts table stores original tweet content
# STR-02: Posts table gains post_type and embedded_post_id columns
SCHEMA_V6_MIGRATION = """
-- STR-01: Embedded posts table for retweet/quote original content
-- D-01: Columns mirror posts table structure for normalization
CREATE TABLE IF NOT EXISTS embedded_posts (
    x_post_id TEXT PRIMARY KEY,           -- Original tweet ID
    created_at TIMESTAMP NOT NULL,        -- Publication date
    text TEXT NOT NULL,                    -- Original tweet text
    author_id TEXT NOT NULL,               -- X user ID
    author_username TEXT NOT NULL,         -- @handle
    author_display_name TEXT,              -- Display name
    media_urls TEXT,                       -- JSON array of media URLs
    link_urls TEXT,                        -- JSON array of link URLs
    available INTEGER DEFAULT 1            -- Boolean: 1=available, 0=deleted/protected
);
"""


def get_schema_version() -> str:
    """Get the current schema version identifier.

    Returns:
        Schema version string (e.g., "v1", "v2", "v3", "v4", "v5", "v6")
    """
    return "v6"


__all__ = ["SCHEMA_V1", "SCHEMA_V2", "SCHEMA_V3_MIGRATION", "SCHEMA_V4_MIGRATION", "SCHEMA_V5_MIGRATION", "SCHEMA_V6_MIGRATION", "get_schema_version"]