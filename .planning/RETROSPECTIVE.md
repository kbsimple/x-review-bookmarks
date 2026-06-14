# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v1.5 — oEmbed Rich Embeds

**Shipped:** 2026-06-13
**Phases:** 1 | **Plans:** 1 | **Tasks:** 3

### What Was Built
- `OEmbedService` — async-style batch fetcher using public Twitter oEmbed API (no credentials required)
- `--rich-embeds / --no-rich-embeds` flag on `export-static` with progress bar feedback
- Static viewer JS rendering path: `renderOEmbedCard()` + lazy `loadTwitterWidget()`
- netlify-deploy skill updated with "deploy with rich embeds" trigger
- 8 new tests: 5 unit tests for OEmbedService, 3 integration tests for StaticExportService rich_embeds path

### What Worked
- **Autonomous GSD execution** — `/gsd-autonomous --from 15` ran discuss → plan → execute without interruption once initial decisions were made
- **Lazy import pattern** — importing OEmbedService inside the conditional branch avoids overhead on the default path and cleanly separates concerns
- **Truthy guard pattern** — `if oembed_map:` vs `is not None` is a subtle but important Python pattern; discovered via research before implementation
- **Zero-dependency approach** — `httpx` was already a project dependency; no new libraries needed
- **Research-first bug discovery** — the `is not None` guard bug was caught by the gsd-phase-researcher before execution, preventing a runtime defect

### What Was Inefficient
- **Context break mid-session** — conversation context ran out mid-execution, requiring a summary-based resume; no work was lost but there was redundant context reconstruction
- **VALIDATION.md gap** — plan checker blocked on missing VALIDATION.md; this file should be created as part of planning, not as a blocker at checker time

### Patterns Established
- **Patch lazy-imported service at definition site:** When a class is imported inside a function with `from .module import Class`, mock it at `src.module.Class` (definition site), not `src.caller.Class`
- **`request_delay=0` for fast tests:** Pass `request_delay=0` to services with `time.sleep` instead of patching `time.sleep` globally — cleaner and more targeted
- **oEmbed CDN pattern:** Use `omit_script=true` to get bare blockquote HTML, then load `widgets.js` once lazily and let SDK auto-process on load — avoids duplicate script loading

### Key Lessons
1. **Truthy vs identity checks matter for optional dicts:** `if d:` (falsy for `{}`) vs `if d is not None:` (True for `{}`) produce different behavior when the empty state should be a no-op. Always use truthy for "was this populated?" checks.
2. **VALIDATION.md should be a planning deliverable:** Including it in the plan as a required file prevents plan checker blocks during execution. Add it to the plan template for future phases.
3. **Public oEmbed APIs are robust:** `publish.twitter.com/oembed` is public, no auth required, and returns consistent JSON. The 404 path for deleted/protected posts is clean. Rate limiting is avoided with a 0.15s inter-request delay.

### Cost Observations
- Model: claude-sonnet-4-6 throughout
- Sessions: 2 (context break mid-execution)
- Notable: Autonomous execution completed Phase 15 in a single 18-minute executor run; the main overhead was planning artifacts and verification

---

## Milestone: v1.6 — Viewer Presentation Modes

**Shipped:** 2026-06-13
**Phases:** 1 | **Plans:** 2 | **Tasks:** ~8

### What Was Built
- Mode switcher (Stream / Carousel) in viewer header — visible on desktop, collapsible on mobile
- Carousel mode: one-at-a-time display with prev/next buttons, keyboard arrow key navigation
- Sticky carousel header on mobile, merged controls bar into header on desktop
- Options panel (renamed from Filters) housing mode switcher and all filter controls
- Responsive layout: desktop merges controls into header; mobile keeps collapsible panel
- Nyquist-compliant Wave 0 RED stubs → Wave 1 implementation

### What Worked
- **CSS body class pattern** (`body.carousel-mode`) — clean separation between mode-specific CSS and base styles, no JS-managed inline style toggling
- **Keyboard listener registered once** outside `renderView()` — avoids duplicate event registration on each render cycle
- **twttr.widgets.load scoped to `#post-list`** — avoids re-processing entire DOM per oEmbed anti-pattern
- **Wave 0 RED stubs** — created clear test gates before implementation; one stub (`test_oembed_reinit_called_in_carousel`) passed immediately because twttr.widgets.load was already present from Phase 15

### What Was Inefficient
- **Multi-iteration UI polish** — carousel UI required 4 commits to get right (merge controls, sticky nav, rename Filters→Options, slim scrolled header); could have been designed upfront
- **Mobile/desktop layout drift** — initial implementation had separate mobile/desktop behaviors that diverged; merging was rework

### Patterns Established
- **Sticky header + scroll-based slim state** — `#post-list` scroll events drive `header.scrolled` class for slim mode; clean and performant
- **Options panel as drawer** — mobile options panel as a collapsible drawer via `#header-options-btn` is reusable for future filter additions
- **Carousel index resets to 0 on renderView()** — simpler UX than preserving index across filter changes; avoids out-of-bounds risk

### Key Lessons
1. **Plan the full responsive layout before Wave 1.** Having "carousel header" mean different things on mobile vs desktop led to 4 refinement commits. A quick UI-SPEC for layout behavior prevents this.
2. **Scope UI cleanup in the same wave.** The rename Filters→Options and option panel reorganization were out-of-scope additions that nonetheless improved coherence — acknowledge them as scope expansions upfront.

### Cost Observations
- Model: claude-sonnet-4-6 throughout
- Sessions: 2 (UI polish required a second pass)
- Notable: The Wave 0 → Wave 1 Nyquist structure worked well; test gates caught a missing `twttr.widgets.load` integration point immediately

---

## Milestone: v1.7 — Deep Linking

