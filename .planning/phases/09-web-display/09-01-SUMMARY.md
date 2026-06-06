---
phase: 09-web-display
plan: 01
subsystem: repository
tags: [data-layer, left-join, embedded-posts, pagination]
requires: [08-00]
provides: [get_paginated_with_embedded, embedded_post_data]
affects: [browse-routes, api-endpoints]
tech-stack:
  added: []
  patterns: [LEFT JOIN, null-safety, JSON-parsing]
key-files:
  created: []
  modified:
    - src/repositories/posts.py
    - src/web/routes/browse.py
decisions:
  - Used LEFT JOIN to fetch embedded posts with paginated posts in single query
  - Created _row_to_dict_with_embedded helper for row conversion
  - Checked embedded_id is not None (not truthy) for null safety
  - Converted available flag from INTEGER to boolean for embedded posts
metrics:
  duration: 15m
  completed_date: 2026-06-06
  tasks_completed: 2
  files_modified: 2
---

# Phase 09 Plan 01: Repository LEFT JOIN for Embedded Posts Summary

## One-Liner

Implemented `get_paginated_with_embedded` method with LEFT JOIN to fetch embedded post data for retweets and quotes in a single query, updating browse routes to use the new method.

## Implementation Summary

### Task 1: PostsRepository.get_paginated_with_embedded()

Added new method to `PostsRepository` that performs a LEFT JOIN with `embedded_posts` table to include embedded post data in paginated results.

**Key implementation details:**
- Created `get_paginated_with_embedded()` method matching `get_paginated()` signature
- Implemented LEFT JOIN query selecting embedded columns with `embedded_` prefix
- Created `_row_to_dict_with_embedded()` helper method
- NULL safety: Check `row['embedded_id'] is not None` (not truthy) because embedded_id could be empty string
- JSON parsing for `media_urls` and `link_urls` fields
- Boolean conversion for `available` flag (INTEGER to bool)

### Task 2: Browse Routes Update

Updated both `/browse` and `/api/posts` endpoints to use the new method.

**Changes:**
- `browse_page()`: Replaced `repo.get_paginated()` with `repo.get_paginated_with_embedded()`
- `api_posts()`: Replaced `repo.get_paginated()` with `repo.get_paginated_with_embedded()`
- Posts now include `embedded_post` key (None for original posts, dict for retweets/quotes)

## Verification Results

All tests passed:
- `test_api_posts_returns_correct_fields` - PASSED
- `test_api_posts_returns_posts_ordered_by_date` - PASSED
- `test_quote_tweet_display` - PASSED
- `test_retweet_display` - PASSED
- `test_unavailable_placeholder` - PASSED

**API Response Structure Verified:**
- Original posts: `embedded_post: null`
- Quote tweets: `embedded_post: {x_post_id, created_at, text, author_id, author_username, author_display_name, media_urls, link_urls, available}`

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Commit | Message | Files |
|--------|---------|-------|
| aef1af9 | feat(09-01): add get_paginated_with_embedded to PostsRepository | src/repositories/posts.py |
| 83f6622 | feat(09-01): update browse routes to use get_paginated_with_embedded | src/web/routes/browse.py |

## Self-Check: PASSED

- [x] `src/repositories/posts.py` contains `get_paginated_with_embedded` method
- [x] `src/repositories/posts.py` contains `_row_to_dict_with_embedded` helper
- [x] `src/web/routes/browse.py` uses `get_paginated_with_embedded` in both endpoints
- [x] All verification tests pass
- [x] Commits exist in git history