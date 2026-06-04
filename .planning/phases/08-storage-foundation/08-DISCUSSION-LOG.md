# Phase 8: Storage Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-04
**Phase:** 08-storage-foundation
**Areas discussed:** Schema design, API expansions, Unavailable handling, Sync integration

---

## Schema Design

| Option | Description | Selected |
|--------|-------------|----------|
| Separate embedded_posts table | Mirror posts table structure. Clean separation, supports querying original content independently. | ✓ |
| JSON column in posts | Store referenced tweet data as JSON blob. Simpler schema but harder to query. | |

**User's choice:** Separate embedded_posts table
**Notes:** Maintains normalization pattern from Phase 2, supports future querying needs.

---

## Recursive Quote Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Flatten to 1 level | Store only the immediate reference. Link to X for deeper context. | ✓ |
| Support full chain | Recursively fetch and store all levels of quotes. More complete but complex. | |

**User's choice:** Flatten to 1 level
**Notes:** Matches REQUIREMENTS.md Out of Scope for quote-of-quote chains.

---

## API Expansions

| Option | Description | Selected |
|--------|-------------|----------|
| Single-pass fetch | Add referenced_tweets.* expansions to main bookmarks call. Data comes with bookmarks. | ✓ |
| Two-pass fetch | Fetch bookmarks first, then make separate API call for referenced tweets. | |

**User's choice:** Single-pass fetch
**Notes:** Leverages existing XClient pattern, no additional rate limit concerns.

---

## Unavailable Original Detection

| Option | Description | Selected |
|--------|-------------|----------|
| Sync-time detection | Check if referenced_id not in includes, mark unavailable immediately. | ✓ |
| Lazy detection | Store referenced IDs, check availability later on display. | |

**User's choice:** Sync-time detection
**Notes:** Fulfills STR-03 requirement for graceful handling during sync.

---

## Rate Limit Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing expansions | Add referenced_tweets fields to existing XClient expansions. No separate handling needed. | ✓ |
| Separate rate limit pool | Track referenced tweet fetches separately. More complex but isolates failures. | |

**User's choice:** Extend existing expansions
**Notes:** Single-pass fetch means same rate limit pool, leverages existing auto-wait handling.

---

## Claude's Discretion

- Exact column types and constraints for embedded_posts table
- Whether to store embedded author info in separate table or embedded_posts
- Error message wording for unavailable posts
- Whether to retry unavailable posts on subsequent syncs

## Deferred Ideas

- FTS5 search including embedded post text (SRCH-F01) — future phase
- Display original post metrics on retweets (MET-F01) — future phase
- Quote-of-quote chain support beyond 1 level (REC-F01) — out of scope