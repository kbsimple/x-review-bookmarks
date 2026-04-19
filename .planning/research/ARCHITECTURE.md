# Architecture Research

**Domain:** Python CLI with SQLite storage and X API integration
**Researched:** 2026-04-18
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLI Layer (Typer)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ fetch        │  │ topics       │  │ resurface    │             │
│  │ command      │  │ command      │  │ command      │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
├─────────┴─────────────────┴─────────────────┴───────────────────────┤
│                        Service Layer                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ FetchService │  │ TopicService │  │SchedulerSvc  │             │
│  │              │  │              │  │ (FSRS)       │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
├─────────┴─────────────────┴─────────────────┴───────────────────────┤
│                       Repository Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ PostRepo     │  │ TopicRepo    │  │ScheduleRepo  │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
├─────────┴─────────────────┴─────────────────┴───────────────────────┤
│                      External Services                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ X API Client │  │ SQLite DB    │  │ Config/Auth │             │
│  │ (Tweepy)     │  │              │  │ (pydantic)   │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **CLI Layer** | Command parsing, user I/O, output formatting | Typer with Rich for tables/progress |
| **Service Layer** | Business logic, orchestration, coordination | Plain Python classes with injected deps |
| **Repository Layer** | Data access abstraction, SQL queries | Repository pattern with SQLite backend |
| **X API Client** | Authentication, rate limiting, API calls | Tweepy OAuth2UserHandler + Client |
| **Scheduler** | Spaced repetition calculations | py-fsrs library (FSRS algorithm) |
| **Config** | Environment vars, credentials, defaults | pydantic-settings BaseSettings |
| **SQLite** | Persistent storage, caching | Single file DB with WAL mode |

## Recommended Project Structure

```
src/x_bookmarked/
├── __init__.py
├── cli.py                 # Typer app entry point
├── main.py                # App initialization, dependency container
├── config/
│   ├── __init__.py
│   └── settings.py        # pydantic-settings configuration
├── auth/
│   ├── __init__.py
│   └── oauth.py           # OAuth 2.0 PKCE flow handler
├── api/
│   ├── __init__.py
│   └── x_client.py        # Tweepy wrapper with rate limiting
├── db/
│   ├── __init__.py
│   ├── connection.py      # SQLite connection manager
│   ├── migrations.py      # Schema migrations
│   ├── models.py          # Dataclasses/Pydantic models
│   └── repositories/
│       ├── __init__.py
│       ├── base.py        # Abstract repository interface
│       ├── posts.py       # Post repository
│       ├── topics.py      # Topic repository
│       └── schedule.py    # Resurfacing schedule repository
├── services/
│   ├── __init__.py
│   ├── fetch_service.py   # Orchestrate X API fetch
│   ├── topic_service.py   # Topic clustering logic
│   └── scheduler_service.py # Spaced repetition scheduling
├── scheduler/
│   ├── __init__.py
│   └── fsrs_wrapper.py    # FSRS algorithm integration
└── utils/
    ├── __init__.py
    └── logging.py         # Structured logging setup

tests/
├── conftest.py            # Fixtures, test database
├── test_repositories/
├── test_services/
└── test_cli/

data/
└── bookmarks.db          # SQLite database file
```

### Structure Rationale

- **cli.py vs main.py:** CLI handles command parsing only; main.py handles dependency injection container setup
- **repositories/:** Each domain entity gets its own repository following single responsibility
- **services/:** One service per major feature area (fetch, topics, scheduling)
- **scheduler/:** Isolated module for FSRS algorithm - could be swapped for SM-2 if needed
- **auth/:** Separate module because OAuth flow has its own state management complexity
- **data/:** SQLite file outside src for easy backup/inspection

## Architectural Patterns

### Pattern 1: Repository Pattern

**What:** Abstract data access behind interfaces so business logic never touches SQL directly.

**When to use:** Always - essential for testability and clean separation.

**Trade-offs:** More boilerplate upfront, but enables in-memory testing and future database swaps.

**Example:**
```python
# db/repositories/base.py
from abc import ABC, abstractmethod
from typing import Protocol

class PostRepository(Protocol):
    """Protocol for dependency injection"""
    def get_by_id(self, post_id: str) -> Post | None: ...
    def get_all_bookmarked(self) -> list[Post]: ...
    def save(self, post: Post) -> None: ...
    def get_posts_for_resurface(self, due_date: datetime) -> list[Post]: ...

# db/repositories/posts.py
class SQLitePostRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_by_id(self, post_id: str) -> Post | None:
        cursor = self._conn.execute(
            "SELECT * FROM posts WHERE id = ?", (post_id,)
        )
        row = cursor.fetchone()
        return Post.from_row(row) if row else None

    def save(self, post: Post) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO posts
               (id, text, author_id, created_at, bookmarked_at, ...)
               VALUES (?, ?, ?, ?, ?, ...)""",
            (post.id, post.text, post.author_id, ...)
        )
        self._conn.commit()
```

