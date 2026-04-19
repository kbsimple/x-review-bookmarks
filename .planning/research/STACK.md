# Stack Research

**Domain:** Python CLI application for X API bookmark management
**Researched:** 2026-04-18
**Confidence:** HIGH

## Recommended Stack

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

## Installation

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

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Typer | Click | Legacy codebases already using Click, need advanced parameter types |
| Typer | argparse | Zero dependencies required, simple scripts with 2-3 arguments |
| Tweepy | raw requests | X API auth complexity is significant; Tweepy handles PKCE flow correctly |
| SQLite (stdlib) | SQLAlchemy ORM | Complex relationships, migrations needed, future PostgreSQL migration planned |
| APScheduler | Celery | Distributed tasks, multi-process workers, Redis-backed queues |
| APScheduler | schedule (library) | Simpler cron-like syntax but no persistence, no async, no SQLite job store |
| sentence-transformers | OpenAI embeddings | No GPU required, no API costs, works offline, privacy-preserving |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **tweepy < 4.10** | OAuth 2.0 PKCE support incomplete | tweepy >= 4.16 |
| **SQLite without WAL mode** | Readers block writers, "database is locked" errors | `PRAGMA journal_mode=WAL` |
| **Global SQLite connections** | Thread safety issues, connection leaks | Connection per thread or thread-local storage |
| **Individual INSERTs without transactions** | 30-50 inserts/sec vs thousands/sec | Wrap bulk operations in `BEGIN/COMMIT` |
| **argparse for new CLI** | High boilerplate, manual help generation | Typer with type hints |
| **TF-IDF for clustering** | Lower quality than embeddings on short text | sentence-transformers embeddings |

## Stack Patterns by Variant

**If migrating from existing project:**
- Reuse auth pattern from x-api project (OAuth 2.0 PKCE with local callback server)
- Pin versions matching existing project for consistency
- Copy `XAuth`, `get_auth`, `verify_credentials` pattern

**If simple MVP first:**
- Start with Typer + sqlite3 directly (no ORM)
- Add SQLAlchemy 2.0 later if relationships become complex
- Use raw SQL for queries, ORM is premature for 100-500 records

**If clustering needs emerge:**
- Start with K-Means (sklearn) - simpler, faster
- Switch to HDBSCAN if topics need organic discovery (no predetermined count)

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| typer 0.24+ | Python >=3.10 | Requires modern type hints |
| sentence-transformers 5.4+ | transformers >=4.41 | Auto-installed as dependency |
| tweepy 4.16+ | requests >=2.27, oauthlib >=3.2 | Auto-installed as dependencies |
| apscheduler 3.11+ | Python >=3.8 | v4.0 in alpha, avoid for production |

## SQLite Configuration Best Practices

```python
def configure_sqlite(db_path: str) -> sqlite3.Connection:
    """Production-ready SQLite configuration for CLI apps."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")        # Concurrent read/write
    conn.execute("PRAGMA synchronous = NORMAL")      # Balance safety/speed
    conn.execute("PRAGMA foreign_keys = ON")         # Enforce relationships
    conn.execute("PRAGMA cache_size = -64000")        # 64MB cache
    conn.execute("PRAGMA busy_timeout = 30000")      # 30s wait for locks
    conn.execute("PRAGMA temp_store = MEMORY")        # In-memory temp tables
    return conn
```

## Project Structure Pattern

```
x-bookmarked-posts/
├── pyproject.toml              # Modern packaging (PEP 621)
├── src/
│   ├── __init__.py
│   ├── cli.py                  # Typer app entry point
│   ├── auth/                   # OAuth 2.0 PKCE (reuse from x-api)
│   │   ├── __init__.py
│   │   └── x_auth.py
│   ├── db/                    # SQLite operations
│   │   ├── __init__.py
│   │   ├── connection.py      # WAL mode config
│   │   └── models.py          # Post schema
│   ├── api/                   # X API client
│   │   ├── __init__.py
│   │   └── bookmarks.py       # Fetch/parse bookmarks
│   └── scheduler/              # APScheduler jobs
│       ├── __init__.py
│       └── resurface.py
├── data/
│   ├── bookmarks.db           # SQLite database
│   └── tokens.json            # OAuth tokens
└── tests/
```

## pyproject.toml Template

```toml
[project]
name = "x-bookmarked-posts"
version = "0.1.0"
description = "Fetch and organize X bookmarked posts with spaced-repetition resurfacing"
requires-python = ">=3.10"
dependencies = [
    "typer[all]>=0.24.0",
    "tweepy>=4.16.0",
    "apscheduler>=3.11.0",
    "pydantic-settings>=2.0.0",
    "rich>=14.0.0",
]

[project.optional-dependencies]
clustering = [
    "sentence-transformers>=5.4.0",
    "scikit-learn>=1.5.0",
    "hdbscan>=0.8.0",
]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]

[project.scripts]
xbm = "src.cli:app"  # Creates `xbm` command

[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"
```

## Sources

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
*Stack research for: Python CLI + X API + SQLite*
*Researched: 2026-04-18*