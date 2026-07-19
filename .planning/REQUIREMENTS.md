# Requirements: X Bookmarked Posts Organizer — v1.8

**Milestone:** v1.8 Background Prefetch
**Created:** 2026-07-18
**Status:** Active

---

## Milestone v1.8 — Background Prefetch

### Prefetch Window

- [ ] **PREFETCH-01:** Carousel pre-renders the next 5 posts into detached DOM elements after the current post renders
- [ ] **PREFETCH-02:** Carousel pre-renders the previous 2 posts into detached DOM elements after the current post renders
- [ ] **PREFETCH-03:** Twitter widgets are pre-initialized via `twttr.widgets.load()` on prefetched oEmbed posts before the user navigates to them

### Scheduling

- [ ] **PREFETCH-04:** Prefetch scheduling uses `requestIdleCallback` with a 200ms max timeout so it never delays current-post render

### Navigation

- [ ] **PREFETCH-05:** On carousel navigation, the viewer swaps in the pre-rendered node from the prefetch pool when available (no re-render from scratch)

### Cache Management

- [ ] **PREFETCH-06:** Prefetch pool is cleared and rebuilt from the new position when search, filter, or sort changes the result set
- [ ] **PREFETCH-07:** Pool entries outside the active window are evicted as the user navigates (limits memory to ~7 hydrated nodes at a time)

### Verification

- [ ] **PREFETCH-08:** String-grep tests verify prefetch JS functions (`schedulePrefetch`, `prefetchPool`) exist in the generated `index.html`

---

## Future Requirements

- Configurable prefetch window size (user setting in viewer UI)
- Prefetch for stream mode (currently not needed — all posts visible)
- Service Worker pre-caching of post JSON across page reloads

## Out of Scope

- Stream mode prefetch — posts are already in the DOM in stream mode
- Server-side prefetch — this is a static export; all logic is client-side JS
- Cross-session prefetch cache — IndexedDB/localStorage prefetch persistence is premature
- Prefetch for non-carousel views

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| PREFETCH-01 | — | Pending |
| PREFETCH-02 | — | Pending |
| PREFETCH-03 | — | Pending |
| PREFETCH-04 | — | Pending |
| PREFETCH-05 | — | Pending |
| PREFETCH-06 | — | Pending |
| PREFETCH-07 | — | Pending |
| PREFETCH-08 | — | Pending |

---
*Requirements created: 2026-07-18*
