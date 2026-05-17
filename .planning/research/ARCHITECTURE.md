# Architecture Research

**Domain:** FastAPI Web App with Google Cast Integration
**Context:** Adding web frontend to existing CLI-focused Python application
**Researched:** 2026-05-17
**Confidence:** HIGH

## Existing Architecture Overview

The current application uses a clean layered architecture:

```
src/
├── cli/
│   └── main.py              # Typer CLI entry point (1877 lines)
├── services/
│   ├── sync.py              # Bookmark sync from X API
│   ├── search.py            # FTS5 full-text search
│   ├── export.py            # JSON/CSV import/export
│   ├── link_checker.py      # Dead link detection
│   ├── embedding.py         # Text embeddings (sentence-transformers)
│   ├── clustering.py        # Topic clustering (K-Means)
│   ├── topic_suggester.py   # AI topic suggestions
│   ├── review_scheduler.py  # FSRS spaced repetition
│   └── review_service.py    # Review workflow logic
├── repositories/
│   ├── posts.py             # Post data access
│   ├── tags.py              # Tag CRUD
│   ├── topics.py            # Topic taxonomy
│   ├── sync_state.py        # Sync metadata
│   └── review_state.py      # Review state persistence
├── db/
│   ├── connection.py        # SQLite factory with WAL mode
│   ├── schema.py            # Table definitions
│   └── migrations.py        # Schema migrations
├── auth/
│   └── oauth.py             # OAuth 2.0 PKCE flow (603 lines)
├── api/
│   └── __init__.py          # X API client (placeholder)
├── config/
│   └── settings.py          # Pydantic Settings
└── __init__.py
```

**Key Patterns:**
- **Repository Pattern**: Data access abstracted in repositories/
- **Service Layer**: Business logic in services/
- **Connection Factory**: `get_connection()` returns SQLite connection with proper PRAGMAs
- **Token Storage**: `data/tokens.json` for OAuth credentials

## Recommended Web Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │  CLI (Typer)│  │  Browser   │  │  Google Cast Sender (JS)    │ │
│  │  xbm auth   │  │  Templates │  │  chrome.cast.media API      │ │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┬───────────────┘ │
└─────────┼────────────────┼───────────────────────┼─────────────────┘
          │                │                       │
          ▼                ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ENTRY POINT LAYER                             │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Application                      │   │