**Shipped:** 2026-06-14
**Phases:** 1 | **Plans:** 2 | **Tasks:** 4 executor tasks

### What Was Built
- Share icon (📤) on every post card — all 4 card types (original, retweet, quote, oEmbed)
- `copyDeepLink()` — clipboard write via `navigator.clipboard.writeText()` with 1500ms "Copied!" visual confirmation
- Hash detection bootstrap — `#post-{id}` hash parsed after `Promise.all().then()` populates `allPosts`, before `renderView()`
- `body.deep-link-mode` CSS class toggle swaps mode-switcher ↔ XBM Home button
- `goHome()` — navigates to `origin + pathname` (fragment-free)
- `showDeepLinkError()` — graceful post-not-found with `esc(postId)` XSS safety
- 11 new string-grep tests (`TestIndexHtmlDeepLink`), Wave 0 RED → Wave 1 GREEN

### What Worked
- **Code review caught WR-01 before it shipped** — deep-link CSS rules were inside `@media (max-width: 600px)` (mobile-only), making XBM Home visible on desktop at all times. Caught by gsd-code-reviewer, fixed before merge. Validates the code review step.
- **CSS class as the runtime mechanism** — `body.deep-link-mode` class toggle is clean; the JS `deepLinkMode` flag ended up inert (declared and set but not read in JS conditionals). The CSS-first approach is the right pattern for visibility toggles.
- **`Promise.all().then()` placement for hash detection** — RESEARCH.md identified this as a pitfall early; placing hash detection after `allPosts` population was correct and executed exactly as designed
- **Nyquist Wave 0 structure** — 11 RED stubs created clear test gates; all 11 turned GREEN in Wave 1 with no surprises
- **`renderCardFooter()` refactor** — extracting shared footer to a helper function enabled the share icon to appear on all 4 card types cleanly

### What Was Inefficient
- **`deepLinkMode` flag declared but never read** — a mild design gap: the flag is set but the CSS class is the actual mechanism. Could have been skipped, or the flag documented as reserved. Minor, but reflects imprecise spec → implementation alignment.
- **Nyquist frontmatter not updated** — `nyquist_compliant` in VALIDATION.md remained `false` after Wave 1; noted in audit as PARTIAL but not blocking. The frontmatter update should be an explicit executor task.

### Patterns Established
- **Hash detection placement:** Always detect URL hashes inside `Promise.all().then()` after async data loading, never at top-level script execution (timing hazard).
- **CSS class for deep-link mode:** `body.deep-link-mode` class is the canonical mechanism for deep-link-specific UI state. JS flags are informational only.
- **`goHome()` fragment-free URL:** `window.location.origin + window.location.pathname` (no fragment) is the canonical way to return to the root viewer without stale deep-link state.

### Key Lessons
1. **Code review pays for itself in one bug.** WR-01 (CSS scoped to mobile-only) would have been a confusing UX defect in production. The code review step that caught it took seconds to run and minutes to fix.
2. **JS flags and CSS classes can drift.** When CSS classes are the actual runtime mechanism, JS flags should either be removed or clearly documented as reserved. Avoid "double-tracking" state in both.
3. **Nyquist frontmatter update should be a named executor task.** The frontmatter remained `false` because there was no explicit task to update it. Add "Update VALIDATION.md nyquist_compliant to true" as a required executor task in Wave 1 plans.

### Cost Observations
- Model: claude-sonnet-4-6 throughout
- Sessions: 1 (clean autonomous execution, no context break)
- Notable: Full discuss → plan → execute → code review → verify → audit → complete cycle in one session; code review WR-01 fix added ~5 minutes but prevented a real defect

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v1.0 | 5 | Established GSD workflow baseline |
| v1.1 | 2 | Added web + cast; multi-layer architecture |
| v1.2 | 4 | Complex embedded post schema; LEFT JOIN patterns |
| v1.3 | 2 | External binary integration (mkcert); platform-specific guides |
| v1.4 | 1 | First static export; self-contained HTML viewer |
| v1.5 | 1 | First external API integration in export pipeline; lazy import pattern |
| v1.6 | 1 | Carousel UI + responsive layout; multi-iteration UI polish |
| v1.7 | 1 | Deep linking; code review caught CSS scoping bug before shipping |

### Cumulative Quality

| Milestone | Tests | Notes |
|-----------|-------|-------|
| v1.0 | ~200 | CLI + SQLite baseline |
| v1.1 | ~350 | Web routes + cast messaging |
| v1.2 | ~560 | Embedded post rendering (complex schema) |
| v1.3 | ~575 | Certificate management + LAN binding |
| v1.4 | 606 | 31 new static export tests |
| v1.5 | 622 | 8 new oEmbed tests |
| v1.6 | 628 | 6 new carousel tests |
| v1.7 | 644 | 11 new deep-link tests (DL-01 through DL-11) |

### Top Lessons (Verified Across Milestones)

1. **Research bugs before planning:** The gsd-phase-researcher catching the `is not None` guard bug (v1.5) and the OEmbedService patch-target issue before planning prevents implementation rework.
2. **Lazy imports for optional features:** Conditional feature flags that import services inside function bodies (v1.4, v1.5) keep startup fast and test isolation clean.
3. **GSD autonomous mode works well for single-phase milestones:** Phases with a single clear deliverable (v1.4–v1.7) complete cleanly with `/gsd-autonomous`; multi-phase milestones benefit more from staged planning.
4. **Code review pays for itself in one bug:** WR-01 in v1.7 (CSS scoped to mobile-only for a global feature) would have been a production defect. The code review step caught it before shipping.
5. **CSS class toggles outperform JS flag tracking:** When CSS classes drive visibility state (`body.deep-link-mode`, `body.carousel-mode`), JS flags become redundant. Pick one mechanism and document which is authoritative.
