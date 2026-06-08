# Requirements: X Bookmarked Posts Organizer

**Defined:** 2026-04-18
**Core Value:** Resurface bookmarked posts on a spaced-repetition schedule so they stay fresh in mind

---

## v1.3 Requirements (Active)

Requirements for Milestone v1.3 — LAN Casting Support (locally-trusted SSL certificates for mobile access).

### Certificate Setup (CERT)

- [ ] **CERT-01**: User can check mkcert installation status via CLI
  - `xbm lan-cert status` reports whether mkcert is installed
  - Reports location of local CA (CAROOT directory)
  - Reports whether CA is installed in system trust store

- [ ] **CERT-02**: User can generate LAN-accessible SSL certificates via CLI
  - `xbm lan-cert generate` creates localhost certificate + LAN IP certificate
  - Certificates stored in `data/certs/` directory
  - 2-year validity for leaf certificates (mkcert default)
  - Uses mkcert subprocess integration (no Python API available)

- [ ] **CERT-03**: User can find instructions for installing CA on devices
  - `xbm lan-cert guide` shows platform-specific instructions
  - Guides for macOS, Windows, Linux, iOS, Android
  - Instructions include both system trust store and browser-specific steps

- [x] **CERT-04**: System detects LAN IP automatically for certificate generation
  - UDP socket trick (`socket.connect(('8.8.8.8', 80))`) for primary IP
  - Certificates include both localhost and LAN IP as SANs
  - Works behind NAT and on multi-interface machines

### Network Binding (NET)

- [ ] **NET-01**: Web server binds to all network interfaces when LAN mode enabled
  - `xbm web --lan` binds to `0.0.0.0` instead of `127.0.0.1`
  - LAN IP displayed in console after startup
  - Clear distinction between localhost and LAN URLs in output

- [ ] **NET-02**: Web server serves HTTPS with mkcert-generated certificates
  - Uvicorn configured with `ssl_keyfile` and `ssl_certfile`
  - Certificates loaded from `data/certs/` directory
  - Graceful error if certificates don't exist

- [ ] **NET-03**: Mobile browsers can access web app without certificate warnings
  - HTTPS works on LAN IP after CA installation
  - Cast SDK loads successfully (requires HTTPS)
  - No self-signed certificate bypass hacks needed

### Platform Guides (PLAT)

- [ ] **PLAT-01**: macOS guide covers Keychain CA installation
  - Command: `mkcert -install` (automatic for system + browsers)
  - Safari and Chrome trust certificates immediately
  - Certificate Trust Settings in Keychain Access for verification

- [ ] **PLAT-02**: Windows guide covers certificate store installation
  - Command: `mkcert -install` (Current User store)
  - Local Machine store requires Administrator: `mkcert -install -install`
  - Works in Edge and Chrome after installation

- [ ] **PLAT-03**: Linux guide covers system CA installation
  - Command: `mkcert -install` (adds to system trust store)
  - Location: `/usr/local/share/ca-certificates/`
  - Run `sudo update-ca-certificates` after installation

- [ ] **PLAT-04**: iOS guide covers profile installation and full trust enablement
  - Step 1: Transfer CA to device (AirDrop, email, web download)
  - Step 2: Install profile in Settings > General > VPN & Device Management
  - Step 3: Enable full trust in Settings > General > About > Certificate Trust Settings
  - Safari requires step 3 for HTTPS to work

- [ ] **PLAT-05**: Android guide covers CA installation and network security config
  - Step 1: Settings > Security > Certificate management > Install certificate
  - Step 2: Select CA certificate from storage
  - Step 3: For Android 7+, create `network_security_config.xml` to trust user certs
  - Chrome requires user cert trust configuration for HTTPS

### Maintenance (MAINT)

- [ ] **MAINT-01**: User can check certificate status and expiration
  - `xbm lan-cert status` shows certificate file paths
  - Shows creation date and expiration date
  - Shows certificate SANs (localhost, LAN IP)
  - Warns if certificates expire within 30 days

- [ ] **MAINT-02**: User can regenerate certificates when expired or LAN IP changes
  - `xbm lan-cert generate --force` regenerates certificates
  - Old certificates backed up before replacement
  - Warning displayed if certificates are still valid (confirm intent)