│  │  src/web/app.py                                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │ API Routes  │  │ Web Routes  │  │ Static Files Mount   │  │   │
│  │  │ /api/*      │  │ /, /browse  │  │ /static/*, /js/*     │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘  │   │
│  └─────────┼────────────────┼─────────────────────────────────────┘
│            │                │                                        │
│  ┌─────────┴────────────────┴─────────────────────────────────────┐ │
│  │                    Auth Middleware                              │ │
│  │  - Check session cookie OR                                     │ │
│  │  - Load from data/tokens.json (shared with CLI)                │ │
│  │  - Refresh tokens on 401                                       │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       SERVICE LAYER (SHARED)                         │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │
│  │SyncService│  │SearchSvc  │  │ReviewSvc  │  │TopicSuggester │   │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └───────┬───────┘   │
└────────┼──────────────┼──────────────┼────────────────┼─────────────┘
         │              │              │                │
         ▼              ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      REPOSITORY LAYER (SHARED)                       │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐│
│  │PostsRepo │  │ TagsRepo │  │TopicsRepo│  │ ReviewStateRepo      ││
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └──────────┬───────────┘│
└────────┼─────────────┼─────────────┼──────────────────┼─────────────┘
         │             │             │                  │
         ▼             ▼             ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                    │
├─────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     SQLite (data/bookmarks.db)                 │ │
│  │  - WAL mode enabled (concurrent reads/writes)                  │ │
│  │  - FTS5 for full-text search                                   │ │
│  │  - Foreign key constraints enabled                             │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     Token Store (data/tokens.json)             │ │
│  │  - Shared between CLI and Web                                  │ │
│  │  - OAuth 2.0 access_token, refresh_token                      │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `src/web/app.py` | FastAPI application factory | Creates app, mounts routers, static files |
| `src/web/routes/` | Web routes (browse, search) | Jinja2 templates, session auth |
| `src/web/api/` | JSON API routes | REST endpoints for CRUD operations |
| `src/web/auth.py` | Web authentication | Session management, token refresh |
| `src/web/templates/` | Jinja2 HTML templates | Base, browse, search, post detail |
| `src/web/static/js/cast.js` | Google Cast sender | CastContext initialization, media loading |
| `src/services/` | Business logic | **REUSED** from CLI implementation |
| `src/repositories/` | Data access | **REUSED** from CLI implementation |
| `src/db/connection.py` | Database connections | **REUSED** from CLI implementation |

## Recommended Project Structure (New Files)

```
src/
├── web/                          # NEW: Web application module
│   ├── __init__.py
│   ├── app.py                    # FastAPI application factory
│   ├── config.py                 # Web-specific settings (host, port, debug)
│   ├── auth.py                   # Session-based auth, token sharing with CLI
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── web.py                # Web routes (/, /browse, /search)
│   │   └── api.py                # JSON API routes (/api/*)
│   ├── templates/
│   │   ├── base.html             # Base template with layout, cast SDK
│   │   ├── browse.html           # Post browsing with pagination
│   │   ├── search.html           # Search results page
│   │   └── post.html             # Single post detail view
│   └── static/
│       ├── css/
│       │   └── styles.css        # Application styles
│       └── js/
│           ├── main.js           # General client-side logic
│           └── cast.js           # Google Cast sender integration
├── cli/                          # EXISTING: CLI module (unchanged)
├── services/                     # EXISTING: Shared business logic
├── repositories/                 # EXISTING: Shared data access
├── db/                           # EXISTING: Database layer
├── auth/                         # EXISTING: OAuth flow (shared)
└── config/                       # EXISTING: Settings
```

### Structure Rationale

- **`src/web/`**: New module for web-specific code, parallel to `src/cli/`
- **`routes/`**: Separate web routes from API routes for clarity
- **`templates/`**: Jinja2 templates for server-side rendering (simpler than SPA)
- **`static/js/cast.js`**: Isolated Google Cast logic for maintainability
- **Shared services/**: Both CLI and web use the same business logic
- **Shared repositories/**: Same data access layer for consistency

## Architectural Patterns

### Pattern 1: Application Factory

**What:** Create FastAPI app in a function, allowing configuration injection and testing.
**When:** Always use for FastAPI applications.
**Trade-offs:** Slightly more complex than global app, but enables testing and config flexibility.

**Example:**
```python
# src/web/app.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database connection pool if needed
    yield
    # Shutdown: Cleanup resources

def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(
        title="X Bookmarked Posts",
        lifespan=lifespan,
    )

    # Mount static files
    app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

    # Templates
    templates = Jinja2Templates(directory="src/web/templates")

    # Include routers
    from .routes.web import web_router
    from .routes.api import api_router
    app.include_router(web_router, templates=templates)
    app.include_router(api_router, prefix="/api")

    return app

# For uvicorn
app = create_app()
```

### Pattern 2: Shared Authentication (CLI + Web)

**What:** Web app reuses OAuth tokens stored by CLI in `data/tokens.json`.
**When:** Single-user, local-first applications where both CLI and web access same tokens.
**Trade-offs:** Simpler than implementing separate auth, but requires file-based token sharing.

**Implementation:**
```python
# src/web/auth.py
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from pathlib import Path
import json

from ..auth.oauth import load_tokens, refresh_access_token
from ..config import Settings

# Token file path (same as CLI)
TOKEN_PATH = Path("data/tokens.json")

async def get_current_user(request: Request) -> dict:
    """
    Dependency that ensures valid authentication.

    Flow:
    1. Check session cookie for access token
    2. Fall back to data/tokens.json (shared with CLI)
    3. If expired, refresh using refresh_token
    4. Return user info or raise HTTPException(401)
    """
    settings = Settings()

    # Try session cookie first
    access_token = request.session.get("access_token")

    # Fall back to shared token file
    if not access_token:
        tokens = load_tokens(TOKEN_PATH)
        if tokens:
            access_token = tokens[0]

    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify token with X API
    try:
        user_data = verify_credentials(access_token)
        return {"username": user_data.username, "access_token": access_token}
    except AuthError as e:
        # Token expired - try refresh
        tokens = load_tokens(TOKEN_PATH)
        if tokens:
            new_access, new_refresh = refresh_access_token(
                settings.client_id,
                settings.client_secret_value,
                tokens[1]  # refresh_token
            )
            # Save refreshed tokens
            save_tokens(new_access, new_refresh, TOKEN_PATH)
            request.session["access_token"] = new_access
            return {"username": "...", "access_token": new_access}

        raise HTTPException(status_code=401, detail="Authentication expired")

# Usage in routes
@router.get("/browse")
async def browse(request: Request, user = Depends(get_current_user)):
    return templates.TemplateResponse("browse.html", {"request": request, "user": user})
```

### Pattern 3: Service Layer Injection

**What:** Inject existing service instances into FastAPI routes via Depends().
**When:** Reusing business logic from CLI in web routes.
**Trade-offs:** Requires adapting services that expect SQLite connections to work with FastAPI's async model.

**Example:**
```python
# src/web/dependencies.py
from fastapi import Depends
from sqlite3 import Connection

from ..db.connection import get_connection
from ..services.search import SearchService
from ..repositories.posts import PostsRepository

def get_db() -> Connection:
    """Dependency that provides a database connection."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

def get_search_service(conn: Connection = Depends(get_db)) -> SearchService:
    """Dependency that provides a SearchService instance."""
    return SearchService(conn)

# Usage in routes
@router.get("/search")
async def search(
    query: str,
    service: SearchService = Depends(get_search_service)
):
    results = service.search(query)
    return {"results": results}
```

### Pattern 4: Google Cast Sender Integration

**What:** JavaScript module that initializes CastContext and handles media loading.
**When:** Any web app that needs to cast content to Chromecast/Smart TV.
**Trade-offs:** Requires HTTPS in production (HTTP only works on localhost).

**Example:**
```javascript
// src/web/static/js/cast.js

// Initialize Cast SDK when available
window['__onGCastApiAvailable'] = function(isAvailable) {
    if (isAvailable) {
        initializeCastApi();
    }
};

function initializeCastApi() {
    const context = cast.framework.CastContext.getInstance();

    // Use Default Media Receiver (no custom receiver app needed)
    context.setOptions({
        receiverApplicationId: chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID,
        autoJoinPolicy: chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED
    });

    // Listen for session changes
    context.addEventListener(
        cast.framework.CastContextEventType.SESSION_STATE_CHANGED,
        function(event) {
            if (event.sessionState === cast.framework.SessionState.SESSION_STARTED) {
                console.log('Cast session started');
            } else if (event.sessionState === cast.framework.SessionState.SESSION_ENDED) {
                console.log('Cast session ended');
            }
        }
    );
}

function castPost(postId, title, author) {
    const castSession = cast.framework.CastContext.getInstance().getCurrentSession();

    if (!castSession) {
        // No active session - prompt user to connect
        console.log('No cast session active');
        return;
    }

    // Create media info for the post
    const mediaInfo = new chrome.cast.media.MediaInfo(
        `/api/posts/${postId}/cast`,  // Endpoint that serves media
        'text/html'  // or appropriate content type
    );

    mediaInfo.metadata = new chrome.cast.media.GenericMediaMetadata();
    mediaInfo.metadata.title = title;
    mediaInfo.metadata.subtitle = `By @${author}`;

    const request = new chrome.cast.media.LoadRequest(mediaInfo);
    castSession.loadMedia(request)
        .then(() => console.log('Media loaded successfully'))
        .catch(error => console.error('Load failed:', error));
}

// Export for use in main.js
window.castPost = castPost;
```

```html
<!-- src/web/templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}X Bookmarked Posts{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', path='/css/styles.css') }}">
</head>
<body>
    <!-- Cast button (custom element) -->
    <google-cast-launcher></google-cast-launcher>

    {% block content %}{% endblock %}

    <!-- Load Cast SDK -->
    <script src="https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1"></script>
    <script src="{{ url_for('static', path='/js/main.js') }}"></script>
    <script src="{{ url_for('static', path='/js/cast.js') }}"></script>
</body>
</html>
```

## Data Flow

### Request Flow: Browse Posts

```
[Browser Request: GET /browse?topic=python&page=2]
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Route: web.py                                        │
│ @router.get("/browse")                                       │
│ async def browse(topic: str | None, page: int = 1, ...)     │
└─────────────────────────────────────────────────────────────┘
    │
    ▼ Depends(get_current_user)
┌─────────────────────────────────────────────────────────────┐
│ Auth Middleware: auth.py                                    │
│ - Check session cookie for access_token                     │
│ - Fall back to data/tokens.json                             │
│ - Verify with X API or refresh if expired                   │
└─────────────────────────────────────────────────────────────┘
    │
    ▼ Depends(get_posts_repository)
┌─────────────────────────────────────────────────────────────┐
│ Repository: PostsRepository(conn)                            │
│ def get_all(topic_id, limit, offset) -> list[dict]          │
│ - SQLite query with FTS5 if search query                    │
│ - Join with post_topics for filtering                       │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Template: browse.html                                        │
│ {% for post in posts %}                                     │
│   <div class="post">{{ post.text }}</div>                   │
│ {% endfor %}                                                 │
│ <button onclick="castPost({{ post.id }})">Cast</button>     │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
[Browser Response: HTML with posts and Cast buttons]
```

### Cast Flow: Load Post on TV

```
[User clicks "Cast" button on post]
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ JavaScript: cast.js                                          │
│ castPost(postId, title, author)                              │
│ - Check if CastSession active                               │
│ - Create MediaInfo with post content URL                    │
│ - Call castSession.loadMedia(request)                       │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Cast SDK → Default Media Receiver                            │
│ - Receiver requests: GET /api/posts/{id}/cast              │
│ - Content-Type: text/html (rendered post view)              │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Route: api.py                                        │
│ @router.get("/api/posts/{id}/cast")                          │
│ async def get_post_for_cast(id: str)                         │
│ - Return HTML rendering of post                              │
│ - Designed for TV display (larger fonts, simpler layout)    │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
[TV displays post content]
```

## Integration Points

### New Components

| Component | Location | Purpose |
|-----------|----------|---------|
| FastAPI App | `src/web/app.py` | Application factory, router mounting |
| Web Routes | `src/web/routes/web.py` | HTML endpoints (/, /browse, /search) |
| API Routes | `src/web/routes/api.py` | JSON endpoints for data |
| Web Auth | `src/web/auth.py` | Session management, token sharing |
| Templates | `src/web/templates/` | Jinja2 HTML templates |
| Static Files | `src/web/static/` | CSS, JavaScript, images |
| Cast Module | `src/web/static/js/cast.js` | Google Cast sender logic |

### Modified Components

| Component | Changes | Why |
|-----------|---------|-----|
| `src/config/settings.py` | Add `web_host`, `web_port`, `session_secret` | Web-specific settings |
| `pyproject.toml` | Add `fastapi`, `uvicorn`, `jinja2` dependencies | New runtime requirements |

### Shared Components (No Changes)

| Component | Usage |
|-----------|-------|
| `src/auth/oauth.py` | Token management (load_tokens, save_tokens, refresh_access_token) |
| `src/services/*` | Business logic (SearchService, PostsRepository, etc.) |
| `src/repositories/*` | Data access layer |
| `src/db/connection.py` | SQLite connection factory |
| `data/tokens.json` | Shared OAuth token store |
| `data/bookmarks.db` | Shared SQLite database |

## Anti-Patterns to Avoid

### Anti-Pattern 1: Duplicating Business Logic

**What people do:** Copy service logic into web routes.
**Why it's wrong:** Divergence between CLI and web, maintenance burden.
**Do this instead:** Import and reuse `src/services/` and `src/repositories/` modules.

```python
# BAD: Duplicating search logic in route
@router.get("/search")
async def search(query: str):
    conn = get_connection()
    cursor = conn.execute("SELECT * FROM posts WHERE ...")
    results = cursor.fetchall()
    return {"results": results}

# GOOD: Reusing existing service
@router.get("/search")
async def search(query: str, service: SearchService = Depends(get_search_service)):
    results = service.search(query)
    return {"results": [r._asdict() for r in results]}
```

### Anti-Pattern 2: Global SQLite Connection

**What people do:** Create one global connection for all requests.
**Why it's wrong:** Thread safety issues, connection leaks, WAL mode doesn't work correctly.
**Do this instead:** Create connection per request using Depends().

```python
# BAD: Global connection
db_connection = get_connection()  # Created at startup

@router.get("/posts")
async def get_posts():
    return db_connection.execute("SELECT * FROM posts").fetchall()

# GOOD: Per-request connection
def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

@router.get("/posts")
async def get_posts(conn: Connection = Depends(get_db)):
    return PostsRepository(conn).get_all()
```

### Anti-Pattern 3: Async SQLite

**What people do:** Use aiosqlite or async wrappers around SQLite.
**Why it's wrong:** SQLite doesn't support true async; WAL mode handles concurrent reads; adds complexity for no benefit at 100-500 post scale.
**Do this instead:** Use synchronous sqlite3 with `run_in_executor()` for blocking operations, or accept sync in FastAPI routes.

```python
# BAD: Over-engineered async
async def get_posts():
    async with aiosqlite.connect("data/bookmarks.db") as db:
        return await db.execute("SELECT * FROM posts")

# GOOD: Sync is fine for local, single-user app
@router.get("/posts")
async def get_posts(conn: Connection = Depends(get_db)):
    # This is fast enough for local, single-user app
    return PostsRepository(conn).get_all()
```

### Anti-Pattern 4: Separate Auth System

**What people do:** Implement new auth system for web (sessions, JWTs).
**Why it's wrong:** Divergence from CLI, tokens stored in two places, confusion.
**Do this instead:** Share `data/tokens.json` between CLI and web, use session cookie only for web convenience.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 100-500 posts (current) | Monolithic FastAPI + SQLite is perfect |
| 10k+ posts | Add pagination to all queries, consider indexes |
| Multiple users | Add user_id column, modify auth to support multi-user |
| Cloud deployment | Replace file-based tokens with database sessions, add HTTPS |

### Scaling Priorities

1. **First bottleneck:** Cast button doesn't work on HTTP in production
   - **Fix:** Use ngrok for local development, require HTTPS for production

2. **Second bottleneck:** Token refresh during long browser session
   - **Fix:** Implement automatic token refresh middleware

3. **Third bottleneck:** Database locking during sync + browse
   - **Fix:** WAL mode already handles this; monitor for contention

## Build Order (Considering Dependencies)

| Phase | Components | Dependencies |
|-------|------------|--------------|
| 1 | `src/web/app.py`, `src/web/routes/web.py`, `src/web/templates/base.html` | FastAPI, Jinja2 |
| 2 | `src/web/auth.py` | Existing `src/auth/oauth.py` |
| 3 | `src/web/routes/api.py` | Existing `src/services/`, `src/repositories/` |
| 4 | `src/web/static/js/main.js`, browse/search templates | None |
| 5 | `src/web/static/js/cast.js`, cast-specific templates | Cast SDK (external) |

**Rationale:**
1. Phase 1 establishes the basic web framework (can test with static content)
2. Phase 2 enables auth-protected routes (required before meaningful data access)
3. Phase 3 exposes data via JSON API (enables dynamic UI)
4. Phase 4 adds client-side interactivity
5. Phase 5 adds Cast integration (depends on Phase 4 for post display)

## Sources

- [FastAPI Templates Documentation](https://fastapi.tiangolo.com/advanced/templates) — HIGH confidence (official)
- [FastAPI Project Structure Guide 2026](https://dev.to/thesius_code_7a136ae718b7/production-ready-fastapi-project-structure-2026-guide-b1g) — MEDIUM confidence (community)
- [Google Cast Web Sender Integration](https://developers.google.com/cast/docs/web_sender/integrate) — HIGH confidence (official)
- [OAuth Token Sharing Patterns](https://kharkevich.org/2024/11/30/oidc-cli-auth/) — MEDIUM confidence (community blog)
- [FastAPI OAuth Examples](https://github.com/lukasthaler/fastapi-oauth-examples) — MEDIUM confidence (community repo)
- [Existing x-bookmarked-posts source](file:///Users/ffaber/claude-projects/x-bookmarked-posts/src/) — HIGH confidence (project reference)

---
*Architecture research for: FastAPI web app with Google Cast integration*
*Researched: 2026-05-17*