# Pitfalls Research

**Domain:** X API integration, content clustering, spaced repetition, FastAPI web app, Google Cast
**Researched:** 2026-04-18 (Milestone 1), 2026-05-17 (Milestone v1.1 - Web App + Cast)
**Confidence:** HIGH

---

## Critical Pitfalls (Milestone 1: CLI + SQLite)

### Pitfall 1: X API Bookmarks Authentication Error (403 Forbidden)

**What goes wrong:**
Developers using tweepy or similar libraries receive `403 Forbidden` when calling the bookmarks endpoint, even with valid credentials. The error states "Authenticating with OAuth 2.0 Application-Only is forbidden for this endpoint."

**Why it happens:**
The `/2/users/:id/bookmarks` endpoint requires **OAuth 2.0 User Context** authentication (OAuth 2.0 Authorization Code Flow with PKCE), not the simpler App-Only Bearer Token. Many developers default to app-only auth which works for public data but fails for user-specific endpoints like bookmarks.

**How to avoid:**
- Implement OAuth 2.0 PKCE flow from the start
- Request scopes: `tweet.read`, `users.read`, `bookmark.read`
- Use tweepy's `OAuth2UserHandler` or equivalent, NOT `OAuth2AppHandler`
- Store refresh tokens for long-running CLI applications

**Warning signs:**
- 403 errors specifically on bookmarks endpoint while other endpoints work
- Error message mentioning "Application-Only" authentication

**Phase to address:** Milestone 1 (CLI + SQLite — fetch and store)

---

### Pitfall 2: X API 800 Bookmark Retrieval Limit

**What goes wrong:**
The X API only allows retrieval of the **800 most recent bookmarks**. Attempting to paginate beyond this returns empty results, even if you have thousands of bookmarks.

**Why it happens:**
This is a hard API limitation, not a rate limit. X doesn't expose older bookmarks through the API. The `result_count: 0` response when bookmarks exist is confusing and leads developers to debug authentication when the real issue is the hard cap.

