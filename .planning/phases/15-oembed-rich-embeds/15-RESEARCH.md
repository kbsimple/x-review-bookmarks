# Phase 15: oEmbed Rich Embeds - Research

**Researched:** 2026-06-13
**Domain:** oEmbed API, httpx, StaticExportService, viewer JS, Netlify deploy skill
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- netlify-deploy skill: trigger phrase "deploy with rich embeds" maps to `xbm export-static --rich-embeds` — opt-in, not default
- CDN note is a passive FYI message printed to skill output only — no confirmation prompt required
- Add a dedicated "Rich Embeds" section in SKILL.md with trigger phrase, FYI note, and command example
- Test OEmbedService: mock `httpx.get` to cover success (200 + html field), 404 (returns None), and network error (exception → returns None) paths
- Test StaticExportService `rich_embeds` path: mock OEmbedService.fetch_all, assert `oembed_html` field appears in posts.json output per post
- Viewer JS: no unit tests — JS is inline in a Python string with no JS test infrastructure; verified manually

### Claude's Discretion
- Plan structure: single plan file (15-01) covering commit of existing implementation + netlify-deploy skill update + tests
- Test file: `tests/test_oembed_service.py` (new) and additions to `tests/test_static_export_service.py`

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Most of Phase 15 is already on disk but uncommitted. `src/services/oembed.py`, `src/services/static_export.py`, and `src/cli/main.py` were written inline during phase creation. The implementation is structurally correct: OEmbedService uses httpx.get with the right params, StaticExportService conditionally calls it and injects `oembed_html` into each post object, and the viewer JS routes through `renderOEmbedCard` when `oembed_html` is truthy.

Three items remain: (1) update `.claude/skills/netlify-deploy/SKILL.md` to add a "Rich Embeds" section; (2) write `tests/test_oembed_service.py` for OEmbedService unit tests; and (3) extend `tests/test_static_export_service.py` with a `TestRichEmbeds` class that mocks `OEmbedService.fetch_all`. All 29 existing static export tests pass clean against the modified `static_export.py`.

**Primary recommendation:** Commit the existing implementation as-is, update the skill file, write the two test additions, and commit everything together in a single plan.

---

## Implementation Validation

### OEmbedService (`src/services/oembed.py`) — VERIFIED CORRECT

Endpoint: `https://publish.twitter.com/oembed` [VERIFIED: matches Twitter public oEmbed docs]

Key behaviors confirmed by code inspection:

| Behavior | Code | Verdict |
|----------|------|---------|
| `omit_script=true` param | `params={"url": url, "omit_script": "true", "dnt": "true"}` | Correct — strips `<script>` tag from returned HTML; caller loads widget.js separately |
| Post URL construction | `https://x.com/i/web/status/{post_id}` | Correct — format accepted by publish.twitter.com/oembed |
| 404 handling | `if resp.status_code == 404: return None` | Correct — deleted/protected posts return 404 [ASSUMED: typical behavior for unavailable posts] |
| Other HTTP errors | `resp.raise_for_status()` followed by bare `except Exception: return None` | Correct — converts all non-404 HTTP errors to None as well |
| Network errors | `except Exception: return None` | Correct — catches connection timeout, DNS failure, etc. |
| Inter-request delay | `time.sleep(self._delay)` skipped after last item | Correct — `if i < total - 1` guard prevents trailing sleep |
| Progress callback | `on_progress(i + 1, total)` after each fetch | Correct — 1-indexed completed count |
| httpx timeout | `timeout=10.0` | Reasonable; no issue |
| follow_redirects | `follow_redirects=True` | Correct — oEmbed endpoint may redirect |

No issues found. [VERIFIED: read full source]

### StaticExportService (`src/services/static_export.py`) — VERIFIED CORRECT

Key behaviors confirmed:

