# X Bookmarked Posts Organizer

A CLI tool that syncs your X (Twitter) bookmarks and resurfaces them on a spaced-repetition schedule so valuable content stays fresh in mind.

**Live viewer:** [xbm-viewer-export.netlify.app](https://xbm-viewer-export.netlify.app)

## Features

- **Sync bookmarks** from X API to local SQLite storage
- **Spaced repetition** resurfaces posts at optimal intervals (FSRS algorithm)
- **Full-text search** with FTS5 (search by content, author, date range)
- **Topic organization** with AI-powered suggestions
- **Static export** — publish to Netlify as a browsable web app
- **Web interface** for browsing on desktop or TV via Google Cast
- **Data portability** — export/import JSON or CSV

## Installation

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e .
```

## Quick Start

```bash
# 1. Authenticate with X (OAuth 2.0 PKCE flow)
xbm auth

# 2. Initialize the database
xbm init

# 3. Sync your bookmarks
xbm sync

# 4. Export to a static site and publish to Netlify
xbm export-static --rich-embeds        # builds data/static-export/
netlify deploy --dir data/static-export/ --prod
```

### Export to Netlify (preferred publishing method)

`xbm export-static` generates a self-contained static web app — no server required.
Deploy it once and re-deploy after each sync to keep the site current.

```bash
# Basic export (no Twitter widgets, fastest)
xbm export-static

# Rich export: fetches native X embed HTML — renders native tweet widgets in the viewer
xbm export-static --rich-embeds

# Limit to most recent N posts
xbm export-static --rich-embeds --limit 200

# Custom output directory
xbm export-static --output ~/Desktop/bookmarks-site
```

Output files written to `data/static-export/` (or `--output` path):

| File | Purpose |
|------|---------|
| `index.html` | Single-file viewer — carousel + stream modes, search, date filter |
| `posts.json` | All post data |
| `search-index.json` | Denormalized search index for client-side filtering |
| `tags.json` | Tag definitions |
| `topics.json` | Topic taxonomy |
| `review_state.json` | Spaced-repetition scheduling state |
| `netlify.toml` | Cache headers for JSON files |

**Deploy to Netlify:**

```bash
# Option 1: Netlify CLI (recommended for repeat deploys)
netlify deploy --dir data/static-export/ --prod

# Option 2: Drag-and-drop
# Open netlify.com/drop and drag the data/static-export/ folder
```

> **Note:** Open the viewer via Netlify, not by double-clicking `index.html`.
> Direct `file://` access blocks `fetch()` so the JSON data files won't load.

### Other browsing options

```bash
# Browse posts in the terminal
xbm browse
xbm browse --order random    # random order
xbm browse --order oldest    # oldest first

# Review posts due for spaced repetition
xbm due      # see what's due
xbm review   # interactive review session

# Start the local web app (HTTPS, works with Google Cast)
xbm web      # opens https://localhost:8000
xbm web --lan  # expose on local network (TV, phone)
```

## CLI Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `xbm auth` | Authenticate with X via OAuth 2.0 PKCE |
| `xbm init` | Initialize SQLite database |
| `xbm verify` | Verify current authentication status |
| `xbm sync` | Sync bookmarks from X API |

### Browsing & Search

| Command | Description |
|---------|-------------|
| `xbm browse` | Browse all posts (newest/oldest/random) |
| `xbm search <query>` | Full-text search posts |
| `xbm due` | View posts due for review |
| `xbm stats` | View post statistics |

### Publishing

| Command | Description |
|---------|-------------|
| `xbm export-static` | Export to static files for Netlify deployment |
| `xbm export-static --rich-embeds` | Include native X widget HTML |
| `xbm export-static --limit N` | Export only the N most recent posts |

### Organization

| Command | Description |
|---------|-------------|
| `xbm note <post_id> <text>` | Add a note to a post |
| `xbm tag <post_id> <tag>` | Tag a post |
| `xbm topic --list` | List topics |
| `xbm suggest-topics` | Generate AI topic suggestions |
| `xbm review-topics` | Review AI topic suggestions |

### Review Management

| Command | Description |
|---------|-------------|
| `xbm review` | Interactive spaced-repetition session |
| `xbm reset <post_id>` | Reset review state for a post |
| `xbm seed` | Initialize review state for posts |

### Data Portability

| Command | Description |
|---------|-------------|
| `xbm export --format json` | Export posts to JSON |
| `xbm export --format csv` | Export posts to CSV |
| `xbm import <file.json>` | Import posts from JSON |
| `xbm check-links` | Check all links and flag dead ones |

### Web Application

| Command | Description |
|---------|-------------|
| `xbm web` | Start web server (https://localhost:8000) |
| `xbm web --port 3000` | Use custom port |
| `xbm web --no-open` | Don't auto-open browser |
| `xbm web --lan` | Expose on LAN (for TV / mobile access) |
| `xbm lan-cert --generate` | Generate LAN SSL certificates |
| `xbm lan-cert --guide` | CA installation guide for mobile |

## Configuration

Create `.env` with your X API credentials:

```
X_CLIENT_ID=your_client_id
X_CLIENT_SECRET=your_client_secret
```

Get credentials from [X Developer Portal](https://developer.twitter.com/en/portal/dashboard).

## Spaced Repetition

During review, choose when to see the post again:
- **[1] Keep fresh** — 3 days
- **[2] Review soon** — 2 weeks
- **[3] Review later** — 2 months

The scheduling uses the FSRS (Free Spaced Repetition Scheduler) algorithm for optimal retention.

## Data Storage

All data stored locally in SQLite:

| File | Description |
|------|-------------|
| `data/bookmarks.db` | Posts, tags, topics, review state |
| `data/tokens.json` | OAuth tokens (auto-managed) |
| `data/localhost.crt` | HTTPS certificate (auto-generated) |
| `data/localhost.key` | HTTPS private key (auto-generated) |
| `data/static-export/` | Static export output for Netlify |

## Requirements

- Python 3.9+
- X Developer API credentials (OAuth 2.0)

## License

MIT License — see [LICENSE](LICENSE)
