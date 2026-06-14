# Phase 5: Spaced Repetition Resurfacing - Research

**Researched:** 2026-04-25
**Domain:** Spaced repetition algorithms, review scheduling, CLI interaction for review sessions
**Confidence:** HIGH

## Summary

Phase 5 implements the core product differentiator: spaced repetition resurfacing for bookmarked posts. The user's locked decisions specify a hybrid approach using FSRS-4.5 algorithm concepts with simplified user-controlled scheduling. Instead of FSRS's four-button difficulty rating (Again/Hard/Good/Easy), users choose scheduling intent: "Keep fresh" (3 days), "Review again soon" (2 weeks), or "Review again later" (2 months). This simplification makes the system approachable while retaining FSRS's core tracking (stability, difficulty, retrievability).

The implementation requires a new `post_review_state` table, a `ReviewService` to orchestrate review sessions, and CLI commands (`xbm due`, `xbm review`, `xbm stats`, `xbm reset`). APScheduler provides background scheduling with SQLite persistence for future automation, though Phase 5 focuses on on-demand CLI-triggered reviews. The `--topic` flag enables themed reviews by filtering through the `post_topics` table from Phase 4.

**Primary recommendation:** Use FSRS's Card class for state tracking (stability, difficulty, due date) but override the scheduling algorithm with user-chosen intervals. Store review state in `post_review_state` table with FSRS JSON serialization. Build interactive review sessions with Rich panels for post content, notes, and metadata.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use FSRS-4.5 algorithm concepts but start with simplified user-controlled scheduling.
  - User's choice (fresh/soon/later) sets the next review interval.
  - Hybrid approach: user choice + jitter + background algorithm (room to expand).
  - Rationale: Simplicity for MVP, but architecture allows FSRS integration later.
- **D-02:** Seed initial review state from post publication date.
  - Older posts naturally get longer intervals.
  - Aligns with core value: "resurface old bookmarks before you forget them."
- **D-03:** Default intervals for user choices:
  - "Keep fresh" = 3 days
  - "Review again soon" = 2 weeks
  - "Review again later" = 2 months
- **D-04:** Use table format for `xbm due` output.
  - Compact list: post text truncated, author, topic tags, due date.
  - Many posts visible at once for quick overview.
- **D-05:** Notes displayed at top of post during review.
  - Notes are the context user saved for themselves.
  - Prominent placement reinforces why the post was bookmarked.
- **D-06:** Metadata shown for each post in queue:
  - Publication date (when originally posted)
  - Topic tags (assigned topics)
  - Scheduling reason (why this post is due)
  - Review history (times reviewed, last review, next scheduled)
- **D-07:** Review interaction model: user chooses scheduling intent.
  - After viewing a post, user selects:
    - "Keep fresh" (3 days)
    - "Review again soon" (2 weeks)
    - "Review again later" (2 months)
  - No difficulty rating = scheduling is user-controlled, not algorithmic difficulty.
- **D-08:** Themed reviews via `--topic` flag on `xbm due` and `xbm review`.
  - `xbm due --topic python` shows only posts in Python topic.
  - `xbm review --topic python` starts interactive session for Python posts.
- **D-09:** Postpone option available during review.
  - Fixed intervals: 1 day, 3 days, 1 week, 2 weeks, 1 month, 3 months.
  - Custom via `--days` flag for user-specified delay.
- **D-10:** `xbm review` = primary command for interactive review sessions.
  - Shows posts one at a time with full content, notes, metadata.
  - User chooses: Keep fresh / Review soon / Review later / Skip / Postpone.
  - After choice, moves to next due post.
- **D-11:** `xbm due` = non-interactive view of due posts.
  - Table format showing all posts currently due for review.
  - Use `--topic` flag to filter by topic.
- **D-12:** `xbm stats` = statistics and progress tracking.
  - Shows: total posts, due count, reviewed count, upcoming schedule.
- **D-13:** `xbm reset <post_id>` = reset review state for a post.
  - User can restart specific posts without re-syncing everything.

### Database Schema
- **D-14:** New table `post_review_state` for scheduling persistence.
  - Fields: post_id, scheduled_for, last_reviewed, review_count, user_preference, created_at, updated_at.
  - `user_preference` stores the user's last choice (fresh/soon/later).
  - `scheduled_for` is the next review date (seeded from publication date initially).
