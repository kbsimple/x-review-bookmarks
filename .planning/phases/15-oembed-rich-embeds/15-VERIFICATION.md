---
phase: 15
slug: 15-oembed-rich-embeds
status: PASS
verified_date: 2026-06-13T00:00:00Z
score: 7/7
---

# Phase 15: oEmbed Rich Embeds — Verification Report

**Phase Goal:** Add `--rich-embeds` option to `export-static` command that fetches native X/Twitter oEmbed HTML at export time and stores it in `posts.json`, with the static viewer rendering it via Twitter's widget JS from CDN at view time.

**Verified:** 2026-06-13
**Status:** PASS
**Re-verification:** No — initial verification

---

## Evidence

### SC-1: `xbm export-static --rich-embeds` flag accepted by CLI

**Status:** PASS

`src/cli/main.py` lines 805-875 define the flag:

- Line 805: `rich_embeds: bool = typer.Option(`
- Line 807: `"--rich-embeds/--no-rich-embeds",`
- Line 844: `if rich_embeds:` — branch triggers oEmbed progress reporting
- Line 874: `rich_embeds=rich_embeds,` — passed through to the export service
- Line 875: `on_oembed_progress=on_oembed_progress if rich_embeds else None,`

The flag is declared, documented in the CLI help string (line 831 shows example usage), and wired to the export call.

---

### SC-2: `OEmbedService` at `src/services/oembed.py` with `fetch_oembed()` and `fetch_all()`

**Status:** PASS

`src/services/oembed.py` exists and is substantive (not a stub):

- Line 25: `class OEmbedService:`
- Line 38: `def fetch_oembed(self, post_id: str) -> Optional[str]:` — returns HTML or None, makes HTTP request to Twitter oEmbed endpoint
- Line 58: `def fetch_all(` — iterates post IDs, calls `fetch_oembed`, returns dict mapping post_id to HTML

Both required methods are present and non-trivial.

---

### SC-3: `_write_posts_json()` uses `if oembed_map:` (truthy guard, not `is not None`)

**Status:** PASS

`src/services/static_export.py` line 188:

```python
if oembed_map:
    export_post["oembed_html"] = oembed_map.get(post_id)
```

The guard is the bare truthy form `if oembed_map:`, not `if oembed_map is not None:`. This means an empty dict `{}` (no results fetched) will correctly skip writing `oembed_html` keys, avoiding null-valued fields in `posts.json`.

---

### SC-4: Viewer JS includes `renderOEmbedCard` and `loadTwitterWidget`

**Status:** PASS

`src/services/static_export.py`:

- Line 767: `function loadTwitterWidget()` — loads Twitter widget.js from CDN
- Line 777: `function renderOEmbedCard(post, reviewState)` — renders the oEmbed HTML block
- Line 786: `if (post.oembed_html) return renderOEmbedCard(post, reviewState);` — post cards branch to rich embed rendering when `oembed_html` is present
- Line 848: `loadTwitterWidget()` — called in page initialization

Both functions are defined and integrated into the render flow; the data-to-render path is complete.

---

### SC-5: Netlify deploy skill has "Rich Embeds" section

**Status:** PASS

`.claude/skills/netlify-deploy/SKILL.md`:

- Line 48: `## Rich Embeds`
- Line 50: `Trigger: user says "deploy with rich embeds" or "redeploy with rich embeds"`
- Line 60: `venv/bin/xbm export-static --rich-embeds` — correct command

The skill section is present with trigger phrase and the exact invocation command.

---

### SC-6: 622 tests pass

**Status:** PASS (accepted on trust — just-confirmed count per user context)

Full test suite was confirmed at 622 passing tests immediately before verification was requested. Re-running the 36-second suite is skipped per the verification instructions.

---

### SC-7: New test files exist — `tests/test_oembed_service.py` and `TestRichEmbeds` in `tests/test_static_export_service.py`

**Status:** PASS

- `tests/test_oembed_service.py` — file exists, contains 5 test functions (verified via `grep -c "def test_"`); not a stub.
- `tests/test_static_export_service.py` line 305: `class TestRichEmbeds:` — class is present in the existing test file.

Both test locations confirmed substantive.

---

## Summary

All 7 success criteria pass. The `--rich-embeds` feature is fully implemented end-to-end:

- CLI accepts the flag and routes it to the service layer
- `OEmbedService` fetches live oEmbed HTML per post
- Export serialization guards correctly against empty maps (truthy check)
- The static viewer JS renders oEmbed cards and bootstraps the Twitter widget
- The Netlify deploy skill documents the rich-embeds workflow
- Test coverage exists for both the new service and the export-service integration

**Phase 15 goal is achieved.**

---

_Verified: 2026-06-13_
_Verifier: Claude (gsd-verifier)_
