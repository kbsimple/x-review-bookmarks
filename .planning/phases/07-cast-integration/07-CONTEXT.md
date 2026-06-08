# Phase 7: Cast Integration - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous workflow)

<domain>
## Phase Boundary

Enable Google Cast integration for viewing bookmarked posts on Chromecast and Smart TVs. Users can cast post content from the web app to their TV, with a mini controller for navigation. This phase completes the v1.1 milestone by adding the primary TV viewing capability.

</domain>

<decisions>
## Implementation Decisions

### Cast SDK Integration
- Google Cast SDK loaded from CDN (no npm package needed)
- Sender API initialized in web app JavaScript
- Uses Chrome browser's built-in Cast extension support
- Cast button appears only when Cast devices are available

### Custom Web Receiver
- Styled Media Receiver with custom CSS for post display
- Receiver loaded from public URL (GitHub Pages or similar)
- Communication via custom message channels
- Supports text, images, author, and date display

### Mini Controller
- Persistent bottom bar during active cast session
- Navigation controls: previous, next, close
- Current post title and progress indicator
- Session state persisted in sender page's JavaScript

### Claude's Discretion
- Exact receiver hosting solution (GitHub Pages vs local server)
- Error handling for connection failures
- Loading states and user feedback
- Poster image for posts without images

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/web/app.py` — FastAPI app can serve receiver HTML
- `src/web/templates/base.html` — Base layout with script includes
- `src/web/static/` — Static files directory for receiver assets
- `src/web/routes/browse.py` — Post data for casting
- `src/repositories/posts.py` — Post data retrieval

### Established Patterns
- **Web routes:** FastAPI routers in `src/web/routes/`
- **Templates:** Jinja2 templates with block inheritance
- **Static files:** Served from `src/web/static/`
- **Pagination:** Cursor-based for efficient data transfer

### Integration Points
- Cast button in `base.html` navigation
- JavaScript in `static/js/cast.js` for sender API
- Receiver HTML at `templates/receiver.html`
- Custom message namespace: `urn:x-cast:com.bookmarked.posts`

</code_context>

<specifics>
## Specific Ideas

- Cast button shows "Cast to TV" tooltip when devices available
- Mini controller slides up from bottom when casting
- Post card shows cast icon overlay when session active
- Receiver shows loading animation while fetching post data
- Author avatar and username prominent on TV display

</specifics>

<deferred>
## Deferred Ideas

- Queue management (play next, shuffle) — deferred to v1.2
- Voice control via Google Assistant — out of scope
- Remote control from phone app — out of scope for v1.1

</deferred>