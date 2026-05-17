# Stack Research

**Domain:** Python CLI + FastAPI web app with Google Cast integration
**Researched:** 2026-05-17 (Milestone 1.1 additions)
**Confidence:** HIGH

---

## Milestone 1.1: Web App + Cast Additions

The following additions extend the existing Milestone 1 CLI stack for the web frontend and Google Cast integration.

### Core Web Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **FastAPI** | 0.136+ | Web framework | Type-hint-based async framework with automatic OpenAPI docs. Native Jinja2 support via `Jinja2Templates`. Integrates cleanly with existing Pydantic models. Standard for Python web APIs in 2026. |
| **Uvicorn** | 0.47+ | ASGI server | Required to run FastAPI. Standard extras include httptools and uvloop for performance. Native SSL support via `--ssl-keyfile` and `--ssl-certfile` for HTTPS development. |
| **Jinja2** | 3.1.6 | HTML templating | Built-in FastAPI integration via `Jinja2Templates` from Starlette. Template inheritance, macros, autoescaping. Already used in Python ecosystem. Current stable release. |
| **python-multipart** | 0.0.28 | Form data parsing | Required for FastAPI `Form()` and `File()` parameters. Handles multipart/form-data requests. Same author as Starlette/Uvicorn (Kludex), well-maintained. |
| **aiosqlite** | 0.20+ | Async SQLite driver | FastAPI is async-native. Using sync sqlite3 in async handlers blocks the event loop. `sqlite+aiosqlite://` connection string for async operations with existing SQLite database. |
| **mkcert** | N/A (CLI tool) | Local HTTPS certificates | Google Cast requires HTTPS secure context. mkcert creates locally-trusted certificates. One-time setup: `mkcert -install && mkcert localhost 127.0.0.1 ::1`. |

### Google Cast Integration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Web Sender SDK** | (JavaScript) | Cast button in browser | Official Google Cast JavaScript SDK. Loaded via `<script src="//www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1">`. Handles device discovery and media control. |
| **PyChromecast** | 13.1.0 | Backend control (optional) | Python library for Chromecast control. Use v13.x for Python 3.10 compatibility (v14+ requires Python 3.11+). Alternative: pure Web Sender SDK for frontend-only control. |
| **Default Media Receiver** | `CC1AD845` | Cast receiver app ID | No custom receiver registration needed. Google-hosted receiver for basic media playback. Use this for v1.1. |

### Web Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **httpx** | Async test client | For async endpoint testing with `AsyncClient`. Included in `fastapi[standard]`. |
| **TestClient** | Sync test client | From `fastapi.testclient` for in-process testing. |

### Installation (Milestone 1.1 Additions)

```bash
# Core web framework (includes uvicorn, jinja2, python-multipart, httpx)
pip install "fastapi[standard]"

# Async SQLite driver
pip install aiosqlite

# Optional: Backend casting control
pip install "PyChromecast<14.0.0"  # v13.x for Python 3.10 compatibility

# Development tools (add to existing)
pip install httpx  # For async endpoint testing
```

---

## Milestone 1: CLI Stack (Existing)

The following was established for Milestone 1 and remains valid.

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.10+ | Runtime | Required by Typer (3.10+), sentence-transformers (3.10+). Modern type hints, pattern matching. |
| **Typer** | 0.24+ | CLI framework | Type-hint-based CLI eliminates boilerplate. Built-in shell completion. Rich integration out of box. Recommended default for 2025-2026 Python CLIs. |
| **Rich** | 14.3+ | Terminal output | Tables, progress bars, syntax highlighting. 460M+ monthly downloads. Maintained by Textualize. Pairs perfectly with Typer. |
| **Tweepy** | 4.16+ | X API v2 client | Only mature Python library for X API. Supports OAuth 2.0 PKCE for bookmarks. Maintained, MIT licensed. Matches existing project pattern. |
| **SQLite** | 3.x (stdlib) | Local storage | Zero-config, single-file database. Perfect for 100-500 bookmark scale. WAL mode for concurrent read/write. |
| **APScheduler** | 3.11+ | Scheduling | In-process cron-like scheduling. SQLite job store for persistence. Handles exponential backoff resurfacing. |
| **Pydantic Settings** | 2.0+ | Configuration | Type-safe config from env vars, .env files. SecretStr for API keys. Twelve-factor app compliance. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **sentence-transformers** | 5.4+ | Text embeddings | Topic clustering. Use all-MiniLM-L6-v2 for 384-dim embeddings (22M params, fast inference). |
| **scikit-learn** | 1.5+ | Clustering algorithms | K-Means or Agglomerative clustering on embeddings. Required for topic assignment. |
| **hdbscan** | 0.8+ | Density clustering | Alternative to K-Means when cluster count unknown. Better for organic topic discovery. |
| **PyYAML** | 6.0+ | YAML parsing | Optional config files. Used in existing project pattern. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **pytest** | Testing | Use CliRunner for in-process CLI testing |
| **pytest-asyncio** | Async testing | If using async patterns later |
| **ruff** | Linting/formatting | Modern, fast replacement for flake8/black |
| **mypy** | Type checking | Typer benefits from strict typing |