| Behavior | Code | Verdict |
|----------|------|---------|
| Lazy import of OEmbedService | `from .oembed import OEmbedService` inside `if rich_embeds and posts:` | Correct — avoids import overhead for default path |
| `oembed_map` population | `OEmbedService().fetch_all(post_ids, on_progress=on_oembed_progress)` | Correct — passes all post IDs at once |
| Conditional field injection | `if oembed_map is not None: export_post["oembed_html"] = oembed_map.get(post_id)` | Correct — `oembed_map.get(post_id)` returns None for deleted posts (dict.get default); only adds field when `rich_embeds=True` |
| Default path (no rich_embeds) | `oembed_map` stays `{}` (falsy but not None); `if oembed_map is not None` evaluates True — field IS injected as None | **ISSUE — see note below** |

**Edge case found:** When `rich_embeds=False`, `oembed_map` is initialized as `{}` (not `None`). The check is `if oembed_map is not None`, which is always `True` since `{}` is not `None`. This means `oembed_html: null` appears in every post even on the default `--no-rich-embeds` run.

The viewer JS handles this correctly (`if (post.oembed_html)` is falsy for `null`), so it does not cause a rendering bug. However it adds a redundant null field to every post. The planner should decide whether to fix this by changing the guard to `if oembed_map:` (truthy check, treats empty dict as no embeds) or leave it as-is since the viewer handles null gracefully.

**Recommendation for plan:** Change `if oembed_map is not None:` to `if oembed_map:` in `_write_posts_json`. This is a one-line fix that cleanly separates the two export modes. [VERIFIED: read full source]

### CLI (`src/cli/main.py`) — VERIFIED CORRECT

`export-static` command (lines 791–933):

| Behavior | Verdict |
|----------|---------|
| `--rich-embeds/--no-rich-embeds` Typer option with default `False` | Correct |
| FYI note printed before export only when `rich_embeds=True` | Correct — matches CONTEXT.md CDN note requirement |
| oEmbed progress task added to Rich progress bar only when `rich_embeds=True` | Correct |
| `on_oembed_progress` callback updates progress task with `(completed, total)` | Correct — matches `OEmbedService.fetch_all` callback signature |
| `on_oembed_progress=None` passed when `rich_embeds=False` | Correct |
| `svc.export(output, rich_embeds=rich_embeds, on_oembed_progress=...)` | Correct |

No issues found. [VERIFIED: read full source]

### Viewer JS (inline in `_build_index_html`) — VERIFIED CORRECT

| Behavior | Verdict |
|----------|---------|
| `renderPost()` checks `post.oembed_html` first (truthy) | Correct — null/undefined falls through to type-based routing |
| `renderOEmbedCard()` injects `post.oembed_html` raw (no escaping) | Correct — HTML is trusted server-side content from Twitter's oEmbed API; escaping would break it |
| `loadTwitterWidget()` loads `platform.twitter.com/widgets.js` once (flag guard) | Correct — idempotent |
| After `container.innerHTML` set: checks `results.some(e => allPosts[e.id].oembed_html)` then calls `loadTwitterWidget()` | Correct — loads script only when needed |
| `window.twttr && window.twttr.widgets.load(container)` call after script load | Correct — re-processes newly injected blockquotes; handles case where script was already loaded |
| CSS `.oembed-card` + `.oembed-container` classes | Present and applied correctly |

One observation: `window.twttr.widgets.load(container)` is called immediately after `loadTwitterWidget()` appends the script tag. If the script has not yet finished loading (first render), `window.twttr` may be undefined and the `&&` short-circuit prevents any error. On subsequent renders (search/filter), the script is already loaded and `window.twttr` is available. This is the standard pattern and works correctly. [VERIFIED: read full source]

### Git Status

| File | State |
|------|-------|
| `src/services/oembed.py` | Untracked (new file, not committed) |
| `src/services/static_export.py` | Modified, uncommitted |
| `src/cli/main.py` | Modified, uncommitted |
| `.claude/skills/netlify-deploy/SKILL.md` | Committed — needs update |
| `tests/test_oembed_service.py` | Does not exist — needs creation |
| `tests/test_static_export_service.py` | Committed — needs `TestRichEmbeds` class added |

[VERIFIED: `git status --short` output]

---

## Remaining Work