### Pattern 2: Service Layer Orchestration

**What:** Services coordinate between repositories, external APIs, and business rules. CLI calls services, never repositories directly.

**When to use:** When business logic spans multiple entities or external systems.

**Trade-offs:** Adds a layer, but keeps CLI thin and logic testable without database.

**Example:**
```python
# services/fetch_service.py
class FetchService:
    def __init__(
        self,
        x_client: XClient,
        post_repo: PostRepository,
        topic_repo: TopicRepository,
    ):
        self._x_client = x_client
        self._post_repo = post_repo
        self._topic_repo = topic_repo

    def fetch_and_store_bookmarks(self) -> FetchResult:
        """Fetch bookmarks from X API and store in database."""
        bookmarks = self._x_client.get_bookmarks()
        for bookmark in bookmarks:
            post = Post.from_x_api(bookmark)
            self._post_repo.save(post)
        return FetchResult(count=len(bookmarks))
```

### Pattern 3: Dependency Injection Container

**What:** Single place to wire up all dependencies. Services receive their dependencies through constructor injection.

**When to use:** For any CLI with multiple services and repositories.

**Trade-offs:** Slightly more setup code, but eliminates hidden global state.

**Example:**
```python
# main.py
from dependency_injector import containers, providers
from db.connection import get_connection
from db.repositories.posts import SQLitePostRepository
from services.fetch_service import FetchService

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    db_connection = providers.Singleton(get_connection, config.db_path)

    post_repo = providers.Singleton(SQLitePostRepository, db_connection)
    topic_repo = providers.Singleton(SQLiteTopicRepository, db_connection)

    x_client = providers.Singleton(XClient, config.twitter_credentials)

    fetch_service = providers.Singleton(
        FetchService, x_client, post_repo, topic_repo
    )

# cli.py
container = Container()
container.config.from_dict({"db_path": "data/bookmarks.db"})

app = typer.Typer()

@app.command()
def fetch():
    service = container.fetch_service()
    result = service.fetch_and_store_bookmarks()
    typer.echo(f"Fetched {result.count} bookmarks")
```

### Pattern 4: SQLite Connection Management

**What:** Thread-local connection with WAL mode and proper pragmas for performance.

**When to use:** Any SQLite-based application.

**Trade-offs:** Single connection per thread - fine for CLI, not for concurrent web apps.

**Example:**
```python
# db/connection.py
import sqlite3
import threading
from contextlib import contextmanager

_thread_local = threading.local()

def get_connection(db_path: str) -> sqlite3.Connection:
    """Get or create thread-local connection with optimal settings."""
    if not hasattr(_thread_local, 'conn'):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Dict-like access
        # Optimize for single-writer CLI usage
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA cache_size = -64000")  # 64MB
        _thread_local.conn = conn
    return _thread_local.conn

@contextmanager
def transaction(conn: sqlite3.Connection):
    """Context manager for transactions with auto-rollback on error."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

## Data Flow

### Fetch Bookmarks Flow

```
User: x-bookmarked fetch
         │
         ▼
    ┌─────────┐
    │ CLI     │ Validates auth, calls service
    └────┬────┘
         │
         ▼
    ┌──────────────┐
    │FetchService  │ Orchestrates fetch
    └──────┬───────┘
         │ │
         │ ▼
         │ ┌─────────┐     ┌──────────┐
         │ │X Client │────▶│ X API    │
         │ └─────────┘     └──────────┘
         │        │
         │        ▼ (bookmarks data)
         │ ┌─────────┐
         │ │PostRepo │
         │ └────┬────┘
         │      │
         ▼      ▼
    ┌───────────┐
    │  SQLite   │
    └───────────┘
         │
         ▼
    Result: "Fetched N bookmarks"
```

### Resurface Schedule Flow

```
User: x-bookmarked resurface
         │
         ▼
    ┌──────────────────┐
    │SchedulerService  │ Queries due posts
    └────────┬─────────┘
             │
         ┌───┴────┐
         ▼        ▼
    ┌─────────┐  ┌───────────┐
    │PostRepo │  │ScheduleRepo│
    └────┬────┘  └─────┬─────┘
         │             │
         ▼             ▼
    ┌─────────────────────┐
    │      SQLite         │
    │  posts + schedules  │
    └─────────────────────┘
             │
             ▼
    ┌──────────────────┐
    │FSRS Wrapper      │ Calculates next due date
    └──────────────────┘
             │
             ▼
    Result: Posts to review today
