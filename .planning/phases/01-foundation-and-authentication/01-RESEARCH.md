# Phase 1: Foundation and Authentication - Research

**Researched:** 2026-04-18
**Domain:** Python CLI, OAuth 2.0 PKCE authentication, SQLite database initialization
**Confidence:** HIGH

## Summary

This phase establishes the foundation for the X Bookmarked Posts Organizer by implementing OAuth 2.0 PKCE authentication with X API and initializing the SQLite database. The authentication pattern is well-established in the existing x-api project, which provides a reference implementation that can be adapted with minimal modifications. The primary technical consideration is the Tweepy library's incomplete token refresh support, requiring a custom extension to `OAuth2UserHandler`.

SQLite initialization requires careful attention to PRAGMA settings—specifically WAL mode for concurrent access and `foreign_keys = ON` for referential integrity, both of which are disabled by default. The database schema for Phase 1 includes only `users` and `tokens` tables, with the `posts` table deferred to Phase 2.

**Primary recommendation:** Reuse x-api authentication patterns verbatim, adapt the scopes to include `bookmark.read` (replace `list.read`/`list.write`), and establish a connection factory function that applies all required PRAGMA settings on every new connection.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Token storage defaults to `data/tokens.json`, configurable via settings.
- Rationale: Simple, consistent with x-api pattern, easy to debug.

**D-02:** SQLite database stored at `data/bookmarks.db`.
- Rationale: Co-located with tokens for simplicity, consistent project structure.

**D-03:** Phase 1 creates minimal schema: `users` and `tokens` tables only.
- Posts table added in Phase 2 when needed.
- Clean phase boundaries; schema grows with functionality.
- Includes WAL mode and foreign key constraints as per requirements.

**D-04:** OAuth scopes: `tweet.read`, `users.read`, `bookmark.read`, `offline.access`.
- Minimal, purpose-specific permissions.
- No unnecessary list permissions from x-api pattern.
- `offline.access` required for refresh tokens.

### Claude's Discretion

