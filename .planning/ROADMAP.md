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

### ✅ v1.6 Viewer Presentation Modes (Phase 16) — SHIPPED 2026-06-13

**Goal:** Add multiple presentation modes to the static viewer — stream view (existing scrollable list) and a one-at-a-time carousel where posts are displayed prominently and navigated individually.

**Depends on:** Phase 15 (oEmbed Rich Embeds)

**Success Criteria:**
1. Viewer has a mode switcher (Stream / Carousel) accessible from the header
2. Stream mode is the existing scrollable vertical list (default, unchanged)
3. Carousel mode shows one post at a time, prominently, with prev/next navigation
4. Carousel supports keyboard navigation (arrow keys)
5. Active mode persists across search/filter changes
6. Both modes work with oEmbed rich embeds

**Plans:** 2 plans

Plans:
- [x] 16-00-PLAN.md — Wave 0: TestIndexHtmlCarousel failing stubs (Nyquist compliance)
- [x] 16-01-PLAN.md — Wave 1: Implement carousel in _build_index_html() (CSS + HTML + JS)

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

---
*Roadmap created: 2026-04-18*
*Roadmap updated: 2026-06-13 — v1.5 (oEmbed Rich Embeds) complete — all 15 phases done*
*Roadmap updated: 2026-06-13 — Phase 16 (Viewer Presentation Modes) added*
*Roadmap updated: 2026-06-13 — Phase 16 planned: 2 plans (Wave 0 stubs + Wave 1 implementation)*
*Roadmap updated: 2026-06-13 — Phase 16 Plan 00 complete (Wave 0 RED stubs — TestIndexHtmlCarousel)*
*Roadmap updated: 2026-06-13 — Phase 16 complete — v1.6 Viewer Presentation Modes shipped — 628 tests pass*
