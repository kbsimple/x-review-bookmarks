# Phase 3: Search, Notes, and Import/Export - Research

**Researched:** 2026-04-23
**Domain:** Python CLI, SQLite FTS5, Async HTTP, Data Import/Export
**Confidence:** HIGH

## Summary

This phase implements full-text search using SQLite FTS5, personal notes storage via schema migration, async link status checking, and data portability via JSON/CSV export/import. The research confirms FTS5's external content table pattern is ideal for syncing search with the posts table, httpx AsyncClient with asyncio.Semaphore is the right choice for concurrent link checking (simpler than aiohttp, supports both sync and async), and schema migrations should use PRAGMA user_version for clean version tracking.

**Primary recommendation:** Use FTS5 with `content='posts'` external content table pattern, httpx AsyncClient with asyncio.Semaphore for link checking, and PRAGMA user_version for schema migrations. All patterns integrate cleanly with existing PostsRepository and Typer CLI structure.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** SQLite FTS5 virtual table for full-text search with `content='posts'` as external content table
- **D-02:** Add `note TEXT` column to posts table for personal notes
- **D-03:** JSON export with metadata wrapper `{version: "1.0", exported_at: ISO_DATE, source: "xbm", posts: [...]}`, CSV with core fields only
- **D-04:** Async concurrent HTTP HEAD requests with httpx or aiohttp (max 10 concurrent), store link status in `link_status TEXT` column
- **D-05:** CLI commands: `xbm search <query>`, `xbm note <post_id> [text]`, `xbm export [--format json|csv]`, `xbm import <file>`, `xbm check-links`

### Claude's Discretion
- Exact FTS5 query syntax and ranking function
- Error messages for failed searches/exports
- Progress bar styling for link checks
- Import conflict resolution (skip existing vs update)

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SRCH-01 | User can search within stored post content (full-text search) | FTS5 external content table pattern with bm25 ranking |
| SRCH-02 | User can search by author name or username | FTS5 multi-column indexing (text + author_username + author_display_name) |
| SRCH-03 | Search results display relevant post content with context | FTS5 snippet() and highlight() functions |
| NOTE-01 | User can add personal notes to bookmarked posts | Schema migration: ADD COLUMN note TEXT |
| NOTE-02 | Notes are displayed when post is resurfaced for review | note column in PostsRepository.get_by_id() |
| CLI-03 | User can search stored posts via CLI command | Typer command with Rich table output |
| IMEX-01 | User can export stored posts to JSON format | Python json module with metadata wrapper |
| IMEX-02 | User can export stored posts to CSV format | Python csv module, core fields only |
| IMEX-03 | User can import posts from JSON export | JSON import with version validation |
| MAINT-01 | Application detects and flags dead links in stored posts | httpx AsyncClient HEAD requests, link_status column |
| MAINT-02 | Application can filter dead links from review queue | Query WHERE link_status != 'dead' |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **SQLite FTS5** | 3.51+ (stdlib) | Full-text search | Built into SQLite, supports bm25 ranking, snippet highlighting, multi-column search |
| **httpx** | 0.27+ | Async HTTP client | Supports sync+async, requests-like API, connection pooling, timeout support |
| **asyncio.Semaphore** | stdlib | Concurrent request limiting | Built-in, clean pattern for limiting concurrent operations |
| **json/csv** | stdlib | Data export/import | Standard library, no dependencies |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Rich** | 15.0+ | Table output for search results | Already in project, consistent CLI output |
| **Typer** | 0.23+ | CLI command structure | Already in project, consistent command pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | aiohttp | aiohttp faster at high concurrency (200+), but httpx simpler API, supports sync testing |
| FTS5 | custom search | FTS5 handles ranking, highlighting, phrase search natively; custom would be complex and slower |
| PRAGMA user_version | try/catch ALTER TABLE | user_version is cleaner for production migrations |

**Installation:**
```bash
# httpx for async link checking
pip install httpx>=0.27.0
```

**Version verification:**
- SQLite 3.51.0 verified (supports FTS5 fully)
- httpx 3.0.1 available (latest stable)
- Rich 15.0+ in project requirements
- Typer 0.23+ in project requirements

## Architecture Patterns

