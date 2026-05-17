# Feature Research

**Domain:** Local web app with Google Cast for displaying bookmarked posts on TV
**Researched:** 2026-05-17
**Confidence:** HIGH (official Google Cast documentation + verified web patterns)

## Context

This is a **subsequent milestone** (v1.1) adding web frontend and Google Cast integration to an existing Python CLI application. The CLI already provides:

- OAuth 2.0 PKCE authentication with X API
- SQLite storage with posts, tags, topics, review state
- FTS5 full-text search
- Topic clustering with AI suggestions
- FSRS-based spaced repetition scheduling

Research below focuses **only** on new features for the web app + casting milestone.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any cast-enabled web app. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Cast button in consistent location | Standard UI pattern for all cast-enabled apps per [Cast Design Checklist](https://developers.google.com/cast/docs/design_checklist/cast-button) | LOW | Use `<google-cast-launcher>` custom element; place in top-right corner |
| Cast button states (disconnected/connecting/connected) | Visual feedback is standard UX; users need to know connection state | LOW | Framework handles animation; use `--connected-color` and `--disconnected-color` CSS |
| HTTPS for sender app | Required for Web SDK to function; browsers block insecure contexts | LOW | Self-signed certs acceptable for local-only; `mkcert` for development |
| Mini controller while casting | Per [Sender App Guidelines](https://developers.google.com/cast/docs/design_checklist/sender): required during active session | MEDIUM | Bar at bottom of sender showing current content, play/pause, navigation |
| Volume control | Per Cast Design Checklist: mandatory on all platforms | LOW | Software slider on web; sync with receiver state |
| Session resumption after disconnect | Users don't want to re-find their content if connection drops | MEDIUM | Store session ID; use `requestSessionById()` on reconnect |
| State synchronization (paused/playing) | Sender and receiver must show same state per [UX Guidelines](https://developers.google.com/cast/docs/ux_guidelines) | MEDIUM | Monitor `IS_PAUSED_CHANGED`, `IS_CONNECTED_CHANGED` events |
| Pagination/infinite scroll | Standard for content browsing; users expect smooth scrolling | MEDIUM | Cursor-based pagination preferred for stable results per [fastapi-pagination](https://github.com/uriyyo/fastapi-pagination/) |
| Search with filters (text, topic, author, date) | Users cannot remember exact titles; FTS5 already built in CLI | MEDIUM | Extend existing FTS5 to web API; add topic/author filters |
| Responsive design | Works on mobile, tablet, desktop browsers | MEDIUM | CSS media queries; touch-friendly controls |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Media Browse landing page on TV | Content discovery without sender app; idle TV shows topic collections per [Media Browse docs](https://developers.google.com/cast/docs/web_receiver/media-browse) | HIGH | Use Cast Media Browse API; show topic-based collections when idle |
| Touch-optimized receiver for smart displays | Better UX on Nest Hub and similar devices | MEDIUM | Use `cast.framework.ui.Controls` with touch-optimized button layout |
| Stream transfer between devices | Continue reading on different screen (phone to TV to tablet) | MEDIUM | Enable `STREAM_TRANSFER` command; preserve position in custom data |
| Voice commands via Google Assistant | Hands-free navigation; "Show me my tech posts" | HIGH | Configure `supportedMediaCommands`; use `entity` for deep links |
| Deep links to specific posts | Jump directly to content from notification or shortcut | MEDIUM | Use `entity` property in LOAD requests; handle in message interceptor |
| Topic-based collections on TV | Organized browsing vs flat list; matches existing topic taxonomy | MEDIUM | Map topics to BrowseContent collections; use topic metadata |
| Reading position persistence | Resume where you left off across sessions | LOW | Store last viewed post ID in SQLite; pass in session custom data |
| Offline cache for posts | Continue reading without network (PWA pattern) | MEDIUM | Service worker caching; IndexedDB for post content |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for this use case.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time sync from X API | Users want instant updates | Adds complexity for minimal value; bookmarks are low-velocity (user already saved them) | Scheduled sync (existing CLI pattern); manual refresh button |
| Video playback in receiver | Users want full media support | Post images are primary content; video is rare; adds significant receiver complexity | Focus on text and image display; link to X for video |
| Multi-user session support | "What if my family wants to use it?" | Personal app; multi-user adds auth complexity without clear use case | Single-user session; document as personal use case |
| Native mobile apps (iOS/Android) | "Shouldn't we have mobile apps?" | Web app works on all platforms via browser; native adds 2x maintenance burden | PWA with offline support; add to home screen |
| Full-thread context display | Users want to see conversations | Project constraint from v1.0: no thread context in data model | Link to X for full thread; show author and post text only |
| Samsung Tizen native app | Original requirement stated in PROJECT.md | Samsung TV SDK is complex; Tizen app requires registration, certification, annual fee | Google Cast works on Samsung Smart TVs with Chromecast built-in (2016+) |
| Default Media Receiver | "Just use the built-in receiver" | Default receiver is video-focused; cannot display text posts properly per [Custom Receiver Guide](https://developers.google.com/cast/docs/web_receiver/basic) | Custom Web Receiver with Media Browse or custom UI |

---

## Feature Dependencies

```
Google Cast Integration
    └──requires──> HTTPS (required for Web SDK)
    └──requires──> Custom Web Receiver (for text/image content)
                         └──requires──> Hosting for receiver HTML/JS
    └──requires──> Cast button component (<google-cast-launcher>)
                         └──requires──> Cast SDK script load from CDN
    └──requires──> Session state management
                         └──requires──> Storage for session ID (SQLite)

Pagination/Infinite Scroll
    └──requires──> Cursor-based API endpoint
                         └──requires──> Index on sort column (created_at)
    └──requires──> Frontend IntersectionObserver
                         └──requires──> Loading state management

Search with Filters
    └──requires──> FTS5 query extension (already built in CLI)
    └──requires──> API endpoints for topics, authors
                         └──requires──> SQLite indexes on foreign keys

Media Browse on TV (optional differentiator)
    └──requires──> Custom Web Receiver app
    └──requires──> BrowseItem data structure
                         └──requires──> Topic-to-collection mapping
    └──requires──> LOAD message interceptor
                         └──requires──> Entity-to-post ID resolution
```

### Dependency Notes

- **Cast requires HTTPS**: Web Sender SDK fails silently without secure context. Self-signed certificates work for local use with `mkcert` for development.
- **Custom Web Receiver required**: Default Media Receiver is designed for video/audio. Text/image content needs custom receiver with Media Browse or custom UI per [official docs](https://developers.google.com/cast/docs/web_receiver/basic).
- **Session state requires SQLite**: Session IDs and custom data need persistence. Use existing SQLite database.
- **Cursor pagination requires stable sort**: Use `created_at` or `id` for consistent cursor behavior. Existing schema has these indexes.

---

## MVP Definition

### Launch With (v1.1)

Minimum viable product — what's needed to validate the web app + casting concept.

- [ ] **FastAPI web app with HTTPS** — Foundation for all web features; serves Jinja2 templates
- [ ] **Shared authentication with CLI** — Reuse existing OAuth 2.0 tokens from SQLite; no separate login
- [ ] **Post browsing with pagination** — Cursor-based API endpoint + infinite scroll frontend
- [ ] **Search/filter (text, topic, author, date)** — Extend existing FTS5 to web API
- [ ] **Cast button with session management** — Connect/disconnect/reconnect handling
- [ ] **Mini controller while casting** — Show current post, navigation controls per [Cast Design Checklist](https://developers.google.com/cast/docs/design_checklist/sender)
- [ ] **Custom Web Receiver for posts** — Display post text, author, images on TV; basic navigation

### Add After Validation (v1.2+)

Features to add once core is working.

- [ ] **Expanded controller with topic navigation** — Browse topics while casting; jump between collections
- [ ] **Reading position persistence** — Resume where you left off across sessions
- [ ] **Media Browse landing page** — Content discovery on TV without sender; show collections when idle
- [ ] **Offline cache for posts** — Service worker + IndexedDB for offline reading
- [ ] **Touch-optimized receiver** — Better smart display experience (Nest Hub)

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Voice commands via Google Assistant** — Hands-free navigation
- [ ] **Stream transfer between devices** — Continue reading on different screen
- [ ] **PWA with offline support** — Install prompt, push notifications
- [ ] **Deep links to specific posts** — Shareable links to individual posts

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| FastAPI web app with HTTPS | HIGH | MEDIUM | P1 |
| Shared authentication | HIGH | LOW | P1 |
| Post browsing pagination | HIGH | MEDIUM | P1 |
| Search/filter | HIGH | MEDIUM | P1 |
| Cast button + session | HIGH | MEDIUM | P1 |
| Mini controller | HIGH | MEDIUM | P1 |
| Custom Web Receiver | HIGH | HIGH | P1 |
| Expanded controller | MEDIUM | LOW | P2 |
| Reading position persistence | MEDIUM | LOW | P2 |
| Media Browse landing page | MEDIUM | MEDIUM | P2 |
| Touch-optimized receiver | LOW | MEDIUM | P3 |
| Voice commands | LOW | HIGH | P3 |
| Offline cache | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

For web apps with casting (text/image content, not video):

| Feature | PictaCast | PixFolio | Cast Player | Our Approach |
|---------|-----------|----------|-------------|--------------|
| Content source | Local folders | Cloud services (Google Photos, etc.) | iPhone library | SQLite database (bookmarked posts) |
| Primary use case | Photo slideshows | Digital photo frame | Photo/video casting | Bookmarked text posts with images |
| Cast support | Yes (primary) | Yes | Yes | Yes (primary goal) |
| Search/filter | Limited (by folder) | By album/date | By album | Full-text + topic + author + date |
| Organization | Folders | Albums | Albums | Topics (AI-suggested from v1.0) |
| Reading position | No | No | No | Yes (planned) |
| Smart display UI | Basic | Photo frame mode | Basic | Media Browse landing page (planned) |
| Text content | No | No | No | Yes (primary content type) |

**Key Differentiation:** This is a **text-first** casting app. Existing photo casting apps handle images well but have no concept of post text, author metadata, topics, or spaced repetition scheduling. The combination of text content + topics + scheduled resurfacing + TV display is unique.

---

## Technical Implementation Notes

### Google Cast Architecture (Sender-Receiver Model)

Per [Cast SDK Documentation](https://developers.google.com/cast/docs/web_sender/integrate):

1. **Sender App** (FastAPI + Jinja2 web app)
   - Loads Cast SDK from Google CDN
   - Uses `<google-cast-launcher>` custom element for Cast button
   - Manages session via `CastContext` singleton
   - Controls receiver via `RemotePlayer` and `RemotePlayerController`

2. **Receiver App** (Custom Web Receiver)
   - HTML5/JS app running on Cast device
   - Uses `cast-media-player` element for built-in UI
   - Handles LOAD messages via `PlayerManager.setMessageInterceptor()`
   - For text/image content: custom UI or Media Browse API per [Media Browse docs](https://developers.google.com/cast/docs/web_receiver/media-browse)

3. **Session Flow**
   - User clicks Cast button → Sender discovers devices
   - User selects device → Sender launches receiver app
   - Sender sends LOAD request with content metadata
   - Receiver displays content, sends status updates
   - Sender displays mini controller with controls

### Cast Requirements for Text/Image Content

Unlike video apps, displaying text posts requires:

1. **Custom Web Receiver**: Default Media Receiver is video-focused. Need custom receiver for:
   - Displaying post text and images
   - Custom layout for post cards
   - Navigation between posts

2. **Media Browse API**: Best option for content discovery on TV per [Media Browse docs](https://developers.google.com/cast/docs/web_receiver/media-browse):
   - Displays grid/list of items with images
   - Maximum 30 items for performance
   - Works when receiver is idle (landing page)
   - Handles selection via LOAD message

3. **Custom Message Passing**: For advanced interactions
   - Use `CastSession.sendMessage()` for custom commands
   - Receiver handles via `CastReceiverContext.addCustomMessageListener()`

### Common Pitfalls for Cast-Enabled Apps

Per [Cast Web Receiver Guide](https://developers.google.com/cast/docs/web_receiver/basic) and [UX Guidelines](https://developers.google.com/cast/docs/ux_guidelines):

| Pitfall | Consequence | Prevention |
|---------|-------------|------------|
| HTTP instead of HTTPS | Cast SDK fails silently | Use `mkcert` for development; configure HTTPS in production |
| Missing `receiverApplicationId` | Cannot find receiver app | Register in Cast Developer Console; use ID in `setOptions()` |
| Not handling session state | UI shows wrong state | Monitor all state events; sync sender and receiver |
| CORS/mixed-content errors | Media fails to load | Configure proper CORS headers on media URLs |
| Overloading receiver | Performance issues on low-power devices | Keep receiver lightweight; limit items in Media Browse to 30 |
| Not testing on real device | Emulators don't catch all issues | Test on actual Chromecast/Nest Hub |
| Multiple video elements in DOM | Receiver crashes | Only one video element active at any time |
| Abrupt state transitions | Poor UX | Use fade-in/fade-out for loading and state changes |

### Pagination Strategy

Per [fastapi-pagination](https://github.com/uriyyo/fastapi-pagination/) and [Leapcell](https://leapcell.io/blog/implementing-diverse-pagination-strategies-in-drf-and-fastapi):

**Use cursor-based pagination** for infinite scroll (not offset-based):

- **Why:** Consistent performance at any depth, stable results during concurrent writes
- **How:** Use `created_at` or `id` as cursor; encode as base64 string
- **Limitation:** No random page access (acceptable for infinite scroll)

**Performance comparison:**

| Strategy | 1K Records | 100K Records | 1M Records |
|----------|-----------|---------------|------------|
| Offset pagination | 10ms | 500ms | 5s |
| Cursor pagination | 10ms | 15ms | 20ms |

---

## Sources

### Google Cast Documentation (HIGH confidence)
- [Google Cast Design Checklist - Sender](https://developers.google.com/cast/docs/design_checklist/sender)
- [Google Cast Design Checklist - Cast Button](https://developers.google.com/cast/docs/design_checklist/cast-button)
- [Google Cast UX Guidelines](https://developers.google.com/cast/docs/ux_guidelines)
- [Integrate Cast SDK into Web Sender App](https://developers.google.com/cast/docs/web_sender/integrate)
- [Custom Web Receiver Guide](https://developers.google.com/cast/docs/web_receiver/basic)
- [Add Core Features to Custom Web Receiver](https://developers.google.com/cast/docs/web_receiver/core_features)
- [Media Browse for Cast](https://developers.google.com/cast/docs/web_receiver/media-browse)
- [Cast SDK Reference](https://developers.google.com/cast/docs/reference/web_receiver)

### Web App Patterns (MEDIUM confidence)
- [Ultimate Guide to Build Cast Web Receiver](https://www.vikramrajput.com/2025/01/16/ultimate-guide-to-build-a-cast-web-receiver-api-application-from-scratch/) — Community guide
- [FastAPI Pagination Strategies](https://leapcell.io/blog/implementing-diverse-pagination-strategies-in-drf-and-fastapi) — Community, verified against official docs
- [fastapi-pagination GitHub](https://github.com/uriyyo/fastapi-pagination/) — Open source, actively maintained
- [FastAPI Jinja2 Templates Tutorial](https://realpython.com/fastapi-jinja2-template/) — Real Python, authoritative

### Competitor Apps (MEDIUM confidence)
- PictaCast - Chrome Web Store listing
- PixFolio - Google Play Store listing
- Cast Player - Apple App Store listing

---
*Feature research for: Web app with Google Cast for bookmarked posts*
*Researched: 2026-05-17*