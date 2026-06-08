# Phase 11: Cast Display - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-07
**Phase:** 11-cast-display
**Areas discussed:** TV Typography, Quote Layout, Media Display, Unavailable Handling

---

## TV Typography

| Option | Description | Selected |
|--------|-------------|----------|
| 3rem base (recommended) | 50% larger than web for TV viewing distance | ✓ |
| 2.5rem base | Moderate increase, may be hard to read from couch | |
| 4rem base | Maximum readability, may crowd content | |

**User's choice:** Use recommendations (autonomous)
**Notes:** Applied 3rem base text size with 2.5rem for author names, matching Phase 9 patterns with TV optimization.

---

## Quote Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Nested cards (recommended) | Same structure as Phase 9 web, TV-optimized spacing | ✓ |
| Flat timeline | Linear display without nesting, simpler but less clear | |
| Side-by-side panels | Original on left, commentary on right — hard on TV | |

**User's choice:** Use recommendations (autonomous)
**Notes:** Nested card structure with outer card (user's commentary), "Quoting @username" label, inner card (original post with #1a1a1a background).

---

## Media Display

| Option | Description | Selected |
|--------|-------------|----------|
| Full-width vertical (recommended) | Single column stack, optimized for TV vertical flow | ✓ |
| 2-column grid | Side-by-side images — too small on TV | |
| Carousel/swiper | Horizontal navigation — complex for remote control | |

**User's choice:** Use recommendations (autonomous)
**Notes:** Full-width media for TV, vertical stack for multiple images, no grid layout (TV screens favor vertical content flow).

---

## Unavailable Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Gray placeholder card (recommended) | Matches Phase 9 web pattern, TV-optimized with larger text | ✓ |
| Red-bordered card | High visibility but may be alarming on TV | |
| Skip entirely | Hide unavailable posts — confusing gap in content | |

**User's choice:** Use recommendations (autonomous)
**Notes:** Gray #1a1a1a card with "Original post unavailable" message, 4rem post icon, author shown if known. Same pattern as web with TV-optimized sizing.

---

## Claude's Discretion

- Exact pixel values for TV spacing
- Animation timing for loading states
- Error message wording
- Fallback image for posts without media

## Deferred Ideas

- Queue management for cast sessions — future enhancement
- Voice control via Google Assistant — out of scope
- Interactive video player on TV — out of scope for v1.2