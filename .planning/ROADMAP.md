# Roadmap: X Bookmarked Posts Organizer

**Core Value:** Resurface bookmarked posts on a spaced-repetition schedule so they stay fresh in mind

**Created:** 2026-04-18
**Granularity:** standard

## Milestones

- ✅ **v1.0 CLI + SQLite** — Phases 1–5 (shipped 2026-04-25)
- ✅ **v1.1 Web + Cast** — Phases 6–7 (shipped 2026-05-17)
- ✅ **v1.2 Embedded Posts** — Phases 8–11 (shipped 2026-06-07)
- ✅ **v1.3 LAN Casting Support** — Phases 12–13 (shipped 2026-06-08)
- ✅ **v1.4 Static Export** — Phase 14 (shipped 2026-06-13)
- ✅ **v1.5 oEmbed Rich Embeds** — Phase 15 (shipped 2026-06-13)
- ✅ **v1.6 Viewer Presentation Modes** — Phase 16 (shipped 2026-06-13)
- ✅ **v1.7 Deep Linking** — Phase 17 (shipped 2026-06-14)

## Phases

<details>
<summary>✅ v1.0 CLI + SQLite (Phases 1–5) — SHIPPED 2026-04-25</summary>

- [x] Phase 1: Foundation and Authentication (5/5 plans) — completed 2026-04-18
- [x] Phase 2: Bookmark Fetch and Storage (4/4 plans) — completed 2026-04-23
- [x] Phase 3: Search, Notes, and Import/Export (6/6 plans) — completed 2026-04-23
- [x] Phase 4: Topic Organization (6/6 plans) — completed 2026-04-25
- [x] Phase 5: Spaced Repetition Resurfacing (4/4 plans) — completed 2026-04-25

</details>

<details>
<summary>✅ v1.1 Web + Cast (Phases 6–7) — SHIPPED 2026-05-17</summary>

- [x] Phase 6: Web Foundation (4/4 plans) — completed 2026-05-17
- [x] Phase 7: Cast Integration (4/4 plans) — completed 2026-05-17

</details>

<details>
<summary>✅ v1.2 Embedded Posts (Phases 8–11) — SHIPPED 2026-06-07</summary>

- [x] Phase 8: Storage Foundation (3/4 plans) — completed 2026-06-04
- [x] Phase 9: Web Display (4/4 plans) — completed 2026-06-06
- [x] Phase 10: CLI Display (3/3 plans) — completed 2026-06-07
- [x] Phase 11: Cast Display (3/3 plans) — completed 2026-06-07

</details>

<details>
<summary>✅ v1.3 LAN Casting Support (Phases 12–13) — SHIPPED 2026-06-08</summary>

- [x] Phase 12: Certificate Management (3/3 plans) — completed 2026-06-08
- [x] Phase 13: LAN Network Access (1/1 plan) — completed 2026-06-08

</details>

<details>
<summary>✅ v1.4 Static Export (Phase 14) — SHIPPED 2026-06-13</summary>

- [x] Phase 14: Static Export (5/5 plans) — completed 2026-06-13

</details>

<details>
<summary>✅ v1.5 oEmbed Rich Embeds (Phase 15) — SHIPPED 2026-06-13</summary>

- [x] Phase 15: oEmbed Rich Embeds (1/1 plan) — completed 2026-06-13

</details>

<details>
<summary>✅ v1.6 Viewer Presentation Modes (Phase 16) — SHIPPED 2026-06-13</summary>

- [x] Phase 16: Viewer Presentation Modes (2/2 plans) — completed 2026-06-13

</details>

<details>
<summary>✅ v1.7 Deep Linking (Phase 17) — SHIPPED 2026-06-14</summary>

- [x] Phase 17: Deep Linking (2/2 plans) — completed 2026-06-14

</details>

## Milestone: v1.8 Background Prefetch (Phase 18)

- [x] Phase 18: Background Prefetch (2/2 plans) — completed 2026-07-18

