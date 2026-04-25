# Phase 5: Spaced Repetition Resurfacing - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Posts are resurfaced for review on a user-controlled schedule with hybrid algorithm support. Users can view currently due posts via CLI, interact with them (mark reviewed, keep fresh, review soon, review later), and trigger themed reviews by topic.

This phase delivers:
- Review scheduling with user-controlled intervals
- `xbm review` command for interactive review sessions
- `xbm due` command to view due posts (non-interactive)
- `xbm stats` command for progress tracking
- `xbm reset <post_id>` to reset review state
- Themed reviews via `--topic` flag
- Notes displayed prominently during review

**Out of scope:**
- Samsung TV app output (future milestone)
- Web app with casting (future milestone)
- AI-generated summaries
- Real-time notifications

</domain>

<decisions>
## Implementation Decisions

### Scheduling Algorithm
- **D-01:** Use FSRS-4.5 algorithm concepts but start with simplified user-controlled scheduling.
  - User's choice (fresh/soon/later) sets the next review interval.
  - Hybrid approach: user choice + jitter + background algorithm (room to expand).
  - Rationale: Simplicity for MVP, but architecture allows FSRS integration later.
- **D-02:** Seed initial review state from post publication date.
  - Older posts naturally get longer intervals.
  - Aligns with core value: "resurface old bookmarks before you forget them."
- **D-03:** Default intervals for user choices:
  - "Keep fresh" → 3 days
  - "Review again soon" → 2 weeks
  - "Review again later" → 2 months

### Review Queue Display
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

### User Interaction
- **D-07:** Review interaction model: user chooses scheduling intent.
  - After viewing a post, user selects:
    - "Keep fresh" (3 days)
    - "Review again soon" (2 weeks)
    - "Review again later" (2 months)
  - No difficulty rating — scheduling is user-controlled, not algorithmic difficulty.
- **D-08:** Themed reviews via `--topic` flag on `xbm due` and `xbm review`.
  - `xbm due --topic python` shows only posts in Python topic.
  - `xbm review --topic python` starts interactive session for Python posts.
- **D-09:** Postpone option available during review.
  - Fixed intervals: 1 day, 3 days, 1 week, 2 weeks, 1 month, 3 months.
  - Custom via `--days` flag for user-specified delay.

### CLI Commands
- **D-10:** `xbm review` — primary command for interactive review sessions.
  - Shows posts one at a time with full content, notes, metadata.
  - User chooses: Keep fresh / Review soon / Review later / Skip / Postpone.
  - After choice, moves to next due post.
- **D-11:** `xbm due` — non-interactive view of due posts.
  - Table format showing all posts currently due for review.
  - Use `--topic` flag to filter by topic.
- **D-12:** `xbm stats` — statistics and progress tracking.
  - Shows: total posts, due count, reviewed count, upcoming schedule.
- **D-13:** `xbm reset <post_id>` — reset review state for a post.
  - User can restart specific posts without re-syncing everything.

### Database Schema
- **D-14:** New table `post_review_state` for scheduling persistence.
  - Fields: post_id, scheduled_for, last_reviewed, review_count, user_preference, created_at, updated_at.
  - `user_preference` stores the user's last choice (fresh/soon/later).
  - `scheduled_for` is the next review date (seeded from publication date initially).
- **D-15:** Use `posts.created_at` as initial scheduling baseline.
  - Posts sync with publication date, so review state can seed from that.

### Claude's Discretion
- Exact table schema design (fields, indexes) — standard patterns apply.
- CLI output formatting with Rich — follow existing patterns from Phases 2-4.
- Error messages for empty review queue — standard "no posts due" message.
- Interval calculation logic (jitter implementation) — start simple, add later.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/REQUIREMENTS.md` — SPAC-01, SPAC-02, SPAC-03, SPAC-04, CLI-02
- `.planning/STATE.md` — Decisions log (FSRS over SM-2, SQLite WAL, all-MiniLM-L6-v2)
- `.planning/ROADMAP.md` — Phase 5 success criteria

### Prior Phases
- `.planning/phases/04-topic-organization/04-RESEARCH.md` — Embedding and clustering patterns
- `.planning/phases/01-foundation-and-authentication/01-CONTEXT.md` — SQLite WAL, FK constraints
- `.planning/research/SUMMARY.md` — Spaced repetition algorithm notes (py-fsrs, FSRS-4)

### Code Patterns
- `src/repositories/posts.py` — PostsRepository for data access
- `src/repositories/topics.py` — TopicsRepository for themed reviews
- `src/cli/main.py` — Typer CLI command patterns
- `src/db/schema.py` — Schema version migration patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **PostsRepository (`src/repositories/posts.py`):** Data access for posts, can extend with review state methods.
- **TopicsRepository (`src/repositories/topics.py`):** Topics for themed reviews (`--topic` filtering).
- **CLI pattern (`src/cli/main.py`):** Typer groups, Rich tables, command structure.
- **Schema migration pattern (`src/db/schema.py`):** SCHEMA_V5_MIGRATION for new tables.

### Established Patterns
- Three-table many-to-many for relationships (posts, topics, post_topics).
- Rich table output for CLI commands.
- Repository pattern for data access.
- Migration-based schema evolution.

### Integration Points
- `post_review_state` table joins to `posts` via `post_id` foreign key.
- Themed reviews filter by `post_topics` topic_id.
- `xbm review` command joins post content + review state + topic tags.

</code_context>

<specifics>
## Specific Ideas

- User sees due posts in table format with `xbm due`, then can run `xbm review` for interactive session.
- During review, notes appear at top of post content — this is why they saved it.
- Three simple choices (fresh/soon/later) with clear time horizons (days/weeks/months).
- Themed reviews let user focus on specific topics when they have limited time.
- Stats command shows progress: how many posts reviewed, how many due, upcoming schedule.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---
*Phase: 05-spaced-repetition-resurfacing*
*Context gathered: 2026-04-25*