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

### Existing Codebase
- [src/db/schema.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/db/schema.py) — HIGH confidence (project reference)
- [src/services/sync.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/services/sync.py) — HIGH confidence (project reference)
- [src/repositories/posts.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/repositories/posts.py) — HIGH confidence (project reference)
- [src/web/templates/browse.html](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/templates/browse.html) — HIGH confidence (project reference)
- [src/web/templates/receiver.html](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/web/templates/receiver.html) — HIGH confidence (project reference)
- [src/api/x_client.py](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/api/x_client.py) — HIGH confidence (project reference)

---
*Architecture research for: Embedded Post Rendering (Milestone v1.2)*
*Researched: 2026-06-04*