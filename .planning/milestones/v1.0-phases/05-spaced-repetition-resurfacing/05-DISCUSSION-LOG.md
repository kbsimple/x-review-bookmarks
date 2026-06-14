# Phase 5: Spaced Repetition Resurfacing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 05-spaced-repetition-resurfacing
**Areas discussed:** Scheduling Algorithm, Review Queue Display, User Interaction, CLI Commands

---

## Scheduling Algorithm

| Option | Description | Selected |
|--------|-------------|----------|
| FSRS-4.5 | Current stable, simpler API, well-documented. Good for production. | ✓ |
| FSRS-5 | Latest algorithm with improved scheduling accuracy. More complex. | |
| You decide | FSRS-4.5 is mature and well-tested. | |

**User's choice:** FSRS-4.5 (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Seed from publication date | Calculate first review based on post.created_at. Older posts get longer intervals. | |
| Default state, learn on first review | New posts start with default parameters (stability=1, difficulty=0.3). | |
| You decide | Seeding from publication date aligns with 'resurface old bookmarks' goal. | ✓ |

**User's choice:** You decide (confirmed: seed from publication date)

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed exponential intervals | 1d, 3d, 1w, 2w, 1m, 3m. Simple, predictable, not personalized. | |
| FSRS with default 'good' | Use FSRS algorithm, assume 'good' for every review. | |
| Hybrid: simple first, FSRS after | First review is simple, then FSRS takes over. | |
| Hybrid: user choice + algorithm | User choice sets interval with room for algorithm later. | ✓ |

**User's choice:** Hybrid: user choice + jitter + background algorithm (can start off as simple, but with room to expand)

**Notes:** User clarified that rating is about user intent for timing, not difficulty:
- "Keep fresh" → short interval (days)
- "Review again soon" → medium interval (weeks)
- "Review again later" → long interval (months)

---

## Review Queue Display

| Option | Description | Selected |
|--------|-------------|----------|
| Table format | Compact list: post text truncated, author, topic tags, due date. Many posts visible at once. | ✓ |
| Card format | Full post content, author info, notes, topics. One post at a time with pagination. | |
| Hybrid | --table flag for compact view, default to card format for focused review. | |

**User's choice:** Table format

| Option | Description | Selected |
|--------|-------------|----------|
| Show notes at top | Notes are the context the user saved for themselves. Show them prominently. | ✓ |
| Show notes after post | Notes supplement post content. Show after the post text. | |
| Show collapsed | Notes can be long. Show first line, expand with --verbose flag. | |

**User's choice:** Show notes at top

| Option | Description | Selected |
|--------|-------------|----------|
| Publication date | When the post was originally published (for context). | ✓ |
| Topic tags | Topic assignments for the post. | ✓ |
| Scheduling reason | Why this post is being resurfaced (e.g., "scheduled for review"). | ✓ |
| Review history | How many times reviewed, last review date, next scheduled date. | ✓ |

**User's choice:** All four metadata options selected (Publication date, Topic tags, Scheduling reason, Review history)

---

## User Interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Rate difficulty (FSRS standard) | Show post, user rates difficulty (1-4), algorithm adjusts next review. | |
| Just mark reviewed/skip | User marks as reviewed, skips, or postpones. Simpler. | ✓ |
| Rate + skip option | Rate difficulty for personalized scheduling, also allow skip/postpone. | |

**User's choice:** Just mark reviewed/skip

| Option | Description | Selected |
|--------|-------------|----------|
| Filter by topic flag | --topic flag to filter queue: `xbm due --topic python`. | ✓ |
| Dedicated themed command | Separate command: `xbm review-topic python` for themed sessions. | |
| You decide | Topic filtering is the primary use case. Make --topic flag default. | |

**User's choice:** Filter by topic flag

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed intervals + custom flag | 1 day, 3 days, 1 week, custom via --days flag. | ✓ |
| Always custom input | User types how many days to postpone. More flexible. | |
| One week default | One week is a reasonable default. Add --days flag for custom. | |

**User's choice:** Fixed intervals + custom flag

**Notes:** User clarified that the rating concept should be about user intent for timing:
- "Keep fresh" (3 days) — see again very soon
- "Review again soon" (2 weeks) — see moderately soon
- "Review again later" (2 months) — wait longer

---

## CLI Commands

| Option | Description | Selected |
|--------|-------------|----------|
| Separate commands: due + review | `xbm due` shows due posts. `xbm review` for interactive session. | |
| Single command with flag | Just `xbm due` with optional --review flag. | |
| Always use `xbm review` | Primary command for viewing and interacting with due posts. | ✓ |

**User's choice:** Always use 'xbm review'

| Option | Description | Selected |
|--------|-------------|----------|
| `xbm stats` command | Show total posts, due count, reviewed count, upcoming schedule. | ✓ |
| Stats flag on `xbm due` | Integrate stats into `xbm due` output with --stats flag. | |
| No stats in Phase 5 | Stats are useful but low priority. Skip for MVP. | |

**User's choice:** `xbm stats` command

| Option | Description | Selected |
|--------|-------------|----------|
| Reset command for posts | `xbm reset <post_id>` — reset a post's review state to start fresh. | ✓ |
| No reset, use re-sync instead | If user wants to relearn, they can delete and re-sync. | |
| You decide | Add `xbm reset` for flexibility. | |

**User's choice:** Reset command for posts

---

## Claude's Discretion

- Exact table schema design (fields, indexes) — standard patterns apply.
- CLI output formatting with Rich — follow existing patterns from Phases 2-4.
- Error messages for empty review queue — standard "no posts due" message.
- Interval calculation logic (jitter implementation) — start simple, add later.

## Deferred Ideas

None — discussion stayed within phase scope.