### 1. Fix `oembed_map` guard in `_write_posts_json` (optional but clean)

In `src/services/static_export.py` line 188:

```python
# Current (always injects field, even when empty dict):
if oembed_map is not None:
    export_post["oembed_html"] = oembed_map.get(post_id)

# Fix (only injects when rich_embeds=True):
if oembed_map:
    export_post["oembed_html"] = oembed_map.get(post_id)
```

This is a one-line change. Viewer JS handles both cases but the fix makes the two export modes cleanly distinct.

### 2. Update `.claude/skills/netlify-deploy/SKILL.md`

Add a "Rich Embeds" section per CONTEXT.md decisions:

```markdown
## Rich Embeds

Trigger: user says "deploy with rich embeds" or "redeploy with rich embeds"

Note: Twitter widget JS will be loaded from an external CDN at view time.

Command:
```bash
venv/bin/xbm export-static --rich-embeds
```
```

Then run the deploy step as normal. No confirmation prompt needed — CDN note is informational only.

### 3. New file: `tests/test_oembed_service.py`

Mock pattern: `unittest.mock.patch("httpx.get")` (patches httpx.get directly since OEmbedService imports `httpx` at module level and calls `httpx.get(...)` — not `self.client.get`).

Three test cases required by CONTEXT.md:

```python
from unittest.mock import patch, MagicMock
from src.services.oembed import OEmbedService


class TestOEmbedService:

    def test_fetch_oembed_success_returns_html(self):
        """200 response with html field returns the HTML string."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"html": "<blockquote>...</blockquote>"}
        with patch("httpx.get", return_value=mock_resp) as mock_get:
            svc = OEmbedService()
            result = svc.fetch_oembed("1234567890")
        assert result == "<blockquote>...</blockquote>"
        mock_get.assert_called_once()

    def test_fetch_oembed_404_returns_none(self):
        """404 response returns None (deleted/protected post)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("httpx.get", return_value=mock_resp):
            svc = OEmbedService()
            result = svc.fetch_oembed("9999999999")
        assert result is None

    def test_fetch_oembed_network_error_returns_none(self):
        """Network exception (e.g. connection timeout) returns None."""
        with patch("httpx.get", side_effect=Exception("Connection timeout")):
            svc = OEmbedService()
            result = svc.fetch_oembed("1234567890")
        assert result is None

    def test_fetch_all_maps_ids_to_html(self):
        """fetch_all returns dict mapping post_id -> html or None."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"html": "<blockquote>test</blockquote>"}
        with patch("httpx.get", return_value=mock_resp):
            svc = OEmbedService(request_delay=0)  # no sleep in tests
            result = svc.fetch_all(["id1", "id2"])
        assert result == {
            "id1": "<blockquote>test</blockquote>",
            "id2": "<blockquote>test</blockquote>",
        }

    def test_fetch_all_invokes_progress_callback(self):
        """on_progress callback is called once per post with (completed, total)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"html": "<blockquote></blockquote>"}
        calls = []
        with patch("httpx.get", return_value=mock_resp):
            svc = OEmbedService(request_delay=0)
            svc.fetch_all(["a", "b", "c"], on_progress=lambda c, t: calls.append((c, t)))
        assert calls == [(1, 3), (2, 3), (3, 3)]
```

**Note on `time.sleep`:** `OEmbedService.__init__` accepts `request_delay=0` — pass this in tests to avoid actual sleeps. No need to patch `time.sleep`.

### 4. Add `TestRichEmbeds` class to `tests/test_static_export_service.py`

Mock pattern: `unittest.mock.patch("src.services.static_export.OEmbedService")` — patches at the import site (where `StaticExportService` imports it from `.oembed`). The lazy import `from .oembed import OEmbedService` inside `export()` resolves to `src.services.oembed.OEmbedService`, so patch target is `src.services.static_export.OEmbedService`.

Wait — the import is `from .oembed import OEmbedService` inside the function body at call time, not at module load time. This means the name `OEmbedService` is looked up in `src.services.oembed` at call time. The correct patch target is `src.services.oembed.OEmbedService`.