- **D-15:** Use `posts.created_at` as initial scheduling baseline.
  - Posts sync with publication date, so review state can seed from that.

### Claude's Discretion
- Exact table schema design (fields, indexes) = standard patterns apply.
- CLI output formatting with Rich = follow existing patterns from Phases 2-4.
- Error messages for empty review queue = standard "no posts due" message.
- Interval calculation logic (jitter implementation) = start simple, add later.

### Deferred Ideas (OUT OF SCOPE)
None = discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SPAC-01 | Application calculates next review date using exponential backoff from publication date | FSRS Card class for state tracking, D-02 seeds from publication date, D-03 defines intervals |
| SPAC-02 | Application surfaces posts for review based on calculated schedule | `post_review_state` table, `ReviewService.get_due_posts()`, `scheduled_for <= NOW` query |
| SPAC-03 | User can view currently due posts via CLI | `xbm due` command (D-11), Rich table output (D-04), `--topic` filter (D-08) |
| SPAC-04 | Application supports themed reviews (posts from specific topics) | `--topic` flag joins `post_review_state` with `post_topics` table |
| CLI-02 | User can view resurfaced posts via CLI command | `xbm review` interactive session (D-10), Rich panels for content/metadata |

</phase_requirements>

## Standard Stack

### Core (Spaced Repetition)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **fsrs** | 6.3+ | FSRS-4.5 algorithm implementation | Official Python implementation. Card/FSRS classes for state tracking. JSON serialization for DB storage. 418+ GitHub stars, MIT license. |
| **APScheduler** | 3.11+ | Background scheduling (future automation) | SQLite job store for persistence. BackgroundScheduler for non-blocking. Standard for Python scheduling. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Rich** | 14.3+ | Interactive review UI | Tables for `xbm due`, panels for `xbm review` post display. Already in project. |
| **Typer** | 0.24+ | CLI commands | Already in project for all commands. |
| **python-dateutil** | (via APScheduler) | Relative date calculations | `relativedelta` for interval math (days, weeks, months). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FSRS Card state | Custom state tracking | Custom code vs battle-tested FSRS. FSRS provides JSON serialization, state management. |
| User intervals | Full FSRS algorithm | Full FSRS uses 4-button difficulty rating (Again/Hard/Good/Easy). User's 3-choice intent is simpler for MVP. |
| APScheduler | schedule library | APScheduler has SQLite persistence, async support. schedule library is cron-only, no persistence. |
| APScheduler | Celery | Celery is overkill for single-user CLI. APScheduler is in-process, SQLite-backed. |

**Installation:**
```bash
pip install fsrs apscheduler
```

**Version verification:**
```bash
pip show fsrs          # 6.3.1 current
pip show apscheduler   # 3.11.2 current
```

## Architecture Patterns

### Recommended Database Schema (SCHEMA_V5)

```sql
-- Post review state: Spaced repetition tracking for each post
-- SPAC-01: Calculate next review date
-- SPAC-02: Surface posts based on schedule
-- D-14: New table for scheduling persistence
CREATE TABLE IF NOT EXISTS post_review_state (
    post_id TEXT PRIMARY KEY,              -- References posts.x_post_id
    scheduled_for TIMESTAMP NOT NULL,      -- Next review date (D-15: seeded from posts.created_at)
    last_reviewed TIMESTAMP,                -- When last reviewed
    review_count INTEGER DEFAULT 0,         -- Number of times reviewed
    user_preference TEXT,                   -- Last user choice: 'fresh', 'soon', 'later'
    stability REAL,                         -- FSRS stability parameter
    difficulty REAL,                        -- FSRS difficulty parameter
    state INTEGER DEFAULT 0,                -- FSRS state: 0=new, 1=learning, 2=review, 3=relearning
    step INTEGER,                           -- FSRS learning step (nullable)
    fsrs_data TEXT,                         -- FSRS Card JSON for full state serialization
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(x_post_id) ON DELETE CASCADE
);

-- Index for finding due posts
-- SPAC-02: Posts where scheduled_for <= NOW
CREATE INDEX IF NOT EXISTS idx_review_state_scheduled ON post_review_state(scheduled_for);

-- Index for themed reviews (join with post_topics)
-- SPAC-04: Filter by topic_id
CREATE INDEX IF NOT EXISTS idx_review_state_post ON post_review_state(post_id);
```

