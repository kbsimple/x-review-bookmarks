# Milestone History

## Milestone 1 (v1.0): CLI + SQLite

**Status:** Complete
**Started:** 2026-04-18
**Completed:** 2026-04-25

**Goal:** Build core CLI functionality for fetching, storing, and organizing bookmarked posts.

**Delivered:**
- OAuth 2.0 PKCE authentication with X API
- SQLite storage with WAL mode (posts, tags, topics, review state)
- Bookmark sync with incremental updates and rate limit handling
- FTS5 full-text search across post content and authors
- Personal notes attached to posts
- JSON/CSV export and import
- Tags and topic taxonomy with hybrid AI suggestions
- FSRS-based spaced repetition scheduling
- Interactive review sessions via CLI

**Phases:** 5
**Requirements:** 34
**Plans:** 22

---

## Milestone 2 (v1.1): Web + Cast

*(Archive not yet created — see ROADMAP.md Phase 6–7 for details)*

---

## Milestone 3 (v1.2): Embedded Posts Display

*(Archive not yet created — see ROADMAP.md Phase 8–11 for details)*

---

## Milestone 4 (v1.3): LAN Casting Support

*(Archive not yet created — see ROADMAP.md Phase 12–13 for details)*

---

## Milestone 5 (v1.4): Static Export

**Status:** Complete
**Started:** 2026-06-13
**Completed:** 2026-06-13

**Goal:** Export bookmarks to a static web app deployable on Netlify — browse, search, and filter bookmarks from any browser without running the local server.

**Delivered:**
- `xbm export-static` CLI command with --output and --db flags
- StaticExportService generating 7 files (5 JSON data files + index.html + netlify.toml)
- Self-contained index.html viewer: dark theme, sticky header, client-side search (Array.filter), date filtering (7 shortcuts), sort by newest/oldest/author
- All user content HTML-escaped via esc() helper (XSS prevention)
- netlify.toml with Cache-Control headers for Netlify CDN
- Repository extensions: PostsRepository.get_all_with_embedded(), ReviewStateRepository.get_all()
- 31 new tests (27 service tests + 4 CLI integration tests)

**Phases:** 1 (Phase 14: Static Export)
**Plans:** 5 (Wave 0–4)

---

## Milestone 6 (v1.5): oEmbed Rich Embeds

**Status:** Complete
**Started:** 2026-06-13
**Completed:** 2026-06-13

**Goal:** Add `--rich-embeds` option to `export-static` for native X widget rendering in the static viewer via the public oEmbed API.

**Delivered:**
- `OEmbedService` at `src/services/oembed.py` — fetches Twitter blockquote HTML per post via public oEmbed API (no auth required)
- `--rich-embeds / --no-rich-embeds` flag on `xbm export-static` with progress reporting
- `oembed_html` field in `posts.json` (populated only with `--rich-embeds`; null for deleted/protected posts)
- Static viewer JS: `renderOEmbedCard()`, `loadTwitterWidget()` — native Twitter widget rendering via CDN
- Fixed truthy guard bug: `if oembed_map:` (was `is not None`) to prevent field injection on default path
- netlify-deploy skill updated with "deploy with rich embeds" trigger and command
- 8 new tests (5 for OEmbedService, 3 for TestRichEmbeds in StaticExportService)

**Phases:** 1 (Phase 15: oEmbed Rich Embeds)
**Plans:** 1 (15-01)
**Known deferred items at close:** 3 (see STATE.md Deferred Items)

---

## Milestone 7 (v1.6): Viewer Presentation Modes

**Status:** Complete
**Started:** 2026-06-13
**Completed:** 2026-06-13

**Goal:** Add multiple presentation modes to the static viewer — stream view (existing scrollable list) and a one-at-a-time carousel where posts are displayed prominently and navigated individually.

**Delivered:**
- Mode switcher (Stream / Carousel) accessible from viewer header
- Stream mode: existing scrollable vertical list (default, unchanged)
- Carousel mode: one post at a time, prominently displayed, with prev/next navigation buttons
- Keyboard navigation in carousel mode (left/right arrow keys)
- Active mode persists across search/filter changes
- Both modes fully work with oEmbed rich embeds
- Desktop and mobile responsive layouts for carousel header controls

**Phases:** 1 (Phase 16: Viewer Presentation Modes)
**Plans:** 2 (Wave 0 RED stubs + Wave 1 implementation)

---

## Milestone 8 (v1.7): Deep Linking

**Status:** Complete
**Started:** 2026-06-14
**Completed:** 2026-06-14

**Goal:** Add shareable deep link URLs to the static viewer. A share icon (📤) on each post card copies a `#post-{id}` URL to the clipboard. Opening that URL opens the viewer in a focused carousel view with an "XBM Home" button in the header to return to the full viewer.

**Delivered:**
- Share icon (📤) on every post card in both stream and carousel modes (all 4 card renderer types)
- `copyDeepLink()` JS function: copies `#post-{id}` URL to clipboard via `navigator.clipboard.writeText()` with 1500ms "Copied!" visual confirmation
- Hash detection in `Promise.all().then()` bootstrap: sets `deep-link-mode` body class, clears all filters, auto-selects matching post in carousel
- CSS class mechanism (`body.deep-link-mode`) swaps mode-switcher ↔ XBM Home button
- `goHome()` navigates to `origin + pathname` (fragment-free, clearing deep-link state)
- `showDeepLinkError()` shows graceful "Post not found" message with `esc(postId)` for XSS safety
- WR-01 bug fixed: deep-link CSS rules moved to global scope (were mistakenly scoped to mobile media query)
- 11 new string-grep tests (`TestIndexHtmlDeepLink`), all GREEN

**Phases:** 1 (Phase 17: Deep Linking)
**Plans:** 2 (Wave 0 RED stubs + Wave 1 implementation)
**Known deferred items at close:** 5 (4 browser UAT scenarios + 1 Nyquist frontmatter flag — see STATE.md Deferred Items and .planning/phases/17-deep-linking/17-HUMAN-UAT.md)

---
*Last updated: 2026-06-14*