---

## v1.2 Requirements (Complete)

Requirements for Milestone v1.2 — Enhanced Post Rendering (retweets and quote tweets).

### Storage (STR)

- [x] **STR-01**: User's synced bookmarks include embedded post data for retweets and quote tweets
  - System fetches `referenced_tweets.id`, `referenced_tweets.id.author_id`, and `referenced_tweets.id.attachments.media_keys` expansions from X API
  - System stores original tweet content in `embedded_posts` table

- [x] **STR-02**: Each post has a type indicating whether it is an original, retweet, or quote tweet
  - `post_type` column stores 'original', 'retweet', or 'quote'
  - `embedded_post_id` references the original tweet for retweets/quotes

- [x] **STR-03**: System handles deleted or protected original posts gracefully
  - Embedded posts have an `available` flag (default true)
  - When X API doesn't return referenced post, mark as unavailable
  - Display shows "Original post unavailable" instead of crashing

### Web Display (WEB)

- [x] **WEB-07**: Quote tweets display user's commentary above the embedded original post
  - Nested card layout with clear visual separation
  - "Quoting @username" label with original content in bordered box
  - Original author avatar, name, and handle visible

- [x] **WEB-08**: Retweets display original author's content with attribution
  - "Reposted" or "Retweeted" indicator with retweeter info
  - Original author prominently displayed
  - Original text, media, and links rendered

- [x] **WEB-09**: Embedded posts render images and video from the original post
  - Media URLs from referenced tweet stored and displayed
  - Same media rendering as regular posts (grid layout, lightbox)

- [x] **WEB-10**: When embedded post is unavailable, user sees a clear placeholder
  - "Original post unavailable" message
  - Original author info if known (from reference ID)
  - Link to X for users who want to investigate

### CLI Display (CLI)

- [x] **CLI-06**: Quote tweets render with Rich Panel showing nested structure
  - User's commentary in main panel
  - Original post in nested border style
  - Clear visual hierarchy with colors

- [x] **CLI-07**: Retweets show "Reposted" indicator with original content
  - "Reposted from @username" header
  - Original text and author info

- [x] **CLI-08**: CLI displays media URLs from embedded posts
  - Shows image/video links for embedded content
  - Same media handling as regular posts

### Cast Display (CAST)

- [x] **CAST-06**: Cast receiver displays embedded posts on TV with optimized layout
  - Larger text sizes for TV readability
  - Nested cards for quote tweets
  - Full-width media display for embedded images

- [x] **CAST-07**: Cast receiver uses high-contrast visual styling for embedded posts
  - Distinct background color for embedded content
  - Clear borders separating quoter's content from original
  - Author info prominently displayed

- [x] **CAST-08**: Cast receiver shows unavailable placeholder when embedded post deleted
  - TV-friendly "Original post unavailable" message
  - Graceful degradation instead of blank space

---

## Future Requirements (Deferred)

### Search Integration (Future)

- [ ] **SRCH-F01**: FTS5 search includes embedded post text
  - Original post content searchable for retweets/quotes
  - Requires schema change to FTS5 virtual table

### Metrics Inheritance (Future)

- [ ] **MET-F01**: Retweets show original post's like/retweet counts
  - Public metrics from original stored and displayed
  - Snapshot at sync time, not live

### Recursive Quotes (Future)

- [ ] **REC-F01**: Support quote-of-quote chains beyond 2 levels
  - Currently flattened to 1 level of nesting
  - Future: show "Quoted from @user" link for deeper chains

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Thread context expansion | Only individual bookmarked posts, not conversation threads |
| Live retweet counts | Metrics stored at sync time, not fetched on-demand |
| Quote-of-quote chains | Limit to 1 level of nesting, link to X for deeper context |
| Real-time sync | Scheduled fetches are sufficient |
| Mobile native app | Web app with casting as fallback |
| Auto-download mkcert | User installs manually via package manager (less error-prone) |
| Automatic cert renewal | Explicit regeneration required for transparency |
| Cloud hosting | Local-only deployment |

---

## Traceability

