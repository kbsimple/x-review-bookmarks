# Phase 8: Storage Foundation - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Sync and store embedded post data for retweets and quote tweets. The posts table gains a `post_type` column to distinguish original posts from retweets/quotes, and a new `embedded_posts` table stores the original content for referenced tweets.

This phase delivers:
- Schema migration adding `post_type` and `embedded_post_id` columns to posts table
- New `embedded_posts` table storing original tweet content
- XClient updated with `referenced_tweets.id.*` expansions
- SyncService modified to extract and store referenced tweet data
- Unavailable original detection and marking

**Out of scope (Phase 9+):**
- Rendering embedded posts in web interface (Phase 9)
- Rendering embedded posts in CLI (Phase 10)
- Rendering embedded posts on TV/Cast (Phase 11)
- FTS5 search including embedded post text (future)

</domain>

<decisions>
## Implementation Decisions

### Schema Design
- **D-01:** Separate `embedded_posts` table mirroring posts table structure.
  - Columns: `x_post_id`, `created_at`, `text`, `author_id`, `author_username`, `author_display_name`, `media_urls`, `link_urls`, `available`
  - Foreign key from posts.embedded_post_id to embedded_posts.x_post_id
  - Rationale: Clean separation, supports querying original content independently, maintains normalization pattern from Phase 2.

### Post Type Classification
- **D-02:** Add `post_type` column to posts table with values: 'original', 'retweet', 'quote'.
  - Add `embedded_post_id` column referencing embedded_posts.x_post_id (nullable, only set for retweets/quotes)
  - Original posts have `post_type='original'` and `embedded_post_id=NULL`
  - Retweets have `post_type='retweet'`, quote tweets have `post_type='quote'`
  - Rationale: STR-02 requirement for distinguishing post types.

### Recursive Quote Handling
- **D-03:** Flatten to 1 level of nesting per REQUIREMENTS.md.
  - If a quote tweet quotes another quote, store only the immediate referenced tweet
  - Deeper chains show "Quoted from @user" link to X for context
  - Rationale: Out of scope for v1.2 to support recursive quote chains.

### API Expansions
- **D-04:** Single-pass fetch with extended expansions.
  - Add to existing XClient.EXPANSIONS: `referenced_tweets.id`, `referenced_tweets.id.author_id`, `referenced_tweets.id.attachments.media_keys`
  - Add to TWEET_FIELDS: `referenced_tweets` (required for expansion)
  - Referenced tweets appear in `includes.tweets` alongside main tweets
  - Rationale: Leverages existing rate limit handling, no additional API calls.

### Unavailable Original Detection
- **D-05:** Sync-time detection for deleted/protected originals.
  - Collect all referenced_tweet_ids from tweets with `referenced_tweets`
  - After API response, check if each referenced_id exists in `includes.tweets`
  - If missing: create embedded_posts row with `available=false`
  - If present: create embedded_posts row with full content and `available=true`
  - Rationale: STR-03 requirement for graceful handling, per Out of Scope "live retweet counts".

### Sync Flow Integration
- **D-06:** Extend existing SyncService._store_tweet method.
  - Extract referenced_tweets from tweet data
  - Look up referenced tweet in includes.tweets
  - Store embedded_post row (available or unavailable)
  - Update posts row with post_type and embedded_post_id
  - Rationale: Minimal changes to existing sync flow, leverages existing rate limit handling.

### Claude's Discretion
- Exact column types and constraints for embedded_posts table
- Whether to store embedded author info in separate table or embedded_posts
- Error message wording for unavailable posts
- Whether to retry unavailable posts on subsequent syncs

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — STR-01, STR-02, STR-03 (Storage requirements for Phase 8)
- `.planning/REQUIREMENTS.md` §Out of Scope — Quote-of-quote chains excluded, live metrics excluded

### Existing Code (from prior phases)
- `src/db/schema.py` — Schema migration pattern (SCHEMA_V2, SCHEMA_V3_MIGRATION, etc.)
- `src/api/x_client.py` — XClient with EXPANSIONS, TWEET_FIELDS, fetch_bookmarks method
- `src/services/sync.py` — SyncService with _store_tweet, _store_tweets methods
- `src/repositories/posts.py` — PostsRepository with upsert_post pattern

### Architecture
- `CLAUDE.md` — Technology stack, SQLite configuration best practices

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **src/db/schema.py** — Schema migration pattern using SCHEMA_V{N}_MIGRATION constants
- **src/db/migrations.py** — Migration runner for applying schema changes
- **src/api/x_client.py** — XClient.EXPANSIONS already includes `author_id, attachments.media_keys`
- **src/services/sync.py** — SyncService._store_tweet extracts tweet data and stores in posts table
- **src/repositories/posts.py** — PostsRepository.upsert_post pattern for insert-or-update

### Established Patterns
- **Schema migrations:** Add new SCHEMA_V{N}_MIGRATION constant, increment get_schema_version()
- **XClient expansions:** Comma-separated string for expansions, separate string for tweet_fields
- **SyncService storage:** _store_tweet method extracts data from tweepy objects and upserts
- **Includes lookup:** `fetch_result.users` dict lookup pattern already exists for author data

### Integration Points
- Add SCHEMA_V6_MIGRATION to schema.py (posts.post_type, posts.embedded_post_id, embedded_posts table)
- Extend XClient.EXPANSIONS with referenced_tweets.id.*
- Extend XClient.TWEET_FIELDS with referenced_tweets
- Modify SyncService._store_tweet to handle referenced_tweets
- Create EmbeddedPostsRepository for embedded_posts CRUD operations

</code_context>

<specifics>
## Specific Ideas

- Follow existing schema migration pattern - each phase gets its own SCHEMA_V{N}_MIGRATION
- Reuse the upsert pattern from PostsRepository for EmbeddedPostsRepository
- Keep embedded_posts columns parallel to posts for consistency
- Mark unavailable with boolean flag rather than nullable columns (clearer semantics)

</specifics>

<deferred>
## Deferred Ideas

- FTS5 search including embedded post text (SRCH-F01) — future phase
- Display original post metrics on retweets (MET-F01) — future phase
- Quote-of-quote chain support beyond 1 level (REC-F01) — out of scope

</deferred>

---
*Phase: 08-storage-foundation*
*Context gathered: 2026-06-04*