## Installation (Milestone 1)

```bash
# Core CLI
pip install typer[all]>=0.24.0

# X API integration
pip install tweepy>=4.16.0

# Database (stdlib, but SQLite best practices)
# No install needed - use sqlite3 from standard library

# Scheduling
pip install apscheduler>=3.11.0

# Configuration
pip install pydantic-settings>=2.0.0

# Topic clustering (Milestone 2)
pip install sentence-transformers>=5.4.0 scikit-learn>=1.5.0

# Development
pip install pytest>=8.0.0 ruff mypy
```

---

## Project Structure (Updated)

```
x-bookmarked-posts/
├── pyproject.toml              # Updated with web dependencies
├── run.py                      # NEW: Dev server entry point
├── certs/                      # NEW: mkcert certificates
│   ├── localhost+2-key.pem
│   └── localhost+2.pem
├── src/
│   ├── __init__.py
│   ├── cli.py                  # Existing Typer app entry point
│   ├── config.py               # Existing Pydantic Settings (add web settings)
│   ├── auth/                   # Existing OAuth 2.0 PKCE
│   │   ├── __init__.py
│   │   └── x_auth.py
│   ├── db/                     # Existing SQLite
│   │   ├── __init__.py
│   │   ├── connection.py       # WAL mode config (sync)
│   │   ├── async_db.py         # NEW: Async session factory
│   │   └── models.py
│   ├── api/                    # Existing X API client
│   │   ├── __init__.py
│   │   └── bookmarks.py
│   ├── scheduler/              # Existing APScheduler jobs
│   │   ├── __init__.py
│   │   └── resurface.py
│   └── web/                    # NEW: FastAPI web app
│       ├── __init__.py
│       ├── app.py              # FastAPI application factory
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── posts.py       # Post browsing endpoints
│       │   └── cast.py        # Cast control endpoints (optional)
│       ├── templates/
│       │   ├── base.html
│       │   ├── posts/
│       │   └── components/
│       └── static/
│           ├── js/
│           │   └── cast.js    # Web Sender SDK integration
│           └── css/
├── data/
│   ├── bookmarks.db           # SQLite database (shared CLI + web)
│   └── tokens.json            # OAuth tokens (shared)
└── tests/
```

## Integration with Existing Stack

### SQLite with Async

The existing CLI uses sync `sqlite3` with WAL mode. For FastAPI:

```python
# src/db/async_db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///./data/bookmarks.db"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite requirement
    echo=False
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

**Key point:** CLI continues using sync sqlite3. FastAPI routes use async sessions. Both access the same database file. WAL mode handles concurrent reads.

### OAuth Authentication

Share existing OAuth 2.0 PKCE flow with web routes:

```python
# Web routes can reuse the same auth flow
from src.auth.x_auth import get_auth, XAuth

@app.get("/auth/callback")
async def auth_callback(code: str, state: str):
    # Same flow as CLI
    auth = get_auth()
    token = auth.fetch_token(code, state)
    # Store in session/cookie for web use
```

### Configuration

Add web-specific settings to existing Pydantic Settings:

```python
# src/config.py additions
class Settings(BaseSettings):
    # Existing...
    
    # NEW: Web app settings
    web_host: str = "127.0.0.1"
    web_port: int = 8443
    web_ssl_keyfile: Path | None = None
    web_ssl_certfile: Path | None = None
    web_debug: bool = False
