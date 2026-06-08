# Architecture Research

**Domain:** X Bookmarked Posts Organizer - Retweet/Quote Tweet Support (Milestone v1.2)
**Context:** Adding embedded post rendering to existing FastAPI + SQLite + Cast architecture
**Researched:** 2026-06-04
**Confidence:** HIGH

---

## Part 1: Existing Architecture Overview

The current application uses a clean layered architecture:

```
src/
├── cli/
│   └── main.py              # Typer CLI entry point
├── services/
│   ├── sync.py              # Bookmark sync from X API
│   ├── search.py            # FTS5 full-text search
│   ├── export.py            # JSON/CSV import/export
│   ├── link_checker.py      # Dead link detection
│   ├── embedding.py         # Text embeddings
│   ├── clustering.py        # Topic clustering
│   ├── topic_suggester.py   # AI topic suggestions
│   ├── review_scheduler.py  # FSRS spaced repetition
│   └── review_service.py    # Review workflow logic
├── repositories/
│   ├── posts.py             # Post data access
│   ├── tags.py              # Tag CRUD
│   ├── topics.py            # Topic taxonomy
│   ├── sync_state.py        # Sync metadata
│   └── review_state.py      # Review state persistence
├── db/
│   ├── connection.py        # SQLite factory with WAL mode
│   ├── schema.py            # Table definitions
│   └── migrations.py        # Schema migrations
├── auth/
│   └── oauth.py             # OAuth 2.0 PKCE flow
├── api/
│   └── x_client.py          # X API client (tweepy wrapper)
├── web/
│   ├── app.py               # FastAPI application
│   ├── routes/              # Web routes (browse, search, cast)
│   └── templates/           # Jinja2 templates
└── config/
    └── settings.py          # Pydantic Settings
```

**Key Patterns:**
- **Repository Pattern**: Data access abstracted in repositories/
- **Service Layer**: Business logic in services/
- **Connection Factory**: `init_database()` returns SQLite connection with proper PRAGMAs
- **Token Storage**: `data/tokens.json` for OAuth credentials

---

## Part 2: Embedded Post Architecture

### System Overview with Embedded Posts

```
+------------------------------------------------------------------+
|                        Presentation Layer                         |
+------------------------------------------------------------------+
|  +-------------+  +-------------+  +---------------------------+ |
|  |   CLI App   |  |  FastAPI    |  |   Cast Receiver (HTML/JS) | |
|  |   (Typer)   |  |   Routes    |  |   Runs on Chromecast      | |
|  +------+------+  +------+------+  +-------------+-------------+ |
         |                |                        |
+--------v----------------v------------------------v---------------+
|                        Service Layer                              |
+------------------------------------------------------------------+
|  +-------------+  +-------------+  +-------------+              |
|  | SyncService |  |SearchService|  |ReviewService|   ...        |
|  +------+------+  +------+------+  +------+------+              |
|         |                                                          |
|         v  (NEW: extracts embedded posts)                         |
|  +-------------------+                                             |
|  | EmbeddedPostRepo |  <-- NEW: stores embedded posts            |
|  +-------------------+                                             |
+------------------------------------------------------------------+
         |
+--------v--------------------------+
|        Repository Layer           |
+----------------------------------+
|  +-------------+  +-------------+|
|  | PostsRepo   |  |EmbeddedRepo||
|  +------+------+  +-------------+|
+----------------------------------+
         |
+--------v--------------------------+
|        SQLite Database            |
+----------------------------------+
|  posts | embedded_posts | topics |
+----------------------------------+
```

### Data Flow for Embedded Posts

```
X API Bookmarks Endpoint
         |
         v
+-------------------+
|    XClient        |  (MODIFIED: fetches referenced_tweets)
| fetch_bookmarks() |
+-------------------+
         |
         v  BookmarkFetchResult
         |   - tweets[]
         |   - users{}
         |   - media{}
         |   - referenced_tweets{}  <-- NEW
         |
+-------------------+
|   SyncService     |
|  _store_tweet()  |  (MODIFIED: extracts embedded posts)
+-------------------+
         |
         +--------------------------+
         |                          |
         v                          v
+-------------------+    +-------------------+
|  PostsRepository  |    | EmbeddedPostRepo  |
|  upsert_post()    |    | upsert_embedded() |
+-------------------+    +-------------------+
         |                          |
         v                          v
     posts table              embedded_posts table
     (post_type,              (original tweet data)
      embedded_post_id)
         |
         v
+-------------------+
|  FastAPI Routes   |
|  /browse, /api    |
+-------------------+
         |
         v
   Jinja2 Templates
   (browse.html with
    embedded_post.html macro)
         |
         v
+-------------------+
|   Cast Receiver   |
|   (MODIFIED)      |
+-------------------+
```

---

## Part 3: Database Schema Changes

### Schema Version 6: Embedded Posts

