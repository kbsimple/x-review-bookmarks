# Phase 14: Static Export - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a CLI command `xbm export-static` that generates a deployable static web app with embedded JSON data for hosting on Netlify. Users run the command, get a `data/static-export/` directory, and drag-and-drop it to Netlify for a public-facing bookmark viewer with client-side search and date filtering.

This phase delivers:
- `xbm export-static` CLI command with optional `--output PATH` flag
- Multiple JSON data files: posts.json, tags.json, topics.json, review_state.json, search-index.json
- Single self-contained `index.html` with inline CSS + JS (no build step, no external deps)
- Client-side search across text + author + tags + topics (native Array.filter)
- Date filtering with exact dates and shortcuts (This week, Last week, This month, Last month, Last 3 months, This Year, Older)
- Netlify deployment instructions printed to console after export
- Optional `netlify.toml` in output directory for configuration

**Out of scope:**
- Netlify API integration (no auto-deploy — user drag-and-drops)
- Cloudflare Pages support (Netlify-only for now)
- Authentication on static site (public viewer only)
- Casting from static site (local-only feature)
- Write operations (no notes/ratings from static viewer)

</domain>

<decisions>
## Implementation Decisions

### JSON Output Structure
- Multiple JSON files in the output directory: posts.json, tags.json, topics.json, review_state.json, search-index.json
- Each file independently loadable (not nested in a single combined file)
- Posts.json embeds referenced post data (retweets, quote tweets) inline in each post object
- Extend existing ExportService JSON format — adds tags, topics, embedded_post fields
- review_state.json includes due_date and interval (FSRS scheduling state) so users can see review progress
- search-index.json is pre-built at export time with denormalized fields: text, author_username, tags joined, topic names joined, created_at (ISO string), created_at_ts (Unix timestamp for date filtering)

### Static Web App
- Single `index.html` with inline CSS + JS (no build step, drag-and-drop deployable)
- Standalone minimal app — no FastAPI dependency, independently maintainable
- All posts loaded into memory on page load (efficient for 100-500 posts)
- Optional `netlify.toml` in output directory (sets cache headers, redirect rules)

### Client-Side Search and Date Filtering
- Push complexity to export time: pre-build search-index.json with all searchable fields denormalized
- Native `Array.filter()` on loaded search index — zero client dependencies, instant results
- Searchable fields: post text + author username + tags + topic names
- Date filtering with shortcuts:
  - "This week" — posts created in the last 7 days
  - "Last week" — posts created 8-14 days ago
  - "This month" — posts created in the current calendar month
  - "Last month" — posts created in the prior calendar month
  - "Last 3 months" — posts created in the last 90 days
  - "This Year" — posts created in the current calendar year
  - "Older" — posts created more than 1 year ago
- Sort options: newest first (default), oldest first, by author (alphabetical)
- Date range computed at runtime against created_at_ts in search index

### Deployment — Netlify
- Output directory: `data/static-export/` by default, `--output PATH` to override
- Overwrite silently on re-run (matches existing `xbm export` behavior)
- Console instructions after export: drag-and-drop URL, or `netlify deploy --dir data/static-export/`
- netlify.toml included with: `publish = "."` (relative to the export dir) and cache headers for JSON files
- No automatic deployment — user initiates via Netlify UI or Netlify CLI

### Claude's Discretion
- Exact HTML/CSS styling and color palette for the static viewer
- Column layout and card design in the viewer
- How "unavailable" embedded posts are displayed in static viewer
- Exact netlify.toml contents

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/services/export.py` — ExportService.export_json() establishes JSON format: {version, exported_at, source, posts: [...]}. Extend this or create StaticExportService that builds on the same repository layer.
- `src/repositories/posts.py`, `tags.py`, `topics.py`, `review_state.py` — All repositories accessible via get_connection()
- `src/repositories/embedded_posts.py` — EmbeddedPostsRepository for querying referenced posts
- `src/config.py` — Settings and get_database_path() for locating data/
- `src/cli/main.py` — Typer app with Rich console; add `export-static` as new command

### Established Patterns
- CLI commands use `typer.Typer()` with Rich console output (Panel, Table, Progress)
- Database access: `get_connection()` → connection → repository instantiation
- File output: write to Path objects, display summary Table after completion
- Error handling: Rich Panel with red border for errors, display actionable command

### Integration Points
- Add `export_static` command to `src/cli/main.py` Typer app
- New service file: `src/services/static_export.py`
- Output lands in `data/static-export/` (alongside existing `data/` directory structure)
- No new database schema needed — reads from existing tables

</code_context>

<specifics>
## Specific Ideas

- User confirmed: "push complexity to export time to optimize for the simplest and most effective client experience"
- Date filtering must include both exact date search and shortcut presets (This week, Last week, This month, Last month, Last 3 months, This Year, Older)
- Netlify is the sole hosting target for this phase
- User gave discretion on JSON structure if a different design is more advantageous
- User gave discretion on viewer app design ("create a separate viewer app to simplify the design as needed")

</specifics>

<deferred>
## Deferred Ideas

- Cloudflare Pages support — mentioned in ROADMAP but deferred to Netlify-only for this phase
- Auto-deploy via Netlify API — would require Netlify PAT, deferred for simplicity
- Sort by topic/tag in viewer — not requested, out of scope
- Public shareable links to individual posts — out of scope for static viewer
</deferred>
