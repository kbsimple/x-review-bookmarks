---
plan: "18-00"
wave: 0
status: complete
commit: 1974f86
---

# Plan 18-00 Summary: RED Test Stubs

**Outcome:** Wave 0 complete. Added `TestIndexHtmlPrefetch` class with 6 RED stub tests to `tests/test_static_export_service.py`.

**Tests added (all failing before Wave 1):**
- `test_schedule_prefetch_function_present` — asserts `schedulePrefetch` in html
- `test_prefetch_window_constants_present` — asserts `PREFETCH_AHEAD` and `PREFETCH_BEHIND` in html
- `test_request_idle_callback_present` — asserts `requestIdleCallback` in html
- `test_prefetch_pool_hit_check_present` — asserts `prefetchPool.has` in html
- `test_clear_prefetch_pool_present` — asserts `clearPrefetchPool` in html
- `test_prefetch_pool_eviction_present` — asserts `prefetchPool.delete` in html

**Verified:** 6 FAILED (AssertionError); existing TestIndexHtmlCarousel and TestIndexHtmlDeepLink unchanged (22 passed).
