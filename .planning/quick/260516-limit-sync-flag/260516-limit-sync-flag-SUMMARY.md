---
status: complete
date: 2026-05-16
commit: 137c08c
---

# Quick Task: Add --limit flag to xbm sync

## Summary

Added a `--limit` flag to the `xbm sync` command that allows users to control the maximum number of bookmarks fetched per sync operation.

## Changes

### Files Modified

1. **src/cli/main.py**
   - Added `limit` parameter to `sync()` function
   - Passes `limit` to `SyncService.sync()`

2. **src/services/sync.py**
   - Updated `sync()` signature to accept optional `limit` parameter
   - Modified `_full_sync()` to check limit after each page fetch
   - Modified `_incremental_sync()` to check limit after each tweet
   - Both methods now early-return when limit is reached

## Usage

```bash
# Fetch all bookmarks (default behavior)
xbm sync

# Fetch only 50 bookmarks
xbm sync --limit 50

# Fetch only 200 bookmarks
xbm sync -l 200
```

## Testing

All 122 CLI tests pass. The existing sync command tests verify the core functionality still works correctly.

## Notes

- Default behavior unchanged: without `--limit`, fetches all available bookmarks
- Limit is enforced during the fetch loop, stopping as soon as the count is reached
- Useful for testing, rate limit management, and incremental sync strategies