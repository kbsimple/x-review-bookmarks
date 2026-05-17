---
status: complete
date: 2026-05-17
commit: 9e1c43f
---

# Summary: Add Post Statistics to Stats Command

## Completed
- Added `get_post_stats()` method to PostsRepository
  - Returns oldest_date, newest_date, total, and by_month breakdown
  - Uses SQLite strftime for month grouping
- Updated `stats` command to display post statistics
  - Shows date range header
  - Displays total posts
  - Visual bar chart for posts per month (like Claude's context usage display)
  - Preserves existing review statistics section

## Files Changed
- `src/repositories/posts.py` - Added `get_post_stats()` method
- `src/cli/main.py` - Enhanced `stats` command output

## Testing
- Ran `venv/bin/xbm stats` - displays correctly with:
  - Post Statistics panel with date range and bar chart
  - Review Statistics panel with existing metrics