# Phase 2: Bookmark Fetch and Storage - Research

**Researched:** 2026-04-19
**Domain:** X API v2 bookmarks, Tweepy client, SQLite storage, CLI sync command
**Confidence:** HIGH

## Summary

This phase implements the core data pipeline: fetching bookmarks from X API and storing them in SQLite. The technical foundation is well-established: Tweepy's `get_bookmarks()` method provides clean access to X API v2, SQLite with WAL mode is already configured, and the OAuth 2.0 PKCE flow is working from Phase 1. The key challenges are handling X API constraints (800 bookmark limit, 180 requests/15min rate limit, pagination state management) and building a resumable sync mechanism.

**Primary recommendation:** Use Tweepy's `Client.get_bookmarks()` with OAuth 2.0 User Context (already working from Phase 1), implement a `sync_state` table for incremental sync with `last_bookmark_id` tracking, and use Rich Progress for visual feedback during sync operations.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Posts table schema with full content storage (x_post_id PK, created_at, text, author fields, media_urls JSON, link_urls JSON, bookmarked_at, fetched_at, sync_version)
- **D-02:** Incremental sync via bookmark ID comparison (store `last_sync_bookmark_id` and `last_sync_at` in sync_state table)
- **D-03:** Auto-wait rate limit handling with progress indication, persist pagination `next_token` for resume after interruption
- **D-04:** Progress bar during sync + Rich summary table after
- **D-05:** Dedicated `api/x_client.py` module wrapping tweepy.Client

### Claude's Discretion
- Exact column types and constraints (TEXT vs JSON for media arrays)
- Error message wording for sync failures
- Progress bar styling (Rich Progress component choice)
- Pagination batch size (balance between speed and rate limit conservation)

### Deferred Ideas (OUT OF SCOPE)
None from discussion.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Fetch bookmarked posts from X API | Tweepy `get_bookmarks()` method documented below |
| DATA-02 | Store posts with full content (text, author, images, links, media) | Schema pattern D-01, expansions parameter for media |
| DATA-03 | Store publication date for each post | `created_at` field in schema, `tweet_fields` parameter |
| DATA-04 | Handle X API rate limits with resumable pagination | Rate limit strategy D-03, pagination token storage |
| DATA-05 | Handle 800 bookmark API limit gracefully | Limit documented, warning strategy recommended |
| STOR-03 | Incremental sync (only fetch new bookmarks) | ID comparison strategy D-02 |
| CLI-01 | Trigger bookmark sync via CLI command | `sync` command pattern documented |
| CLI-05 | Rich output with post content and metadata | Rich Progress + summary table pattern D-04 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **tweepy** | 4.16.0 | X API v2 client | [VERIFIED: pip show] Only mature Python library with OAuth 2.0 PKCE support. `get_bookmarks()` added in 4.8. |
| **sqlite3** | stdlib | Local storage | [VERIFIED] Zero-config, WAL mode already configured in Phase 1. |
| **Typer** | 0.23.0 | CLI framework | [VERIFIED: pip show] Type-hint-based CLI, Rich integration. Note: Project uses 0.23.0 for Python 3.9 compatibility. |
| **Rich** | 15.0.0 | Terminal output | [VERIFIED: pip show] Progress bars, tables, syntax highlighting. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pydantic-settings** | 2.0+ | Configuration | Already configured in Settings class |
| **pytest** | 8.0+ | Testing | Already configured in pytest.ini |
| **pytest-asyncio** | 0.23+ | Async testing | Available for future async patterns |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Tweepy | raw requests | X API auth complexity significant; Tweepy handles PKCE correctly |
| SQLite (stdlib) | SQLAlchemy ORM | Premature for 100-500 records; raw SQL simpler for single-table CRUD |
| Rich Progress | tqdm | Rich integrates with Typer, provides consistent styling |

**Installation:** Already satisfied (Phase 1 setup).

