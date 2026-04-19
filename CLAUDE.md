<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:project-start source:PROJECT.md -->
## Project

**X Bookmarked Posts Organizer**

A Python CLI application that fetches bookmarked posts from X (Twitter) using the X Developer API, stores them in SQLite as persistent storage and cache, then organizes them into topics for scheduled resurfacing. The resurfacing follows an exponential backoff schedule based on time since publication, keeping valuable content fresh in memory.

**Core Value:** Resurface bookmarked posts on a spaced-repetition schedule so they stay fresh in mind — content you saved because it mattered, delivered back to you before you forget it.

### Constraints

- **Tech Stack:** Python (matching existing project pattern)
- **API Access:** X Developer API credentials available (OAuth 2.0 PKCE)
- **Data Model:** Posts stored with text, author, images, links, media; no thread context required
- **Output:** Samsung Smart TV app (primary), web app with casting (fallback)
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
# Core CLI
# X API integration
# Database (stdlib, but SQLite best practices)
# No install needed - use sqlite3 from standard library
# Scheduling
# Configuration
# Topic clustering (Milestone 2)
# Development
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
- Reuse auth pattern from x-api project (OAuth 2.0 PKCE with local callback server)
- Pin versions matching existing project for consistency
- Copy `XAuth`, `get_auth`, `verify_credentials` pattern
- Start with Typer + sqlite3 directly (no ORM)
- Add SQLAlchemy 2.0 later if relationships become complex
- Use raw SQL for queries, ORM is premature for 100-500 records
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
## Project Structure Pattern
## pyproject.toml Template
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
<!-- GSD:stack-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
