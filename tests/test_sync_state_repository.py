"""Tests for sync state repository.

Tests for:
- Get state
- Update state
- Save pagination token
- Total bookmarks tracking
"""

import pytest
from pathlib import Path
import sys
import sqlite3
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db_with_sync_state():
    """Create a temporary SQLite database with sync_state table.

    Yields:
        sqlite3.Connection: Connection with sync_state table created.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Apply required PRAGMAs
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")

    # Create sync_state table per D-02
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_sync_bookmark_id TEXT,
            last_sync_at TIMESTAMP,
            pagination_token TEXT,
            total_bookmarks INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    yield conn

    conn.close()
    db_path.unlink(missing_ok=True)


class TestSyncStateRepository:
    """Tests for SyncStateRepository operations."""

    def test_get_state_returns_defaults(self, temp_db_with_sync_state):
        """Verify get_state returns SyncState with defaults for new database.

        D-02: New sync_state returns None values and 0 total.
        """
        from src.repositories.sync_state import SyncStateRepository, SyncState

        repo = SyncStateRepository(temp_db_with_sync_state)
        state = repo.get_state()

        assert isinstance(state, SyncState)
        assert state.last_sync_bookmark_id is None
        assert state.last_sync_at is None
        assert state.pagination_token is None
        assert state.total_bookmarks == 0

    def test_update_state_stores_bookmark_id(self, temp_db_with_sync_state):
        """Verify update_state stores last_sync_bookmark_id.

        D-02: Store last_sync_bookmark_id for incremental sync.
        """
        from src.repositories.sync_state import SyncStateRepository

        repo = SyncStateRepository(temp_db_with_sync_state)

        repo.update_state(last_sync_bookmark_id="bookmark_12345")

        state = repo.get_state()
        assert state.last_sync_bookmark_id == "bookmark_12345"

    def test_update_state_stores_pagination_token(self, temp_db_with_sync_state):
        """Verify update_state stores pagination_token.

        DATA-04: Persist pagination_token for resume after interruption.
        """
        from src.repositories.sync_state import SyncStateRepository

        repo = SyncStateRepository(temp_db_with_sync_state)

        repo.update_state(pagination_token="next_page_token_xyz")

        state = repo.get_state()
        assert state.pagination_token == "next_page_token_xyz"

    def test_update_state_reset_pagination(self, temp_db_with_sync_state):
        """Verify update_state can reset pagination_token.

        Called after successful sync completion to clear resume point.
        """
        from src.repositories.sync_state import SyncStateRepository

        repo = SyncStateRepository(temp_db_with_sync_state)

        # Set a pagination token
        repo.update_state(pagination_token="resume_token")

        # Reset it
        repo.update_state(reset_pagination=True)

        state = repo.get_state()
        assert state.pagination_token is None

    def test_increment_count_adds_to_total(self, temp_db_with_sync_state):
        """Verify increment_count adds to total_bookmarks.

        DATA-05: Track total for 800 limit warning.
        """
        from src.repositories.sync_state import SyncStateRepository

        repo = SyncStateRepository(temp_db_with_sync_state)

        # Start at 0
        assert repo.get_state().total_bookmarks == 0

        # Increment by 5
        repo.increment_count(5)
        assert repo.get_state().total_bookmarks == 5

        # Increment by 3 more
        repo.increment_count(3)
        assert repo.get_state().total_bookmarks == 8

    def test_set_total_count(self, temp_db_with_sync_state):
        """Verify set_total_count sets absolute value.

        Used after full sync to set accurate count.
        """
        from src.repositories.sync_state import SyncStateRepository

        repo = SyncStateRepository(temp_db_with_sync_state)

        repo.set_total_count(42)

        state = repo.get_state()
        assert state.total_bookmarks == 42

    def test_update_state_preserves_existing_values(self, temp_db_with_sync_state):
        """Verify update_state preserves values not explicitly set.

        COALESCE ensures only non-None values are updated.
        """
        from src.repositories.sync_state import SyncStateRepository

        repo = SyncStateRepository(temp_db_with_sync_state)

        # Set bookmark ID
        repo.update_state(last_sync_bookmark_id="first_id")

        # Update pagination token only
        repo.update_state(pagination_token="token_xyz")

        # Bookmark ID should still be there
        state = repo.get_state()
        assert state.last_sync_bookmark_id == "first_id"
        assert state.pagination_token == "token_xyz"

    def test_update_state_updates_timestamp(self, temp_db_with_sync_state):
        """Verify update_state updates last_sync_at timestamp.

        D-02: Store last_sync_at for sync history.
        """
        import time
        from src.repositories.sync_state import SyncStateRepository

        repo = SyncStateRepository(temp_db_with_sync_state)

        before = time.time()
        repo.update_state(last_sync_bookmark_id="test_id")
        after = time.time()

        state = repo.get_state()
        assert state.last_sync_at is not None
        assert before <= state.last_sync_at <= after