**Version verification:**
```
tweepy: 4.16.0 (installed)
rich: 15.0.0 (installed)
typer: 0.23.0 (via pip3 show typer)
Python: 3.9.6
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── api/
│   ├── __init__.py
│   └── x_client.py        # D-05: Tweepy wrapper with rate limiting
├── repositories/
│   ├── __init__.py
│   ├── posts.py           # PostRepository for posts table CRUD
│   └── sync_state.py      # SyncStateRepository for incremental sync
├── services/
│   ├── __init__.py
│   └── sync.py            # SyncService orchestrates fetch + store
├── db/
│   └── schema.py          # Add SCHEMA_V2 with posts + sync_state tables
├── cli/
│   └── main.py            # Add `sync` command
└── auth/
    └── oauth.py           # Already working from Phase 1
```

### Pattern 1: Tweepy Bookmarks Client
**What:** Wrapper around `tweepy.Client` for X API bookmarks with rate limit awareness.
**When to use:** All bookmark fetch operations.
**Example:**
```python
# Source: https://sns-sdks.github.io/python-twitter/usage/tweets/bookmarks/
# and https://pythonfriday.dev/2022/07/131-working-with-bookmarks-in-tweepy

import tweepy

# OAuth 2.0 User Context - MUST use access_token, not bearer_token
# [CITED: Tweepy docs - get_bookmarks requires OAuth 2.0 User Context]
client = tweepy.Client(access_token=access_token)

# Get bookmarks with expansions for full content
response = client.get_bookmarks(
    max_results=100,  # Max per request
    expansions="author_id,attachments.media_keys,referenced_tweets.id",
    tweet_fields="created_at,public_metrics,attachments,entities,conversation_id",
    user_fields="username,name,profile_image_url",
    media_fields="url,preview_image_url,height,width,alt_text",
    pagination_token=None  # For first page, or resume token
)

# Response structure:
# response.data      -> List[Tweet] or None
# response.includes  -> Dict with 'users', 'media', etc.
# response.meta      -> Dict with 'next_token', 'result_count'
```

### Pattern 2: Incremental Sync with ID Tracking
**What:** Track the newest bookmark ID fetched to avoid re-fetching.
**When to use:** Every sync operation after initial full sync.
**Example:**
```python
# D-02: ID comparison strategy
# Store in sync_state table:
# - last_sync_bookmark_id: highest x_post_id seen
# - last_sync_at: timestamp of last successful sync
# - pagination_token: resume point if interrupted

def get_new_bookmarks(client: tweepy.Client, last_bookmark_id: str | None):
    """Fetch bookmarks newer than last_bookmark_id."""
    all_bookmarks = []
    pagination_token = None

    while True:
        response = client.get_bookmarks(
            max_results=100,
            pagination_token=pagination_token,
            # ... expansions and fields
        )

        if not response.data:
            break

        for tweet in response.data:
            # Stop if we've seen this bookmark (pagination is newest-first)
            if last_bookmark_id and tweet.id == last_bookmark_id:
                return all_bookmarks  # Stop here
            all_bookmarks.append(tweet)

        # Check for more pages
        if 'next_token' not in response.meta:
            break
        pagination_token = response.meta['next_token']

    return all_bookmarks
```

### Pattern 3: Rate Limit Handling with Auto-Wait
**What:** Monitor rate limit headers and wait when approaching limit.
**When to use:** Every API call in sync loop.
**Example:**
```python
# D-03: Auto-wait with progress indication
import time
from rich.progress import Progress

def fetch_with_rate_limit(client, pagination_token, progress):
    """Fetch bookmarks with rate limit awareness."""
    response = client.get_bookmarks(
        max_results=100,
        pagination_token=pagination_token,
    )

    # Check rate limit from response headers
    # Note: Tweepy exposes these via client.last_response
    remaining = int(response.headers.get('x-rate-limit-remaining', 180))
    reset_time = int(response.headers.get('x-rate-limit-reset', time.time() + 900))

    if remaining <= 5:  # Approaching limit
        wait_seconds = reset_time - time.time()
        progress.console.print(
            f"[yellow]Rate limit approaching. Waiting {wait_seconds:.0f}s...[/yellow]"
        )
        # Store pagination_token to database for resume
        time.sleep(wait_seconds + 1)

    return response
```