```

---

## HTTPS Development Setup

Google Cast requires HTTPS (secure context). Use mkcert:

```bash
# Install mkcert (one-time)
brew install mkcert  # macOS
# choco install mkcert  # Windows
# apt install mkcert   # Linux

# Create local CA and certificates
mkcert -install
mkcert localhost 127.0.0.1 ::1

# Move to project
mv localhost+2.pem certs/localhost.pem
mv localhost+2-key.pem certs/localhost-key.pem
```

**Run with HTTPS:**
```bash
# Development
uvicorn src.web.app:app --host 127.0.0.1 --port 8443 \
    --ssl-keyfile certs/localhost-key.pem \
    --ssl-certfile certs/localhost.pem \
    --reload
```

---

## Google Cast Integration

### Frontend (Web Sender SDK)

```html
<!-- templates/base.html -->
<script src="//www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1"></script>

<!-- Cast button -->
<google-cast-launcher></google-cast-launcher>

<script>
// Initialize Cast context
window.__onGCastApiAvailable = (isAvailable) => {
  if (isAvailable) {
    cast.framework.CastContext.getInstance().setOptions({
      receiverApplicationId: chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID,
      autoJoinPolicy: chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED
    });
  }
};

// Cast media
async function castMedia(url, contentType) {
  const context = cast.framework.CastContext.getInstance();
  const session = context.getCurrentSession();
  const mediaInfo = new chrome.cast.media.MediaInfo(url, contentType);
  const request = new chrome.cast.media.LoadRequest(mediaInfo);
  await session.loadMedia(request);
}
</script>
```

### Backend (Optional PyChromecast)

For server-initiated casting:

```python
# src/web/routes/cast.py
import pychromecast
from fastapi import APIRouter

router = APIRouter()

@router.post("/cast/{post_id}")
async def cast_to_tv(post_id: int):
    # Discover devices
    chromecasts, browser = pychromecast.get_chromecasts()
    if not chromecasts:
        raise HTTPException(404, "No Chromecast devices found")

    # Select device (could be user-configured)
    cast = chromecasts[0]
    cast.wait()

    # Get post media URL
    post = await get_post(post_id)
    media_url = post.media_url or post.link

    # Cast
    mc = cast.media_controller
    mc.play_media(media_url, "image/jpeg")

    return {"status": "casting", "device": cast.name}
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| FastAPI | Flask | Legacy codebases, simpler apps without async needs |
| FastAPI | Django | Full-featured CMS needs, admin panel, ORM-first architecture |
| Jinja2Templates | HTMX | Interactive UIs without full SPA framework, hypermedia-driven |
| aiosqlite | sync sqlite3 (blocking) | Never in async handlers - blocks event loop, kills performance |
| mkcert | self-signed cert | mkcert auto-trusts in system/browser, self-signed requires manual trust |
| mkcert | ngrok tunnel | Need remote access (e.g., mobile testing), but requires internet |
| Web Sender SDK | Custom Receiver | Custom UI on TV, but requires registration and hosting |
| PyChromecast 13.x | PyChromecast 14+ | If upgrading to Python 3.11+, v14+ has newer API but breaking changes |
| Typer | Click | Legacy codebases already using Click, need advanced parameter types |
| Typer | argparse | Zero dependencies required, simple scripts with 2-3 arguments |
| Tweepy | raw requests | X API auth complexity is significant; Tweepy handles PKCE flow correctly |
| SQLite (stdlib) | SQLAlchemy ORM | Complex relationships, migrations needed, future PostgreSQL migration planned |
| APScheduler | Celery | Distributed tasks, multi-process workers, Redis-backed queues |
| APScheduler | schedule (library) | Simpler cron-like syntax but no persistence, no async, no SQLite job store |
| sentence-transformers | OpenAI embeddings | No GPU required, no API costs, works offline, privacy-preserving |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **sync sqlite3 in async routes** | Blocks event loop, 10x slower under load | aiosqlite with async_session |
| **FastAPI `def` routes for I/O** | Works but `async def` preferred for I/O operations | `async def` consistently |
| **self-signed certificates** | Browser warnings break Cast SDK initialization | mkcert for local dev |
| **localhost for Cast testing** | Cast SDK may reject localhost in some browsers | Use `127.0.0.1` or local IP |
| **HTTP for Cast** | Presentation API deprecated on insecure origins | HTTPS with mkcert |
| **PyChromecast 14+** | Requires Python 3.11+, project uses 3.10+ | PyChromecast 13.x |
| **SQLAlchemy ORM (full)** | Overkill for 100-500 records, existing raw SQL works | Continue raw SQL with aiosqlite |
| **Full SPA framework** | Overkill for browse/search/cast functionality | Jinja2 templates + vanilla JS |
| **tweepy < 4.10** | OAuth 2.0 PKCE support incomplete | tweepy >= 4.16 |
| **SQLite without WAL mode** | Readers block writers, "database is locked" errors | `PRAGMA journal_mode=WAL` |
| **Global SQLite connections** | Thread safety issues, connection leaks | Connection per thread or thread-local storage |
| **Individual INSERTs without transactions** | 30-50 inserts/sec vs thousands/sec | Wrap bulk operations in `BEGIN/COMMIT` |
| **argparse for new CLI** | High boilerplate, manual help generation | Typer with type hints |
| **TF-IDF for clustering** | Lower quality than embeddings on short text | sentence-transformers embeddings |