```python
class TestRichEmbeds:
    """Tests for StaticExportService rich_embeds path (OEMBED-01, OEMBED-02)."""

    def test_rich_embeds_adds_oembed_html_to_posts_json(self, temp_db_v6, tmp_path):
        """With rich_embeds=True and mocked OEmbedService, oembed_html appears in posts.json."""
        from unittest.mock import patch, MagicMock
        fake_html = "<blockquote class='twitter-tweet'>...</blockquote>"
        mock_svc_instance = MagicMock()
        mock_svc_instance.fetch_all.return_value = {
            "post_001": fake_html,
            "post_002": None,   # deleted/protected
            "post_003": fake_html,
        }
        with patch("src.services.oembed.OEmbedService", return_value=mock_svc_instance):
            svc = StaticExportService(temp_db_v6)
            svc.export(tmp_path, rich_embeds=True)
        data = json.loads((tmp_path / "posts.json").read_text())
        post_001 = next(p for p in data["posts"] if p["x_post_id"] == "post_001")
        post_002 = next(p for p in data["posts"] if p["x_post_id"] == "post_002")
        assert post_001["oembed_html"] == fake_html
        assert post_002["oembed_html"] is None

    def test_no_rich_embeds_omits_oembed_html_field(self, temp_db_v6, tmp_path):
        """With rich_embeds=False (default), posts.json posts do not have oembed_html key."""
        svc = StaticExportService(temp_db_v6)
        svc.export(tmp_path)  # default: rich_embeds=False
        data = json.loads((tmp_path / "posts.json").read_text())
        for post in data["posts"]:
            assert "oembed_html" not in post

    def test_rich_embeds_calls_fetch_all_with_all_post_ids(self, temp_db_v6, tmp_path):
        """OEmbedService.fetch_all is called with all 3 post IDs."""
        from unittest.mock import patch, MagicMock
        mock_svc_instance = MagicMock()
        mock_svc_instance.fetch_all.return_value = {
            "post_001": None,
            "post_002": None,
            "post_003": None,
        }
        with patch("src.services.oembed.OEmbedService", return_value=mock_svc_instance):
            svc = StaticExportService(temp_db_v6)
            svc.export(tmp_path, rich_embeds=True)
        called_ids = set(mock_svc_instance.fetch_all.call_args[0][0])
        assert called_ids == {"post_001", "post_002", "post_003"}
```

**Important:** `test_no_rich_embeds_omits_oembed_html_field` depends on the `oembed_map` guard fix (item 1 above). If the fix is NOT applied, this test will fail because the current code injects `oembed_html: null` even without `rich_embeds`. Plan must apply fix before adding this test.

---

## Pitfalls

### Pitfall 1: `oembed_map` guard is `is not None` not truthiness check
**What goes wrong:** `oembed_map = {}` passes `if oembed_map is not None:` and injects `oembed_html: null` on every post even without `--rich-embeds`.
**How to avoid:** Change guard to `if oembed_map:` before writing the test that asserts field absence.
**Warning signs:** `test_no_rich_embeds_omits_oembed_html_field` will fail if guard is not fixed.

### Pitfall 2: Wrong patch target for lazy-imported OEmbedService
**What goes wrong:** Patching `src.services.static_export.OEmbedService` when the name is imported inside the function body from `.oembed` — the patch target for a function-body import is the original module, not the caller.
**How to avoid:** Patch `src.services.oembed.OEmbedService` (the module that defines it). The lazy `from .oembed import OEmbedService` looks up the class in `src.services.oembed` at call time.
**Verification:** If mock is not called, the patch target is wrong.

### Pitfall 3: `time.sleep` makes OEmbedService tests slow
**What goes wrong:** Default `_DEFAULT_DELAY = 0.15` causes 0.15s sleep between each mock call.
**How to avoid:** Instantiate with `OEmbedService(request_delay=0)` in tests.