### Recommended Project Structure
```
src/
├── db/
│   ├── connection.py      # Existing: get_connection() with WAL mode
│   ├── schema.py          # Extend: SCHEMA_V3 with FTS5, note, link_status
│   └── migrations.py      # NEW: Migration logic with user_version tracking
├── services/
│   ├── sync.py            # Existing: SyncService pattern
│   ├── search.py          # NEW: SearchService with FTS5 queries
│   ├── link_checker.py    # NEW: Async LinkCheckerService
│   └── export.py          # NEW: ExportService for JSON/CSV
├── repositories/
│   └── posts.py           # Extend: search(), add_note(), update_link_status()
└── cli/
    └── main.py            # Extend: search, note, export, import, check-links commands
```

### Pattern 1: FTS5 External Content Table
**What:** Create FTS5 virtual table that indexes the posts table without duplicating content.

**When to use:** When you need full-text search on existing data without storage overhead.

**Example:**
```sql
-- Source: https://sqlite.org/fts5.html
-- Create FTS5 virtual table linked to posts table
CREATE VIRTUAL TABLE posts_fts USING fts5(
    text,                    -- Full-text indexed
    author_username,         -- Searchable username
    author_display_name,     -- Searchable display name
    content='posts',         -- External content table
    content_rowid='rowid'    -- Use SQLite's built-in rowid
);

-- Triggers to keep FTS index synchronized (CRITICAL)
CREATE TRIGGER posts_ai AFTER INSERT ON posts BEGIN
    INSERT INTO posts_fts(rowid, text, author_username, author_display_name)
    VALUES (new.rowid, new.text, new.author_username, new.author_display_name);
END;

CREATE TRIGGER posts_ad AFTER DELETE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, text, author_username, author_display_name)
    VALUES ('delete', old.rowid, old.text, old.author_username, old.author_display_name);
END;

CREATE TRIGGER posts_au AFTER UPDATE ON posts BEGIN
    INSERT INTO posts_fts(posts_fts, rowid, text, author_username, author_display_name)
    VALUES ('delete', old.rowid, old.text, old.author_username, old.author_display_name);
    INSERT INTO posts_fts(rowid, text, author_username, author_display_name)
    VALUES (new.rowid, new.text, new.author_username, new.author_display_name);
END;
```

### Pattern 2: Search Query with Ranking and Snippets
**What:** Use bm25() for relevance ranking and snippet() for context display.

**Example:**
```python
# Source: https://sqlite.org/fts5.html
def search_posts(conn, query: str, limit: int = 20) -> list[dict]:
    """Search posts with FTS5 ranking and snippets."""
    cursor = conn.execute("""
        SELECT
            p.x_post_id,
            p.author_username,
            p.created_at,
            snippet(posts_fts, 0, '<mark>', '</mark>', '...', 10) as snippet,
            bm25(posts_fts) as rank
        FROM posts_fts
        JOIN posts p ON p.rowid = posts_fts.rowid
        WHERE posts_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit))
    return [dict(row) for row in cursor.fetchall()]

# Multi-column search: "{author_username text} : search_term"
# Author-specific: "author_username : username_term"
```

### Pattern 3: Schema Migration with user_version
**What:** Track schema version and apply migrations incrementally.

**Example:**
```python
# Source: https://stackoverflow.com/questions/3604310
def migrate_to_v3(conn: sqlite3.Connection) -> None:
    """Migrate from v2 to v3: Add note, link_status columns and FTS5 table."""
    current_version = conn.execute("PRAGMA user_version").fetchone()[0]
    
    if current_version < 3:
        # Add note column
        conn.execute("ALTER TABLE posts ADD COLUMN note TEXT")
        
        # Add link_status column
        conn.execute("ALTER TABLE posts ADD COLUMN link_status TEXT DEFAULT 'unchecked'")
        
        # Create FTS5 virtual table
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
                text, author_username, author_display_name,
                content='posts', content_rowid='rowid'
            )
        """)
        
        # Create sync triggers
        conn.execute("CREATE TRIGGER IF NOT EXISTS posts_ai ...")
        conn.execute("CREATE TRIGGER IF NOT EXISTS posts_ad ...")
        conn.execute("CREATE TRIGGER IF NOT EXISTS posts_au ...")
        
        # Populate FTS index from existing data
        conn.execute("""
            INSERT INTO posts_fts(rowid, text, author_username, author_display_name)
            SELECT rowid, text, author_username, author_display_name FROM posts
        """)
        
        # Update version
        conn.execute("PRAGMA user_version = 3")
        conn.commit()
```