---

## Version Compatibility

### Milestone 1.1 Additions

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| FastAPI 0.136+ | Python 3.10+ | 3.11/3.12 recommended |
| Starlette 1.0+ | FastAPI 0.136+ | Breaking changes from 0.x |
| Uvicorn 0.47+ | Python 3.10+ | SSL support built-in |
| aiosqlite 0.20+ | Python 3.10+ | Async wrapper for sqlite3 |
| PyChromecast 13.x | Python 3.10+ | v14+ drops 3.10 support |
| Jinja2 3.1.6 | FastAPI (via Starlette) | Native Jinja2Templates support |
| python-multipart 0.0.28 | FastAPI | Required for Form/File parameters |

### Milestone 1 (Existing)

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| typer 0.24+ | Python >=3.10 | Requires modern type hints |
| sentence-transformers 5.4+ | transformers >=4.41 | Auto-installed as dependency |
| tweepy 4.16+ | requests >=2.27, oauthlib >=3.2 | Auto-installed as dependencies |
| apscheduler 3.11+ | Python >=3.8 | v4.0 in alpha, avoid for production |

---

## HTTPS Requirements Detail

| Environment | Approach | Certificate Source |
|-------------|----------|-------------------|
| Development | mkcert | Local CA, auto-trusted |
| Testing (mobile) | ngrok | ngrok's TLS tunnel |
| Production (not v1.1) | Let's Encrypt | certbot automation |

**Why HTTPS for Google Cast:**
1. Browsers deprecated Presentation API on insecure origins
2. `navigator.requestMediaKeySystemAccess` requires secure context
3. Cast SDK initialization fails without HTTPS in most browsers
4. `window.isSecureContext` must be `true`

---

## SQLite Configuration Best Practices

```python
def configure_sqlite(db_path: str) -> sqlite3.Connection:
    """Production-ready SQLite configuration for CLI apps."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")        # Concurrent read/write
    conn.execute("PRAGMA synchronous = NORMAL")      # Balance safety/speed
    conn.execute("PRAGMA foreign_keys = ON")         # Enforce relationships
    conn.execute("PRAGMA cache_size = -64000")       # 64MB cache
    conn.execute("PRAGMA busy_timeout = 30000")      # 30s wait for locks
    conn.execute("PRAGMA temp_store = MEMORY")       # In-memory temp tables
    return conn
```

---

## pyproject.toml Template (Updated)

```toml
[project]
name = "x-bookmarked-posts"
version = "1.1.0"
description = "Fetch and organize X bookmarked posts with spaced-repetition resurfacing and web interface"
requires-python = ">=3.10"
dependencies = [
    # Milestone 1 (CLI)
    "typer[all]>=0.24.0",
    "tweepy>=4.16.0",
    "apscheduler>=3.11.0",
    "pydantic-settings>=2.0.0",
    "rich>=14.0.0",
    # Milestone 1.1 (Web)
    "fastapi[standard]>=0.136.0",
    "aiosqlite>=0.20.0",
]

[project.optional-dependencies]
clustering = [
    "sentence-transformers>=5.4.0",
    "scikit-learn>=1.5.0",
    "hdbscan>=0.8.0",
]
cast = [
    "PyChromecast<14.0.0",  # v13.x for Python 3.10 compatibility
]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
    "httpx>=0.27.0",
]

[project.scripts]
xbm = "src.cli:app"  # CLI command
xbm-web = "run:main"  # Web server command

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"
```

