---
phase: 15-oembed-rich-embeds
plan: "01"
subsystem: api
tags: [oembed, httpx, twitter, static-export, netlify]

# Dependency graph
requires:
  - phase: 14-static-export
    provides: StaticExportService, export-static CLI command, netlify-deploy skill
provides:
  - OEmbedService with fetch_oembed and fetch_all (src/services/oembed.py)
  - --rich-embeds flag on xbm export-static with viewer JS rendering
  - oembed_html field in posts.json per post (rich_embeds=True path only)
  - netlify-deploy skill updated with "deploy with rich embeds" trigger
  - 8 new tests covering OEmbedService and StaticExportService rich_embeds path
affects:
  - netlify-deploy skill (updated)
  - static viewer index.html (renderOEmbedCard + loadTwitterWidget JS)

# Tech tracking
tech-stack:
  added: [httpx (already project dependency, now used in services layer)]
  patterns:
    - "Lazy import inside function body: from .oembed import OEmbedService inside export() to avoid import overhead on default path"
    - "Patch lazy-imported service at definition site: src.services.oembed.OEmbedService not static_export"
    - "OEmbedService(request_delay=0) in tests to skip time.sleep without patching"
    - "Truthy guard for optional dict injection: if oembed_map: (not is not None)"

key-files:
  created:
    - src/services/oembed.py
    - tests/test_oembed_service.py
  modified:
    - src/services/static_export.py
    - src/cli/main.py
    - tests/test_static_export_service.py
    - .claude/skills/netlify-deploy/SKILL.md
    - .planning/STATE.md

key-decisions:
  - "oembed_map guard changed from is not None to truthy check: if oembed_map: — empty dict default path now cleanly omits oembed_html field from all posts"
  - "Patch target for lazy-imported OEmbedService is src.services.oembed.OEmbedService (definition site, not caller site)"
  - "OEMBED-03 (viewer JS rendering) is manual-only — JS is inline in a Python string with no JS test infrastructure"
  - "request_delay=0 passed in tests to skip time.sleep without needing to mock time"

patterns-established:
  - "Lazy import pattern for optional dependencies: import inside function body inside the conditional branch that needs it"
  - "OEmbedService mock setup: patch returns_value=mock_svc_instance where mock_svc_instance.fetch_all.return_value = {...}"

requirements-completed: [OEMBED-01, OEMBED-02, OEMBED-03, OEMBED-04]

# Metrics
duration: 18min
completed: 2026-06-13
---

# Phase 15 Plan 01: oEmbed Rich Embeds Summary

**oEmbed service with httpx fetching Twitter blockquote HTML, injected into posts.json via --rich-embeds flag, with native X widget rendering in the static viewer**

## Performance

- **Duration:** 18 min
- **Started:** 2026-06-13T20:10:00Z
- **Completed:** 2026-06-13T20:28:00Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Fixed oembed_map guard bug (`is not None` -> truthy check) so default export cleanly omits `oembed_html` from all posts
- Committed 4 Phase 15 implementation files: OEmbedService (new), StaticExportService (extended), main.py (--rich-embeds flag), STATE.md
- Added 8 new tests: 5 for OEmbedService, 3 for StaticExportService TestRichEmbeds class; full suite 622 passed
- Updated netlify-deploy skill with "## Rich Embeds" section containing trigger phrase and command

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix oembed_map guard bug and commit existing implementation** - `662f091` (feat)
2. **Task 2: Write tests for OEmbedService and TestRichEmbeds** - `219c457` (test)
3. **Task 3: Update netlify-deploy skill with Rich Embeds section** - `324be1d` (docs)

## Files Created/Modified
- `src/services/oembed.py` - OEmbedService: fetch_oembed (single post) and fetch_all (batch with progress callback)
- `src/services/static_export.py` - Extended export() with rich_embeds param; bug fix on oembed_map guard; viewer JS for renderOEmbedCard + loadTwitterWidget
- `src/cli/main.py` - --rich-embeds/--no-rich-embeds Typer option on export-static command with CDN note
- `tests/test_oembed_service.py` - 5 unit tests for OEmbedService (success, 404, network error, fetch_all mapping, progress callback)
- `tests/test_static_export_service.py` - TestRichEmbeds class added (3 tests: oembed_html present, oembed_html absent by default, fetch_all called with all IDs)
- `.claude/skills/netlify-deploy/SKILL.md` - "## Rich Embeds" section with trigger phrase and deploy command
- `.planning/STATE.md` - Phase 15 roadmap evolution note

## Decisions Made
- Changed `if oembed_map is not None:` to `if oembed_map:` — the variable is initialized as `{}` (empty dict, falsy) on the no-rich-embeds path; `is not None` always evaluated True for `{}`, causing `oembed_html: null` on every post even without `--rich-embeds`
- Patch target confirmed as `src.services.oembed.OEmbedService` (not `src.services.static_export.OEmbedService`) because the lazy import `from .oembed import OEmbedService` inside export() resolves the name from its definition module at call time
- OEMBED-03 (viewer JS) has no unit tests by design — JS is embedded in a Python string constant with no JS test infrastructure in the project; verified manually

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed oembed_map guard: `is not None` -> truthy check**
- **Found during:** Task 1 (reviewing static_export.py before commit)
- **Issue:** `oembed_map = {}` (empty dict) on default path passes `if oembed_map is not None:`, injecting `oembed_html: null` into every post even without `--rich-embeds`
- **Fix:** Changed guard to `if oembed_map:` — empty dict is falsy, so field only injected when OEmbedService.fetch_all returns a populated map
- **Files modified:** src/services/static_export.py line 188
- **Verification:** `grep -n "if oembed_map:" src/services/static_export.py` confirms line 188; `test_no_rich_embeds_omits_oembed_html_field` passes
- **Committed in:** `662f091` (Task 1 commit)

**2. [Plan deviation] ROADMAP.md not included in Task 1 commit**
- **Found during:** Task 1 (git status showed ROADMAP.md clean)
- **Issue:** Plan listed ROADMAP.md as a file to commit in Task 1, but it was already committed in a prior session (when Phase 15 was planned); git showed it with no uncommitted changes
- **Fix:** Omitted from staging — committing a clean file would create a no-op diff
- **Impact:** None — ROADMAP.md content is correct and committed

---

**Total deviations:** 1 bug fix (Rule 1), 1 plan discrepancy (ROADMAP already committed)
**Impact on plan:** Bug fix essential for OEMBED-04 correctness. Plan discrepancy has no impact.

## Issues Encountered
None — all tasks executed cleanly. Patch target for lazy import worked as expected (`src.services.oembed.OEmbedService`).

## User Setup Required
None - no external service configuration required. The --rich-embeds flag requires internet access to publish.twitter.com at export time but no credentials.

## Next Phase Readiness
- Phase 15 complete; all 4 OEMBED requirements satisfied
- Rich embeds feature ready for production use via `xbm export-static --rich-embeds`
- netlify-deploy skill updated with trigger phrase for autonomous redeploy with embeds
- Full test suite at 622 tests, all passing

---
*Phase: 15-oembed-rich-embeds*
*Completed: 2026-06-13*

## Self-Check: PASSED
- src/services/oembed.py: FOUND
- tests/test_oembed_service.py: FOUND
- tests/test_static_export_service.py (TestRichEmbeds): FOUND
- Commit 662f091: FOUND
- Commit 219c457: FOUND
- Commit 324be1d: FOUND
- Guard fix `if oembed_map:` at line 188: FOUND
- Trigger phrase "deploy with rich embeds" in SKILL.md: FOUND
