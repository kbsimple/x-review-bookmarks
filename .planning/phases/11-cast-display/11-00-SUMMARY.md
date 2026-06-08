---
phase: 11-cast-display
plan: 00
subsystem: cast-receiver-testing
tags: [testing, tdd, embedded-posts, fixtures]
requires: [CAST-06, CAST-07, CAST-08]
provides: [test-infrastructure-for-cast-receiver]
affects: [tests/test_cast_receiver.py]
tech-stack:
  added: []
  patterns: [pytest fixtures, mock database, TDD scaffolding]
key-files:
  created:
    - tests/test_cast_receiver.py
  modified: []
decisions:
  - Fixtures cover all post_type variants (original, retweet, quote, unavailable)
  - Mock database includes embedded_posts table with available/unavailable records
  - Template tests check for embedded post elements in receiver.html
  - API tests verify embedded_post data is returned correctly
  - T1-T5 tests verify rendering behavior per D-01 through D-10
metrics:
  duration: 15m
  completed: "2026-06-08T05:15:00Z"
---

# Phase 11 Plan 00: Test Scaffolding Summary

## One-liner

Created comprehensive test file with fixtures for all post_type variants and TDD scaffolding for embedded post rendering in Cast receiver.

## Implementation

### Task 1: Create test file with pytest fixtures

**File created:**
- `tests/test_cast_receiver.py` - 1026 lines

**Mock data created:**

- `MOCK_EMBEDDED_POSTS_CAST` - 4 embedded post records:
  - `cast_embedded_001`: Available quote tweet original (text only)
  - `cast_embedded_002`: Available retweet original with media (2 images)
  - `cast_embedded_003`: Unavailable embedded post (deleted/protected)
  - `cast_embedded_004`: Available original with multiple media (3 images)

- `MOCK_POSTS_CAST` - 5 posts covering all embedded post scenarios:
  - `cast_original_001`: Original post (no embedded content)
  - `cast_retweet_001`: Retweet with available embedded post
  - `cast_quote_001`: Quote tweet with available embedded post
  - `cast_unavailable_001`: Quote tweet with unavailable embedded post
  - `cast_quote_media_001`: Quote tweet with embedded media

**Fixtures created:**
- `mock_db_cast` - Creates temp SQLite with posts and embedded_posts tables
- `test_client_template` - FastAPI test client for template tests (no database)
- `test_client_cast` - FastAPI test client with mock database for API tests
- `original_post_fixture`, `retweet_post_fixture`, `quote_tweet_fixture`
- `unavailable_embedded_fixture`, `embedded_media_fixture`

### Task 2: Create failing tests for embedded post rendering

**Test classes created:**

1. `TestCastReceiverTemplate` - 4 tests for HTML template structure:
   - `test_receiver_has_embedded_post_container` - D-03: Nested card structure
   - `test_receiver_has_quote_tweet_elements` - D-03, D-04: Quoting label
   - `test_receiver_has_retweet_elements` - D-07, D-08: Attribution header
   - `test_receiver_has_unavailable_placeholder` - D-09, D-10: Placeholder

2. `TestCastApiPostEndpoint` - 5 tests for API endpoint:
   - `test_api_post_returns_original_without_embedded` - T1: Original posts
   - `test_api_post_returns_retweet_with_embedded` - T2: Retweets
   - `test_api_post_returns_quote_with_embedded` - T3: Quote tweets
   - `test_api_post_returns_unavailable_embedded` - T4: Unavailable
   - `test_api_post_returns_embedded_with_media` - T5: Embedded media

3. `TestEmbeddedPostRendering` - 5 TDD tests (T1-T5):
   - `test_t1_original_post_no_nested_card` - T1: Original renders without nested
   - `test_t2_retweet_with_reposted_header` - T2: Retweet with attribution
   - `test_t3_quote_tweet_nested_card` - T3: Quote with nested card
   - `test_t4_unavailable_post_placeholder` - T4: Unavailable placeholder
   - `test_t5_embedded_media_in_nested_card` - T5: Embedded media rendering

4. `TestCastReceiverLoadPostFunction` - 3 tests for JavaScript function:
   - `test_loadpost_handles_original_post` - Verify function exists
   - `test_loadpost_handles_embedded_post_field` - Verify function signature
   - `test_loadpost_processes_post_type` - Verify post_type handling

5. `TestCastStylingTV` - 3 tests for TV styling (PASSED):
   - `test_tv_base_text_size` - D-01: 3rem text size
   - `test_tv_high_contrast_colors` - D-02: Black background, white text
   - `test_tv_author_avatar_size` - D-04: 80px avatar

## Verification

Test collection: 20 tests collected
Test results: 14 failed, 6 passed

Failing tests (TDD - expected to fail until implementation):
- Template tests: receiver.html lacks embedded post elements
- API tests: Need to return embedded_post data
- Rendering tests: Need implementation in receiver.html

Passing tests:
- LoadPost tests: Function exists in template
- TV styling tests: Existing CSS matches D-01, D-02, D-04

```
pytest tests/test_cast_receiver.py -v --collect-only | grep "test_" | wc -l
# Result: 20 tests collected

pytest tests/test_cast_receiver.py -v --tb=no | grep "FAILED" | wc -l
# Result: 14 failing tests (TDD scaffolding)
```

## Deviations from Plan

### Combined Tasks

The plan specified separate Task 1 (fixtures) and Task 2 (failing tests), but both were implemented in a single commit because:
- Fixtures and tests are tightly coupled in the same file
- TDD approach requires both to be complete for meaningful verification
- The test file naturally includes both fixtures and test cases

### Test Count Mismatch

The plan verification expected 5 tests for Task 1 and 5 failing tests for Task 2, but:
- Created 20 tests total (comprehensive coverage)
- 14 tests fail (TDD - will pass after implementation)
- 6 tests pass (checking existing elements)

This provides more comprehensive TDD scaffolding than the minimum required.

## Known Stubs

The following test assertions are stubs pending implementation:

1. `test_t1_original_post_no_nested_card`: TODO assertion for embedded-post absence
2. `test_t2_retweet_with_reposted_header`: TODO assertion for "Reposted" headers
3. `test_t3_quote_tweet_nested_card`: TODO assertion for "Quoting" label
4. `test_t4_unavailable_post_placeholder`: TODO assertion for unavailable message
5. `test_t5_embedded_media_in_nested_card`: TODO assertion for embedded media

These stubs will be activated during Phase 11 implementation.

## Threat Flags

None - test infrastructure only, no security surface introduced.

## Self-Check: PASSED

- [x] `tests/test_cast_receiver.py` exists with 1026 lines
- [x] Fixtures cover original, retweet, quote, unavailable, media variants
- [x] Test classes for template, API, rendering, loadPost, styling
- [x] 5 T1-T5 tests exist in TestEmbeddedPostRendering class
- [x] Tests reference D-01 through D-10 decisions
- [x] Commit 00a39b7 exists

---
*Completed: 2026-06-08T05:15:00Z*
*Duration: 15 minutes*