---

## Sources

### Milestone 1.1 (Web + Cast)

- [FastAPI Release Notes](https://fastapi.tiangolo.com/release-notes) — HIGH confidence (official)
- [FastAPI Templates Documentation](https://fastapi.tiangolo.com/advanced/templates) — HIGH confidence (official)
- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/) — HIGH confidence (official)
- [Uvicorn Documentation](https://uvicorn.dev/) — HIGH confidence (official)
- [Uvicorn Release Notes](https://uvicorn.dev/release-notes/) — HIGH confidence (official)
- [Starlette 1.0.0 Release](https://pypi.org/project/starlette/) — HIGH confidence (official)
- [PyChromecast PyPI](https://pypi.org/project/PyChromecast/) — HIGH confidence (official)
- [PyChromecast v14.0.0 Breaking Changes](https://github.com/home-assistant-libs/pychromecast/releases/tag/14.0.0) — HIGH confidence (GitHub)
- [Google Cast Web Sender Integration](https://developers.google.com/cast/docs/web_sender/integrate) — HIGH confidence (official)
- [Google Cast HTTPS Requirements](https://developers.google.com/cast/docs/web_sender) — HIGH confidence (official)
- [python-multipart PyPI](https://pypi.org/project/python-multipart/) — HIGH confidence (official)
- [Jinja2 PyPI](https://pypi.org/project/Jinja2/) — HIGH confidence (official)
- [aiosqlite with FastAPI Guide](https://mjmjmj.name/python/async-sqlalchemy/) — MEDIUM confidence (community)
- [FastAPI Async Database Connections](https://oneuptime.com/blog/post/2026-02-02-fastapi-async-database/view) — MEDIUM confidence (community)
- [mkcert for Local HTTPS](https://woile.dev/blog/local-https-development-in-python-with-mkcert.html) — MEDIUM confidence (community)
- [Local HTTPS Setup Guide 2026](https://dev.to/emily-flias/how-can-i-set-up-ssl-on-localhost-httpslocalhost-3f4g) — MEDIUM confidence (community)

### Milestone 1 (CLI)

- [Typer Documentation](https://typer.tiangolo.com/) — HIGH confidence (official)
- [Rich PyPI](https://pypi.org/project/rich/) — HIGH confidence (official)
- [Tweepy Documentation](https://docs.tweepy.org/en/latest/) — HIGH confidence (official)
- [Tweepy PyPI v4.16.0](https://pypi.org/project/tweepy/) — HIGH confidence (official)
- [X API Bookmarks Documentation](https://developer.x.com/en/docs/x-api/tweets/bookmarks/introduction) — HIGH confidence (official)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/en/master/) — HIGH confidence (official)
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/api/pydantic_settings/) — HIGH confidence (official)
- [Sentence Transformers Documentation](https://www.sbert.net/examples/applications/clustering/README.html) — HIGH confidence (official)
- [SQLite WAL Mode Best Practices](https://www.pythonlore.com/optimizing-sqlite3-performance-with-connection-pooling/) — MEDIUM confidence (community)
- [Python CLI Architecture Guide](https://medium.com/@kaushikking89/python-cli-architecture-building-interfaces-with-typer-argparse-fc2239c255ed) — MEDIUM confidence (community, Apr 2026)
- [Existing x-api project](file:///Users/ffaber/claude-projects/x-api/src/auth/x_auth.py) — HIGH confidence (project reference)
- [SQLAlchemy vs Raw SQL](https://thelinuxcode.com/sqlalchemy-core-vs-orm-how-i-choose-the-right-layer-in-2026/) — MEDIUM confidence (community)

---
*Stack research for: Python CLI + FastAPI web app + Google Cast*
*Initial research: 2026-04-18*
*Web app additions: 2026-05-17*