```

### Topic Assignment Flow

```
User: x-bookmarked topics cluster
         │
         ▼
    ┌──────────────┐
    │TopicService  │ Loads unclassified posts
    └───────┬──────┘
            │
   ┌────────┴────────┐
   ▼                 ▼
┌─────────┐    ┌────────────┐
│TopicRepo│    │AI Client   │ (if using LLM)
└────┬────┘    │or rules    │
     │         └─────┬──────┘
     │               │
     └───────┬───────┘
             ▼
    ┌─────────────────┐
    │Assign topics    │
    │Update DB        │
    └─────────────────┘
```

### Key Data Flows

1. **Fetch Flow:** CLI → FetchService → XClient → X API → FetchService → PostRepo → SQLite
2. **Resurface Flow:** CLI → SchedulerService → PostRepo + ScheduleRepo → SQLite → FSRS → output
3. **Topic Flow:** CLI → TopicService → PostRepo + TopicRepo → SQLite → (optional AI) → SQLite update

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 100-500 bookmarks | Single-file SQLite sufficient. In-memory operations fast. No indexing needed beyond primary keys. |
| 500-5K bookmarks | Add indexes on `created_at`, `topic_id`, `next_due`. Consider connection pooling if web interface added. |
| 5K+ bookmarks | Consider SQLite full-text search for content search. May need background indexing. |

### Scaling Priorities

1. **First bottleneck:** SQLite file I/O if database on network drive - keep local
2. **Second bottleneck:** Full-text search for finding posts by content - add FTS5 virtual table

## Anti-Patterns

### Anti-Pattern 1: Business Logic in CLI

**What people do:** Put query logic and business rules directly in CLI command functions.

**Why it's wrong:** Untestable without CLI invocation, mixes concerns, hard to reuse.

**Do this instead:**
```python
# BAD - logic in CLI
@app.command()
def fetch():
    conn = sqlite3.connect("bookmarks.db")
    client = tweepy.Client(token)
    bookmarks = client.get_bookmarks()
    for b in bookmarks:
        conn.execute("INSERT INTO posts ...")
    typer.echo("Done")

# GOOD - CLI just calls service
@app.command()
def fetch():
    service = container.fetch_service()
    result = service.fetch_and_store_bookmarks()
    typer.echo(f"Fetched {result.count} bookmarks")