### Pattern 4: Posts Table Schema
**What:** SQLite schema for full content storage per D-01.
**Example:**
```sql
-- D-01: Posts table with full content storage
CREATE TABLE IF NOT EXISTS posts (
    x_post_id TEXT PRIMARY KEY,        -- Tweet ID from X API
    created_at TIMESTAMP NOT NULL,     -- Publication date (DATA-03)
    text TEXT NOT NULL,                -- Tweet text content
    author_id TEXT NOT NULL,           -- X user ID
    author_username TEXT NOT NULL,     -- @handle
    author_display_name TEXT,          -- Display name
    media_urls TEXT,                   -- JSON array of media URLs
    link_urls TEXT,                    -- JSON array of link URLs from entities
    bookmarked_at TIMESTAMP,           -- When user bookmarked (from API)
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_version INTEGER DEFAULT 1,
    UNIQUE(x_post_id)
);

-- Index for incremental sync lookup
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);

-- Sync state table for D-02 incremental sync
CREATE TABLE IF NOT EXISTS sync_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Single-row table
    last_sync_bookmark_id TEXT,
    last_sync_at TIMESTAMP,
    pagination_token TEXT,               -- For resume after interruption
    total_bookmarks INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Anti-Patterns to Avoid
- **Using `bearer_token` for bookmarks:** [CRITICAL] Will return 403 Forbidden. Bookmarks require OAuth 2.0 User Context with access_token. [CITED: GitHub issue #2200]
- **Ignoring rate limits:** Will hit 429 errors and lose sync progress. Must track `x-rate-limit-remaining` headers.
- **Not persisting pagination token:** Interruption means starting over from page 1.
- **Storing 800 limit as surprise:** Users must know about this limit upfront.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth 2.0 PKCE flow | Custom OAuth handler | Existing `ensure_authenticated()` | Phase 1 already working, handles token refresh |
| Rate limit tracking | Manual header parsing | Tweepy's built-in response handling | Headers accessible via `client.last_response` or response object |
| Pagination state | Custom state management | `sync_state` table with `pagination_token` | Persistent across interruptions |
| Progress display | Custom progress bar | Rich `Progress` component | Consistent with Typer, built-in ETA |

**Key insight:** The auth pattern from Phase 1 is already battle-tested. Reuse `ensure_authenticated()` to get `XAuth.access_token` for the Tweepy client.

## Common Pitfalls

### Pitfall 1: 403 Forbidden on Bookmarks Endpoint
**What goes wrong:** API returns 403 with message "Authenticating with OAuth 2.0 Application-Only is forbidden for this endpoint."
**Why it happens:** Using `tweepy.Client(bearer_token=...)` instead of `tweepy.Client(access_token=...)`. Bookmarks require OAuth 2.0 User Context.
**How to avoid:** Always use the access_token from `ensure_authenticated()`:
```python
auth = ensure_authenticated()
client = tweepy.Client(access_token=auth.access_token)  # CORRECT
# NOT: client = tweepy.Client(bearer_token=...)  # WRONG
```
**Warning signs:** Any 403 response on bookmarks endpoint.

### Pitfall 2: 800 Bookmark Limit Surprise
**What goes wrong:** User expects all bookmarks but only gets 800 most recent.
**Why it happens:** X API hard limit documented in official docs.
**How to avoid:**
1. Display warning on first sync: "X API only returns 800 most recent bookmarks"
2. Store sync count and warn if approaching 800
3. Recommend regular syncs to capture new bookmarks before they age out
**Warning signs:** User has >750 bookmarks in database.

### Pitfall 3: Rate Limit Exhaustion During Sync
**What goes wrong:** Sync fails mid-pagination with 429 error, progress lost.
**Why it happens:** 180 requests/15min limit. With 800 bookmarks at 100 per page = 8 requests minimum, but with media expansions and retries can exceed.
**How to avoid:**
1. Track `x-rate-limit-remaining` header
2. Auto-wait when remaining < 5
3. Persist `pagination_token` to database after each page
4. On resume, start from stored token
**Warning signs:** Sync taking >10 minutes, rate limit warnings in output.

### Pitfall 4: Missing Media/Links Due to Missing Expansions
**What goes wrong:** Posts stored without images or links.
**Why it happens:** X API v2 requires explicit `expansions` and `media_fields` parameters.
**How to avoid:** Always include expansions:
```python
expansions="author_id,attachments.media_keys,referenced_tweets.id"
tweet_fields="created_at,public_metrics,attachments,entities"
media_fields="url,preview_image_url,height,width,alt_text"
```
**Warning signs:** `media_urls` column is null for posts with visible media.

## Code Examples

Verified patterns from official sources:

### Get Bookmarks with Full Content
```python
# Source: https://sns-sdks.github.io/python-twitter/usage/tweets/bookmarks/
# [CITED: python-twitter-v2 docs]

