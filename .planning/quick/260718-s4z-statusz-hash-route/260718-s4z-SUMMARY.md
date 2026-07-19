---
quick_id: 260718-s4z
slug: statusz-hash-route
status: complete
commit: 5eb4ab6
date: 2026-07-18
---

# Summary: #statusz hash route

**Outcome:** Complete. 654 tests passing (4 new). Commit `5eb4ab6`.

## What was built

`#statusz` is now a navigable hash route in the static viewer. Visiting `/index.html#statusz`
(or appending `#statusz` to any Netlify URL) renders a clean status table with:

| Field | Source |
|-------|--------|
| Version | `XBM_VERSION` constant (baked in at export time — `0.1.0`) |
| Exported | `exportedDate` JS global (from `posts.json`) |
| Total posts | `totalPostCount` JS global |
| Rich embeds | Runtime detection: any post with `oembed_html` |
| Prefetch window | `PREFETCH_AHEAD` / `PREFETCH_BEHIND` constants |
| View mode | `currentMode` JS global |
| Posts loaded | `Object.keys(allPosts).length` |
| Search index | `searchIndex.length` |
| Review states | `reviewMap.size` |
| Prefetch pool | `prefetchPool.size` |

"← XBM Home" link clears `deep-link-mode` and calls `renderView()` to return to the main viewer.

## Changes
- `src/services/static_export.py`: CSS, `XBM_VERSION`, `renderStatusz()`, early hash detection, bootstrap hash check
- `tests/test_static_export_service.py`: `TestIndexHtmlStatusz` (4 tests)