Plans:
- [ ] 18-00-PLAN.md — RED test stubs: TestIndexHtmlPrefetch (6 failing tests)
- [ ] 18-01-PLAN.md — Implementation: prefetch globals, 4 new JS functions, modified renderCarousel and renderView

### Phase Details

**Phase 18: Background Prefetch**

Goal: Add a forward-weighted prefetch pool to carousel mode — pre-render 5 posts ahead and 2 behind with Twitter widget pre-initialization so carousel navigation never waits for widget load.

Requirements: PREFETCH-01, PREFETCH-02, PREFETCH-03, PREFETCH-04, PREFETCH-05, PREFETCH-06, PREFETCH-07, PREFETCH-08

Canonical refs: `src/services/static_export.py` (inline JS), existing `renderCarousel`, `loadTwitterWidget`, `twttr.widgets.load` patterns

Success criteria:
1. Navigating to the next/prev carousel post within the prefetch window shows content with no visible delay or blank flash
2. oEmbed Twitter widgets are already rendered (not loading) when navigating to a prefetched post
3. Changing search, filter, or sort clears the prefetch pool and rebuilds from the new carousel position
4. Prefetch never delays first-post render (requestIdleCallback guard in place)
5. Generated `index.html` contains `schedulePrefetch` and `prefetchPool` identifiers (verified by string-grep tests)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation and Authentication | v1.0 | 5/5 | Complete | 2026-04-18 |
| 2. Bookmark Fetch and Storage | v1.0 | 4/4 | Complete | 2026-04-23 |
| 3. Search, Notes, and Import/Export | v1.0 | 6/6 | Complete | 2026-04-23 |
| 4. Topic Organization | v1.0 | 6/6 | Complete | 2026-04-25 |
| 5. Spaced Repetition Resurfacing | v1.0 | 4/4 | Complete | 2026-04-25 |
| 6. Web Foundation | v1.1 | 4/4 | Complete | 2026-05-17 |
| 7. Cast Integration | v1.1 | 4/4 | Complete | 2026-05-17 |
| 8. Storage Foundation | v1.2 | 3/4 | Complete | 2026-06-04 |
| 9. Web Display | v1.2 | 4/4 | Complete | 2026-06-06 |
| 10. CLI Display | v1.2 | 3/3 | Complete | 2026-06-07 |
| 11. Cast Display | v1.2 | 3/3 | Complete | 2026-06-07 |
| 12. Certificate Management | v1.3 | 3/3 | Complete | 2026-06-08 |
| 13. LAN Network Access | v1.3 | 1/1 | Complete | 2026-06-08 |
| 14. Static Export | v1.4 | 5/5 | Complete | 2026-06-13 |
| 15. oEmbed Rich Embeds | v1.5 | 1/1 | Complete | 2026-06-13 |
| 16. Viewer Presentation Modes | v1.6 | 2/2 | Complete | 2026-06-13 |
| 17. Deep Linking | v1.7 | 2/2 | Complete | 2026-06-14 |
| 18. Background Prefetch | v1.8 | 2/2 | Complete | 2026-07-18 |

---
*Roadmap created: 2026-04-18*
*Roadmap updated: 2026-06-13 — v1.5 (oEmbed Rich Embeds) complete — all 15 phases done*
*Roadmap updated: 2026-06-13 — Phase 16 complete — v1.6 Viewer Presentation Modes shipped — 628 tests pass*
*Roadmap updated: 2026-06-14 — Phase 17 complete — v1.7 Deep Linking shipped — 644 tests pass*
*Roadmap updated: 2026-06-14 — v1.7 milestone closed — archive at milestones/v1.7-ROADMAP.md*
*Roadmap updated: 2026-07-18 — v1.8 milestone started — Phase 18: Background Prefetch*
*Roadmap updated: 2026-07-18 — Phase 18 planned — 2 plans in 2 waves*