```sql
-- Schema version 6: Embedded posts for retweets and quote tweets
-- EMB-01: Store embedded post data for retweets and quote tweets
-- EMB-02: Embedded posts display with full original content

-- Add columns to posts table to track post type
ALTER TABLE posts ADD COLUMN post_type TEXT DEFAULT 'original';
-- Values: 'original', 'retweet', 'quote'

ALTER TABLE posts ADD COLUMN embedded_post_id TEXT;
-- References embedded_posts.x_post_id of the embedded/quoted post
-- For retweets: the original tweet ID
-- For quotes: the quoted tweet ID

-- Create embedded_posts table for storing referenced posts
-- These are NOT bookmarks - they're context for bookmarked posts
CREATE TABLE IF NOT EXISTS embedded_posts (
    x_post_id TEXT PRIMARY KEY,        -- Original tweet ID
    created_at TIMESTAMP NOT NULL,     -- Original publication date
    text TEXT NOT NULL,                -- Original text content
    author_id TEXT NOT NULL,           -- Original author ID
    author_username TEXT NOT NULL,     -- Original @handle
    author_display_name TEXT,          -- Original display name
    media_urls TEXT,                   -- JSON array of media URLs
    link_urls TEXT,                    -- JSON array of link URLs
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for finding embedded posts by author
CREATE INDEX IF NOT EXISTS idx_embedded_posts_author ON embedded_posts(author_id);

-- Index for finding posts that reference a specific embedded post
CREATE INDEX IF NOT EXISTS idx_posts_embedded_id ON posts(embedded_post_id);
```

### Entity Relationships

```
posts (bookmarked)
    |
    +-- post_type = 'original' --> No embedded content
    |
    +-- post_type = 'retweet' --> embedded_post_id --> embedded_posts
    |                                                     |
    |                                                     v
    |                                              Original tweet data
    |
    +-- post_type = 'quote' --> embedded_post_id --> embedded_posts
                                                       |
                                                       v
                                                Original tweet data
```

**Key Insight:** Embedded posts are NOT bookmarks. They're context data for retweets and quotes. They shouldn't appear in search results, review queue, or exports independently.

---

## Part 4: X API Integration Changes

### X API v2 Referenced Tweets Structure

From official X API documentation, retweets and quote tweets contain a `referenced_tweets` field:

```json
// Retweet example
{
  "data": [{
    "id": "1229851574555508737",
    "text": "RT @suhemparack: I built an Alexa Skill for Twitter...",
    "referenced_tweets": [{
      "type": "retweeted",
      "id": "1229843515603144704"
    }]
  }]
}

// Quote tweet example
{
  "data": [{
    "id": "1328399838128467969",
    "text": "My commentary here https://t.co/...",
    "referenced_tweets": [{
      "type": "quoted",
      "id": "1327011423252144128"
    }]
  }]
}
```

### Modified XClient Expansions

```python
class XClient:
    # Current expansions
    EXPANSIONS = "author_id,attachments.media_keys"

    # EMB-01: Add referenced_tweets expansions for embedded posts
    EXPANSIONS = (
        "author_id,attachments.media_keys,"
        "referenced_tweets.id,"
        "referenced_tweets.id.author_id,"
        "referenced_tweets.id.attachments.media_keys"
    )

    # Add referenced_tweets to tweet fields
    TWEET_FIELDS = (
        "created_at,public_metrics,attachments,entities,referenced_tweets"
    )
```

### Modified BookmarkFetchResult

```python
@dataclass
class BookmarkFetchResult:
    tweets: list[Any] = field(default_factory=list)
    users: dict[str, Any] = field(default_factory=dict)
    media: dict[str, Any] = field(default_factory=dict)
    # EMB-01: Add referenced_tweets dict
    referenced_tweets: dict[str, Any] = field(default_factory=dict)
    next_token: Optional[str] = None
    result_count: int = 0
    rate_limit: RateLimitInfo = field(default_factory=RateLimitInfo)
```

### Sync Service Changes

```python
def _store_tweet(self, tweet: Any, fetch_result: BookmarkFetchResult) -> None:
    """Store a single tweet with embedded post handling."""

    # Determine post type from referenced_tweets
    post_type = "original"
    embedded_post_id = None

    if hasattr(tweet, 'referenced_tweets') and tweet.referenced_tweets:
        for ref in tweet.referenced_tweets:
            if ref.type == "retweeted":
                post_type = "retweet"
                embedded_post_id = str(ref.id)
                break
            elif ref.type == "quoted":
                post_type = "quote"
                embedded_post_id = str(ref.id)
                break

    # Store embedded post data if present
    if embedded_post_id and embedded_post_id in fetch_result.referenced_tweets:
        self._store_embedded_post(
            fetch_result.referenced_tweets[embedded_post_id],
            fetch_result
        )

    # Store main post
    post = {
        'x_post_id': str(tweet.id),
        'created_at': tweet.created_at.isoformat(),
        'text': tweet.text,
        'author_id': str(tweet.author_id),
        'author_username': author.username,
        'author_display_name': author.name,
        'media_urls': [...],
        'link_urls': [...],
        'post_type': post_type,
        'embedded_post_id': embedded_post_id,
    }
    self._posts_repo.upsert_post(post)
```

---

## Part 5: Template Rendering Patterns

### Jinja2 Macro for Embedded Posts