- Token refresh logic — standard OAuth 2.0 flow, implement with tweepy extension
- Error messages for auth failures — follow x-auth.py patterns
- Database migration approach — simple initialization script, migrations deferred until needed

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | User can authenticate with X via OAuth 2.0 PKCE flow | x-auth.py reference implementation, Tweepy OAuth2UserHandler, local callback server pattern |
| AUTH-02 | Application stores and refreshes access tokens securely | Token persistence to JSON, custom refresh method for OAuth2UserHandler (PR #1806/#1953 workaround) |
| AUTH-03 | Application handles token expiration gracefully | AuthError exception pattern, 401/429 handling, verify_credentials pattern |
| STOR-01 | Application stores posts in SQLite database with WAL mode enabled | PRAGMA journal_mode=WAL, connection factory pattern |
| STOR-02 | Application enables foreign key constraints on database connections | PRAGMA foreign_keys=ON on every connection |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Python** | 3.10+ | Runtime | Required for modern type hints (Typer), pattern matching |
| **Typer** | 0.24.1 | CLI framework | Type-hint-based CLI, Rich integration, shell completion [VERIFIED: PyPI] |
| **Rich** | 15.0.0 | Terminal output | Tables, progress bars, styled panels. Pairs with Typer. [VERIFIED: PyPI] |
| **Tweepy** | 4.16.0 | X API v2 client | Only mature Python library with OAuth 2.0 PKCE support [VERIFIED: PyPI] |
| **SQLite** | 3.x (stdlib) | Local storage | Zero-config, WAL mode for concurrent access [CITED: sqlite.org] |
| **Pydantic Settings** | 2.13.1 | Configuration | Type-safe env vars, SecretStr for API keys, .env support [VERIFIED: PyPI] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pytest** | 8.0+ | Testing | CliRunner for in-process CLI testing |
| **pytest-asyncio** | 0.23+ | Async testing | Future-proofing for async patterns |
| **ruff** | latest | Linting/formatting | Modern replacement for flake8/black |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Typer | Click | Legacy codebases already using Click; Typer is cleaner for new projects |
| Tweepy | raw requests | X API auth complexity is significant; Tweepy handles PKCE flow correctly |
| SQLite (stdlib) | SQLAlchemy ORM | ORM is premature for 100-500 records; add later if relationships become complex |
| JSON file tokens | OS keychain | Keychain is more secure but adds complexity; defer to security hardening phase |

**Installation:**
```bash
pip install typer>=0.24.0 rich>=15.0.0 tweepy>=4.16.0 pydantic-settings>=2.0.0
pip install pytest pytest-asyncio ruff  # dev dependencies
```

## Architecture Patterns

### Recommended Project Structure

```
x-bookmarked-posts/
├── src/
│   ├── auth/
│   │   ├── __init__.py
│   │   └── oauth.py          # OAuth 2.0 PKCE flow (adapt from x-api)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py    # SQLite connection factory with PRAGMAs
│   │   └── schema.py        # CREATE TABLE statements
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py      # Pydantic Settings for env vars
│   └── cli/
│       ├── __init__.py
│       └── main.py          # Typer app entry point
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── test_oauth.py        # Auth flow tests
│   └── test_db.py           # Database tests
├── data/
│   ├── tokens.json          # OAuth tokens (gitignored)
│   └── bookmarks.db         # SQLite database (gitignored)
├── pyproject.toml
├── .env.example
└── CLAUDE.md
```

### Pattern 1: OAuth 2.0 PKCE Authentication Flow

**What:** User-initiated authentication with X API using OAuth 2.0 PKCE flow
**When to use:** First run or when tokens are expired/invalid
**Source:** [CITED: x-api/src/auth/x_auth.py]

```python
# src/auth/oauth.py - Key components to adapt from x-auth.py

import os
import tweepy
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import threading
import json
from pathlib import Path

class AuthError(Exception):
    """Raised when X API authentication fails."""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

@dataclass
class XAuth:
    client_id: str
    client_secret: str
    access_token: str
    refresh_token: str

# Module-level handler for PKCE flow
_oauth2_handler: tweepy.OAuth2UserHandler | None = None

def get_authorization_url(client_id: str, client_secret: str) -> str:
    """Create OAuth 2.0 PKCE authorization URL."""
    global _oauth2_handler
    _oauth2_handler = tweepy.OAuth2UserHandler(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://127.0.0.1:8080/callback",
        scope=["tweet.read", "users.read", "bookmark.read", "offline.access"],
    )
    return _oauth2_handler.get_authorization_url()

def wait_for_callback(port: int = 8080, timeout: int = 300) -> str:
    """Start local HTTP server to capture OAuth callback code."""
    # ... (copy from x-auth.py lines 257-308)

def ensure_authenticated() -> XAuth:
    """Orchestrate full OAuth 2.0 PKCE flow on first run."""
    # Load from tokens.json, or initiate PKCE flow
    # ... (adapt from x-auth.py lines 311-363)
```

**Key differences from x-api:**
- Scopes: `["tweet.read", "users.read", "bookmark.read", "offline.access"]` (no `list.read`/`list.write`)
- Token file location: `data/tokens.json`

### Pattern 2: Token Refresh (Workaround Required)

**What:** Refresh expired access tokens using refresh token
**When to use:** Access token expired, refresh token available
**Source:** [CITED: GitHub Issue #1953, PR #1806]

```python
# IMPORTANT: Tweepy's OAuth2UserHandler does NOT expose refresh_token()
# This is a known issue with open PRs. Workaround:

import tweepy
from requests.auth import HTTPBasicAuth

class RefreshableOAuth2UserHandler(tweepy.OAuth2UserHandler):
    """Extended OAuth2UserHandler with token refresh support."""
    
    def refresh_access_token(self, refresh_token: str) -> dict:
        """Exchange refresh token for new access token."""
        # Workaround for tweepy issue #1953
        token_data = super().refresh_token(
            "https://api.twitter.com/2/oauth2/token",
            refresh_token=refresh_token,
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
        )
        return token_data

def refresh_tokens(auth: XAuth, handler: RefreshableOAuth2UserHandler) -> XAuth:
    """Refresh access token and return updated XAuth."""
    new_tokens = handler.refresh_access_token(auth.refresh_token)
    return XAuth(
        client_id=auth.client_id,
        client_secret=auth.client_secret,
        access_token=new_tokens["access_token"],
        refresh_token=new_tokens.get("refresh_token", auth.refresh_token),
    )
```

### Pattern 3: SQLite Connection Factory with PRAGMAs

**What:** Create properly configured SQLite connections
**When to use:** Every database connection
**Source:** [CITED: sqlite.org/wal.html, pythonlore.com]

```python
# src/db/connection.py

import sqlite3
from pathlib import Path
from contextlib import contextmanager

def get_connection(db_path: str | Path = "data/bookmarks.db") -> sqlite3.Connection:
    """Create a SQLite connection with all required PRAGMA settings.
    
    CRITICAL: Each PRAGMA must be set on EVERY connection:
    - journal_mode=WAL: Enables concurrent readers during writes
    - foreign_keys=ON: Enforces referential integrity (OFF by default!)
    - synchronous=NORMAL: Safe with WAL, faster than FULL
    - busy_timeout=5000: Waits 5s instead of failing on lock contention
    """
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    
    # Essential PRAGMAs - must be set on every connection
    conn.execute("PRAGMA foreign_keys = ON")      # CRITICAL: OFF by default!
    conn.execute("PRAGMA journal_mode = WAL")     # Persists across connections
    conn.execute("PRAGMA synchronous = NORMAL")   # Safe with WAL
    conn.execute("PRAGMA busy_timeout = 5000")    # 5s wait on lock
    
    return conn

@contextmanager
def transaction(conn: sqlite3.Connection):
    """Context manager for transactions with auto-commit/rollback."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

### Pattern 4: Pydantic Settings for Configuration

**What:** Type-safe configuration from environment variables
**When to use:** Loading X API credentials, database paths
**Source:** [CITED: docs.pydantic.dev/latest/api/pydantic_settings]

```python
# src/config/settings.py

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='X_',              # X_CLIENT_ID, X_CLIENT_SECRET, etc.
        env_file='.env',
        case_sensitive=False,
    )
    
    # Required credentials - fail at startup if missing
    client_id: str
    client_secret: SecretStr         # Hidden from logs/repr
    
    # Optional with defaults
    access_token: str = ""
    refresh_token: str = ""
    
    # Configurable paths
    token_path: Path = Path("data/tokens.json")
    database_path: Path = Path("data/bookmarks.db")
    
    @property
    def client_secret_value(self) -> str:
        """Access the actual secret value."""
        return self.client_secret.get_secret_value()

# Usage:
# settings = Settings()  # Raises ValidationError if X_CLIENT_ID missing
# client_id = settings.client_id
```

### Pattern 5: Database Schema Initialization

**What:** CREATE TABLE statements for Phase 1 schema
**When to use:** First run, database initialization
**Source:** [ASSUMED - standard SQLite schema pattern]

```python
# src/db/schema.py

SCHEMA_V1 = """
-- Users table: stores X user information
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    x_user_id TEXT UNIQUE NOT NULL,      -- X platform user ID
    username TEXT NOT NULL,
    display_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tokens table: stores OAuth tokens for each user
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Index for fast token lookup by user
CREATE INDEX IF NOT EXISTS idx_tokens_user_id ON tokens(user_id);
"""

def init_database(conn: sqlite3.Connection) -> None:
    """Initialize database schema with required tables."""
    conn.executescript(SCHEMA_V1)
    conn.commit()
```

### Anti-Patterns to Avoid

- **Global SQLite connections:** Thread safety issues, connection leaks. Use connection factory or thread-local storage.
- **Missing PRAGMA foreign_keys=ON:** FK constraints silently ignored, leading to orphaned data.
- **Storing access_token only:** Need both access_token AND refresh_token for refresh flow.
- **Binding callback server to 0.0.0.0:** Security risk; always use 127.0.0.1.
- **Using tweepy < 4.10:** OAuth 2.0 PKCE support incomplete. Use >= 4.16.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth 2.0 PKCE flow | Custom HTTP server + state management | Tweepy OAuth2UserHandler | PKCE complexity, security edge cases |
| Token refresh | Manual POST to /oauth2/token | RefreshableOAuth2UserHandler extension | Token encoding, error handling |
| CLI argument parsing | argparse manual help generation | Typer with type hints | Auto-generated help, shell completion |
| Configuration management | os.getenv() scattered everywhere | Pydantic Settings | Type validation, SecretStr, .env support |
| Database connections | sqlite3.connect() without PRAGMAs | Connection factory function | Ensures FK enforcement, WAL mode |

**Key insight:** The OAuth 2.0 PKCE flow is the most common failure point (403 Forbidden errors from using wrong auth type). Reuse proven patterns from x-auth.py rather than reimplementing.

## Common Pitfalls

### Pitfall 1: X API 403 Forbidden on Bookmarks Endpoint
**What goes wrong:** Using app-only Bearer Token instead of OAuth 2.0 User Context authentication
**Why it happens:** Bookmarks endpoint requires user context, not app-only auth
**How to avoid:** Always use `tweepy.OAuth2UserHandler` (PKCE flow), NEVER `OAuth2AppHandler` or raw Bearer Token
**Warning signs:** 403 Forbidden response when calling `client.get_bookmarks()`

### Pitfall 2: Foreign Key Constraints Silently Ignored
**What goes wrong:** INSERT succeeds when referencing non-existent parent row
**Why it happens:** SQLite disables FK enforcement by default for backwards compatibility
**How to avoid:** Call `PRAGMA foreign_keys = ON` on EVERY connection (not just once)
**Warning signs:** Orphaned rows in tokens table after user deletion, referential integrity violations

### Pitfall 3: Database Locked Errors Under Concurrent Access
**What goes wrong:** "database is locked" errors when multiple operations run simultaneously
**Why it happens:** Default rollback journal mode blocks readers during writes
**How to avoid:** Enable WAL mode with `PRAGMA journal_mode = WAL` and set `busy_timeout`
**Warning signs:** Intermittent failures in tests or concurrent operations

### Pitfall 4: Token Refresh Not Working
**What goes wrong:** 401 Unauthorized after access token expires, even with valid refresh token
**Why it happens:** Tweepy's `OAuth2UserHandler` doesn't expose refresh functionality (GitHub Issue #1953)
**How to avoid:** Extend `OAuth2UserHandler` with custom `refresh_access_token()` method
**Warning signs:** Authentication fails after ~2 hours (token expiry)

### Pitfall 5: Callback Server Security Issues
**What goes wrong:** OAuth callback server accessible from external networks
**Why it happens:** Binding to `0.0.0.0` instead of `127.0.0.1`
**How to avoid:** Always use `HTTPServer(("127.0.0.1", port), ...)` for callback server
**Warning signs:** Callback server responds to external requests

## Code Examples

### OAuth 2.0 PKCE Complete Flow

```python
# src/auth/oauth.py - Complete first-run flow

import os
import json
from pathlib import Path
from dataclasses import dataclass
import tweepy

from ..config.settings import Settings

class AuthError(Exception):
    """Raised when authentication fails."""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

@dataclass
class XAuth:
    client_id: str
    client_secret: str
    access_token: str
    refresh_token: str

_oauth2_handler: tweepy.OAuth2UserHandler | None = None

def ensure_authenticated(settings: Settings) -> XAuth:
    """Ensure valid OAuth tokens, running first-run flow if needed."""
    global _oauth2_handler
    
    # Try loading stored tokens
    tokens = load_tokens(settings.token_path)
    if tokens:
        access_token, refresh_token = tokens
        # TODO: Add token validation/refresh logic
        return XAuth(
            client_id=settings.client_id,
            client_secret=settings.client_secret_value,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    
    # First-run: initiate OAuth 2.0 PKCE
    auth_url = get_authorization_url(
        settings.client_id,
        settings.client_secret_value,
    )
    print(f"Open this URL in your browser:\n{auth_url}")
    
    code = wait_for_callback()
    access_token, refresh_token = exchange_code_for_token(code)
    save_tokens(access_token, refresh_token, settings.token_path)
    
    return XAuth(
        client_id=settings.client_id,
        client_secret=settings.client_secret_value,
        access_token=access_token,
        refresh_token=refresh_token,
    )

def get_authorization_url(client_id: str, client_secret: str) -> str:
    """Generate OAuth 2.0 PKCE authorization URL."""
    global _oauth2_handler
    _oauth2_handler = tweepy.OAuth2UserHandler(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://127.0.0.1:8080/callback",
        scope=["tweet.read", "users.read", "bookmark.read", "offline.access"],
    )
    return _oauth2_handler.get_authorization_url()

def save_tokens(access_token: str, refresh_token: str, path: Path) -> None:
    """Persist tokens to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"access_token": access_token, "refresh_token": refresh_token}, f)

def load_tokens(path: Path) -> tuple[str, str] | None:
    """Load tokens from JSON file."""
    try:
        with open(path) as f:
            data = json.load(f)
        return data["access_token"], data["refresh_token"]
    except FileNotFoundError:
        return None
```

### Database Initialization

```python
# src/db/__init__.py

import sqlite3
from pathlib import Path
from .connection import get_connection
from .schema import SCHEMA_V1

def init_database(db_path: Path | None = None) -> sqlite3.Connection:
    """Initialize database with schema and return connection.
    
    Creates data/ directory if needed, applies schema, ensures WAL mode.
    """
    if db_path is None:
        from ..config.settings import Settings
        settings = Settings()
        db_path = settings.database_path
    
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    conn.executescript(SCHEMA_V1)
    conn.commit()
    return conn
```

### Typer CLI Entry Point

```python
# src/cli/main.py

import typer
from rich.console import Console
from ..config.settings import Settings
from ..auth.oauth import ensure_authenticated, AuthError
from ..db import init_database

app = typer.Typer(rich_markup_mode="rich")
console = Console()

@app.command()
def auth() -> None:
    """Authenticate with X API using OAuth 2.0 PKCE flow."""
    try:
        settings = Settings()
        auth = ensure_authenticated(settings)
        console.print(f"[green]Successfully authenticated as client {auth.client_id}[/green]")
    except AuthError as e:
        console.print(f"[red]Authentication failed: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def init() -> None:
    """Initialize the database with required tables."""
    conn = init_database()
    console.print("[green]Database initialized successfully[/green]")
    conn.close()

if __name__ == "__main__":
    app()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| argparse manual CLI | Typer type-hint CLI | 2020+ | Auto-generated help, shell completion, Rich integration |
| Manual token refresh | Extended OAuth2UserHandler | 2024+ | Workaround for tweepy issue #1953 |
| Global sqlite connections | Connection factory pattern | Standard practice | Thread-safe, consistent PRAGMA application |
| Plain text secrets in env | Pydantic SecretStr | Pydantic v2 | Prevents accidental logging of secrets |

**Deprecated/outdated:**
- `tweepy < 4.10`: OAuth 2.0 PKCE support incomplete. Use >= 4.16.
- SQLite without WAL mode: Readers block writers. Always enable WAL.
- OAuth2AppHandler for bookmarks: Requires user context. Use OAuth2UserHandler.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | x-auth.py patterns work for bookmark.read scope | Architecture | Low - same OAuth flow, different scope name |
| A2 | Token expiry is ~2 hours (X API standard) | Common Pitfalls | Medium - verify with X API docs |
| A3 | users and tokens tables are sufficient for Phase 1 | Schema | Low - CONTEXT.md locked this decision |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

## Open Questions

1. **Token refresh interval**
   - What we know: X API access tokens expire after ~2 hours
   - What's unclear: Should we proactively refresh before expiry, or reactively on 401?
   - Recommendation: Implement reactive refresh on 401 response, with optional proactive refresh before API calls

2. **User ID persistence**
   - What we know: X API returns user info from GET /2/users/me
   - What's unclear: Should we store user_id in tokens table or derive from API calls?
   - Recommendation: Store user_id in tokens table for foreign key relationship

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|----------|---------|----------|
| Python 3.10+ | Runtime | ✓ | system Python | — |
| pip | Package management | ✓ | system pip | — |
| SQLite | Data storage | ✓ | stdlib | — |

**Missing dependencies with no fallback:**
- None — all dependencies are Python packages installed via pip

**Missing dependencies with fallback:**
- None — Phase 1 has no external service dependencies

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pytest.ini |
| Quick run command | `pytest tests/ -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| AUTH-01 | User can initiate OAuth 2.0 PKCE flow | unit | `pytest tests/test_oauth.py::test_get_authorization_url -x` | ❌ Wave 0 |
| AUTH-01 | Callback server captures auth code | unit | `pytest tests/test_oauth.py::test_wait_for_callback -x` | ❌ Wave 0 |
| AUTH-02 | Application stores access tokens | unit | `pytest tests/test_oauth.py::test_save_and_load_tokens -x` | ❌ Wave 0 |
| AUTH-02 | Application refreshes expired tokens | unit | `pytest tests/test_oauth.py::test_refresh_token -x` | ❌ Wave 0 |
| AUTH-03 | Application handles expired tokens gracefully | unit | `pytest tests/test_oauth.py::test_handle_expired_token -x` | ❌ Wave 0 |
| AUTH-03 | Application handles invalid tokens gracefully | unit | `pytest tests/test_oauth.py::test_handle_invalid_token -x` | ❌ Wave 0 |
| STOR-01 | SQLite database initialized with WAL mode | unit | `pytest tests/test_db.py::test_wal_mode_enabled -x` | ❌ Wave 0 |
| STOR-02 | Foreign keys enforced on connections | unit | `pytest tests/test_db.py::test_foreign_keys_enabled -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/ -x`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_oauth.py` — covers AUTH-01, AUTH-02, AUTH-03
- [ ] `tests/test_db.py` — covers STOR-01, STOR-02
- [ ] `tests/conftest.py` — shared fixtures (mock_auth, temp_db, mock_settings)
- [ ] Framework install: `pip install pytest pytest-asyncio`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | OAuth 2.0 PKCE flow (industry standard) |
| V3 Session Management | yes | Token storage in local file with restrictive permissions |
| V4 Access Control | no | Single-user local application |
| V5 Input Validation | yes | Pydantic Settings validates env vars |
| V6 Cryptography | yes | SecretStr for sensitive values |

### Known Threat Patterns for OAuth 2.0 / Local CLI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Code interception | Tampering | PKCE (built into OAuth2UserHandler) |
| CSRF on callback | Tampering | State parameter validation (Tweepy handles) |
| Token theft (local file) | Information Disclosure | File permissions 0600, consider OS keychain |
| Callback server exposure | Tampering | Bind to 127.0.0.1 only, not 0.0.0.0 |
| Stale token usage | Elevation of Privilege | Validate token before API calls, refresh on 401 |

## Sources

### Primary (HIGH confidence)

- [Tweepy Documentation](https://docs.tweepy.org/en/latest/) — OAuth 2.0 PKCE flow, OAuth2UserHandler
- [Tweepy PyPI v4.16.0](https://pypi.org/project/tweepy/) — Version verification
- [Typer Documentation](https://typer.tiangolo.com/) — CLI patterns, CliRunner testing
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/api/pydantic_settings/) — BaseSettings, SecretStr
- [SQLite WAL Mode](https://www.sqlite.org/wal.html) — Write-Ahead Logging
- [SQLite Foreign Keys](https://www.sqlite.org/foreignkeys.html) — FK enforcement
- [X API Bookmarks Documentation](https://developer.x.com/en/docs/x-api/tweets/bookmarks/introduction) — Scopes, endpoints
- [x-api/src/auth/x_auth.py](file:///Users/ffaber/claude-projects/x-api/src/auth/x_auth.py) — Reference implementation

### Secondary (MEDIUM confidence)

- [SQLite WAL Best Practices](https://www.pythonlore.com/optimizing-sqlite3-performance-with-connection-pooling/) — PRAGMA configuration
- [SQLite Transactions Guide](https://thelinuxcode.com/sqlite-transactions-a-practical-guide-to-autocommit-wal-savepoint-and-production-patterns/) — Transaction patterns
- [CLI Authentication Guide](https://dev.to/logto/getting-cli-authentication-right-the-complete-guide-to-all-4-methods-1mnf) — PKCE flow patterns
- [Building CLI Tools with Typer and Rich](https://dasroot.net/posts/2026/01/building-cli-tools-with-typer-and-rich/) — CLI patterns

### Tertiary (LOW confidence)

- [Tweepy GitHub Issue #1953](https://github.com/tweepy/tweepy/issues/1953) — Token refresh workaround needed

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries are mature with official documentation, versions verified on PyPI
- Architecture: HIGH — Reference implementation exists in x-api, standard SQLite patterns well-documented
- Pitfalls: HIGH — X API constraints documented officially, SQLite gotchas are well-known

**Research date:** 2026-04-18
**Valid until:** 90 days (stable libraries, well-established patterns)