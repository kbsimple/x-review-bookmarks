---
phase: 09-web-display
plan: 02
subsystem: web-templates
tags: [jinja2, macros, post-cards, embedded-posts]
completed: 2026-06-06
duration: 2 minutes
---

# Phase 9 Plan 02: Template Macros for Conditional Post Card Rendering

## One-Liner

Implemented Jinja2 macros for conditional post card rendering with nested cards for quote tweets, attribution headers for retweets, media grids, video thumbnails, and image lightbox.

## Key Decisions

1. **Single macro routing pattern** - `render_post_card()` routes to specialized macros based on `post_type`, keeping all post rendering logic centralized in one file.
2. **NULL safety throughout** - All macros check `embedded_post and embedded_post.available` before accessing properties, handling edge cases for missing data.
3. **Lightbox in base template** - Lightbox modal and script included in base.html for global availability, avoiding per-page duplication.

## Files Created/Modified

| File | Status | Description |
|------|--------|-------------|
| `src/web/templates/components/_post_card.html` | created | Main macro file with render_post_card, render_retweet_card, render_quote_card, render_original_card, render_unavailable_placeholder, render_media_grid, render_video_thumbnail |
| `src/web/templates/browse.html` | modified | Updated to import and use render_post_card macro |
| `src/web/templates/components/_lightbox.html` | created | Lightbox modal and JavaScript for image expansion |
| `src/web/templates/base.html` | modified | Added lightbox modal and script includes |
| `tests/test_web_browse.py` | modified | Fixed XSS test assertion for proper security verification |

## Requirements Satisfied

- **WEB-07**: Quote tweets display user's commentary above nested original post card
- **WEB-08**: Retweets show "Reposted from @author" header with original content
- **WEB-09**: Embedded media renders in adaptive grid (1 full, 2 side-by-side, 3+ in 2x2)
- **WEB-10**: Unavailable posts show gray placeholder with author if known

## Deviations from Plan

None - plan executed exactly as written.

## Security

- All user content uses Jinja2 auto-escape (no `|safe` filter on user data)
- NULL safety checks before accessing `embedded_post` properties
- Video thumbnails link to X with `target="_blank" rel="noopener noreferrer"`
- Image lightbox uses event.stopPropagation() to prevent modal close on image click

## Tests

All 17 tests pass:
- `test_quote_tweet_display`: Verifies quote tweet nested card structure
- `test_retweet_display`: Verifies retweet attribution headers
- `test_unavailable_placeholder`: Verifies placeholder for unavailable posts
- `test_embedded_media_display`: Verifies adaptive media grid
- `test_no_xss_in_embedded`: Verifies XSS prevention in embedded content

## Commit

`9636fd0`: feat(09-02): implement conditional post card rendering with macros

## Self-Check

- [x] All files exist at specified paths
- [x] Commit exists in git history
- [x] All tests pass (17/17)

## Next Steps

- Plan 09-03: Update `/api/posts` endpoint to return HTML snippets with embedded post data for HTMX infinite scroll