```html
<!-- templates/components/embedded_post.html -->
{% macro render_embedded_post(embedded_post, post_type) %}
<div class="embedded-post-container border-l-4 pl-4 my-3
            {% if post_type == 'retweet' %}border-green-500 bg-green-50{% else %}border-blue-500 bg-blue-50{% endif %}">
    {% if post_type == 'retweet' %}
    <div class="text-sm text-gray-500 mb-1">
        <span class="font-medium text-green-600">Retweeted</span>
    </div>
    {% elif post_type == 'quote' %}
    <div class="text-sm text-gray-500 mb-1">
        <span class="font-medium text-blue-600">Quoting</span>
    </div>
    {% endif %}

    <div class="embedded-post">
        <div class="flex items-center gap-2 mb-2">
            <span class="font-medium text-gray-900">@{{ embedded_post.author_username }}</span>
            <span class="text-xs text-gray-400">{{ embedded_post.created_at[:10] }}</span>
        </div>
        <p class="text-gray-700">{{ embedded_post.text[:300] }}{% if embedded_post.text|length > 300 %}...{% endif %}</p>
        {% if embedded_post.media_urls and embedded_post.media_urls|length > 0 %}
        <div class="embedded-images mt-2">
            <img src="{{ embedded_post.media_urls[0] }}" alt="" class="rounded max-w-xs">
        </div>
        {% endif %}
        <a href="https://x.com/{{ embedded_post.author_username }}/status/{{ embedded_post.x_post_id }}"
           target="_blank" class="text-xs text-blue-500 hover:underline mt-2 inline-block">
            View original on X
        </a>
    </div>
</div>
{% endmacro %}
```

### Modified browse.html Template

```html
{% extends "base.html" %}
{% from "components/embedded_post.html" import render_embedded_post %}

{% block content %}
<div class="space-y-6">
    {% for post in posts %}
    <div class="bg-white rounded-lg shadow p-4 hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between mb-2">
            <span class="text-sm text-gray-500">
                {% if post.post_type == 'retweet' %}
                <span class="text-green-600 font-medium">Retweet</span> by
                {% elif post.post_type == 'quote' %}
                <span class="text-blue-600 font-medium">Quote</span> by
                {% endif %}
                @{{ post.author_username }}
            </span>
            <span class="text-xs text-gray-400">{{ post.created_at[:10] }}</span>
        </div>

        {% if post.post_type == 'retweet' %}
        {# Retweet: Show embedded post only (retweets have no added text) #}
        {% if post.embedded_post %}
        {{ render_embedded_post(post.embedded_post, 'retweet') }}
        {% else %}
        <div class="text-gray-400 italic">Original post no longer available</div>
        {% endif %}

        {% elif post.post_type == 'quote' %}
        {# Quote: Show user's commentary first, then embedded post #}
        <p class="text-gray-800 mb-3">{{ post.text[:200] }}{% if post.text|length > 200 %}...{% endif %}</p>
        {% if post.embedded_post %}
        {{ render_embedded_post(post.embedded_post, 'quote') }}
        {% else %}
        <div class="text-gray-400 italic">Quoted post no longer available</div>
        {% endif %}

        {% else %}
        {# Original post #}
        <p class="text-gray-800 mb-3">{{ post.text[:200] }}{% if post.text|length > 200 %}...{% endif %}</p>
        {% endif %}

        {# Rest of post card (images, tags, topics, etc.) #}
    </div>
    {% endfor %}
</div>
{% endblock %}
```

---

## Part 6: Repository Changes

### PostsRepository Modifications

```python
def get_by_id(self, x_post_id: str) -> Optional[dict[str, Any]]:
    """Get a post by x_post_id with embedded post data."""

    row = self._conn.execute(
        "SELECT * FROM posts WHERE x_post_id = ?",
        (x_post_id,)
    ).fetchone()

    if row is None:
        return None

    post = self._row_to_dict(row)

    # EMB-02: Load embedded post if present
    if post.get('embedded_post_id'):
        embedded = self._conn.execute(
            "SELECT * FROM embedded_posts WHERE x_post_id = ?",
            (post['embedded_post_id'],)
        ).fetchone()

        if embedded:
            post['embedded_post'] = self._embedded_row_to_dict(embedded)

    return post

def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
    """Convert a database row to dict, parsing JSON fields."""
    return {
        'x_post_id': row['x_post_id'],
        'created_at': row['created_at'],
        'text': row['text'],
        'author_id': row['author_id'],
        'author_username': row['author_username'],
        'author_display_name': row['author_display_name'],
        'media_urls': json.loads(row['media_urls']) if row['media_urls'] else [],
        'link_urls': json.loads(row['link_urls']) if row['link_urls'] else [],
        'bookmarked_at': row['bookmarked_at'],
        'fetched_at': row['fetched_at'],
        'sync_version': row['sync_version'],
        'note': row['note'] if 'note' in row.keys() else None,
        'link_status': row['link_status'] if 'link_status' in row.keys() else 'unchecked',
        'post_type': row['post_type'] if 'post_type' in row.keys() else 'original',
        'embedded_post_id': row['embedded_post_id'] if 'embedded_post_id' in row.keys() else None,
    }

def _embedded_row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
    """Convert embedded post row to dict."""
    return {
        'x_post_id': row['x_post_id'],
        'created_at': row['created_at'],
        'text': row['text'],
        'author_id': row['author_id'],
        'author_username': row['author_username'],
        'author_display_name': row['author_display_name'],
        'media_urls': json.loads(row['media_urls']) if row['media_urls'] else [],
        'link_urls': json.loads(row['link_urls']) if row['link_urls'] else [],
    }
```

### New EmbeddedPostsRepository

