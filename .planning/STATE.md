---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: oEmbed Rich Embeds
status: complete
last_updated: "2026-06-13T20:28:00Z"
last_activity: 2026-06-13 — Phase 15 Plan 01 (oEmbed rich embeds) complete
progress:
  total_phases: 15
  completed_phases: 15
  total_plans: 58
  completed_plans: 58
  percent: 100
---

# STATE: X Bookmarked Posts Organizer

**Last updated:** 2026-06-13

## Project Reference

**Core Value:** Resurface bookmarked posts on a spaced-repetition schedule so they stay fresh in mind

**Current Focus:** Milestone v1.4 — Static Export — COMPLETE

**Milestone:** v1.4 Static Export — COMPLETE

## Current Position

Phase: 15 — oEmbed Rich Embeds (COMPLETE — Plan 01 done)
Status: Phase 15 complete — all 58 plans done across 15 phases
Last activity: 2026-06-13 — Plan 15-01 oEmbed rich embeds committed (324be1d)

## Progress

```
Phase 15 Progress
███████████████████████████ 100% (15/15 phases complete, plan 58/58)
```

## Milestone v1.3 Goals

**Goal:** Enable browsing and casting from mobile devices on the same LAN without certificate warnings.

**Achieved:**
- ✅ Generate locally-trusted SSL certificates using mkcert
- ✅ CLI command to set up LAN-accessible certificates
- ✅ Web server binds to LAN IP with proper certificate
- ✅ Mobile browser can access and cast to TV

## Completed Phases

| Phase | Goal | Status |
|-------|------|--------|
| 12. Certificate Management | Generate and manage LAN SSL certificates | ✅ Complete |
| 13. LAN Network Access | Bind server to LAN and enable mobile access | ✅ Complete |
| 14. Static Export | Export bookmarks to Netlify-deployable static site | ✅ Complete |
| 15. oEmbed Rich Embeds | --rich-embeds option for export-static with native X widget rendering | ✅ Complete |

## Key Decisions

- **oembed_map guard:** Changed `is not None` to truthy check `if oembed_map:` — empty dict (default path) is falsy, cleanly omits oembed_html field
- **OEmbedService patch target:** src.services.oembed.OEmbedService (definition site) not static_export — lazy import resolves at call time
- **OEMBED-03 manual-only:** Viewer JS (renderOEmbedCard + loadTwitterWidget) has no unit tests — JS embedded in Python string, no JS test infrastructure
- **export-static lazy import:** StaticExportService imported inside function body to avoid circular import risk
- **StaticExportService is standalone:** Does not extend ExportService — different shape (directory vs file, multiple outputs)
- **source field = 'xbm-static':** Distinguishes static export from CLI export format ('xbm')
- **Sorted search-index strings:** tags/topics strings sorted alphabetically for deterministic test output
- **get_all_with_embedded reuses _row_to_dict_with_embedded:** Avoids duplicating JSON parsing logic
- **get_all excludes FSRS internals:** user_preference, step, fsrs_data omitted from export
- **HTML as single Python string constant via _build_index_html():** No templating library needed
- **esc() helper for XSS prevention:** All user content escaped before innerHTML insertion
- **mkcert for local SSL:** Generate locally-trusted certificates that mobile devices can trust
- **LAN IP binding:** Server binds to 0.0.0.0 for network access (dual binding)
- **One-time setup:** CA installation on devices is a one-time manual step per device
- **CLI-first approach:** Certificate management through `xbm lan-cert` commands before server startup
- **Block on missing certs:** Server startup blocked if certificates don't exist, with clear error message

## Technical Context

### Implementation Order (from ARCHITECTURE.md)

1. **Phase 12: Certificate Management**
   - `src/web/lan_certs.py` — mkcert integration, LAN IP detection
   - Modified `src/config/settings.py` — Add LAN settings
   - Added `lan-cert` CLI commands — status, generate, guide
   - Certificate status and regeneration commands

2. **Phase 13: LAN Network Access**
   - Modified `src/cli/main.py` — Added `--lan` flag to web command
   - Certificate check blocks startup if missing
   - Dual URL display (localhost + LAN IP)
   - Platform-specific guidance output

### Dependencies

- **mkcert:** External binary (user installs via package manager)
- **cryptography:** Existing library (fallback for self-signed certs)
- **socket:** Standard library (LAN IP detection)

## Completed Milestones

- **v1.0 (Milestone 1):** CLI + SQLite — 5 phases, 34 requirements — Complete
- **v1.1 (Milestone 2):** Web App with Casting — 2 phases, 14 requirements — Complete
- **v1.2 (Milestone 3):** Enhanced Post Rendering — 4 phases, 13 requirements — Complete
- **v1.3 (Milestone 4):** LAN Casting Support — 2 phases, 14 requirements — Complete

## Session Continuity

### Quick Start Commands

- View roadmap: `cat .planning/ROADMAP.md`
- View requirements: `cat .planning/REQUIREMENTS.md`
- View project context: `cat .planning/PROJECT.md`
- View research: `cat .planning/research/SUMMARY.md`
- View research details: `ls .planning/research/`

### Key Files

- **Roadmap:** `.planning/ROADMAP.md`
- **Requirements:** `.planning/REQUIREMENTS.md`
- **Project:** `.planning/PROJECT.md`
- **Research:** `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md`
- **Milestones:** `.planning/MILESTONES.md`

### Roadmap Evolution

- Phase 15 added: oEmbed Rich Embeds — --rich-embeds option for export-static with native X widget rendering and netlify-deploy skill update

### Next Actions

Phase 15 complete. All 58 plans across 15 phases complete. Project is fully feature-complete for v1.4/v1.5 milestone.

Phase 15 summary:
- Plan 01 (15-01): OEmbedService + --rich-embeds flag + viewer JS + bug fix + 8 tests + netlify-deploy skill (622 tests pass)

Phase 14 summary:
- Wave 0 (14-00): test infrastructure stubs
- Wave 1 (14-01): repository extensions (get_all_with_embedded + ReviewStateRepository.get_all)
- Wave 2 (14-02): StaticExportService + 5 JSON writers + activated tests
- Wave 3 (14-03): index.html + netlify.toml + activated tests (27 tests pass)
- Wave 4 (14-04): export-static CLI command + 4 CLI tests (31 static tests pass, 606 total pass)

## Deferred Items

Items acknowledged and deferred at milestone close on 2026-06-13:

| Category | Item | Status |
|----------|------|--------|
| quick_task | 260516-limit-sync-flag | missing |
| quick_task | 260517-fix-failing-tests | missing |
| quick_task | 260517-stats-command | missing |

---
*State initialized: 2026-04-18*
*Milestone v1.3 roadmap created: 2026-06-08*
*Milestone v1.3 complete: 2026-06-08*
*Milestone v1.5 complete: 2026-06-13*