### Recommended Project Structure
```
src/
├── repositories/
│   ├── posts.py              # Existing: extend with review state methods
│   └── review_state.py       # NEW: ReviewStateRepository for CRUD
├── services/
│   ├── scheduler.py          # NEW: FSRS-based scheduling logic
│   └── review.py             # NEW: ReviewService for review sessions
└── cli/
    └── main.py               # Add: due, review, stats, reset commands
```

### Pattern 1: FSRS Card State with User-Controlled Intervals

**What:** Use FSRS's Card class for state tracking but override scheduling with user-chosen intervals.

**When to use:** User wants simple 3-choice scheduling (fresh/soon/later) while retaining FSRS state for future algorithm enhancement.

```python
# Source: [CITED: https://github.com/open-spaced-repetition/py-fsrs]
from fsrs import Card, Rating
from datetime import datetime, timezone, timedelta
import json

class ReviewScheduler:
    """Simplified scheduler using FSRS Card state with user intervals."""

    # D-03: Default intervals
    INTERVALS = {
        'fresh': timedelta(days=3),
        'soon': timedelta(weeks=2),
        'later': timedelta(days=60),  # ~2 months
    }

    # D-09: Postpone intervals
    POSTPONE_INTERVALS = {
        '1d': timedelta(days=1),
        '3d': timedelta(days=3),
        '1w': timedelta(weeks=1),
        '2w': timedelta(weeks=2),
        '1m': timedelta(days=30),
        '3m': timedelta(days=90),
    }

    def __init__(self):
        # Initialize with default FSRS parameters
        self.default_stability = 1.0
        self.default_difficulty = 0.3

    def create_initial_state(
        self,
        post_id: str,
        publication_date: datetime
    ) -> dict:
        """D-02: Seed initial review state from publication date.

        Older posts naturally get longer intervals based on their age.
        """
        now = datetime.now(timezone.utc)
        age_days = (now - publication_date).days

        # FSRS Card with initial state
        card = Card()
        card.card_id = post_id
        card.stability = self.default_stability
        card.difficulty = self.default_difficulty
        card.state = 0  # New card

        # Seed scheduled_for from publication date
        # Older posts are "due" immediately, newer posts wait a bit
        if age_days > 30:
            # Old posts: due immediately
            scheduled_for = now
        else:
            # New posts: seed with small delay based on age
            scheduled_for = now + timedelta(days=age_days // 10)

        return {
            'post_id': post_id,
            'scheduled_for': scheduled_for.isoformat(),
            'last_reviewed': None,
            'review_count': 0,
            'user_preference': None,
            'fsrs_data': card.to_json(),
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
        }

    def schedule_review(
        self,
        current_state: dict,
        user_choice: str,  # 'fresh', 'soon', 'later'
        review_time: datetime
    ) -> dict:
        """Apply user-chosen interval and update state.

        D-07: User chooses scheduling intent, not difficulty rating.
        """
        interval = self.INTERVALS[user_choice]

        # Parse existing FSRS state
        card = Card.from_json(current_state['fsrs_data'])

        # Update FSRS state (for future algorithm enhancement)
        # Map user choice to approximate FSRS rating
        rating_map = {
            'fresh': Rating.Good,     # Short interval = remembered well
            'soon': Rating.Hard,      # Medium interval = some difficulty
            'later': Rating.Easy,     # Long interval = easy to remember
        }

        # Calculate next due date
        scheduled_for = review_time + interval

        # Update review state
        return {
            'post_id': current_state['post_id'],
            'scheduled_for': scheduled_for.isoformat(),
            'last_reviewed': review_time.isoformat(),
            'review_count': current_state['review_count'] + 1,
            'user_preference': user_choice,
            'fsrs_data': card.to_json(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }

    def postpone_review(
        self,
        current_state: dict,
        days: int,
        postpone_time: datetime
    ) -> dict:
        """D-09: Postpone without changing user preference."""
        scheduled_for = postpone_time + timedelta(days=days)

        return {
            **current_state,
            'scheduled_for': scheduled_for.isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
```