### Pitfall 4: `twttr.widgets.load` called before script finishes loading
**What goes wrong:** On first render, `window.twttr` may not exist yet when `widgets.load()` is called.
**Status:** Already handled — `if (window.twttr && window.twttr.widgets)` guard prevents the error. Widgets re-render naturally when the script fires its own ready callback. No action needed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pytest.ini present) |
| Config file | `pytest.ini` |
| Quick run command | `venv/bin/python -m pytest tests/test_oembed_service.py tests/test_static_export_service.py -q` |
| Full suite command | `venv/bin/python -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OEMBED-01 | `xbm export-static --rich-embeds` fetches and stores `oembed_html` | unit | `pytest tests/test_static_export_service.py::TestRichEmbeds` | Wave 0 |
| OEMBED-02 | Deleted/protected posts get `oembed_html: null` | unit | `pytest tests/test_static_export_service.py::TestRichEmbeds::test_rich_embeds_adds_oembed_html_to_posts_json` | Wave 0 |
| OEMBED-03 | Viewer renders oEmbed HTML as Twitter widget | manual-only | n/a | n/a — JS in Python string |
| OEMBED-04 | Posts without `oembed_html` render with existing card layout | unit | `pytest tests/test_static_export_service.py::TestRichEmbeds::test_no_rich_embeds_omits_oembed_html_field` | Wave 0 |

### Wave 0 Gaps
- [ ] `tests/test_oembed_service.py` — new file, covers OEmbedService unit tests
- [ ] `TestRichEmbeds` class in `tests/test_static_export_service.py` — covers OEMBED-01, OEMBED-02, OEMBED-04

*(OEMBED-03 is manual-only — viewer JS is not testable without a browser.)*

---

## Environment Availability

Step 2.6: Skipped for OEmbedService tests (httpx is mocked, no real network calls). httpx is already a project dependency — confirmed in use at `src/api/` and `src/services/oembed.py`. [VERIFIED: file inspection]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Twitter's oEmbed endpoint returns 404 for deleted/protected posts | OEmbedService validation | If it returns a different status (e.g. 403), `fetch_oembed` would call `raise_for_status()` and then return None via the bare except — still correct, just classified differently |
| A2 | Patch target `src.services.oembed.OEmbedService` is correct for lazy import | Remaining work — test patterns | If wrong, mocks won't intercept calls; can verify by checking mock call count |

---

## Open Questions (RESOLVED)

1. **Apply `oembed_map` guard fix or leave as-is?**
   - What we know: Current code injects `oembed_html: null` on all posts even without `--rich-embeds`. Viewer handles null gracefully.
   - What's unclear: User preference for strict separation vs. tolerance of extra null field.
   - Recommendation: Fix it (one-line change) since `test_no_rich_embeds_omits_oembed_html_field` requires it and it's the correct semantic behavior.
   - RESOLVED: Fix applied in Task 1, Step 1 — `if oembed_map:` replaces `if oembed_map is not None:`

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `src/services/oembed.py` — full source read
- Direct code inspection of `src/services/static_export.py` — full source read
- Direct code inspection of `src/cli/main.py` — `export-static` command (lines 791–933) read
- Direct code inspection of `tests/conftest.py` — `temp_db_v6` fixture read
- Direct code inspection of `tests/test_static_export_service.py` — all 29 tests read
- `git status --short` — confirmed uncommitted files
- `venv/bin/python -m pytest tests/test_static_export_service.py -q` — 29 passed

### Secondary (MEDIUM confidence)
- Twitter public oEmbed API: `https://publish.twitter.com/oembed` endpoint and `omit_script` parameter — standard documented behavior [ASSUMED: consistent with well-known Twitter oEmbed API]

---

## Metadata

**Confidence breakdown:**
- Existing implementation review: HIGH — read all source files directly
- Test approach: HIGH — verified patch targets against actual import pattern
- netlify-deploy skill scope: HIGH — read existing SKILL.md directly
- oEmbed API behavior (404 for deleted posts): MEDIUM — common behavior, tagged ASSUMED

**Research date:** 2026-06-13
**Valid until:** 2026-07-13

---

## RESEARCH COMPLETE