### Pattern 4: Async Link Checking with Semaphore
**What:** Use httpx AsyncClient with asyncio.Semaphore to limit concurrent requests.

**Example:**
```python
# Source: https://www.python-httpx.org/async/ and https://rednafi.com/python/limit-concurrency-with-semaphore/
import asyncio
import httpx
from dataclasses import dataclass
from typing import Optional

@dataclass
class LinkStatus:
    url: str
    status: str  # "ok", "dead", "error", "unchecked"
    last_checked: Optional[str] = None
    status_code: Optional[int] = None

class LinkChecker:
    MAX_CONCURRENT = 10
    TIMEOUT = 10.0  # seconds
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = httpx.Timeout(timeout)
    
    async def check_links(self, urls: list[str]) -> list[LinkStatus]:
        """Check multiple URLs concurrently with semaphore limiting."""
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [self._check_single(client, url, semaphore) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r if isinstance(r, LinkStatus) else self._error_result(url, r) 
                for url, r in zip(urls, results)]
    
    async def _check_single(
        self, client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore
    ) -> LinkStatus:
        async with semaphore:  # Limit concurrent requests
            try:
                response = await client.head(url, follow_redirects=True)
                return LinkStatus(
                    url=url,
                    status="ok" if 200 <= response.status_code < 400 else "dead",
                    status_code=response.status_code
                )
            except httpx.TimeoutException:
                return LinkStatus(url=url, status="error")
            except httpx.HTTPError:
                return LinkStatus(url=url, status="dead")
```

### Pattern 5: CLI Search Command with Rich Table
**What:** Use Rich Table for formatted search results output.

**Example:**
```python
# Source: https://rich.readthedocs.io/en/latest/tables.html
from rich.console import Console
from rich.table import Table
import typer

@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results"),
) -> None:
    """Search stored posts by content and author."""
    console = Console()
    
    # Perform search
    results = search_service.search(query, limit)
    
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return
    
    # Build results table
    table = Table(title=f"Search Results for '{query}'")
    table.add_column("#", style="dim", width=4)
    table.add_column("Author", style="cyan")
    table.add_column("Snippet", style="white")
    table.add_column("Date", style="dim")
    
    for i, post in enumerate(results, 1):
        table.add_row(
            str(i),
            f"@{post['author_username']}",
            post['snippet'][:80] + "..." if len(post['snippet']) > 80 else post['snippet'],
            post['created_at'][:10]  # YYYY-MM-DD
        )
    
    console.print(table)
    console.print(f"[dim]Showing {len(results)} results[/dim]")
```

### Anti-Patterns to Avoid
- **Creating FTS5 table without triggers:** Index will go stale on INSERT/UPDATE/DELETE
- **Using aiohttp over httpx for this project:** httpx supports both sync and async, simpler for testing
- **ALTER TABLE IF NOT EXISTS:** SQLite doesn't support this; use PRAGMA user_version
- **Checking all links on every sync:** Cache link_status, only recheck "unchecked" or stale entries

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Full-text search | Custom LIKE queries | SQLite FTS5 | FTS5 handles ranking, phrase search, prefix search, stemming |
| Concurrent HTTP requests | Manual threading | httpx AsyncClient + asyncio.Semaphore | Connection pooling, timeout handling, async/await native |
| Search result highlighting | Custom string matching | FTS5 snippet() and highlight() | Handles tokenization correctly, configurable markers |
| Schema migrations | try/catch ALTER TABLE | PRAGMA user_version | Clean version tracking, idempotent migrations |

**Key insight:** FTS5's external content table pattern eliminates data duplication while providing fast full-text search. The triggers are essential for keeping the index synchronized.

## Runtime State Inventory

> Not applicable — this phase adds database columns and CLI commands, no renaming or migration of runtime state.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — new columns added to existing posts table | Migration script adds columns |
| Live service config | None | N/A |
| OS-registered state | None | N/A |
| Secrets/env vars | None | N/A |
| Build artifacts | None | N/A |

## Common Pitfalls

### Pitfall 1: FTS5 Index Goes Stale
**What goes wrong:** Creating FTS5 table but forgetting triggers causes search to miss new/updated posts.
**Why it happens:** FTS5 is a separate virtual table that must be updated when the content table changes.
**How to avoid:** Always create INSERT, UPDATE, DELETE triggers when using external content table pattern.
**Warning signs:** Search results don't show recently synced posts, or show old versions of edited posts.