```python
class EmbeddedPostsRepository:
    """Repository for embedded_posts table CRUD operations."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def upsert_embedded_post(self, post: dict[str, Any]) -> None:
        """Insert or update an embedded post."""
        self._conn.execute(
            """
            INSERT INTO embedded_posts (
                x_post_id, created_at, text, author_id, author_username,
                author_display_name, media_urls, link_urls
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(x_post_id) DO UPDATE SET
                created_at = excluded.created_at,
                text = excluded.text,
                author_id = excluded.author_id,
                author_username = excluded.author_username,
                author_display_name = excluded.author_display_name,
                media_urls = excluded.media_urls,
                link_urls = excluded.link_urls
            """,
            (
                post['x_post_id'],
                post['created_at'],
                post['text'],
                post['author_id'],
                post['author_username'],
                post.get('author_display_name'),
                json.dumps(post.get('media_urls', [])),
                json.dumps(post.get('link_urls', [])),
            )
        )
        self._conn.commit()

    def get_by_id(self, x_post_id: str) -> Optional[dict[str, Any]]:
        """Get an embedded post by ID."""
        row = self._conn.execute(
            "SELECT * FROM embedded_posts WHERE x_post_id = ?",
            (x_post_id,)
        ).fetchone()
        return self._row_to_dict(row) if row else None
```

---

## Part 7: Cast Receiver Changes

### Modified receiver.html

```html
<script>
function loadPost(post) {
    // Hide loading, show content
    document.getElementById('loading').style.display = 'none';
    document.getElementById('post-container').classList.add('active');

    // Update author
    document.getElementById('author-avatar').textContent = '@';
    document.getElementById('author-name').textContent = post.author_username || 'Unknown';
    document.getElementById('post-date').textContent = formatDate(post.created_at);

    // Handle different post types
    const contentEl = document.getElementById('post-content');

    if (post.post_type === 'retweet' && post.embedded_post) {
        // Retweet: Show "Retweeted" header, then original content
        contentEl.innerHTML = `
            <div class="retweet-header" style="color: #22c55e; font-size: 1.5rem; margin-bottom: 1rem;">
                Retweeted from @${post.embedded_post.author_username}
            </div>
            <div class="original-content">${post.embedded_post.text || 'No content'}</div>
        `;
        loadEmbeddedMedia(post.embedded_post);
    } else if (post.post_type === 'quote' && post.embedded_post) {
        // Quote: Show user's commentary, then quoted post
        contentEl.innerHTML = `
            <div class="quote-content" style="margin-bottom: 2rem;">${post.text || 'No content'}</div>
            <div class="quoted-post" style="border-left: 4px solid #3b82f6; padding-left: 1.5rem; color: #888;">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">Quoting @${post.embedded_post.author_username}</div>
                <div>${post.embedded_post.text || 'No content'}</div>
            </div>
        `;
        loadEmbeddedMedia(post.embedded_post);
    } else {
        // Original post
        contentEl.textContent = post.text || 'No content';
        loadPostMedia(post);
    }

    // Update topics
    updateTopics(post.topics);
}

function loadEmbeddedMedia(embeddedPost) {
    const imagesContainer = document.getElementById('post-images');
    imagesContainer.innerHTML = '';
    if (embeddedPost.media_urls && embeddedPost.media_urls.length > 0) {
        embeddedPost.media_urls.forEach(url => {
            const img = document.createElement('img');
            img.src = url;
            img.alt = 'Embedded post image';
            imagesContainer.appendChild(img);
        });
    }
}
</script>
```

---

## Part 8: Anti-Patterns to Avoid

### Anti-Pattern 1: Storing Embedded Posts in Same Table

**What people do:** Add all embedded post columns to the `posts` table.

**Why it's wrong:**
- Embedded posts are NOT bookmarks - they're context
- They shouldn't appear in search results, review queue, or exports
- Duplicate storage if multiple people retweet the same original

**Do this instead:** Separate `embedded_posts` table with no user association.

### Anti-Pattern 2: Fetching Embedded Posts On-Demand

**What people do:** Fetch original tweet from X API when user views a retweet.

**Why it's wrong:**
- Rate limits (180 requests/15 min)
- Latency for user
- Fails if original tweet is deleted
- No offline capability

**Do this instead:** Fetch and store embedded posts during sync.

### Anti-Pattern 3: Ignoring Deleted Originals

**What people do:** Assume referenced posts always exist in API response.

**Why it's wrong:**
- Original tweet may be deleted
- X API may not return referenced tweet data
- Author may have blocked user

**Do this instead:** Gracefully handle missing embedded posts with fallback UI.

### Anti-Pattern 4: Recursive Quote Chains

**What people do:** Try to render quote-of-quote-of-quote chains.

**Why it's wrong:**
- X flattens quote chains in bookmarks
- Complexity grows exponentially
- Edge cases multiply

**Do this instead:** Only store/render one level of embedded post.

---

## Part 9: Integration Points

### Modified Files

| File | Change Type | Description |
|------|-------------|-------------|
| `src/db/schema.py` | MODIFY | Add SCHEMA_V6_MIGRATION |
| `src/api/x_client.py` | MODIFY | Add referenced_tweets expansions |
| `src/services/sync.py` | MODIFY | Extract and store embedded posts |
| `src/repositories/posts.py` | MODIFY | Load embedded post data |
| `src/repositories/embedded_posts.py` | NEW | Repository for embedded_posts table |
| `src/web/templates/browse.html` | MODIFY | Render embedded posts |
| `src/web/templates/components/embedded_post.html` | NEW | Macro for embedded post rendering |
| `src/web/templates/receiver.html` | MODIFY | Cast receiver embedded post display |
| `src/web/routes/cast.py` | MODIFY | API returns embedded post data |
| `src/cli/main.py` | MODIFY | CLI renders embedded posts |

### Build Order (Dependencies)

