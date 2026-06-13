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

### Cumulative Quality

| Milestone | Tests | Notes |
|-----------|-------|-------|
| v1.0 | ~200 | CLI + SQLite baseline |
| v1.1 | ~350 | Web routes + cast messaging |
| v1.2 | ~560 | Embedded post rendering (complex schema) |
| v1.3 | ~575 | Certificate management + LAN binding |
| v1.4 | 606 | 31 new static export tests |
| v1.5 | 622 | 8 new oEmbed tests |

### Top Lessons (Verified Across Milestones)

1. **Research bugs before planning:** The gsd-phase-researcher catching the `is not None` guard bug (v1.5) and the OEmbedService patch-target issue before planning prevents implementation rework.
2. **Lazy imports for optional features:** Conditional feature flags that import services inside function bodies (v1.4, v1.5) keep startup fast and test isolation clean.
3. **GSD autonomous mode works well for single-phase milestones:** Phases with a single clear deliverable (v1.4, v1.5) complete cleanly with `/gsd-autonomous`; multi-phase milestones benefit more from staged planning.