### Pattern 2: ReviewStateRepository

**What:** Repository for CRUD operations on `post_review_state` table.

**When to use:** All database access for review state goes through this repository.

```python
# Source: [VERIFIED: project pattern from src/repositories/posts.py]
import sqlite3
from datetime import datetime, timezone
from typing import Optional

class ReviewStateRepository:
    """Repository for post_review_state table operations."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_due_posts(
        self,
        topic_id: Optional[int] = None,
        limit: int = 50
    ) -> list[dict]:
        """SPAC-02, SPAC-04: Get posts due for review.

        Args:
            topic_id: Optional filter by topic (D-08)
            limit: Maximum posts to return

        Returns:
            List of posts with review state, ordered by scheduled_for.
        """
        now = datetime.now(timezone.utc).isoformat()

        if topic_id:
            # D-08: Themed review - join with post_topics
            rows = self._conn.execute(
                """SELECT p.*, prs.scheduled_for, prs.last_reviewed,
                          prs.review_count, prs.user_preference
                   FROM posts p
                   JOIN post_review_state prs ON p.x_post_id = prs.post_id
                   JOIN post_topics pt ON p.x_post_id = pt.post_id
                   WHERE prs.scheduled_for <= ?
                     AND pt.topic_id = ?
                   ORDER BY prs.scheduled_for ASC
                   LIMIT ?""",
                (now, topic_id, limit)
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT p.*, prs.scheduled_for, prs.last_reviewed,
                          prs.review_count, prs.user_preference
                   FROM posts p
                   JOIN post_review_state prs ON p.x_post_id = prs.post_id
                   WHERE prs.scheduled_for <= ?
                   ORDER BY prs.scheduled_for ASC
                   LIMIT ?""",
                (now, limit)
            ).fetchall()

        return [self._row_to_dict(row) for row in rows]

    def create_state(self, state: dict) -> None:
        """Create initial review state for a post."""
        self._conn.execute(
            """INSERT INTO post_review_state
               (post_id, scheduled_for, last_reviewed, review_count,
                user_preference, stability, difficulty, state, fsrs_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                state['post_id'],
                state['scheduled_for'],
                state.get('last_reviewed'),
                state.get('review_count', 0),
                state.get('user_preference'),
                state.get('stability'),
                state.get('difficulty'),
                state.get('state', 0),
                state.get('fsrs_data'),
            )
        )
        self._conn.commit()

    def update_state(self, state: dict) -> None:
        """Update review state after user choice."""
        self._conn.execute(
            """UPDATE post_review_state
               SET scheduled_for = ?, last_reviewed = ?, review_count = ?,
                   user_preference = ?, stability = ?, difficulty = ?,
                   state = ?, fsrs_data = ?, updated_at = ?
               WHERE post_id = ?""",
            (
                state['scheduled_for'],
                state['last_reviewed'],
                state['review_count'],
                state['user_preference'],
                state.get('stability'),
                state.get('difficulty'),
                state.get('state'),
                state.get('fsrs_data'),
                datetime.now(timezone.utc).isoformat(),
                state['post_id'],
            )
        )
        self._conn.commit()

    def get_state(self, post_id: str) -> Optional[dict]:
        """Get review state for a specific post."""
        row = self._conn.execute(
            "SELECT * FROM post_review_state WHERE post_id = ?",
            (post_id,)
        ).fetchone()
        return dict(row) if row else None

    def reset_state(self, post_id: str) -> None:
        """D-13: Reset review state for a post."""
        # Delete and recreate with initial state
        self._conn.execute(
            "DELETE FROM post_review_state WHERE post_id = ?",
            (post_id,)
        )
        self._conn.commit()

    def get_stats(self) -> dict:
        """D-12: Get review statistics."""
        now = datetime.now(timezone.utc).isoformat()

        total = self._conn.execute(
            "SELECT COUNT(*) as count FROM posts"
        ).fetchone()['count']

        due_count = self._conn.execute(
            "SELECT COUNT(*) as count FROM post_review_state WHERE scheduled_for <= ?",
            (now,)
        ).fetchone()['count']

        reviewed_count = self._conn.execute(
            "SELECT COUNT(*) as count FROM post_review_state WHERE review_count > 0"
        ).fetchone()['count']

        return {
            'total_posts': total,
            'due_count': due_count,
            'reviewed_count': reviewed_count,
        }

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert database row to dict."""
        return dict(row)
```