### Pitfall 2: Missing FTS5 Population on Migration
**What goes wrong:** Migration creates FTS5 table but doesn't populate it with existing data.
**Why it happens:** FTS5 table is empty after creation, even with content='posts' option.
**How to avoid:** After creating FTS5 table, run `INSERT INTO posts_fts(...) SELECT ... FROM posts` to populate index.
**Warning signs:** Search returns empty results even though posts table has data.

### Pitfall 3: Async Link Checker Overwhelms Network
**What goes wrong:** Checking hundreds of links concurrently causes timeouts, rate limits, or connection errors.
**Why it happens:** No concurrency limiting means all requests fire simultaneously.
**How to avoid:** Use `asyncio.Semaphore(MAX_CONCURRENT)` to limit simultaneous requests to 5-10.
**Warning signs:** Many "connection error" results, slow overall performance, hanging requests.

### Pitfall 4: Import Without Version Validation
**What goes wrong:** Importing JSON from a different version corrupts data or causes errors.
**Why it happens:** No validation of JSON format or version field.
**How to avoid:** Check `version` field in JSON wrapper, reject unknown versions, validate required fields before importing.
**Warning signs:** Import succeeds but data is malformed, or columns mismatch.

### Pitfall 5: Note Command Without Idempotency
**What goes wrong:** Repeated note commands create duplicate entries or fail unexpectedly.
**Why it happens:** Not handling NULL vs empty string correctly, or missing upsert logic.
**How to avoid:** Use UPDATE SET note = ? WHERE x_post_id = ?, handle both create and update cases.
**Warning signs:** Note shows old value after update, or "column cannot be null" errors.

## Code Examples

### FTS5 Search with Combined Text and Author Query
```python
# Source: https://sqlite.org/fts5.html
def search_posts_combined(conn, query: str, author: Optional[str] = None, limit: int = 20):
    """Search posts with optional author filter.
    
    Supports:
    - Phrase search: "exact phrase"
    - Prefix search: term*
    - Boolean: term1 AND term2, term1 OR term2, -term3
    - Author filter: author:username
    """
    if author:
        # Filter by author using column-specific match
        fts_query = f"{{author_username author_display_name}} : {query}"
    else:
        fts_query = query
    
    cursor = conn.execute("""
        SELECT
            p.x_post_id,
            p.author_username,
            p.author_display_name,
            p.created_at,
            highlight(posts_fts, 0, '[match]', '[/match]') as highlighted_text,
            bm25(posts_fts) as rank
        FROM posts_fts
        JOIN posts p ON p.rowid = posts_fts.rowid
        WHERE posts_fts MATCH ?
        ORDER BY bm25(posts_fts)
        LIMIT ?
    """, (fts_query, limit))
    
    return [dict(row) for row in cursor.fetchall()]
```

### Note Command Implementation
```python
# CLI command for adding/updating/removing notes
@app.command()
def note(
    post_id: str = typer.Argument(..., help="X post ID"),
    text: Optional[str] = typer.Argument(None, help="Note text (omit to show, use --clear to remove)"),
    clear: bool = typer.Option(False, "--clear", "-c", help="Remove note"),
) -> None:
    """Add, update, or remove a note on a post."""
    conn = get_connection()
    repo = PostsRepository(conn)
    
    post = repo.get_by_id(post_id)
    if not post:
        console.print(f"[red]Post not found: {post_id}[/red]")
        raise typer.Exit(1)
    
    if clear:
        repo.update_note(post_id, None)
        console.print(f"[green]Note removed from post {post_id}[/green]")
    elif text is None:
        # Show existing note
        current_note = post.get('note')
        if current_note:
            console.print(Panel(current_note, title=f"Note for {post_id}"))
        else:
            console.print(f"[yellow]No note for post {post_id}[/yellow]")
    else:
        repo.update_note(post_id, text)
        console.print(f"[green]Note added to post {post_id}[/green]")
    
    conn.close()
```