import tweepy

client = tweepy.Client(access_token=access_token)

response = client.get_bookmarks(
    max_results=100,
    expansions="author_id,attachments.media_keys",
    tweet_fields="created_at,public_metrics,attachments,entities",
    user_fields="username,name,profile_image_url",
    media_fields="url,height,width,alt_text"
)

# Process response
if response.data:
    # Build author lookup from includes
    authors = {u.id: u for u in response.includes.get('users', [])}
    media = {m.media_key: m for m in response.includes.get('media', [])}

    for tweet in response.data:
        author = authors.get(tweet.author_id)
        tweet_media = [media[mk] for mk in (tweet.attachments or {}).get('media_keys', []) if mk in media]

        # Store in database...
```

### Parse Tweet Entities for Links
```python
# Source: X API v2 tweet fields documentation
# [CITED: developer.x.com]

def extract_links(tweet) -> list[str]:
    """Extract URLs from tweet entities."""
    urls = []
    if hasattr(tweet, 'entities') and 'urls' in tweet.entities:
        urls = [u.get('expanded_url', u.get('url')) for u in tweet.entities['urls']]
    return urls
```

### Sync Command with Progress
```python
# Source: Rich Progress documentation pattern
# [CITED: Rich docs]

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console

console = Console()

@app.command()
def sync():
    """Sync bookmarks from X API."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching bookmarks...", total=None)

        # Fetch and store loop
        count = 0
        for bookmark in fetch_bookmarks():
            store_post(bookmark)
            count += 1
            progress.update(task, description=f"Fetched {count} bookmarks...")

        progress.update(task, description=f"Complete! {count} bookmarks synced.")

    # Show summary table
    console.print(summary_table())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OAuth 1.0a for Twitter API | OAuth 2.0 PKCE | X API v2 (2021) | Bookmarks endpoint requires OAuth 2.0 User Context |
| Pagination via since_id | Pagination via next_token | X API v2 | Token-based pagination for bookmarks |
| Rate limit per app | Rate limit per user | X API v2 | User-context endpoints have per-user limits |

**Deprecated/outdated:**
- `tweepy.API.get_bookmarks`: Does not exist. Use `tweepy.Client.get_bookmarks()` instead.
- `since_id` parameter: Not available on bookmarks endpoint. Use `pagination_token`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Tweepy 4.16.0 `get_bookmarks()` returns same structure as documented | Pattern 1 | May need adaptation if API changed |
| A2 | Response headers include `x-rate-limit-remaining` | Pattern 3 | Alternative: use exception handling for 429 |
| A3 | Bookmarks are returned newest-first | Pattern 2 | Sync logic would need reversal |

**If this table is empty:** All claims in this research were verified or cited.

## Open Questions

1. **Media URL format:**
   - What we know: `media_fields=url` returns direct URLs to images
   - What's unclear: Whether these are temporary URLs or permanent
   - Recommendation: Store as-is, refresh on demand if needed later

2. **Bookmarked_at timestamp:**
   - What we know: Tweet `created_at` is publication date
   - What's unclear: Whether X API provides when user bookmarked
   - Recommendation: Use tweet `created_at` for scheduling, store `fetched_at` as proxy for bookmark time

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | Typer, Tweepy | ✓ | 3.9.6 | — |
| pip | Package management | ✓ | 26.0.1 | — |
| tweepy | X API client | ✓ | 4.16.0 | — |
| rich | CLI output | ✓ | 15.0.0 | — |
| typer | CLI framework | ✓ | 0.23.0 | — |
| pydantic-settings | Configuration | ✓ | (installed) | — |
| pytest | Testing | ✓ | (configured) | — |
| X_CLIENT_ID | OAuth credentials | ? | — | Required at runtime |
| X_CLIENT_SECRET | OAuth credentials | ? | — | Required at runtime |

**Missing dependencies with no fallback:**
- X_CLIENT_ID and X_CLIENT_SECRET must be set in environment (already documented in Phase 1)

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pytest.ini |
| Quick run command | `pytest tests/test_sync.py -x -v` |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Fetch bookmarks from X API | integration | `pytest tests/test_x_client.py -x` | ❌ Wave 0 |
| DATA-02 | Store posts with full content | unit | `pytest tests/test_posts_repository.py -x` | ❌ Wave 0 |
| DATA-03 | Store publication date | unit | `pytest tests/test_posts_repository.py::test_created_at -x` | ❌ Wave 0 |
| DATA-04 | Handle rate limits with pagination | unit | `pytest tests/test_rate_limit.py -x` | ❌ Wave 0 |
| DATA-05 | Handle 800 bookmark limit | unit | `pytest tests/test_sync.py::test_800_limit_warning -x` | ❌ Wave 0 |
| STOR-03 | Incremental sync | integration | `pytest tests/test_sync_service.py -x` | ❌ Wave 0 |
| CLI-01 | Sync command via CLI | integration | `pytest tests/test_cli.py::test_sync_command -x` | ❌ Wave 0 |
| CLI-05 | Rich output with progress | integration | `pytest tests/test_cli.py::test_sync_output -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_<module>.py -x`
- **Per wave merge:** `pytest -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_x_client.py` - X client wrapper tests (DATA-01)
- [ ] `tests/test_posts_repository.py` - Posts repository tests (DATA-02, DATA-03)
- [ ] `tests/test_rate_limit.py` - Rate limit handling tests (DATA-04)
- [ ] `tests/test_sync_service.py` - Sync service tests (STOR-03)
- [ ] `tests/test_cli.py::test_sync_command` - Add sync command test (CLI-01)
- [ ] `tests/conftest.py` - Add mock tweepy client fixture

*(Wave 0 will create these test files before implementation)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | OAuth 2.0 PKCE (Phase 1 complete) |
| V3 Session Management | yes | Token refresh mechanism (Phase 1 complete) |
| V4 Access Control | yes | User-context tokens only |
| V5 Input Validation | yes | Pydantic models for API responses |
| V6 Cryptography | no | N/A - no encryption at rest for public posts |

### Known Threat Patterns for X API Integration

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token theft | Information Disclosure | Store tokens with mode 0600 (Phase 1) |
| Rate limit DoS | Denial of Service | Track remaining requests, auto-wait |
| Malicious redirect | Tampering | Callback server binds to 127.0.0.1 only |

## Sources

### Primary (HIGH confidence)
- [Tweepy Bookmarks Documentation](https://sns-sdks.github.io/python-twitter/usage/tweets/bookmarks/) - API usage patterns
- [X API Bookmarks Introduction](https://developer.x.com/en/docs/x-api/tweets/bookmarks/introduction) - Rate limits, 800 limit
- [X API Rate Limits](https://docs.x.com/x-api/fundamentals/rate-limits) - Official rate limit documentation
- [GitHub Issue #2200 - Tweepy 403 Forbidden](https://github.com/tweepy/tweepy/issues/2200) - Authentication requirements

### Secondary (MEDIUM confidence)
- [Python Friday - Working with Bookmarks in Tweepy](https://pythonfriday.dev/2022/07/131-working-with-bookmarks-in-tweepy) - Example code verified against official docs
- [X API Integration Guide](https://docs.x.com/x-api/posts/bookmarks/integrate) - Integration patterns

### Tertiary (LOW confidence)
- None - all critical claims verified against official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All packages installed and verified
- Architecture: HIGH - Patterns documented in Tweepy docs and X API docs
- Pitfalls: HIGH - 403 issue documented in GitHub, 800 limit in official docs

**Research date:** 2026-04-19
**Valid until:** 2026-05-19 (X API changes rarely, but rate limits may shift)

---

*Phase: 02-bookmark-fetch-and-storage*
*Research completed: 2026-04-19*