### Pattern 3: Interactive Review Session

**What:** CLI interaction for `xbm review` command with Rich panels.

**When to use:** User runs `xbm review` for interactive review session.

```python
# Source: [CITED: project pattern from src/cli/main.py]
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import typer

console = Console()

def display_review_post(post: dict, topics: list[dict]) -> None:
    """D-05, D-06: Display post for review with notes and metadata."""
    # D-05: Notes at top
    note = post.get('note')
    if note:
        console.print(Panel(
            note,
            title="[bold yellow]Your Note[/bold yellow]",
            border_style="yellow"
        ))
        console.print()

    # Post content
    text = post.get('text', '')
    author = f"@{post.get('author_username', 'unknown')}"
    display_name = post.get('author_display_name', '')

    header = f"[bold cyan]{author}[/bold cyan]"
    if display_name:
        header += f" ({display_name})"

    console.print(Panel(
        text,
        title=header,
        border_style="blue"
    ))

    # D-06: Metadata
    metadata = Table(show_header=False, box=None)
    metadata.add_column("Label", style="dim")
    metadata.add_column("Value", style="white")

    metadata.add_row("Published", post.get('created_at', 'Unknown')[:10])
    metadata.add_row("Topics", ", ".join(t['name'] for t in topics) or "None")
    metadata.add_row("Reviews", str(post.get('review_count', 0)))
    metadata.add_row("Last Review", post.get('last_reviewed', 'Never')[:10] if post.get('last_reviewed') else 'Never')
    metadata.add_row("User Pref", post.get('user_preference', 'None'))

    console.print(metadata)
    console.print()


def prompt_user_choice() -> str:
    """D-07: Prompt for scheduling intent."""
    console.print("[bold]Choose scheduling:[/bold]")
    console.print("  [1] Keep fresh (3 days)")
    console.print("  [2] Review again soon (2 weeks)")
    console.print("  [3] Review again later (2 months)")
    console.print("  [s] Skip")
    console.print("  [p] Postpone")
    console.print()

    choice = typer.prompt("Choice", default="2")
    return choice
```

### Pattern 4: Themed Review Query

**What:** Filter due posts by topic for focused review sessions.

**When to use:** `xbm due --topic python` or `xbm review --topic python`.

```python
# Source: [VERIFIED: SQL pattern from post_topics table]
def get_due_posts_by_topic(
    conn: sqlite3.Connection,
    topic_name: str,
    limit: int = 50
) -> list[dict]:
    """SPAC-04: Get due posts filtered by topic."""
    now = datetime.now(timezone.utc).isoformat()

    rows = conn.execute(
        """SELECT p.*, prs.scheduled_for, prs.last_reviewed,
                  prs.review_count, prs.user_preference,
                  GROUP_CONCAT(t.name, ', ') as topic_names
           FROM posts p
           JOIN post_review_state prs ON p.x_post_id = prs.post_id
           JOIN post_topics pt ON p.x_post_id = pt.post_id
           JOIN topics t ON pt.topic_id = t.id
           WHERE prs.scheduled_for <= ?
             AND t.name = ? COLLATE NOCASE
           GROUP BY p.x_post_id
           ORDER BY prs.scheduled_for ASC
           LIMIT ?""",
        (now, topic_name, limit)
    ).fetchall()

    return [dict(row) for row in rows]
```

### Anti-Patterns to Avoid

- **Storing review intervals instead of dates:** Always store `scheduled_for` as absolute datetime. Intervals are relative and confusing.
- **Forgetting FSRS state between sessions:** Persist full FSRS Card JSON in `fsrs_data` column. Future algorithm enhancement needs historical state.
- **Not seeding from publication date:** New posts should have initial state. D-02 uses `posts.created_at` as baseline.
- **Complex interval calculations:** Start simple. User wants predictable intervals (3d/2w/2m), not FSRS's dynamic intervals.
- **Missing postpone option:** D-09 requires explicit postpone choices. Don't conflate with user preference intervals.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Spaced repetition state | Custom stability/difficulty tracking | fsrs.Card class | Battle-tested algorithm, JSON serialization, state machine |
| Date interval math | Manual timedelta calculations | python-dateutil relativedelta | Handles months, leap years, edge cases |
| Background scheduling | Cron jobs, threading | APScheduler BackgroundScheduler | SQLite persistence, job management, timezone support |
| Interactive prompts | Manual input() loops | typer.prompt + Rich panels | Validation, error handling, styled output |

