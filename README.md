# X Bookmarked Posts Organizer

A CLI tool that syncs your X (Twitter) bookmarks and resurfaces them on a spaced-repetition schedule so valuable content stays fresh in mind.

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

# 4. Browse your posts
xbm browse
xbm browse --order random    # random order
xbm browse --order oldest    # oldest first

# 5. Review posts due for spaced repetition
xbm due      # see what's due
xbm review   # interactive review session
```

## Main Commands

| Command | Description |
|---------|-------------|
| `xbm auth` | Authenticate with X via OAuth |
| `xbm init` | Initialize SQLite database |
| `xbm sync` | Sync bookmarks from X API |
| `xbm browse` | Browse all posts (newest/oldest/random) |
| `xbm due` | View posts due for review |
| `xbm review` | Interactive spaced-repetition session |
| `xbm stats` | View post statistics |
| `xbm search <query>` | Full-text search posts |
| `xbm note <post_id> <text>` | Add a note to a post |
| `xbm tag <post_id> <tag>` | Tag a post |
| `xbm topic --list` | List topics |

## Configuration

Create `.env.local` with your X API credentials:

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

## Data Storage

All data stored locally in SQLite:
- `data/bookmarks.db` — posts, tags, topics, review state
- `data/tokens.json` — OAuth tokens (auto-managed)

## License

MIT License — see [LICENSE](LICENSE)