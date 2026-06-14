# Phase 15: oEmbed Rich Embeds - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `--rich-embeds` option to `xbm export-static` that fetches native X widget HTML (via the public oEmbed API) for each post at export time and stores it in posts.json. The static viewer renders posts with oEmbed HTML as native Twitter blockquote widgets; posts without it fall back to the existing custom card. The netlify-deploy skill is updated to expose this option.

**Important:** Core implementation (OEmbedService, StaticExportService param, CLI flag, viewer rendering) was completed inline during phase creation in the current conversation. Files are on disk but uncommitted. Remaining work is: netlify-deploy skill update + tests for the new code + committing everything.

</domain>

<decisions>
## Implementation Decisions

### netlify-deploy Skill Update
- Trigger phrase "deploy with rich embeds" maps to `xbm export-static --rich-embeds` — opt-in, not default
- CDN note is a passive FYI message printed to skill output only — no confirmation prompt required
- Add a dedicated "Rich Embeds" section in SKILL.md with trigger phrase, FYI note, and command example

### Test Coverage
- Test OEmbedService: mock `httpx.get` to cover success (200 + html field), 404 (returns None), and network error (exception → returns None) paths
- Test StaticExportService `rich_embeds` path: mock OEmbedService.fetch_all, assert `oembed_html` field appears in posts.json output per post
- Viewer JS: no unit tests — JS is inline in a Python string with no JS test infrastructure; verified manually

### Claude's Discretion
- Plan structure: single plan file (15-01) covering commit of existing implementation + netlify-deploy skill update + tests
- Test file: `tests/test_oembed_service.py` (new) and additions to `tests/test_static_export_service.py`

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py` — `temp_db_v6` fixture for StaticExportService tests
- `tests/test_static_export_service.py` — existing pattern: `StaticExportService(temp_db_v6).export(tmp_path)` + JSON parse
- `httpx` is a project dependency (already used in `src/api/` and `src/services/oembed.py`)
- `.claude/skills/netlify-deploy/SKILL.md` — existing skill to update

### Established Patterns
- OEmbedService created at `src/services/oembed.py` — `fetch_oembed(post_id) -> str | None`, `fetch_all(post_ids, on_progress) -> dict`
- StaticExportService.export() signature extended: `rich_embeds: bool = False, on_oembed_progress: Any = None`
- CLI flag: `--rich-embeds / --no-rich-embeds` typer.Option on `export-static` command
- Viewer: `renderOEmbedCard()` + `loadTwitterWidget()` added; `renderPost()` checks `post.oembed_html` first

### Integration Points
- netlify-deploy skill invokes `venv/bin/xbm export-static` — needs `--rich-embeds` passthrough
- `test_static_export_service.py` → add `TestRichEmbeds` class using mock OEmbedService

</code_context>

<specifics>
## Specific Ideas

- CDN note wording: "Note: Twitter widget JS will be loaded from an external CDN at view time." — keep it one line, informational only
- Skill trigger: user says "deploy with rich embeds" or "redeploy with rich embeds" → skill appends `--rich-embeds`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
