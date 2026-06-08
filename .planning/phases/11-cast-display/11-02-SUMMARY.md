---
phase: 11-cast-display
plan: 02
subsystem: cast-messaging
tags: [cast, embedded-posts, api, messaging]
requires: [CAST-06, CAST-07, CAST-08]
provides: [cast-sender-embedded-post, api-endpoint-embedded-post]
affects: [src/web/static/js/cast.js, src/web/routes/cast.py, src/repositories/posts.py]
tech-stack:
  added: []
  patterns: [LEFT JOIN for embedded posts, explicit message payload]
key-files:
  created: []
  modified:
    - src/web/static/js/cast.js
    - src/repositories/posts.py
    - src/web/routes/cast.py
decisions:
  - Cast sender builds explicit payload with post_type and embedded_post fields
  - API endpoint uses get_by_id_with_embedded() for single post lookup
  - Embedded post data includes author, text, media, and available flag
metrics:
  duration: 10m
  completed: "2026-06-07T12:30:00Z"
---

# Phase 11 Plan 02: Cast Messaging for Embedded Posts Summary

## One-liner

Extended cast messaging to include embedded post data for retweets and quote tweets, enabling TV display of nested original content.

## Implementation

### Task 1: Add embedded_post to cast message

**File modified:** `src/web/static/js/cast.js`

**Changes:**
- Updated `loadPost()` to build explicit message payload with all required fields
- Added `post_type` field (defaults to 'original')
- Added `embedded_post` field (null for original posts)
- Added debug logging for embedded post data when casting retweets/quotes

**Message format:**
```javascript
{
    type: 'LOAD_POST',
    postId: postId,
    post: {
        x_post_id, author_username, author_display_name,
        text, created_at, media_urls, topics,
        post_type: 'original' | 'retweet' | 'quote',
        embedded_post: null | { x_post_id, text, author_username, ... }
    }
}
```

### Task 2: Update API endpoint for cast data

**Files modified:**
- `src/repositories/posts.py` - Added `get_by_id_with_embedded()` method
- `src/web/routes/cast.py` - Updated endpoint to use new method

**PostsRepository.get_by_id_with_embedded():**
- LEFT JOIN with embedded_posts table
- Returns post with `embedded_post` key populated for retweets/quotes
- Returns `embedded_post: null` for original posts

**API endpoint /api/posts/{post_id}:**
- Now returns `post_type` field
- Now returns `embedded_post` field with full data
- Includes `available` flag for deleted/protected posts

### Task 3: Verify end-to-end embedded post casting

**Tests run:** 20 total (16 passed, 4 TDD scaffolding)

**Passing tests (API endpoint):**
- test_api_post_returns_original_without_embedded
- test_api_post_returns_retweet_with_embedded
- test_api_post_returns_quote_with_embedded
- test_api_post_returns_unavailable_embedded
- test_api_post_returns_embedded_with_media

**Failing tests (TDD scaffolding for future plan):**
- test_receiver_has_embedded_post_container
- test_receiver_has_quote_tweet_elements
- test_receiver_has_retweet_elements
- test_receiver_has_unavailable_placeholder

These 4 template tests are TDD scaffolding for receiver.html updates in subsequent plans.

## Verification

```bash
# Task 1 verification
grep -q "post_type" src/web/static/js/cast.js && echo "PASS"
grep -q "embedded_post" src/web/static/js/cast.js && echo "PASS"

# Task 2 verification - all 5 API tests pass
pytest tests/test_cast_receiver.py::TestCastApiPostEndpoint -v
# Result: 5 passed

# Task 3 verification - embedded post data flow
pytest tests/test_cast_receiver.py --tb=no -q
# Result: 16 passed, 4 failed (template tests for future plan)
```

## Deviations from Plan

None - plan executed exactly as written.

The 4 failing template tests are intentional TDD scaffolding for subsequent plans that will update receiver.html to render embedded posts visually.

## Known Stubs

The following test assertions are stubs pending receiver.html implementation:

1. `test_t1_original_post_no_nested_card`: TODO assertion for embedded-post absence
2. `test_t2_retweet_with_reposted_header`: TODO assertion for "Reposted" headers
3. `test_t3_quote_tweet_nested_card`: TODO assertion for "Quoting" label
4. `test_t4_unavailable_post_placeholder`: TODO assertion for unavailable message
5. `test_t5_embedded_media_in_nested_card`: TODO assertion for embedded media

These stubs will be activated in subsequent plans when receiver.html is updated.

## Threat Flags

None - no new security surface introduced. The API endpoint uses existing database connection patterns.

## Self-Check: PASSED

- [x] `src/web/static/js/cast.js` includes post_type and embedded_post in LOAD_POST
- [x] `src/repositories/posts.py` has get_by_id_with_embedded() method
- [x] `src/web/routes/cast.py` endpoint returns embedded_post data
- [x] All 5 API endpoint tests pass
- [x] Commit 333822f exists (Task 1)
- [x] Commit 456809d exists (Task 2)

---
*Completed: 2026-06-07T12:30:00Z*
*Duration: 10 minutes*