**How to avoid:**
- Document this limitation clearly for users
- Implement incremental sync: fetch new bookmarks regularly before they fall beyond the 800 limit
- Consider alternative: if user wants older bookmarks, they may need to manually export from X's data download feature
- Store bookmarks immediately when added (can't retroactively fetch)

**Warning signs:**
- Pagination returning `result_count: 0` but `meta.next_token` still present
- User reports having 1000+ bookmarks but API only returns 800

**Phase to address:** Milestone 1 (document limitation, design sync strategy)

---

### Pitfall 3: Rate Limit Exhaustion Without Recovery Strategy

**What goes wrong:**
Applications crash or lose data when hitting X API rate limits (180 requests/15min for bookmarks GET). Without proper handling, the app may corrupt sync state or fail silently.

**Why it happens:**
- Not monitoring `x-rate-limit-remaining` headers
- Treating 429 errors as failures instead of "wait and retry"
- No persistence of pagination state between rate limit windows

**How to avoid:**
- Check rate limit headers before each request
- Implement exponential backoff with jitter for 429 responses
- Store `next_token` in SQLite between sessions to resume pagination
- Design sync as resumable operations, not all-or-nothing

**Warning signs:**
- Intermittent 429 errors in logs
- Incomplete bookmark syncs that restart from beginning

**Phase to address:** Milestone 1 (implement rate limit handling in fetch logic)

---

### Pitfall 4: Spaced Repetition "Ease Hell" (SM-2 Algorithm)

**What goes wrong:**
Content resurfaces increasingly frequently until users are overwhelmed with reviews. The algorithm makes it easier to decrease ease factor than increase it, causing items to spiral into review loops.

**Why it happens:**
Classic SM-2 formula asymmetry: perfect recall (q=5) only slightly increases ease factor, while anything less decreases it significantly. Over time, ease factors drift toward minimum (1.3), making intervals impractically short.

**How to avoid:**
- Consider FSRS (Free Spaced Repetition Scheduler) as a modern alternative to SM-2
- If using SM-2, implement "ease hell" mitigations:
  - Add "easy" bonus that boosts ease factor more aggressively
  - Cap minimum interval at 1-2 days (never below)
  - Implement periodic ease factor recalculation based on actual recall
- Use exponential backoff schedule based on publication date, not just SM-2 intervals

**Warning signs:**
- Users seeing the same posts repeatedly within days
- Average ease factor trending toward 1.3
- Review counts increasing over time despite correct recalls

**Phase to address:** Milestone 3 (Delivery — scheduled resurfacing)

---

### Pitfall 5: Clustering Semantic Drift

**What goes wrong:**
Topic clusters become meaningless over time as content vocabulary shifts. Posts about "AI" from 2023 cluster differently than 2026 posts, creating fragmented or overlapping topics.

**Why it happens:**
- Static embedding models don't adapt to language evolution
- New topics emerge that weren't in predefined set
- AI-suggested topics trained on old data don't match new content patterns

**How to avoid:**
- Implement hybrid approach as planned: predefined topics anchor clustering, AI suggests new topics
- Periodic re-clustering with updated models
- Store embeddings with posts; allow re-clustering without re-fetching
- Human-in-the-loop topic validation before assignment

**Warning signs:**
- "Uncategorized" cluster growing disproportionately
- Topic names that don't match post content
- Users manually reassigning posts frequently

**Phase to address:** Milestone 2 (Topic clustering)

---

### Pitfall 6: SQLite Foreign Key Constraint Violations

**What goes wrong:**
Orphaned records, inconsistent data, and cascade failures. Posts reference non-existent authors, topics reference deleted posts, queries return unexpected results.

**Why it happens:**
SQLite **disables foreign key enforcement by default** for backward compatibility. Many developers create FK constraints but never enable them, assuming they work like PostgreSQL.

**How to avoid:**
```python
# Enable FK enforcement on EVERY connection
conn = sqlite3.connect('bookmarks.db')
conn.execute("PRAGMA foreign_keys = ON")  # CRITICAL
```

**Warning signs:**
- Database queries returning orphaned records
- DELETE operations succeeding when they should fail
- Integrity errors appearing only in production at scale

**Phase to address:** Milestone 1 (SQLite schema setup)

---

## Critical Pitfalls (Milestone v1.1: Web App + Cast)

### Pitfall 7: SQLite Thread Safety with FastAPI

**What goes wrong:**
`sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread.`

FastAPI runs `def` endpoints in a threadpool. SQLite connections created in one thread cannot be used in another. The existing CLI code uses a single connection pattern that breaks under concurrent web requests.

**Why it happens:**
SQLite's default `check_same_thread=True` enforces thread safety at the connection level. CLI apps work fine with a single connection. FastAPI's threadpool creates multiple threads for sync endpoints, and each thread gets its own connection pool slot. Without proper configuration, connections leak or cross-thread usage triggers errors.

**How to avoid:**
```python
# Option 1: Async with aiosqlite (RECOMMENDED)
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    "sqlite+aiosqlite:///./app.db",
    echo=False,
)

# Option 2: Sync with check_same_thread=False (acceptable for single-user)
from sqlalchemy import create_engine

engine = create_engine(
    "sqlite:///./app.db",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,  # Detect stale connections
)
```

**Warning signs:**
- Intermittent "database is locked" errors under load
- `ProgrammingError` about thread safety
- Memory growth from unclosed connections
- Requests hanging indefinitely

**Phase to address:** Phase 1 (Web Foundation) — Must be resolved before any web endpoints work reliably.

---

### Pitfall 8: Local HTTPS Required for Google Cast (Self-Signed Certs Don't Work)

**What goes wrong:**
Chromecast/Google Cast devices reject self-signed SSL certificates. The Cast SDK requires HTTPS for production receiver apps, and browsers have deprecated the Presentation API on insecure origins.

**Why it happens:**
Google Cast security model requires certificates from trusted Certificate Authorities. Self-signed certificates fail because the Cast device has no way to validate them. During development you can use HTTP, but production publishing requires a real CA-signed certificate.

**How to avoid:**
1. **Development:** Use HTTP (acceptable for local development)
2. **Local HTTPS testing:** Use `mkcert` to create locally-trusted certificates:

```bash
# Install mkcert
brew install mkcert nss  # macOS

# Create and trust local CA
mkcert -install

# Generate certificate for localhost
mkcert localhost 127.0.0.1 ::1

# Creates: localhost.pem and localhost-key.pem
```

3. **Production:** Use Let's Encrypt or Cloudflare for free trusted certificates

**For this project (local-only deployment):**
- Use mkcert for HTTPS during development
- Document that users must run `mkcert -install` before casting
- Consider HTTP fallback for users who can't set up HTTPS

**Warning signs:**
- Cast button appears but devices don't show
- "Certificate invalid" errors in Cast SDK
- Presentation API returns `NotSupportedError`

**Phase to address:** Phase 2 (Cast Integration) — HTTPS must work before Cast can function.

---

### Pitfall 9: Token Storage in localStorage (XSS Vulnerable)

**What goes wrong:**
Storing OAuth access tokens in `localStorage` or `sessionStorage` exposes them to any JavaScript running on the page, including compromised third-party scripts.

**Why it happens:**
It's the easiest way to persist tokens between page reloads. Many tutorials show this pattern. But if any script on the page is compromised (supply chain attack, XSS vulnerability), tokens are immediately stolen.

**How to avoid:**
| Token Type | Storage Method | Why |
|------------|----------------|-----|
| Access token | Memory (JS variable) | Lost on refresh, but not accessible to XSS |
| Refresh token | HttpOnly SameSite=Strict cookie | Backend sets it, JavaScript can't read it |
| PKCE code_verifier | Memory only | Never persist; generated fresh each flow |

**For this project:**
- The CLI already stores tokens securely (file with 0600 permissions or OS keyring)
- Web app should read from same secure storage via FastAPI endpoint
- Web app should NOT expose raw tokens to frontend JavaScript

```python
# Instead of returning tokens to frontend:
@app.get("/auth/status")
async def auth_status(user: User = Depends(get_current_user)):
    return {"authenticated": True, "username": user.username}

# Token refresh happens server-side, transparent to frontend
```

**Warning signs:**
- Tokens visible in browser DevTools Application > Local Storage
- Frontend code accessing `localStorage.getItem('access_token')`
- No HttpOnly cookies being set by auth endpoints

**Phase to address:** Phase 1 (Web Foundation) — Authentication pattern must be correct from the start.

---

### Pitfall 10: Blocking the Event Loop with Sync Operations

**What goes wrong:**
FastAPI is async, but using `async def` with synchronous SQLite operations blocks the entire event loop. All requests hang while one request waits for the database.

**Why it happens:**
`async def` doesn't make sync code async. It just tells FastAPI "this function might use await." If you do `db.query()` inside `async def`, it blocks the event loop because there's no `await` to yield control.

**How to avoid:**
```python
# WRONG - Blocks event loop
@app.get("/posts")
async def get_posts():
    posts = db.query(Post).all()  # BLOCKS!
    return posts

# OPTION 1: Use async driver (aiosqlite) - RECOMMENDED
@app.get("/posts")
async def get_posts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post))
    return result.scalars().all()

# OPTION 2: Use sync endpoint (runs in threadpool)
@app.get("/posts")
def get_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).all()
    return posts
```

**Rule of thumb:**
- Use `async def` + `await` for async database drivers
- Use `def` (sync) for sync database operations — FastAPI runs these in a threadpool

**Warning signs:**
- API response times spike under minimal concurrent load
- One slow request blocks all other requests
- CPU idle but requests timing out

**Phase to address:** Phase 1 (Web Foundation) — Must choose async vs sync approach before building endpoints.

---

### Pitfall 11: CLI and Web Sharing Database Without WAL Mode

**What goes wrong:**
`sqlite3.OperationalError: database is locked` when CLI tries to sync while web server is running.

**Why it happens:**
SQLite's default journal mode allows only one writer. If the web server holds a read lock, CLI sync can't write. If CLI is syncing, web requests block.

**How to avoid:**
```python
# Enable WAL mode (already in project, but verify)
import sqlite3

conn = sqlite3.connect("bookmarks.db")
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")  # Wait up to 5s for locks
```

**WAL mode benefits:**
- Readers don't block writers
- Writers don't block readers
- Multiple readers can coexist
- Still only one writer at a time

**Warning signs:**
- "database is locked" errors when running CLI commands while web server active
- Web requests hang during CLI sync
- CLI sync fails when web server running

**Phase to address:** Phase 1 (Web Foundation) — Must verify WAL mode is properly enabled before web app runs.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip rate limit handling | Faster initial implementation | Data loss during sync, API bans | Never — must have from day one |
| Use app-only auth | Simpler OAuth flow | Cannot access bookmarks endpoint at all | Never — wrong auth type |
| Store embeddings without metadata | Faster writes | Cannot re-cluster without re-fetching | Never — include source model metadata |
| Skip pagination state persistence | Simpler code | Cannot resume after interruption | Never — essential for reliable sync |
| Use plain text clustering | No ML dependencies | Poor topic quality, semantic loss | MVP only — replace before production |
| Store BLOBs in SQLite (images) | Single-file simplicity | Database bloat, slow queries | Never — store paths only |
| Store tokens in localStorage | Easy to implement, persists across reloads | XSS vulnerability, tokens stolen if any script compromised | Never |
| Use BackgroundTasks for sync | Quick async-looking code | Blocks event loop, reduces throughput | Only for sub-100ms operations |
| Skip HTTPS for local dev | Faster setup, no certificates | Cast won't work, browser blocks features | Development only (not for Cast testing) |
| Use single Uvicorn worker | Simpler deployment | Single-threaded, no concurrency | CLI-only, never for web app |
| Return raw token to frontend | Simpler auth flow | Security exposure, XSS vulnerable | Never |
| Skip connection pool config | Default settings work in dev | Connection exhaustion under load, timeouts | Prototype only |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| X API bookmarks | Using Bearer Token (app-only) auth | Use OAuth 2.0 User Context with PKCE |
| X API bookmarks | Assuming all bookmarks retrievable | Only 800 most recent available via API |
| X API pagination | Using `since_id` like pagination tokens | `since_id` for new content, `next_token` for pages |
| X API rate limits | Checking after error | Monitor `x-rate-limit-remaining` headers proactively |
| OAuth 2.0 PKCE | Using "plain" challenge method | Always use S256 (SHA-256) |
| OAuth 2.0 PKCE | Storing code_verifier in localStorage | Store temporarily, clear after token exchange |
| tweepy library | Using `OAuth2AppHandler` for bookmarks | Use `OAuth2UserHandler` with PKCE flow |
| Embedding APIs | Not tracking embedding model version | Store model name/version with embeddings |
| Google Cast SDK | Self-hosting `cast_receiver_framework.js` | Always use Google-hosted SDK via gstatic |
| Google Cast | Using `contentId` for everything | Use `entity` for identifiers, `contentUrl` for media URLs |
| Google Cast | Setting `maxInactivity` to high values for debugging | Remove debug settings before production; use defaults |
| Google Cast | Assuming iOS Chrome supports casting | iOS Chrome does not support Cast; handle gracefully |
| OAuth PKCE (shared) | Same localStorage key for multiple apps | Use prefixed keys (`myapp_pkce_verifier`) to avoid collisions |
| SQLite + FastAPI | Forgetting `check_same_thread=False` | Required when using sync SQLite with FastAPI |
| SQLite + FastAPI | Using default pool settings | Configure `pool_pre_ping=True`, set pool timeout |
| Local HTTPS | Using self-signed certificates | Use mkcert for local development, Let's Encrypt for production |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No SQLite WAL mode | Database locked errors under concurrent reads | `PRAGMA journal_mode=WAL` | Multiple processes reading |
| `fetchall()` on large result sets | Memory exhaustion, slow queries | Iterate cursor, use generators | 100+ posts per query |
| No embedding cache | Re-embedding same text repeatedly | Cache embeddings keyed by text hash | Any re-processing |
| Individual SQL inserts | 50x slower bulk operations | Use `executemany()` for bulk | 10+ inserts per operation |
| Missing indexes on queries | Slow searches, topic lookups | Index `WHERE`, `JOIN`, `ORDER BY` columns | 500+ posts stored |
| Clustering without dimensionality reduction | Curse of dimensionality | Use PCA/t-SNE on high-dim embeddings | Depends on embedding size |
| N+1 queries | Database CPU spikes, slow page loads | Use eager loading (`selectinload`) | 10+ concurrent users |
| Single Uvicorn worker | Requests queue, latency spikes | Use Gunicorn with multiple workers: `(2 x CPU) + 1` | Any concurrent load |
| No connection pool limits | "Too many connections" errors | Configure `pool_size`, `max_overflow`, `pool_timeout` | Depends on SQLite limits |
| Sync DB in async endpoints | Event loop blocked, all requests hang | Use async drivers OR use sync endpoints | First slow query |
| Large JSON in responses | Memory spikes, slow serialization | Paginate, stream responses, use `response_model` | 1000+ records per response |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing OAuth tokens in plaintext files | Token theft enables account takeover | Use system keyring (keyring library) or encrypted storage |
| OAuth tokens without expiration handling | Compromised tokens valid indefinitely | Implement refresh token flow, validate expiration |
| SQLite database file with default permissions | Other users can read bookmarks | `chmod 0o600` on database file |
| Using "plain" PKCE challenge method | Interceptable authorization codes | Always use S256 challenge method |
| Logging X API responses with tokens | Tokens in log files, breach risk | Filter sensitive fields from logs |
| Long-lived access tokens | Extended exposure window if compromised | Use short-lived tokens with refresh |
| Tokens in localStorage | XSS steals tokens, full account compromise | Store in memory (access) + HttpOnly cookie (refresh) |
| Exposed /docs in production | API schema visible to attackers | Disable in production: `docs_url=None if production else "/docs"` |
| CORS allow_origins=["*"] | Any origin can call API | Restrict to actual frontend origin |
| No rate limiting on auth endpoints | Brute force attacks | Add rate limiting on `/auth/*` endpoints |
| PKCE code_verifier in URL/state | Intercepted verifier defeats PKCE | Store in memory only, never persist or transmit |
| Refresh token in localStorage | Long-lived token stolen | HttpOnly SameSite=Strict cookie, server-set |
| Debug settings in production (Cast) | App doesn't close properly | Remove `maxInactivity` overrides before production |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| "800 bookmark limit" surprise | Users expect full history | Clear messaging at setup, incremental sync emphasis |
| Overwhelming review schedule | Users abandon the app | Implement daily review caps, review scheduling preferences |
| Unexplainable topic assignments | Users distrust AI clustering | Show confidence scores, allow manual topic assignment |
| No offline capability | App useless without internet | Cache everything needed for review locally |
| "Ghost" posts in reviews | Posts deleted on X still surface | Track post deletion status, filter from reviews |
| No feedback mechanism for topics | No way to improve clustering over time | Allow topic corrections, use as training signal |
| Cast button appears but no devices | Frustration, appears broken | Show "No devices found" message, verify HTTPS |
| Auth expires mid-session | Sudden logout, lost work | Silent token refresh, session persistence |
| Long sync with no progress | User thinks app is frozen | Progress bar, status updates |
| Posts don't update after CLI sync | Stale data shown, confusion | Polling or WebSocket for updates |
| Error messages like "Error occurred" | User can't troubleshoot | Specific error: "Rate limited by X API, wait 15 min" |
| Mobile layout on TV | Text too small, unusable | Dedicated Cast receiver with TV layout |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **OAuth PKCE Flow:** Often missing refresh token handling — verify complete flow with token refresh
- [ ] **Rate Limit Handling:** Often implemented only for errors — verify proactive header monitoring
- [ ] **Foreign Keys:** Often defined but not enforced — verify `PRAGMA foreign_keys = ON` is called
- [ ] **Pagination Resume:** Often tested only for happy path — verify resume after interruption
- [ ] **Ease Factor Bounds:** Often missing minimum enforcement — verify `EF < 1.3` check
- [ ] **Topic Confidence:** Often showing only assignments — verify confidence scores exposed
- [ ] **Token Expiration:** Often only checking at startup — verify expiration checked before each API call
- [ ] **Cast Integration:** Works on HTTPS but not HTTP — verify Cast SDK loads, receiver app launches, certificate is trusted
- [ ] **Token Refresh:** Appears to work but fails after first expiration — test refresh flow, verify new tokens stored correctly
- [ ] **Database Connection:** Works in dev but leaks connections — verify `pool_pre_ping`, connection cleanup in finally blocks
- [ ] **WAL Mode:** Set but not persisted across connections — verify `PRAGMA journal_mode=WAL` returns "wal" on new connections
- [ ] **Authentication Sharing:** CLI works but web shows unauthenticated — verify web reads from same token storage
- [ ] **Error Handling:** Returns 500 for all errors — implement proper HTTP status codes, error response format
- [ ] **CORS:** Works locally but fails from different port — configure `allow_origins` to include frontend URL
- [ ] **Health Check:** Returns `{"status": "ok"}` without checking DB — implement real dependency health check

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong OAuth type | LOW | Re-authenticate with correct flow (PKCE), tokens invalidate |
| Rate limit hit | LOW | Wait for reset, resume from stored `next_token` |
| Missing FK enforcement | MEDIUM | Add constraints, run integrity check script, clean orphaned data |
| Ease hell in SM-2 | MEDIUM | Bulk recalculate ease factors, reset affected items to learning phase |
| Embedding model deprecated | HIGH | Re-embed all stored content with new model, re-cluster |
| 800 limit discovered late | HIGH | No recovery for lost bookmarks — document clearly upfront |
| Semantic drift in clusters | MEDIUM | Re-cluster with updated model, manual review of topic changes |
| SQLite thread errors | LOW | Add `check_same_thread=False` or migrate to aiosqlite |
| Database locked errors | LOW | Verify WAL mode, add `busy_timeout` pragma |
| Token storage refactor | MEDIUM | Move tokens to server-side storage, implement refresh proxy |
| HTTPS refactor | LOW | Install mkcert, regenerate certificates, update config |
| Event loop blocking | MEDIUM | Identify sync operations, convert to async or move to sync endpoints |
| Cast not connecting | LOW | Verify HTTPS, check certificate trust, ensure Google-hosted SDK |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

### Milestone 1 (CLI + SQLite)

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| X API Auth (403) | Milestone 1 | Test bookmarks endpoint returns data, not 403 |
| 800 Bookmark Limit | Milestone 1 | Document limitation, implement incremental sync |
| Rate Limit Handling | Milestone 1 | Test sync resume after hitting rate limit |
| Foreign Keys | Milestone 1 | Integrity test: insert orphan record should fail |
| Spaced Repetition Ease Hell | Milestone 3 | Test: repeated correct reviews increase intervals |
| Clustering Drift | Milestone 2 | Test: re-cluster after model version change |
| SQLite WAL Mode | Milestone 1 | Verify `PRAGMA journal_mode` returns `wal` |
| Token Storage Security | Milestone 1 | Audit: tokens not in plaintext files |
| Pagination State Persistence | Milestone 1 | Test: interrupt sync, resume from last position |
| Embedding Model Versioning | Milestone 2 | Test: embeddings include model metadata |

### Milestone v1.1 (Web App + Cast)

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SQLite thread safety | Phase 1 (Web Foundation) | Run concurrent requests test, verify no thread errors |
| Local HTTPS setup | Phase 1 (Web Foundation) | Access app via HTTPS, verify Cast SDK loads |
| Token storage security | Phase 1 (Web Foundation) | Audit token flow, verify no localStorage access |
| Event loop blocking | Phase 1 (Web Foundation) | Load test with concurrent requests |
| WAL mode verification | Phase 1 (Web Foundation) | Run CLI sync while web server active |
| Cast SDK integration | Phase 2 (Cast Integration) | Verify receiver app launches, media plays |
| CORS configuration | Phase 1 (Web Foundation) | Test from frontend origin, verify headers |
| Error handling | Phase 1 (Web Foundation) | Trigger various error conditions, check response codes |

---

## Sources

### Milestone 1 Sources (X API, Spaced Repetition, SQLite)

- [X API Rate Limits 2026](https://api.sorsa.io/blog/twitter-api-rate-limits-2026)
- [X API Error 226 Anti-Automation](https://api.sorsa.io/blog/twitter-this-request-looks-like-automated)
- [X Developer Platform - Pagination](https://developer.x.com/en/docs/twitter-api/pagination)
- [X API Rate Limits](https://docs.x.com/x-api/fundamentals/rate-limits)
- [Twitter API Bookmarks Introduction](https://developer.x.com/en/docs/x-api/tweets/bookmarks/introduction)
- [tweepy Bookmarks Auth Issue #2200](https://github.com/tweepy/tweepy/issues/2200)
- [Stack Overflow: How to get more bookmarks with Twitter API v2](https://stackoverflow.com/questions/75394990/how-to-get-more-and-more-bookmarks-with-twitter-api-v2)
- [SuperMemo Algorithm FAQ](https://supermemopedia.com/wiki/SuperMemo_Algorithm_FAQ)
- [SM-2 Algorithm Issues](https://github.com/thyagoluciano/sm2/issues/5)
- [Better Spaced Repetition Algorithm SM2+](http://www.blueraja.com/blog/477/a-better-spaced-repetition-learning-algorithm-sm2)
- [Common SQLite Mistakes](https://cmsqlite.net/common-sqlite-mistakes-developers-make-and-how-to-avoid-them/)
- [SQLite Quirks and Gotchas](https://sqlite.org/quirks.html)
- [OAuth2 PKCE Patterns & Anti-Patterns](https://www.sachith.co.uk/oauth2-oidc-and-pkce-done-right-patterns-anti-patterns-practical-guide-mar-18-2026/)
- [7 OAuth 2.0 Security Pitfalls](https://duendesoftware.com/learn/7-common-security-pitfalls-oauth-2-0-implementations)
- [Text Clustering Techniques Review](https://link.springer.com/article/10.1007/s41060-024-00540-x)
- [Meilisearch Text Clustering Blog](https://www.meilisearch.com/blog/text-clustering)
- [Retry Logic Exponential Backoff](https://hackernoon.com/why-your-retry-logic-is-taking-down-your-system-and-how-to-fix-it)
- [Retry with Exponential Backoff and Jitter](https://knowledgelib.io/software/patterns/retry-exponential-backoff/2026)

### Milestone v1.1 Sources (FastAPI, Google Cast, Local HTTPS)

- [FastAPI Best Practices 2026](https://pratikpathak.com/fastapi-best-practices-building-production-ready-python-apis-in-2026/) — MEDIUM confidence (community blog)
- [FastAPI Production Patterns 2025](https://orchestrator.dev/blog/2025-1-30-fastapi-production-patterns/) — MEDIUM confidence (community blog)
- [FastAPI Under Load: 5 Production Issues](https://dev.to/zestminds_technologies_c1/fastapi-under-load-5-production-issues-most-teams-discover-too-late-4m39) — MEDIUM confidence (community blog)
- [Google Cast Web Sender Integration](https://developers.google.com/cast/docs/web_sender/integrate) — HIGH confidence (official Google docs)
- [Google Cast Web Receiver Documentation](https://developers.google.com/cast/docs/web_receiver/basic) — HIGH confidence (official Google docs)
- [Google Cast Error Codes](https://developers.google.com/cast/docs/web_receiver/error_codes) — HIGH confidence (official Google docs)
- [Google Cast Registration](https://developers.google.com/cast/docs/registration) — HIGH confidence (official Google docs)
- [Chromecast self-signed SSL certificate (Stack Overflow)](https://stackoverflow.com/questions/21959435/chromecast-self-signed-ssl-certificate) — MEDIUM confidence (community Q&A)
- [SQLite thread safety (FastAPI GitHub Issue)](https://github.com/mfreeborn/fastapi-sqlalchemy/issues/45) — HIGH confidence (issue documentation)
- [SQLite database locked (Stack Overflow)](https://stackoverflow.com/questions/79707043/how-to-make-concurrent-writes-in-sqlite-with-fastapi-sqlalchemy-without-datab) — MEDIUM confidence (community Q&A)
- [FastAPI deadlock with SQLite (GitHub Issue)](https://github.com/fastapi/fastapi/issues/3205) — HIGH confidence (issue documentation)
- [Best Practices for Storing Access Tokens](https://curity.medium.com/best-practices-for-storing-access-tokens-in-the-browser-6b3d515d9814) — MEDIUM confidence (security blog)
- [PKCE vs Device Flow for CLI Auth (WorkOS)](https://workos.com/blog/pkce-vs-device-flow-cli-auth) — HIGH confidence (auth provider blog)
- [OIDC CLI Authentication](https://kharkevich.org/2024/11/30/oidc-cli-auth/) — MEDIUM confidence (personal blog)
- [mkcert GitHub Repository](https://github.com/Filosottile/mkcert) — HIGH confidence (official project)
- [Use HTTPS for local development (web.dev)](https://web.dev/articles/how-to-use-local-https) — HIGH confidence (Google web.dev)

---

*Pitfalls research for: X Bookmarked Posts Organizer*
*Researched: 2026-04-18 (Milestone 1), 2026-05-17 (Milestone v1.1)*