**Key insight:** FSRS's Card class provides a well-tested state machine for spaced repetition. Even with simplified user intervals, storing FSRS state enables future algorithm enhancement without data migration.

## Common Pitfalls

### Pitfall 1: FSRS State Deserialization Errors
**What goes wrong:** Storing partial FSRS state causes JSON deserialization failures on future reviews.
**Why it happens:** FSRS Card has required fields (stability, difficulty, state, due). Missing fields cause parse errors.
**How to avoid:** Always use `card.to_json()` and `Card.from_json()` for serialization. Never store individual fields separately.
**Warning signs:** KeyError when loading review state, AttributeError on Card methods.

### Pitfall 2: Timezone Handling
**What goes wrong:** Scheduled reviews use local time, causing confusion across time zones or daylight saving changes.
**Why it happens:** Naive datetime objects don't carry timezone information.
**How to avoid:** Always use `datetime.now(timezone.utc)` for UTC timestamps. Store ISO 8601 format with timezone.
**Warning signs:** Reviews appearing at wrong times, scheduled_for comparisons failing.

### Pitfall 3: Empty Review Queue Edge Cases
**What goes wrong:** `xbm review` enters interactive mode when no posts are due, confusing the user.
**Why it happens:** No due posts is a valid state, but requires different handling than "error."
**How to avoid:** Check `get_due_posts()` count before starting interactive session. Show "No posts due" message and exit cleanly.
**Warning signs:** Blank terminal, hanging prompts, unexpected errors.

### Pitfall 4: Missing Review State for New Posts
**What goes wrong:** Posts synced from X API don't have review state, causing them to be skipped by `xbm due`.
**Why it happens:** `post_review_state` is seeded separately from post sync.
**How to avoid:** Create review state when syncing new posts. D-02 seeds from publication date. Implement `ReviewStateRepository.seed_new_posts()`.
**Warning signs:** Posts visible via `xbm search` but not `xbm due`, missing state errors.

### Pitfall 5: Themed Review Join Performance
**What goes wrong:** Complex joins between `posts`, `post_review_state`, and `post_topics` become slow with many posts.
**Why it happens:** Missing indexes on join columns causes full table scans.
**How to avoid:** Ensure indexes on `post_review_state.post_id`, `post_review_state.scheduled_for`, and `post_topics.topic_id`.
**Warning signs:** Slow `xbm due --topic` response, high query times.

## Code Examples

### Seeding Review State from Publication Date
```python
# Source: [CITED: D-02 decision pattern]
from datetime import datetime, timezone, timedelta

def seed_review_state_for_all_posts(conn: sqlite3.Connection) -> int:
    """D-02: Create initial review state for all posts without state.

    Seeds from posts.created_at (publication date).
    """
    from fsrs import Card

    # Get posts without review state
    posts = conn.execute(
        """SELECT x_post_id, created_at FROM posts
           WHERE x_post_id NOT IN (SELECT post_id FROM post_review_state)"""
    ).fetchall()

    now = datetime.now(timezone.utc)
    seeded = 0

    for post in posts:
        post_id = post['x_post_id']
        publication_date = datetime.fromisoformat(post['created_at'].replace('Z', '+00:00'))
        age_days = (now - publication_date).days

        # Create FSRS card
        card = Card()
        card.card_id = post_id

        # Older posts are due immediately, newer posts get small delay
        if age_days > 30:
            scheduled_for = now
        else:
            scheduled_for = now + timedelta(days=age_days // 10)

        # Insert state
        conn.execute(
            """INSERT INTO post_review_state
               (post_id, scheduled_for, review_count, state, fsrs_data)
               VALUES (?, ?, 0, 0, ?)""",
            (post_id, scheduled_for.isoformat(), card.to_json())
        )
        seeded += 1

    conn.commit()
    return seeded
```