### JSON Export with Metadata Wrapper
```python
import json
from datetime import datetime, timezone

def export_to_json(posts: list[dict], output_path: Path) -> None:
    """Export posts to JSON with metadata wrapper."""
    export_data = {
        "version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": "xbm",
        "post_count": len(posts),
        "posts": posts
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

def import_from_json(input_path: Path, repo: PostsRepository, conflict: str = "skip") -> tuple[int, int]:
    """Import posts from JSON export.
    
    Args:
        conflict: "skip" to skip existing, "update" to update existing
    
    Returns:
        Tuple of (imported_count, skipped_count)
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Validate version
    if data.get("version") != "1.0":
        raise ValueError(f"Unsupported export version: {data.get('version')}")
    
    if data.get("source") != "xbm":
        raise ValueError(f"Invalid source: {data.get('source')}")
    
    imported = 0
    skipped = 0
    
    for post in data.get("posts", []):
        existing = repo.get_by_id(post["x_post_id"])
        if existing and conflict == "skip":
            skipped += 1
            continue
        
        # Map JSON fields to repository format
        repo.upsert_post(post)
        imported += 1
    
    return imported, skipped
```

### CSV Export (Core Fields Only)
```python
import csv

CSV_FIELDS = ["x_post_id", "text", "author_username", "author_display_name", "created_at", "note"]

def export_to_csv(posts: list[dict], output_path: Path) -> None:
    """Export posts to CSV with core fields only."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction='ignore')
        writer.writeheader()
        
        for post in posts:
            writer.writerow({
                "x_post_id": post.get("x_post_id", ""),
                "text": post.get("text", ""),
                "author_username": post.get("author_username", ""),
                "author_display_name": post.get("author_display_name", ""),
                "created_at": post.get("created_at", ""),
                "note": post.get("note", "") or ""
            })
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LIKE '%term%' queries | FTS5 full-text search | SQLite 3.9.0 (2015) | Orders of magnitude faster, supports ranking |
| Synchronous link checking | Async with semaphore | Python 3.7+ | Non-blocking, handles many links efficiently |
| ALTER TABLE try/catch | PRAGMA user_version | SQLite best practice | Clean migration tracking |
| Custom search highlighting | FTS5 snippet()/highlight() | FTS5 introduction | Correct tokenization, configurable |

**Deprecated/outdated:**
- **FTS3/FTS4:** Replaced by FTS5 in SQLite 3.9.0+, FTS5 has better query syntax and ranking
- **requests for async:** Use httpx for async support, same API as requests

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Import conflict resolution should default to "skip" | Import/Export | User may want "update" behavior — make configurable via --update flag |
| A2 | 10 concurrent requests is safe for most link checking | Link Checker | Some sites may rate limit; make configurable |
| A3 | FTS5 phrase search handles most user queries | Search | Complex boolean queries may need preprocessing |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

## Open Questions (RESOLVED)

1. **Import conflict resolution default**
   - What we know: JSON import needs to handle existing posts
   - What's unclear: Should default be "skip" (safer) or "update" (more complete)?
   - Recommendation: Default to "skip", add `--update` flag for explicit update behavior

2. **Link recheck frequency**
   - What we know: Links can become dead over time
   - What's unclear: Should links be rechecked automatically? On what schedule?
   - Recommendation: Store last_checked timestamp, recheck "unchecked" or entries older than 30 days on `check-links` command

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| SQLite FTS5 | Search | ✓ | 3.51.0 | N/A (stdlib) |
| httpx | Link checking | ✗ | — | Install required |
| Python 3.9+ | Async patterns | ✓ | 3.9+ | N/A |
| Rich | CLI output | ✓ | 15.0+ | N/A |
| Typer | CLI framework | ✓ | 0.23+ | N/A |

**Missing dependencies with no fallback:**
- httpx: Required for async link checking — add to pyproject.toml

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml (testpaths: tests, python_files: test_*.py) |
| Quick run command | `pytest tests/test_search.py -x` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRCH-01 | Full-text search within stored post content | unit | `pytest tests/test_search_service.py -x` | ❌ Wave 0 |
| SRCH-02 | Search by author name or username | unit | `pytest tests/test_search_service.py -x` | ❌ Wave 0 |
| SRCH-03 | Search results with context display | unit | `pytest tests/test_search_service.py -x` | ❌ Wave 0 |
| NOTE-01 | Add personal notes to posts | unit | `pytest tests/test_posts_repository.py -x` | ✅ Extend existing |
| NOTE-02 | Notes displayed in review | unit | `pytest tests/test_posts_repository.py -x` | ✅ Extend existing |
| CLI-03 | CLI search command | integration | `pytest tests/test_cli.py::TestSearchCommand -x` | ❌ Wave 0 |
| IMEX-01 | Export to JSON with metadata | unit | `pytest tests/test_export_service.py -x` | ❌ Wave 0 |
| IMEX-02 | Export to CSV | unit | `pytest tests/test_export_service.py -x` | ❌ Wave 0 |
| IMEX-03 | Import from JSON | unit | `pytest tests/test_export_service.py -x` | ❌ Wave 0 |
| MAINT-01 | Detect and flag dead links | unit | `pytest tests/test_link_checker.py -x` | ❌ Wave 0 |
| MAINT-02 | Filter dead links from review queue | unit | `pytest tests/test_posts_repository.py::test_get_posts_exclude_dead_links -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_<module>.py -x`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_search_service.py` — covers SRCH-01, SRCH-02, SRCH-03
- [ ] `tests/test_export_service.py` — covers IMEX-01, IMEX-02, IMEX-03
- [ ] `tests/test_link_checker.py` — covers MAINT-01
- [ ] `tests/test_cli.py::TestSearchCommand` — covers CLI-03
- [ ] `tests/test_cli.py::TestNoteCommand` — covers NOTE-01 CLI interface
- [ ] `tests/test_cli.py::TestExportCommand` — covers IMEX-01, IMEX-02 CLI interface
- [ ] `tests/test_cli.py::TestImportCommand` — covers IMEX-03 CLI interface
- [ ] `tests/test_cli.py::TestCheckLinksCommand` — covers MAINT-01 CLI interface
- [ ] Extend `tests/test_posts_repository.py` — add note and link_status column tests

