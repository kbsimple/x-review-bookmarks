# Phase 18: Background Prefetch - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-18
**Phase:** 18-background-prefetch
**Areas discussed:** Rendering context, Prefetch mechanism, Timing, Cache management
**Mode:** --auto (Claude selected recommended options throughout)

---

## Rendering Context

| Option | Description | Selected |
|--------|-------------|----------|
| Carousel mode — adjacent posts | Pre-render next/previous post while viewing current | ✓ |
| Deep link landing — the linked post | Prefetch specifically for #post-{id} URL landing | |
| All posts on initial load | Pre-init all Twitter widgets after page loads | |

**User's choice:** Carousel mode — adjacent posts
**Notes:** User confirmed this is the target rendering context.

---

## What to Prefetch

| Option | Description | Selected |
|--------|-------------|----------|
| Twitter widget initialization | Pre-warm twttr.widgets.load() for oEmbed posts | ✓ (implied) |
| Post images / media | Preload <img> src URLs for upcoming posts | ✓ (implied) |
| Multiple posts | 5-10 posts in advance | ✓ |

**User's choice:** "Anything that will make page rendering faster. Multiple posts might be prefetched (such as 5-10) in advance."
**Notes:** User wants broad prefetch, not limited to oEmbed. 5-10 posts window specified.

---

## Timing

| Option | Description | Selected |
|--------|-------------|----------|
| After current post renders | Start prefetch immediately after renderCarousel() | ✓ |
| On browser idle (requestIdleCallback) | Wait for idle, then prefetch | |
| On user intent | Detect hover/swipe start | |

**User's choice:** "Make a decision about this. It should be smart and not block the initial rendering of the first post."
**Notes:** [auto] Claude selected: requestIdleCallback({timeout:200}) with setTimeout fallback. Fires after current post render, yields to browser on first opportunity.

---

## Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Hidden off-screen DOM + twttr.widgets.load() | Pre-render into hidden divs, warm widgets | ✓ |
| Preload images only | new Image().src for upcoming media | |
| You decide | Claude picks mechanism | |

**User's choice:** "You decide the mechanism"
**Notes:** [auto] Claude selected: DOM node pool with hidden off-screen container. Chosen because it handles both oEmbed widget pre-warming and non-oEmbed DOM-parse savings consistently.

---

## Cache Invalidation

| Option | Description | Selected |
|--------|-------------|----------|
| Discard and re-prefetch from new position | Clear pool when result set changes | ✓ |
| Keep prefetch cache across filter changes | Preserve stale nodes | |
| You decide | Claude decides | |

**User's choice:** "You decide"
**Notes:** [auto] Claude selected: clear pool in renderView() carousel branch (fires on filter/search/sort changes). Navigation calls renderCarousel() directly — pool NOT cleared on navigation (intentional).

---

## Window Bias

| Option | Description | Selected |
|--------|-------------|----------|
| Forward-weighted (5 ahead, 2 behind) | Asymmetric, matches typical navigation direction | ✓ |
| Symmetric (5 ahead, 5 behind) | Equal in both directions | |
| You decide | Claude picks | |

**User's choice:** Forward-weighted (5 ahead, 2 behind)
**Notes:** User explicitly selected this option.

---

## Autonomous Mode Decisions (Claude's Discretion)

Areas where user granted Claude full discretion ("be autonomous with execution of this phase"):

- Pool data structure: `Map<postId, HTMLElement>` — O(1) lookup
- Prefetch container: single hidden `div#prefetch-container` off-screen in body
- Widget warming: direct `twttr.widgets.load(container)`, not `loadTwitterWidget()` (avoids skeleton timer pollution)
- Warm-state detection: `!cardNode.querySelector('blockquote.twitter-tweet')`
- Node reuse: temp div reference capture pattern for nav nodes
- Pool cancellation: cancel pending timer on clearPrefetchPool()

## Deferred Ideas

- Configurable window size in viewer UI
- Service Worker cross-session pre-caching
- Stream mode prefetch (no use case)
- IndexedDB persistence