```

### Anti-Pattern 2: Global Database Connection

**What people do:** Create a module-level `conn = sqlite3.connect()` global.

**Why it's wrong:** Hidden state, hard to test, connection leak potential.

**Do this instead:** Use dependency injection container to provide connection, or thread-local storage.

### Anti-Pattern 3: Raw SQL in Services

**What people do:** Call `conn.execute()` directly from service layer.

**Why it's wrong:** Tightly couples services to SQLite, can't test without database.

**Do this instead:** Services call repository interfaces, repositories handle SQL.

### Anti-Pattern 4: Storing Full API Responses

**What people do:** Serialize entire X API JSON response and store as blob.

**Why it's wrong:** Schema hard to query, migrations painful, SQLite JSON functions limited.

**Do this instead:** Extract fields to typed columns, store only necessary data. Use `json` column type for truly flexible fields.

### Anti-Pattern 5: Sync API Calls Without Rate Limiting

**What people do:** Loop through bookmarks calling API without rate limit handling.

**Why it's wrong:** X API rate limits will cause failures, no retry logic.

**Do this instead:** Use Tweepy's `wait_on_rate_limit=True` or implement backoff with `tenacity` library.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **X API v2** | Tweepy Client + OAuth2UserHandler | PKCE flow required. Tokens expire in 2 hours unless `offline.access` scope. |
| **FSRS Scheduler** | py-fsrs library | Imported directly, stateless calculations. Store card state in DB. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI → Services | Direct function calls | Services injected via container |
| Services → Repositories | Interface (Protocol) | Enables mock repositories for testing |
| Services → X Client | Interface | Enables mock API for testing |
| Repositories → SQLite | Direct connection | Connection from container |

### Authentication Flow (OAuth 2.0 PKCE)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     OAuth 2.0 PKCE Flow                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. CLI generates PKCE pair (code_verifier, code_challenge)        │
│                     │                                               │
│                     ▼                                               │
│  2. CLI opens browser to X authorization URL with code_challenge   │
│                     │                                               │
│                     ▼                                               │
│  3. User authorizes in browser                                     │
│                     │                                               │
│                     ▼                                               │
│  4. X redirects to callback URL with authorization code           │
│                     │                                               │
│                     ▼                                               │
│  5. CLI exchanges code + code_verifier for access_token            │
│                     │                                               │
│                     ▼                                               │
│  6. CLI stores token (optionally refresh_token for offline.access) │
│                     │                                               │
│                     ▼                                               │
│  7. CLI creates Tweepy Client with access_token                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Implementation Points:**
- Use `tweepy.OAuth2UserHandler` for PKCE flow
- Store tokens securely (not in source control)
- Use `offline.access` scope for long-running CLI that doesn't require re-auth
- Refresh tokens before they expire (2 hour default)

## Build Order Implications

Based on dependency analysis, recommended build order:

### Phase 1: Core Infrastructure
1. **Project structure** - Create folder layout
2. **Configuration** - pydantic-settings for env vars
3. **Database layer** - Connection manager, migrations, basic models
4. **Repository interfaces** - Protocols/ABCs for repositories

### Phase 2: Data Foundation
5. **Repository implementations** - SQLite repositories for posts, topics
6. **Test fixtures** - In-memory SQLite for fast tests
7. **Domain models** - Post, Topic, Schedule dataclasses

### Phase 3: External Integration
8. **OAuth 2.0 PKCE handler** - Authentication flow
9. **X API client wrapper** - Tweepy client with rate limiting
10. **Token storage** - Secure credential persistence

### Phase 4: Core Features
11. **FetchService** - Bookmark retrieval and storage
12. **CLI fetch command** - Wire up to fetch service
13. **TopicService** - Clustering logic (predefined + optional AI)

### Phase 5: Spaced Repetition
14. **FSRS wrapper** - Integrate py-fsrs
15. **ScheduleRepository** - Store/retrieve review schedules
16. **SchedulerService** - Calculate due dates, query due posts
17. **CLI resurface command** - Display posts due for review

### Phase 6: Delivery (Future Milestone)
18. **Web server** - FastAPI for Samsung TV / casting
19. **Web endpoints** - REST API for scheduled posts

## Sources

- [Python CLI Architecture: Building Interfaces with Typer & argparse](https://medium.com/@kaushikking89/python-cli-architecture-building-interfaces-with-typer-argparse-fc2239c255ed) - HIGH confidence
- [Python CLI Tools with Click and Typer Guide](https://devtoolbox.dedyn.io/blog/python-click-typer-cli-guide) - HIGH confidence
- [Stop Writing Scripts: 5 Production CLI Patterns](https://dev.to/leejackson/building-a-production-ready-python-cli-tool-with-logging-error-handling-and-auto-updates-in-2026-58ca) - HIGH confidence
- [Python CLI Apps Opinionated Whitepaper](https://kb.adrianbacceli.com/00_Toolbox/Runbooks/Python-CLI-Apps-%E2%80%93-Opinionated-Whitepaper--and-Runbook) - MEDIUM confidence
- [sqlite-utils by Simon Willison](https://github.com/simonw/sqlite-utils) - HIGH confidence
- [Advanced SQLite: Repository Pattern](https://logicandlegacy.blogspot.com/2026/04/advanced-python-sqlite-indices-n1.html) - HIGH confidence
- [Database Interoperability with Repository Pattern](https://sudoblark.com/blog/database-interoperability-in-python-with-the-repository-enterprise-pattern/) - MEDIUM confidence
- [Tweepy Authentication Documentation](http://docs.tweepy.org/en/latest/authentication.html) - HIGH confidence (official)
- [How to Implement Twitter OAuth 2.0 with PKCE using Tweepy](https://medium.com/%40nkangprecious26/table-of-contents-155038d8f0c3) - MEDIUM confidence
- [X OAuth 2.0 Authorization Code Flow Documentation](https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code) - HIGH confidence (official)
- [py-fsrs Spaced Repetition Library](https://github.com/open-spaced-repetition/py-fsrs) - HIGH confidence
- [Social Media Database Schema Example](https://github.com/ssahibsingh/Social-Media-Database-Project/blob/main/schema.sql) - MEDIUM confidence
- [Dependency Injector CLI Tutorial](https://python-dependency-injector.ets-labs.org/tutorials/cli.html) - HIGH confidence

---
*Architecture research for: Python CLI + SQLite + X API*
*Researched: 2026-04-18*