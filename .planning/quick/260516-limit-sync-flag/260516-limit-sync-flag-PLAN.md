---
mode: quick
description: Add --limit flag to xbm sync command to control max bookmarks fetched per sync
---

# Quick Task: Add --limit flag to xbm sync

## Objective

Add a `--limit` flag to the `xbm sync` command that allows users to control the maximum number of bookmarks fetched per sync. This prevents accidentally flooding the X API and allows for incremental syncs during testing or rate limit management.

## Current Behavior

The `xbm sync` command currently fetches all available bookmarks (up to X API's 800 limit) with no user control over the count.

## Target Behavior

```bash
xbm sync              # Fetch all bookmarks (current behavior)
xbm sync --limit 50   # Fetch only 50 bookmarks
xbm sync --limit 200  # Fetch only 200 bookmarks
```

## Tasks

### Task 1: Add --limit parameter to sync command

**Files:**
- `src/cli/main.py`
- `src/services/sync.py`

**Action:**

1. In `src/cli/main.py`, add `limit` parameter to the `sync` function:
   ```python
   def sync(
       db_path: Optional[Path] = typer.Option(...),
       limit: Optional[int] = typer.Option(
           None,
           "--limit",
           "-l",
           help="Maximum number of bookmarks to fetch (default: all)",
       ),
   ) -> None:
   ```

2. Pass `limit` to `SyncService.sync_all()` call

3. In `src/services/sync.py`, modify `sync_all()` to accept optional `limit` parameter:
   ```python
   def sync_all(self, limit: Optional[int] = None) -> SyncResult:
       # Add check after fetch:
       # if limit and result.total_fetched >= limit:
       #     break
   ```

4. Add docstring updates documenting the new parameter

**Verify:**
```bash
pytest tests/test_cli.py -x -v
pytest tests/test_sync.py -x -v
```

**Done:**
- `--limit` flag works with `xbm sync`
- Default behavior unchanged (fetches all)
- Tests pass