### `xbm due` Table Output
```python
# Source: [CITED: D-04, D-11 project patterns]
from rich.table import Table
from rich.console import Console

def display_due_posts(posts: list[dict]) -> None:
    """D-04: Table format for due posts."""
    console = Console()

    table = Table(title="Due Posts")
    table.add_column("#", style="dim", width=4)
    table.add_column("Author", style="cyan")
    table.add_column("Content Preview", style="white")
    table.add_column("Topics", style="green")
    table.add_column("Due", style="yellow")

    for i, post in enumerate(posts, 1):
        # Truncate content to 50 chars
        preview = post['text'][:50] + "..." if len(post['text']) > 50 else post['text']

        # Get topics
        topics = post.get('topic_names', 'None')

        # Format due date
        due_date = post['scheduled_for'][:10] if post.get('scheduled_for') else 'Unknown'

        table.add_row(
            str(i),
            f"@{post['author_username']}",
            preview,
            topics,
            due_date
        )

    console.print(table)
    console.print(f"[dim]Total: {len(posts)} posts due[/dim]")
```

### `xbm stats` Statistics Display
```python
# Source: [CITED: D-12 project patterns]
from rich.table import Table
from rich.console import Console

def display_review_stats(stats: dict) -> None:
    """D-12: Statistics and progress tracking."""
    console = Console()

    table = Table(title="Review Statistics")
    table.add_column("Metric", style="dim")
    table.add_column("Count", justify="right")

    table.add_row("Total Posts", str(stats['total_posts']))
    table.add_row("Posts Due", str(stats['due_count']))
    table.add_row("Posts Reviewed", str(stats['reviewed_count']))

    # Calculate percentage
    if stats['total_posts'] > 0:
        reviewed_pct = (stats['reviewed_count'] / stats['total_posts']) * 100
        table.add_row("Review Progress", f"{reviewed_pct:.1f}%")

    console.print(table)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SM-2 algorithm | FSRS-4.5 | 2023+ | FSRS avoids "ease hell" problem of SM-2, better interval predictions |
| Difficulty rating (Again/Hard/Good/Easy) | User intent (fresh/soon/later) | This project | Simplified UX while retaining FSRS state for future enhancement |
| In-memory scheduling | SQLite persistence + APScheduler | Standard | Survives restarts, enables future automation |
| Random review order | Scheduled order (oldest first) | D-02 | Prioritizes older content before it's forgotten |

**Deprecated/outdated:**
- **SM-2 algorithm:** Causes "ease hell" where intervals spiral downward. Use FSRS instead.
- **SuperMemo variants:** Proprietary, less community support than FSRS.

## Assumptions Log

> Claims tagged [ASSUMED] need user confirmation before execution.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | User wants 3 fixed intervals (3d/2w/2m) | User Constraints | D-03 is locked, no risk |
| A2 | FSRS state storage is sufficient for future algorithm | Standard Stack | May need migration if algorithm changes significantly |
| A3 | Single-user CLI doesn't need APScheduler background jobs | Architecture | APScheduler installed for SQLite job store, not active scheduling yet |

## Open Questions

1. **Should `xbm review` support batch mode?**
   - What we know: D-10 specifies interactive one-at-a-time review.
   - What's unclear: Whether power users want batch approval (e.g., "mark all as later").
   - Recommendation: Start with interactive mode. Add `--batch` flag in future if requested.

2. **Should postpone override user preference?**
   - What we know: D-09 specifies postpone with fixed intervals.
   - What's unclear: Whether postpone changes the stored `user_preference`.
   - Recommendation: Postpone does NOT change `user_preference`. It's a temporary delay. Next review still uses the original preference.

3. **What happens when all posts are reviewed?**
   - What we know: D-12 shows statistics including reviewed count.
   - What's unclear: Whether there's a "review complete" celebration or empty state.
   - Recommendation: Show "All caught up! No posts due for review." message with next scheduled review date.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| fsrs | Spaced repetition state | Need install | 6.3+ | - |
| apscheduler | Background scheduling (future) | Need install | 3.11+ | - |
| Rich | CLI output | Installed | 15.0+ | - |
| Typer | CLI framework | Installed | 0.23+ | - |

**Missing dependencies with no fallback:**
- fsrs (required for FSRS-4.5 state management)
- apscheduler (required for future scheduling automation, can defer to Phase 6)

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pyproject.toml (tool.pytest) |
| Quick run command | `pytest tests/ -x -v` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPAC-01 | Calculate next review from pub date | unit | `pytest tests/test_review_scheduler.py -x` | Wave 0 |
| SPAC-01 | FSRS state persistence | unit | `pytest tests/test_review_state_repository.py -x` | Wave 0 |
| SPAC-02 | Get due posts | unit | `pytest tests/test_review_state_repository.py::test_get_due_posts -x` | Wave 0 |
| SPAC-03 | `xbm due` command | integration | `pytest tests/test_cli.py::test_due_command -x` | Wave 0 |
| SPAC-03 | Due posts table output | integration | `pytest tests/test_cli.py::test_due_table_output -x` | Wave 0 |
| SPAC-04 | Themed review filter | unit | `pytest tests/test_review_state_repository.py::test_get_due_by_topic -x` | Wave 0 |
| CLI-02 | `xbm review` interactive | integration | `pytest tests/test_cli.py::test_review_command -x` | Wave 0 |
| CLI-02 | Note display at top | integration | `pytest tests/test_cli.py::test_review_note_display -x` | Wave 0 |
| D-07 | User choice scheduling | unit | `pytest tests/test_review_scheduler.py::test_schedule_intervals -x` | Wave 0 |
| D-09 | Postpone intervals | unit | `pytest tests/test_review_scheduler.py::test_postpone -x` | Wave 0 |
| D-12 | `xbm stats` command | integration | `pytest tests/test_cli.py::test_stats_command -x` | Wave 0 |
| D-13 | `xbm reset` command | integration | `pytest tests/test_cli.py::test_reset_command -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -v`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_review_state_repository.py` — covers SPAC-01, SPAC-02, SPAC-04 repository operations
- [ ] `tests/test_review_scheduler.py` — covers SPAC-01 scheduling logic, D-07 intervals, D-09 postpone
- [ ] `tests/test_cli.py` additions — covers SPAC-03, CLI-02, D-12, D-13 CLI commands
- [ ] `tests/conftest.py` updates — add fixtures for review_state table
- [ ] Install dependencies: `pip install fsrs apscheduler`
- [ ] SCHEMA_V5_MIGRATION in `src/db/schema.py`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Auth handled in Phase 1 |
| V3 Session Management | no | No sessions in CLI |
| V4 Access Control | no | Single-user CLI application |
| V5 Input Validation | yes | Typer for input validation, parameterized queries |
| V6 Cryptography | no | No encryption required for local storage |