```
1. SCHEMA_V6_MIGRATION (database)
   |
   v
2. EmbeddedPostsRepository (new)
   |
   v
3. XClient modifications (API layer)
   |
   v
4. SyncService modifications (service layer)
   |
   v
5. PostsRepository modifications (repository layer)
   |
   v
6. Template changes (presentation layer)
   |
   v
7. Cast API changes (API layer)
   |
   v
8. CLI rendering (CLI layer)
```

**Rationale:**
1. Schema must exist before repositories
2. Repository must exist before sync can use it
3. XClient must fetch referenced_tweets before sync can process them
4. Sync must store embedded posts before templates can display them
5. Templates need repository methods to load embedded data
6. Cast receiver depends on API returning embedded data
7. CLI depends on same repository methods as web

---

## Part 10: Scaling Considerations

| Concern | At 100 bookmarks | At 500 bookmarks | At 1000 bookmarks |
|---------|-----------------|------------------|-------------------|
| Embedded posts storage | ~20-50 embedded posts | ~100-200 embedded posts | ~200-400 embedded posts |
| Storage overhead | Negligible (<1MB) | Low (~2-5MB) | Low (~5-10MB) |
| Query performance | Single JOIN on get_by_id | Add index on embedded_post_id | Consider lazy loading |
| API rate limits | Not affected (stored at sync time) | Same | Same |

### Cleanup Strategy

Embedded posts should be cleaned up when no posts reference them:

```python
def cleanup_orphaned_embedded_posts(self) -> int:
    """Remove embedded posts with no references."""
    result = self._conn.execute("""
        DELETE FROM embedded_posts
        WHERE x_post_id NOT IN (
            SELECT DISTINCT embedded_post_id
            FROM posts
            WHERE embedded_post_id IS NOT NULL
        )
    """)
    self._conn.commit()
    return result.rowcount
```

---

---

## Part 11: LAN SSL Architecture (Milestone v1.3)

**Context:** Enable browsing and casting from mobile devices on the same LAN without certificate warnings.

### Current SSL Handling

```
xbm web command
    |
    v
ensure_https_certs() in src/web/certs.py
    |
    v
Generate self-signed cert (cryptography library)
    |
    v
uvicorn.run(app, host="127.0.0.1", ssl_keyfile, ssl_certfile)
    |
    v
Browser shows certificate warning (self-signed)
```

### Component Responsibilities for LAN SSL

| Component | Responsibility | Implementation |
|-----------|---------------|----------------|
| `src/web/certs.py` | Self-signed cert generation (existing) | cryptography library, RSA 2048-bit |
| `src/web/lan_certs.py` (NEW) | mkcert integration, LAN IP detection | subprocess (mkcert), socket |
| `src/config/settings.py` | Configuration management (modified) | Pydantic Settings with LAN options |
| `src/cli/main.py` | CLI entry point (modified) | Typer commands for LAN setup |

---

## Part 12: New Module - LAN Certificates

### Module: `src/web/lan_certs.py`

**Purpose:** Detect LAN IP, generate mkcert-based certificates with proper SANs, manage CA installation.

```python
"""LAN SSL certificate generation using mkcert.

LAN-01: Generate locally-trusted SSL certificates for LAN access.
LAN-02: CLI command to set up mkcert and install CA on devices.
"""

import socket
import subprocess
from pathlib import Path
from typing import Optional

from .certs import generate_self_signed_cert


def get_lan_ip() -> Optional[str]:
    """Detect LAN IP using UDP socket trick (no network traffic sent).

    Returns:
        LAN IP address (e.g., "192.168.1.100") or None if detection fails.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Connect to public DNS (8.8.8.8) to determine routing
            # No data is actually sent
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except OSError:
        return None


def check_mkcert_installed() -> bool:
    """Check if mkcert CLI tool is available.

    Returns:
        True if mkcert is installed and accessible.
    """
    try:
        result = subprocess.run(
            ['mkcert', '-help'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_mkcert_ca() -> bool:
    """Run 'mkcert -install' to install local CA.

    Returns:
        True if CA installation succeeded.
    """
    try:
        result = subprocess.run(
            ['mkcert', '-install'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def generate_mkcert_cert(
    hosts: list[str],
    cert_path: Path,
    key_path: Path,
) -> tuple[Path, Path]:
    """Generate certificate valid for all specified hosts (SANs).

    Args:
        hosts: List of hostnames/IPs to include as SANs.
        cert_path: Path to save certificate file.
        key_path: Path to save private key file.

    Returns:
        Tuple of (cert_path, key_path).

    Raises:
        RuntimeError: If mkcert command fails.
    """
    # Ensure parent directories exist
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    # Build mkcert command
    cmd = [
        'mkcert',
        '-cert-file', str(cert_path),
        '-key-file', str(key_path),
    ] + hosts

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"mkcert failed: {result.stderr}")

    return cert_path, key_path


def ensure_lan_certs(
    lan_ip: str,
    cert_path: Optional[Path] = None,
    key_path: Optional[Path] = None,
) -> tuple[Path, Path]:
    """Ensure HTTPS certificates exist for LAN access.

    Uses mkcert if available (trusted), falls back to self-signed (warning).

    Args:
        lan_ip: LAN IP address to include in certificate.
        cert_path: Path to certificate file. Defaults to data/lan.crt.
        key_path: Path to private key file. Defaults to data/lan.key.

    Returns:
        Tuple of (cert_path, key_path).
    """
    if cert_path is None:
        cert_path = Path("data/lan.crt")
    if key_path is None:
        key_path = Path("data/lan.key")

    if not cert_path.exists() or not key_path.exists():
        if check_mkcert_installed():
            # Use mkcert for trusted certificates
            generate_mkcert_cert(
                hosts=["localhost", "127.0.0.1", lan_ip, "::1"],
                cert_path=cert_path,
                key_path=key_path,
            )
        else:
            # Fall back to self-signed (shows browser warning)
            generate_self_signed_cert(
                cert_path=cert_path,
                key_path=key_path,
                common_name=lan_ip,
            )

    return cert_path, key_path


__all__ = [
    "get_lan_ip",
    "check_mkcert_installed",
    "install_mkcert_ca",
    "generate_mkcert_cert",
    "ensure_lan_certs",
]
```