### v1 Requirements (Complete)

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| STOR-01 | Phase 1 | Complete |
| STOR-02 | Phase 1 | Complete |
| DATA-01 | Phase 2 | Complete |
| DATA-02 | Phase 2 | Complete |
| DATA-03 | Phase 2 | Complete |
| DATA-04 | Phase 2 | Complete |
| DATA-05 | Phase 2 | Complete |
| STOR-03 | Phase 2 | Complete |
| CLI-01 | Phase 2 | Complete |
| CLI-05 | Phase 2 | Complete |
| SRCH-01 | Phase 3 | Complete |
| SRCH-02 | Phase 3 | Complete |
| SRCH-03 | Phase 3 | Complete |
| NOTE-01 | Phase 3 | Complete |
| NOTE-02 | Phase 3 | Complete |
| CLI-03 | Phase 3 | Complete |
| IMEX-01 | Phase 3 | Complete |
| IMEX-02 | Phase 3 | Complete |
| IMEX-03 | Phase 3 | Complete |
| MAINT-01 | Phase 3 | Complete |
| MAINT-02 | Phase 3 | Complete |
| ORG-01 | Phase 4 | Complete |
| ORG-02 | Phase 4 | Complete |
| ORG-03 | Phase 4 | Complete |
| ORG-04 | Phase 4 | Complete |
| CLI-04 | Phase 4 | Complete |
| SPAC-01 | Phase 5 | Complete |
| SPAC-02 | Phase 5 | Complete |
| SPAC-03 | Phase 5 | Complete |
| SPAC-04 | Phase 5 | Complete |
| CLI-02 | Phase 5 | Complete |

### v1.1 Requirements (Complete)

| Requirement | Phase | Status |
|-------------|-------|--------|
| WEB-01 | Phase 6 | Complete |
| WEB-02 | Phase 6 | Complete |
| WEB-03 | Phase 6 | Complete |
| WEB-04 | Phase 6 | Complete |
| WEB-05 | Phase 6 | Complete |
| WEB-06 | Phase 6 | Complete |
| CAST-01 | Phase 7 | Complete |
| CAST-02 | Phase 7 | Complete |
| CAST-03 | Phase 7 | Complete |
| CAST-04 | Phase 7 | Complete |
| CAST-05 | Phase 7 | Complete |
| RCVR-01 | Phase 7 | Complete |
| RCVR-02 | Phase 7 | Complete |
| RCVR-03 | Phase 7 | Complete |

### v1.2 Requirements (Complete)

| Requirement | Phase | Status |
|-------------|-------|--------|
| STR-01 | Phase 8 | Complete |
| STR-02 | Phase 8 | Complete |
| STR-03 | Phase 8 | Complete |
| WEB-07 | Phase 9 | Complete |
| WEB-08 | Phase 9 | Complete |
| WEB-09 | Phase 9 | Complete |
| WEB-10 | Phase 9 | Complete |
| CLI-06 | Phase 10 | Complete |
| CLI-07 | Phase 10 | Complete |
| CLI-08 | Phase 10 | Complete |
| CAST-06 | Phase 11 | Complete |
| CAST-07 | Phase 11 | Complete |
| CAST-08 | Phase 11 | Complete |

### v1.3 Requirements (Planned)

| Requirement | Phase | Status |
|-------------|-------|--------|
| CERT-01 | Phase 12 | Planned |
| CERT-02 | Phase 12 | Planned |
| CERT-03 | Phase 12 | Planned |
| CERT-04 | Phase 12 | Planned |
| MAINT-01 | Phase 12 | Planned |
| MAINT-02 | Phase 12 | Planned |
| NET-01 | Phase 13 | Planned |
| NET-02 | Phase 13 | Planned |
| NET-03 | Phase 13 | Planned |
| PLAT-01 | Phase 13 | Planned |
| PLAT-02 | Phase 13 | Planned |
| PLAT-03 | Phase 13 | Planned |
| PLAT-04 | Phase 13 | Planned |
| PLAT-05 | Phase 13 | Planned |

**Coverage:**
- v1 requirements: 34 total (Complete)
- v1.1 requirements: 14 total (Complete)
- v1.2 requirements: 13 total (Complete)
- v1.3 requirements: 14 total (Planned)
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-04-18*
*Last updated: 2026-06-08 after v1.3 requirements added*