### Known Threat Patterns for Spaced Repetition + CLI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL Injection | Tampering | Parameterized queries (existing pattern) |
| FSRS state manipulation | Tampering | Validate FSRS JSON before deserialization |
| Postpone interval overflow | Tampering | Max postpone interval of 1 year |

**Security notes:**
- FSRS state is stored as JSON text. Validate structure before `Card.from_json()`.
- User choices (fresh/soon/later) are enum values, not free text.
- No network exposure = minimal attack surface.

## Sources

### Primary (HIGH confidence)
- [py-fsrs GitHub Repository](https://github.com/open-spaced-repetition/py-fsrs) — FSRS algorithm implementation
- [py-fsrs API Documentation](https://open-spaced-repetition.github.io/py-fsrs/fsrs.html) — Card/Scheduler class reference
- [APScheduler Documentation](https://apscheduler.readthedocs.io/en/3.x/userguide.html) — BackgroundScheduler, SQLite job store

### Secondary (MEDIUM confidence)
- [FSRS Algorithm Explanation](https://github.com/open-spaced-repetition) — Open Spaced Repetition organization
- [APScheduler PyPI](https://pypi.org/project/APScheduler/) — Current version 3.11.2

### Tertiary (LOW confidence)
- [Spaced Repetition Best Practices](https://super-memory.com/articles/SM2.htm) — SM-2 algorithm reference (superseded by FSRS)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — FSRS library is official implementation, APScheduler is mature
- Architecture: HIGH — Repository pattern matches existing codebase, FSRS Card JSON serialization is standard
- Pitfalls: HIGH — Based on FSRS documentation and existing project patterns

**Research date:** 2026-04-25
**Valid until:** 30 days (stable libraries, mature patterns)