---

## Part 13: Modified Files for LAN SSL

### Modified: `src/config/settings.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # LAN access settings
    enable_lan: bool = False  # Enable LAN binding (set via --lan flag)
    lan_host: str = "0.0.0.0"  # Bind to all interfaces for LAN
    lan_cert_path: Path = Path("data/lan.crt")
    lan_key_path: Path = Path("data/lan.key")

    # mkcert settings
    mkcert_enabled: bool = True  # Use mkcert if available
```

### Modified: `src/cli/main.py` - New `lan-setup` Command

```python
@app.command("lan-setup")
def lan_setup(
    install_ca: bool = typer.Option(True, "--install-ca/--no-install-ca",
                                    help="Install mkcert CA on this machine"),
) -> None:
    """Set up LAN-accessible HTTPS certificates using mkcert.

    LAN-01: Generate locally-trusted SSL certificates for LAN access.
    LAN-02: CLI command to set up mkcert and install CA on devices.

    This command will:
    1. Check if mkcert is installed
    2. Install local CA (optional)
    3. Detect LAN IP address
    4. Generate certificate with SANs for localhost, 127.0.0.1, and LAN IP

    Examples:
        xbm lan-setup
        xbm lan-setup --no-install-ca
    """
    try:
        # Check mkcert installation
        if not check_mkcert_installed():
            console.print(Panel(
                Text.assemble(
                    ("mkcert is not installed\n\n", "bold red"),
                    ("Install with:\n", "dim"),
                    ("  macOS: brew install mkcert\n", "cyan"),
                    ("  Linux: sudo apt install mkcert\n", "cyan"),
                    ("  Windows: choco install mkcert\n", "cyan"),
                    ("\nSee: https://github.com/FiloSottile/mkcert\n", "dim"),
                ),
                title="[bold red]Prerequisite Missing[/bold red]",
                border_style="red",
            ))
            raise typer.Exit(1)

        # Install CA if requested
        if install_ca:
            console.print("[cyan]Installing local CA...[/cyan]")
            if not install_mkcert_ca():
                console.print("[yellow]Warning: Could not install CA automatically[/yellow]")
                console.print("[dim]Run 'mkcert -install' manually[/dim]")

        # Detect LAN IP
        lan_ip = get_lan_ip()
        if not lan_ip:
            console.print("[red]Could not detect LAN IP address[/red]")
            console.print("[dim]Ensure you're connected to a network[/dim]")
            raise typer.Exit(1)

        console.print(f"[cyan]Detected LAN IP: {lan_ip}[/cyan]")

        # Generate certificates
        cert_path, key_path = ensure_lan_certs(lan_ip)

        # Success message
        console.print(Panel(
            Text.assemble(
                ("LAN certificates generated!\n\n", "bold green"),
                ("Certificate: ", "dim"),
                (f"{cert_path}\n", "cyan"),
                ("Key: ", "dim"),
                (f"{key_path}\n", "cyan"),
                ("\n", ""),
                ("LAN URL: ", "dim"),
                (f"https://{lan_ip}:8000\n\n", "cyan"),
                ("To access from mobile:\n", "bold yellow"),
                ("1. Install the CA certificate on your device\n", "dim"),
                ("   macOS: The CA is already trusted\n", "dim"),
                ("   iOS: AirDrop rootCA.pem to device, Settings > General > About > Certificate Trust Settings\n", "dim"),
                ("   Android: Transfer rootCA.pem, Settings > Security > Install certificates\n", "dim"),
                ("2. Navigate to ", "dim"),
                (f"https://{lan_ip}:8000", "cyan"),
            ),
            title="[bold]LAN Setup Complete[/bold]",
            border_style="green",
        ))

    except typer.Exit:
        raise
    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("LAN setup failed\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        raise typer.Exit(1)
```

### Modified: `src/cli/main.py` - Updated `web` Command

```python
@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    lan: bool = typer.Option(False, "--lan", help="Enable LAN access (bind to 0.0.0.0)"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser automatically"),
    db_path: Optional[Path] = typer.Option(None, "--db", "-d", help="Database path"),
) -> None:
    """Start the web application server.

    WEB-01: User can access application via web browser at localhost.
    WEB-02: Web app serves posts over HTTPS (required for Google Cast).
    LAN-03: Web server binds to LAN IP with proper certificate.
    LAN-04: Mobile browser can access and cast to TV.

    Examples:
        xbm web                      # Localhost only
        xbm web --lan                # LAN access (requires lan-setup first)
        xbm web --lan --port 3000
    """
    import uvicorn
    import webbrowser

    try:
        # Load settings
        try:
            settings = Settings()
            if db_path is None:
                db_path = settings.database_path
        except Exception:
            db_path = Path("data/bookmarks.db")

        # Determine certificate paths and host binding
        if lan:
            host = "0.0.0.0"  # Bind to all interfaces

            # Detect LAN IP for display
            from ..web.lan_certs import get_lan_ip
            lan_ip = get_lan_ip()

            if not lan_ip:
                console.print("[red]Could not detect LAN IP address[/red]")
                raise typer.Exit(1)

            # Use LAN certificates
            cert_path = settings.lan_cert_path
            key_path = settings.lan_key_path

            # Ensure certificates exist
            if not cert_path.exists() or not key_path.exists():
                console.print(Panel(
                    Text.assemble(
                        ("LAN certificates not found\n\n", "bold red"),
                        ("Run 'xbm lan-setup' first\n", "cyan"),
                    ),
                    title="[bold red]Certificate Missing[/bold red]",
                    border_style="red",
                ))
                raise typer.Exit(1)

            display_url = f"https://{lan_ip}:{port}"
        else:
            # Localhost only
            from ..web.certs import ensure_https_certs
            cert_path, key_path = ensure_https_certs()
            display_url = f"https://{host}:{port}"

        # Create the FastAPI app
        from ..web.app import create_app

        app = create_app()

        # Print startup message
        console.print(Panel(
            Text.assemble(
                ("Starting web server...\n", "bold cyan"),
                ("\n", ""),
                ("URL: ", "dim"),
                (f"{display_url}\n", "cyan"),
                ("\n", ""),
                ("Note: ", "yellow"),
                ("HTTPS certificate active\n", "dim"),
                ("      ", "dim"),
                ("(trusted on this machine)" if lan else "(self-signed, browser warning expected)\n", "dim"),
            ),
            title="[bold]X Bookmarked Posts - Web[/bold]",
            border_style="cyan",
        ))

        # Open browser if requested (localhost only)
        if open_browser and not lan:
            webbrowser.open(f"https://localhost:{port}")

        # Run the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            ssl_keyfile=str(key_path),
            ssl_certfile=str(cert_path),
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        console.print(Panel(
            Text.assemble(
                ("Failed to start web server\n", "bold red"),
                (str(e), "red"),
            ),
            title="[bold red]Error[/bold red]",
            border_style="red",
        ))
        raise typer.Exit(1)
```

---

## Part 14: Data Flow for LAN SSL

### Certificate Setup Flow

```
User runs: xbm lan-setup
    |
    v
check_mkcert_installed() -> False?
    |
    +-- False --> Print instructions to install mkcert
    |             Return error
    |
    v True
install_mkcert_ca() -> Run 'mkcert -install'
    |
    v
get_lan_ip() -> Detect LAN IP (e.g., 192.168.1.100)
    |
    v
generate_mkcert_cert(
    hosts=["localhost", "127.0.0.1", "192.168.1.100", "::1"],
    cert_path="data/lan.crt",
    key_path="data/lan.key"
)
    |
    v
Certificate created with SANs for all hosts
    |
    v
Print success message with:
  - LAN URL: https://192.168.1.100:8000
  - Instructions for installing CA on mobile device
```

### LAN Web Server Flow

```
User runs: xbm web --lan
    |
    v
Load Settings (enable_lan=True when --lan flag used)
    |
    v
ensure_lan_certs(lan_ip="192.168.1.100")
    |
    +-- mkcert available --> Use mkcert-generated cert
    |                          (trusted by devices with CA installed)
    |
    +-- mkcert not available --> Fall back to self-signed cert
    |                            (browser warning on all devices)
    |
    v
uvicorn.run(
    app,
    host="0.0.0.0",  # Bind to all interfaces
    port=8000,
    ssl_keyfile=str(key_path),
    ssl_certfile=str(cert_path),
)
    |
    v
Server accessible at:
  - https://localhost:8000 (local)
  - https://192.168.1.100:8000 (LAN)
```

---

## Part 15: Anti-Patterns for LAN SSL

### Anti-Pattern 1: Hardcoded Certificate Paths

**What people do:** Use hardcoded paths like `"cert.pem"` without checking if they exist.

**Why it's wrong:** Breaks when run from different directories, no clear ownership.

**Do this instead:**

```python
# Use Settings for all paths
settings = Settings()
cert_path = settings.lan_cert_path  # data/lan.crt by default
```

### Anti-Pattern 2: Certificate SANs Missing Localhost

**What people do:** Generate cert only for LAN IP (e.g., `192.168.1.100`).

**Why it's wrong:** Breaks local development access (https://localhost:8000 shows warning).

**Do this instead:**

```python
# Always include localhost and loopback
hosts = ["localhost", "127.0.0.1", lan_ip, "::1"]
```

### Anti-Pattern 3: Binding to 0.0.0.0 Without HTTPS

**What people do:** Enable LAN binding (`--host 0.0.0.0`) without HTTPS.

**Why it's wrong:** Exposes application to network without encryption, security risk.

**Do this instead:**

```python
# Enforce HTTPS when LAN is enabled
if lan and not cert_path.exists():
    console.print("[red]LAN access requires HTTPS certificates.[/red]")
    console.print("[dim]Run 'xbm lan-setup' first.[/dim]")
    raise typer.Exit(1)
```

### Anti-Pattern 4: mkcert CA Key Shared

**What people do:** Copy `rootCA-key.pem` to other machines.

**Why it's wrong:** Compromises security - anyone with the key can sign certificates.

**Do this instead:**

```python
# Never share or copy rootCA-key.pem
# Install mkcert separately on each machine
console.print("""
[bold]To install CA on mobile device:[/bold]
1. Run: mkcert -CAROOT  (shows CA certificate location)
2. Transfer rootCA.pem (NOT rootCA-key.pem) to device
3. Install as trusted certificate on device
""")
```

---

## Part 16: Integration Points for LAN SSL

### New Files

| File | Purpose | Dependencies |
|------|---------|--------------|
| `src/web/lan_certs.py` | mkcert integration, LAN IP detection | subprocess (mkcert), socket |

### Modified Files

| File | Changes | New Dependencies |
|------|---------|------------------|
| `src/config/settings.py` | Add LAN settings (enable_lan, lan_cert_path, etc.) | None |
| `src/cli/main.py` | Add `lan-setup` command, modify `web` command | `src/web/lan_certs.py` |

### Unchanged Files

| File | Why No Changes |
|------|----------------|
| `src/web/app.py` | SSL is handled at uvicorn level, not app level |
| `src/web/certs.py` | Still used as fallback for self-signed certs |
| `src/web/routes/*.py` | HTTP handlers don't need to know about SSL |
| `src/db/*.py` | Data layer independent of web serving |
| `src/services/*.py` | Business logic independent of web serving |

---

## Part 17: Implementation Order

Based on dependencies, implement in this order:

1. **Phase 1: Core Infrastructure**
   - `src/web/lan_certs.py` - LAN IP detection and mkcert integration
   - Modify `src/config/settings.py` - Add LAN settings

2. **Phase 2: CLI Integration**
   - Add `lan-setup` command to `src/cli/main.py`
   - Modify `web` command with `--lan` flag

3. **Phase 3: User Guidance**
   - Error messages when mkcert not installed
   - Instructions for CA installation on mobile devices
   - Documentation in CLI help text

---

## Part 18: Scaling Considerations for LAN

| Scale | Considerations |
|-------|----------------|
| Single user (100-500 bookmarks) | Current architecture is optimal |
| Family/home network (multiple devices) | LAN SSL handles multiple devices accessing same server |
| Public internet | Out of scope - use reverse proxy (Caddy, Traefik) with Let's Encrypt |

### Scaling Priorities

1. **First priority:** Certificate refresh handling (mkcert certs expire, handle gracefully)
2. **Future consideration:** If serving multiple households, consider separate instances rather than scaling single instance

---

## Sources

### X API Documentation
- [X API Data Dictionary](https://docs.x.com/x-api/fundamentals/data-dictionary) — HIGH confidence (official)
- [X API Fields Reference](https://docs.x.com/x-api/fundamentals/fields) — HIGH confidence (official)
- [X API Post Lookup](https://docs.x.com/x-api/posts/post-lookup-by-post-id) — HIGH confidence (official)

### Template Patterns
- [Jinja2 Macros Documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/#macros) — HIGH confidence (official)
- [FastAPI Jinja2 Templates Guide](https://realpython.com/fastapi-jinja2-template/) — HIGH confidence (community)

### Database Patterns
- [Twitter Database Design Patterns](https://thelinuxcode.com/how-i-design-a-database-for-a-twitterstyle-platform-in-2026/) — MEDIUM confidence (community)
- [SQLite Foreign Keys](https://www.sqlite.org/foreignkeys.html) — HIGH confidence (official)

### LAN SSL Patterns
- [mkcert GitHub Repository](https://github.com/FiloSottile/mkcert) — HIGH confidence (official)
- [Local HTTPS Development in Python with Mkcert](https://woile.dev/blog/local-https-development-in-python-with-mkcert.html) — MEDIUM confidence (community)
- [mkcert Cheat Sheet](https://1337skills.com/cheatsheets/mkcert/) — MEDIUM confidence (community reference)
- [FastAPI HTTPS Documentation](https://fastapi-fastapi.mintlify.app/deployment/https) — HIGH confidence (official)
- [Python LAN IP Detection](https://thelinuxcode.com/finding-ip-address-using-python-practical-patterns-for-local-public-and-interface-specific-ips/) — MEDIUM confidence (community)
- [Uvicorn SSL Configuration](https://github.com/tiangolo/fastapi/blob/master/docs/en/docs/deployment/https.md) — HIGH confidence (official)

### Existing Codebase
- [src/db/schema.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/db/schema.py) — HIGH confidence (project reference)
- [src/services/sync.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/services/sync.py) — HIGH confidence (project reference)
- [src/repositories/posts.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/repositories/posts.py) — HIGH confidence (project reference)
- [src/web/templates/browse.html](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/templates/browse.html) — HIGH confidence (project reference)
- [src/web/templates/receiver.html](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/templates/receiver.html) — HIGH confidence (project reference)
- [src/api/x_client.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/api/x_client.py) — HIGH confidence (project reference)
- [src/web/certs.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/certs.py) — HIGH confidence (project reference)
- [src/cli/main.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/cli/main.py) — HIGH confidence (project reference)
- [src/config/settings.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/config/settings.py) — HIGH confidence (project reference)

---
*Architecture research for: Embedded Post Rendering (Milestone v1.2) and LAN SSL Integration (Milestone v1.3)*
*Researched: 2026-06-04 (v1.2), 2026-06-07 (v1.3)*