*(If no gaps: "None — existing test infrastructure covers all phase requirements")*

## Security Domain

> Security enforcement enabled (workflow.nyquist_validation: true)

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — CLI tool uses stored OAuth tokens |
| V3 Session Management | no | N/A — no web sessions |
| V4 Access Control | no | N/A — single-user CLI |
| V5 Input Validation | yes | FTS5 parameterized queries, Typer argument validation |
| V6 Cryptography | no | N/A — no encryption in this phase |

### Known Threat Patterns for Python CLI + SQLite

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection in search queries | Tampering | Parameterized FTS5 queries (MATCH parameter) |
| Path traversal in import/export | Tampering | Typer validates paths, use Path.resolve() |
| SSRF in link checking | Tampering | Timeout limits, no redirects to internal IPs (validate URLs) |
| DoS via large imports | Denial of Service | Limit import file size, batch inserts with transactions |

## Sources

### Primary (HIGH confidence)
- [SQLite FTS5 Extension](https://sqlite.org/fts5.html) — FTS5 syntax, bm25(), snippet(), highlight(), external content tables
- [httpx Async Documentation](https://www.python-httpx.org/async/) — AsyncClient usage, connection pooling
- [Rich Tables Documentation](https://rich.readthedocs.io/en/latest/tables.html) — Table construction, styling

### Secondary (MEDIUM confidence)
- [SQLite ALTER TABLE IF NOT EXISTS](https://stackoverflow.com/questions/3604310) — Migration patterns, PRAGMA user_version
- [httpx vs aiohttp Comparison](http://smartproxy.io/blog/httpx-vs-requests-vs-aiohttp) — Performance comparison, use case guidance
- [Python asyncio Semaphore](https://rednafi.com/python/limit-concurrency-with-semaphore/) — Concurrent request limiting pattern
- [Typer Testing Guide](https://typer.tiangolo.com/tutorial/testing/) — CliRunner usage patterns

### Tertiary (LOW confidence)
- [Python CLI Testing Patterns](https://pytest-with-eric.com/pytest-advanced/pytest-argparse-typer) — Testing CLI commands (verified against official docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — SQLite FTS5 is built-in and stable, httpx is well-documented, patterns match existing codebase
- Architecture: HIGH — External content table pattern is SQLite-recommended, triggers are documented, migration pattern is standard
- Pitfalls: HIGH — Common FTS5 and async pitfalls identified from official docs and community resources

**Research date:** 2026-04-23
**Valid until:** 90 days — SQLite FTS5 is stable, httpx API unlikely to change significantly