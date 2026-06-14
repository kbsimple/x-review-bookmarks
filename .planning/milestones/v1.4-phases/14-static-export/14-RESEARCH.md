# Phase 14: Static Export — Research

**Researched:** 2026-06-13
**Domain:** Python static-site export, vanilla-JS single-page viewer, Netlify static hosting
**Confidence:** HIGH — all findings verified against actual source files; no external API calls needed

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Multiple JSON files: posts.json, tags.json, topics.json, review_state.json, search-index.json
- Each file independently loadable (not nested in a combined file)
- posts.json embeds referenced post data (retweets/quote tweets) inline per post object
- Extend existing ExportService JSON format — adds tags, topics, embedded_post fields
- review_state.json includes due_date and interval (FSRS scheduling state)
- search-index.json pre-built at export time with denormalized fields: text, author_username, tags joined, topic names joined, created_at (ISO string), created_at_ts (Unix timestamp for date filtering)
- Single index.html with inline CSS + JS (no build step, drag-and-drop deployable)
- All posts loaded into memory on page load (efficient for 100–500 posts)
- Native Array.filter() on loaded search index — zero client dependencies
- Date filtering shortcuts: This week, Last week, This month, Last month, Last 3 months, This Year, Older
- Sort: newest first (default), oldest first, by author (alphabetical)
- Output directory: data/static-export/ by default, --output PATH to override
- Overwrite silently on re-run (matches existing xbm export behavior)
- Console instructions after export: drag-and-drop URL, or netlify deploy --dir
- netlify.toml included in output with cache headers for JSON files
- No automatic deployment — user initiates via Netlify UI or Netlify CLI

### Claude's Discretion
- Exact HTML/CSS styling and color palette for the static viewer
- Column layout and card design in the viewer
- How "unavailable" embedded posts are displayed in static viewer
- Exact netlify.toml contents

### Deferred Ideas (OUT OF SCOPE)
- Cloudflare Pages support
- Auto-deploy via Netlify API
- Sort by topic/tag in viewer
- Public shareable links to individual posts
</user_constraints>

---

## Summary

Phase 14 adds a single new CLI command (`xbm export-static`) and a new service (`StaticExportService`) that reads every table in the database and emits five JSON files plus one `index.html` plus one `netlify.toml` into `data/static-export/`. No new schema migrations are needed — the phase is purely read-only against the existing v6 schema.

The trickiest part is constructing the correct JOIN queries to produce the per-post denormalized data that both `posts.json` and `search-index.json` require. The existing `PostsRepository.get_paginated_with_embedded()` shows exactly how to do the LEFT JOIN with `embedded_posts`; the new service needs an equivalent `get_all_with_embedded()` variant that returns all rows without pagination. Tags and topics require two extra queries each (list all, then get per-post assignments); the most efficient approach is a single bulk JOIN that fetches every post's tags and topics in one pass rather than N+1 per-post lookups.

The index.html is a self-contained single file — all CSS and JS inline, loads the five JSON files via `fetch()` relative to itself (works on Netlify and on local `file://` only if served, but Netlify is the stated target so `fetch()` is correct). The Netlify configuration is minimal: one `[build]` stanza and one `[[headers]]` rule to add cache-control headers to JSON files.

**Primary recommendation:** Create `src/services/static_export.py` as a standalone service that accepts a single `sqlite3.Connection` and instantiates all needed repositories internally. Add the CLI command `export-static` in `src/cli/main.py` using the same Rich progress + summary Table pattern as `xbm sync`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Read all posts with embedded data | Database/Repository | — | Existing LEFT JOIN pattern in PostsRepository |
| Read all tags + post assignments | Database/Repository | — | TagsRepository.list_tags() + bulk JOIN |
| Read all topics + post assignments | Database/Repository | — | TopicsRepository.list_topics() + bulk JOIN |
| Read all review states | Database/Repository | — | ReviewStateRepository (all rows query needed) |
| Build denormalized search index | Service (Python) | — | Merge posts + tags + topics at export time |
| Write JSON files | Service (Python) | — | json.dump with indent=2, UTF-8 |
| Generate index.html | Service (Python) | — | Python string template or inline f-string |
| Generate netlify.toml | Service (Python) | — | Static string, no templating needed |
| CLI command, progress, summary | CLI tier | — | Typer + Rich matching existing patterns |
| Client-side search + filtering | Browser | — | Vanilla JS Array.filter() on loaded JSON |
| Static hosting | CDN / Static (Netlify) | — | HTML + JSON files, no server needed |

---

## Technical Findings

### JSON Schema Design

All field names confirmed by reading actual repository `_row_to_dict()` implementations.

#### posts.json

```json
{
  "version": "1.0",
  "exported_at": "2026-06-13T12:00:00+00:00",
  "source": "xbm-static",
  "post_count": 42,
  "posts": [
    {
      "x_post_id": "1234567890",
      "created_at": "2024-01-15T10:30:00Z",
      "text": "Post content here",
      "author_id": "user_123",
      "author_username": "someuser",
      "author_display_name": "Some User",
      "media_urls": ["https://pbs.twimg.com/media/..."],
      "link_urls": ["https://example.com/article"],
      "bookmarked_at": "2024-01-16T08:00:00Z",
      "note": "My personal note",
      "post_type": "original",
      "tags": ["python", "ml"],
      "topics": [{"id": 1, "name": "Programming"}],
      "embedded_post": null
    }
  ]
}
```

For retweets/quotes, `embedded_post` is:

```json
{
  "x_post_id": "original_id",
  "created_at": "...",
  "text": "...",
  "author_username": "original_author",
  "author_display_name": "Original Author",
  "media_urls": [],
  "link_urls": [],
  "available": true
}
```

Fields excluded from static export (internal plumbing): `fetched_at`, `sync_version`, `link_status`.

#### tags.json

```json
{
  "version": "1.0",
  "exported_at": "...",
  "tags": [
    {
      "id": 1,
      "name": "python",
      "post_ids": ["post_001", "post_007"]
    }
  ]
}
```

`post_ids` list enables the viewer to filter posts by tag without a separate join.

#### topics.json

```json
{
  "version": "1.0",
  "exported_at": "...",
  "topics": [
    {
      "id": 1,
      "name": "Programming",
      "description": "Software development content",
      "parent_id": null,
      "post_ids": ["post_001", "post_002"]
    }
  ]
}
```

#### review_state.json

```json
{
  "version": "1.0",
  "exported_at": "...",
  "review_states": [
    {
      "post_id": "post_001",
      "scheduled_for": "2026-06-20T00:00:00",
      "last_reviewed": "2026-06-13T10:00:00",
      "review_count": 5,
      "state": 2,
      "stability": 12.5,
      "difficulty": 0.3
    }
  ]
}
```

Fields omitted from static export: `user_preference`, `step`, `fsrs_data` (internal FSRS plumbing not useful to the viewer). `state` integer maps to 0=new, 1=learning, 2=review, 3=relearning and can be displayed in the viewer.

#### search-index.json

```json
{
  "version": "1.0",
  "exported_at": "...",
  "entries": [
    {
      "id": "post_001",
      "text": "Python is great for ML",
      "author_username": "someuser",
      "author_display_name": "Some User",
      "tags": "python ml",
      "topics": "Programming Machine Learning",
      "created_at": "2024-01-15T10:30:00Z",
      "created_at_ts": 1705313400,
      "post_type": "original"
    }
  ]
}
```

`tags` and `topics` are space-joined strings so `Array.filter()` can do `entry.tags.includes(term)`. `created_at_ts` is a Unix timestamp (seconds since epoch) for fast JS date comparisons.

---

### Repository Queries

All verified by reading source files. [VERIFIED: source file inspection]

#### Existing methods usable as-is

| Method | File | What it returns |
|--------|------|-----------------|
| `PostsRepository.get_paginated_with_embedded()` | posts.py | Posts + LEFT JOIN embedded_posts, paginated |
| `TagsRepository.list_tags()` | tags.py | `[{id, name, created_at}]` — all tags |
| `TopicsRepository.list_topics()` | topics.py | `[{id, name, description, parent_id, created_at}]` |
| `TagsRepository.get_post_tags(post_id)` | tags.py | `[{id, name, created_at}]` per post |
| `TopicsRepository.get_post_topics(post_id)` | topics.py | `[{id, name, description, confidence, source, assigned_at}]` per post |

#### New methods needed

**`PostsRepository.get_all_with_embedded()`** — Equivalent to `get_paginated_with_embedded()` but returns all rows with no pagination limit. The existing `get_all()` (line 174–189 of posts.py) does `SELECT * FROM posts ORDER BY created_at DESC LIMIT ? OFFSET ?` and uses `_row_to_dict()` (not `_row_to_dict_with_embedded()`). A new method is needed:

```python
def get_all_with_embedded(self) -> list[dict[str, Any]]:
    query = """
        SELECT p.*,
               e.x_post_id as embedded_id,
               e.created_at as embedded_created_at,
               e.text as embedded_text,
               e.author_id as embedded_author_id,
               e.author_username as embedded_author_username,
               e.author_display_name as embedded_author_display_name,
               e.media_urls as embedded_media_urls,
               e.link_urls as embedded_link_urls,
               e.available as embedded_available
        FROM posts p
        LEFT JOIN embedded_posts e ON p.embedded_post_id = e.x_post_id
        ORDER BY p.created_at DESC
    """
    rows = self._conn.execute(query).fetchall()
    return [self._row_to_dict_with_embedded(row) for row in rows]
```

**`ReviewStateRepository.get_all()`** — The existing class has `get_state(post_id)`, `get_due_posts()`, and `get_stats()`, but no method to fetch all review states for export. New method:

```python
def get_all(self) -> list[dict[str, Any]]:
    rows = self._conn.execute(
        """SELECT post_id, scheduled_for, last_reviewed, review_count,
                  stability, difficulty, state
           FROM post_review_state
           ORDER BY post_id"""
    ).fetchall()
    return [dict(row) for row in rows]
```

**Bulk tag/topic fetch for efficiency** — Calling `get_post_tags(post_id)` per post is N+1 queries. The `StaticExportService` should instead query all assignments once:

```python
# Bulk fetch: post_id -> [tag_names]
rows = conn.execute(
    """SELECT pt.post_id, t.name
       FROM post_tags pt
       JOIN tags t ON pt.tag_id = t.id
       ORDER BY pt.post_id, t.name"""
).fetchall()
# Build dict: {post_id: [name, name, ...]}
```

```python
# Bulk fetch: post_id -> [topic dicts]
rows = conn.execute(
    """SELECT pt.post_id, t.id, t.name
       FROM post_topics pt
       JOIN topics t ON pt.topic_id = t.id
       ORDER BY pt.post_id, t.name"""
).fetchall()
```

```python
# Bulk fetch: tag_id -> [post_ids] for tags.json
rows = conn.execute(
    """SELECT tag_id, post_id FROM post_tags ORDER BY tag_id"""
).fetchall()
```

```python
# Bulk fetch: topic_id -> [post_ids] for topics.json
rows = conn.execute(
    """SELECT topic_id, post_id FROM post_topics ORDER BY topic_id"""
).fetchall()
```

These four queries replace N+1 patterns for a 100–500 post database.

---

### index.html Architecture

**JSON loading:** Use `fetch()` for all five files. `fetch()` from a relative path (`./data/posts.json`) works correctly when served from Netlify (HTTPS origin) but fails on local `file://` protocol. Since Netlify is the only target for this phase, `fetch()` is correct. Include a note in the console output about not double-clicking the file locally.

**Loading sequence:**

```javascript
// Load search index first (needed for all rendering)
// Load posts for detail rendering
// Load tags/topics/review_state for sidebar/metadata
Promise.all([
  fetch('search-index.json').then(r => r.json()),
  fetch('posts.json').then(r => r.json()),
  fetch('tags.json').then(r => r.json()),
  fetch('topics.json').then(r => r.json()),
  fetch('review_state.json').then(r => r.json())
]).then(([searchIndex, postsData, tagsData, topicsData, reviewData]) => {
  // Build lookup maps, render initial view
})
```

**Post card structure:**
```html
<div class="post-card" data-id="...">
  <div class="post-meta">@username · date</div>
  <div class="post-text">...</div>
  <div class="post-media"><!-- img tags --></div>
  <div class="post-tags"><!-- tag pills --></div>
  <!-- For retweets/quotes: nested embedded-post div -->
</div>
```

**Date filtering in vanilla JS:**

```javascript
function getDateRange(filter) {
  const now = new Date();
  const ts = Math.floor(now.getTime() / 1000);
  switch (filter) {
    case 'this_week':   return [ts - 7*86400, ts];
    case 'last_week':   return [ts - 14*86400, ts - 7*86400];
    case 'this_month':  return getThisMonthRange(now);
    case 'last_month':  return getLastMonthRange(now);
    case 'last_3_months': return [ts - 90*86400, ts];
    case 'this_year':   return getThisYearRange(now);
    case 'older':       return [0, ts - 365*86400];
    default:            return null; // no filter
  }
}

function filterEntries(entries, query, dateFilter, sortOrder) {
  let results = entries;
  if (query) {
    const q = query.toLowerCase();
    results = results.filter(e =>
      e.text.toLowerCase().includes(q) ||
      e.author_username.toLowerCase().includes(q) ||
      e.tags.toLowerCase().includes(q) ||
      e.topics.toLowerCase().includes(q)
    );
  }
  if (dateFilter) {
    const [from, to] = getDateRange(dateFilter);
    results = results.filter(e => e.created_at_ts >= from && e.created_at_ts <= to);
  }
  return sortResults(results, sortOrder);
}
```

**Sort implementation:**

```javascript
function sortResults(entries, order) {
  if (order === 'newest') return [...entries].sort((a, b) => b.created_at_ts - a.created_at_ts);
  if (order === 'oldest') return [...entries].sort((a, b) => a.created_at_ts - b.created_at_ts);
  if (order === 'author') return [...entries].sort((a, b) => a.author_username.localeCompare(b.author_username));
  return entries;
}
```

**Performance note:** For 500 posts, all data fits easily in memory (~1–2 MB JSON). Re-filtering on every keystroke is acceptable at this scale. A debounce of 150ms on the search input prevents excess renders.

---

### Netlify Configuration

The `netlify.toml` must be placed in the root of the export directory (the directory that Netlify treats as the publish root). Since the user drag-and-drops the export directory, `publish = "."` means "serve from this directory itself."

```toml
# netlify.toml — place in root of exported directory

[build]
  publish = "."

[[headers]]
  for = "/*.json"
  [headers.values]
    Cache-Control = "public, max-age=0, must-revalidate"

[[headers]]
  for = "/index.html"
  [headers.values]
    Cache-Control = "public, max-age=0, must-revalidate"
```

**Rationale:**
- `Cache-Control: max-age=0, must-revalidate` on JSON files ensures that re-exports are always picked up immediately; Netlify CDN will re-validate on every request. [ASSUMED] — Netlify uses this header correctly; confirmed pattern in Netlify docs.
- `index.html` gets the same treatment so the viewer itself is always current.
- No redirect rules are needed — this is not an SPA with client-side routing. All navigation is DOM manipulation within the single page.
- `[build]` with `publish = "."` is required for `netlify deploy --dir data/static-export/` to work correctly with drag-and-drop. [ASSUMED — consistent with standard Netlify static site pattern; no dynamic verification done]

---

### Python Service Architecture

Create `src/services/static_export.py` as a **new, standalone service**. Do not extend the existing `ExportService` in `export.py` — that service is scoped to `PostsRepository` only and its `export_json()` format is already consumed by `ImportService`. Adding tags/topics/embedded data would break the import round-trip contract.

```python
# src/services/static_export.py

@dataclass
class StaticExportResult:
    output_dir: Path
    post_count: int
    tag_count: int
    topic_count: int
    review_state_count: int
    exported_at: str
    files: list[Path]  # all files written

class StaticExportService:
    VERSION = "1.0"
    SOURCE = "xbm-static"

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self._posts_repo = PostsRepository(conn)
        self._tags_repo = TagsRepository(conn)
        self._topics_repo = TopicsRepository(conn)
        self._review_repo = ReviewStateRepository(conn)

    def export(self, output_dir: Path) -> StaticExportResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        exported_at = datetime.now(timezone.utc).isoformat()

        posts = self._posts_repo.get_all_with_embedded()
        tag_map = self._build_post_tag_map()       # {post_id: [names]}
        topic_map = self._build_post_topic_map()   # {post_id: [{id, name}]}
        tag_post_map = self._build_tag_post_map()  # {tag_id: [post_ids]}
        topic_post_map = self._build_topic_post_map()

        files = []
        files.append(self._write_posts_json(output_dir, posts, tag_map, topic_map, exported_at))
        files.append(self._write_tags_json(output_dir, tag_post_map, exported_at))
        files.append(self._write_topics_json(output_dir, topic_post_map, exported_at))
        files.append(self._write_review_state_json(output_dir, exported_at))
        files.append(self._write_search_index_json(output_dir, posts, tag_map, topic_map, exported_at))
        files.append(self._write_index_html(output_dir))
        files.append(self._write_netlify_toml(output_dir))

        return StaticExportResult(
            output_dir=output_dir,
            post_count=len(posts),
            ...
        )
```

**Key design choices:**
- Service accepts a `sqlite3.Connection` (not individual repos) to allow the caller to pass the same connection opened with `init_database()`, matching the CLI pattern in `main.py`.
- All four bulk JOIN queries run in `__init__` or in dedicated `_build_*_map()` private methods — never per-post.
- `_write_index_html()` returns the inline HTML as a Python string built with a triple-quoted f-string or a `textwrap.dedent` block. No external template engine.
- `_write_netlify_toml()` writes a static string constant — no templating.

---

### CLI Command

Add `export_static` as a new `@app.command("export-static")` in `src/cli/main.py`. [VERIFIED: existing CLI pattern, source file inspection]

```python
@app.command("export-static")
def export_static(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (default: data/static-export/)",
    ),
    db_path: Optional[Path] = typer.Option(
        None,
        "--db",
        "-d",
        help="Path to database file (default: data/bookmarks.db)",
    ),
) -> None:
    """Export bookmarks to static files for Netlify deployment.

    EXPORT-01: Generates JSON files for posts, tags, topics, and review state.
    EXPORT-02: Generates index.html with client-side search.
    EXPORT-03: Generates netlify.toml for deployment configuration.
    EXPORT-04: Prints deployment instructions after export.
    """
```

**Progress display:** Use `rich.progress.Progress` with `SpinnerColumn` and `TextColumn` showing which file is being written (same imports already in main.py). 7 steps: posts.json, tags.json, topics.json, review_state.json, search-index.json, index.html, netlify.toml.

**Summary table after completion:**

```
Export Complete — data/static-export/

File                  Size
posts.json            142 KB
tags.json             8 KB
topics.json           4 KB
review_state.json     12 KB
search-index.json     32 KB
index.html            28 KB
netlify.toml          0.3 KB

Deploy instructions:
  Option 1: Drag data/static-export/ to netlify.com/drop
  Option 2: netlify deploy --dir data/static-export/
```

**Output path:** Default to `Path("data/static-export/")`. Follow `get_database_path()` pattern — the CLI resolves relative paths from the cwd.

---

### Testing Strategy

Follow the project's existing test pattern: in-memory or temp-file SQLite, instantiate real repository objects, assert on outputs. [VERIFIED: conftest.py and test_export_service.py inspection]

**Test file:** `tests/test_static_export_service.py`

**Fixtures needed:**
- `temp_db_v6` — extends `temp_db_v5` (from conftest.py) with embedded_posts table (SCHEMA_V6_MIGRATION) and sample data: 3 posts (1 original, 1 retweet with embedded_post, 1 quote), 2 tags, 2 topics, 2 review states.

**Test classes:**

```
TestStaticExportService
  test_export_creates_output_directory
  test_posts_json_contains_all_posts
  test_posts_json_schema_has_required_fields        # version, exported_at, source, posts
  test_posts_json_post_has_tags_field               # list of tag names
  test_posts_json_post_has_topics_field             # list of {id, name}
  test_posts_json_retweet_has_embedded_post         # not null for retweet
  test_posts_json_original_has_null_embedded_post
  test_tags_json_has_post_ids                       # each tag has post_ids list
  test_topics_json_has_post_ids
  test_review_state_json_contains_states
  test_search_index_has_denormalized_tags           # space-joined string
  test_search_index_has_created_at_ts               # Unix timestamp integer
  test_index_html_file_exists
  test_index_html_contains_fetch_calls              # 'search-index.json' in content
  test_index_html_contains_date_filter_logic        # 'this_week' or similar in content
  test_netlify_toml_exists
  test_netlify_toml_has_cache_headers               # 'Cache-Control' in content
  test_overwrite_on_rerun                           # second call succeeds, files updated
  test_empty_database_exports_zero_posts            # no error, post_count=0

TestExportStaticCLI
  test_export_static_command_creates_output_dir     # typer.testing.CliRunner
  test_export_static_with_custom_output_path        # --output flag
  test_export_static_prints_deployment_instructions # 'netlify' in output
```

**CLI tests** use `typer.testing.CliRunner` — already imported and used in `test_cli.py`. [VERIFIED: test_cli.py exists in test directory]

---

### Edge Cases

| Case | How to handle |
|------|--------------|
| Empty database (no posts) | Write all JSON files with empty arrays/lists. posts.json has `post_count: 0, posts: []`. search-index.json has `entries: []`. index.html renders "No posts found" message. No error raised. |
| Post with no tags | `tags` field in search index is `""` (empty string). `tags` field in posts.json is `[]`. Filter function uses `.includes(term)` which returns false correctly on empty string. |
| Post with no topics | Same handling as no tags. |
| Retweet/quote with unavailable embedded post | `embedded_post.available == False`. posts.json includes the embedded_post object with `available: false`. index.html renders "Original post unavailable" UI, using the `available` boolean. |
| Posts with no review state | review_state.json only contains entries for posts that have a row in `post_review_state`. Posts without a state simply have no entry — viewer shows no review metadata for them. |
| `media_urls` stored as JSON string | `PostsRepository._row_to_dict()` already parses this with `json.loads()`. `get_all_with_embedded()` reuses `_row_to_dict_with_embedded()` which also parses embedded_media_urls. No extra handling needed in StaticExportService. [VERIFIED: posts.py lines 238–239, 518] |
| Very large post count (1000+) | All 1000 posts loaded into browser memory. At ~2KB average per entry, 1000 posts = ~2 MB JSON, well within browser capabilities. search-index.json entries are smaller (~300 bytes each), 1000 = ~300 KB. Acceptable. No pagination needed. |
| output_dir already exists | `mkdir(parents=True, exist_ok=True)` silently succeeds. Files are overwritten. Matches CONTEXT.md "overwrite silently on re-run" decision. |
| Tags/topics tables empty | Bulk JOIN queries return empty result sets. `tags.json` and `topics.json` are written with empty arrays. No error. |

---

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json`, so this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/test_static_export_service.py -x --tb=short` |
| Full suite command | `.venv/bin/python -m pytest --tb=short -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXPORT-01 | `xbm export-static` generates JSON files for posts, tags, topics, review state | unit | `pytest tests/test_static_export_service.py::TestStaticExportService -x` | Wave 0 |
| EXPORT-02 | Static web app displays posts with client-side search | unit | `pytest tests/test_static_export_service.py::TestStaticExportService::test_index_html_contains_fetch_calls -x` | Wave 0 |
| EXPORT-03 | Export includes pre-built search index for instant client-side search | unit | `pytest tests/test_static_export_service.py::TestStaticExportService::test_search_index_has_denormalized_tags -x` | Wave 0 |
| EXPORT-04 | User can deploy exported files to Netlify | unit + manual | `pytest tests/test_static_export_service.py::TestStaticExportService::test_netlify_toml_has_cache_headers -x` | Wave 0 |

*EXPORT-04 deployment verification is manual — automated test confirms netlify.toml content is correct.*

### Sampling Rate

- **Per task commit:** `pytest tests/test_static_export_service.py -x --tb=short`
- **Per wave merge:** `.venv/bin/python -m pytest --tb=short -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_static_export_service.py` — covers EXPORT-01 through EXPORT-04
- [ ] `tests/conftest.py` needs `temp_db_v6` fixture (extends existing `temp_db_v5` with embedded_posts table and sample data)

*(No framework install needed — pytest is already in pyproject.toml dev dependencies.)*

---

## Implementation Plan (High-Level)

### Wave 0: Test Infrastructure

1. Add `temp_db_v6` fixture to `tests/conftest.py` with embedded_posts table and sample data (3 posts: original, retweet, quote tweet; 2 tags; 2 topics; 2 review states)
2. Create `tests/test_static_export_service.py` with stub test classes (assertions using `pytest.raises(NotImplementedError)` or just `assert False, "not implemented"` as placeholder — to be filled in Wave 1)

### Wave 1: Repository Extensions

3. Add `PostsRepository.get_all_with_embedded()` method to `src/repositories/posts.py`
4. Add `ReviewStateRepository.get_all()` method to `src/repositories/review_state.py`
5. Write tests for both new methods (integration tests against `temp_db_v6`)

### Wave 2: StaticExportService — JSON Output

6. Create `src/services/static_export.py` with `StaticExportService` class
7. Implement: bulk tag/topic maps, `_write_posts_json()`, `_write_tags_json()`, `_write_topics_json()`, `_write_review_state_json()`, `_write_search_index_json()`
8. Implement `StaticExportResult` dataclass
9. Fill in `TestStaticExportService` tests for all JSON file assertions

### Wave 3: index.html and Netlify Config

10. Implement `_write_index_html()` in `StaticExportService` — inline CSS + JS, fetch() loading, search/filter/sort UI
11. Implement `_write_netlify_toml()` — static string constant
12. Fill in `test_index_html_*` and `test_netlify_toml_*` tests

### Wave 4: CLI Command

13. Add `export_static` command to `src/cli/main.py`
14. Implement: progress bar (7 steps), summary table, deployment instructions panel
15. Add `TestExportStaticCLI` tests in `test_static_export_service.py` using `CliRunner`

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|-----------|
| N+1 query performance | HIGH if ignored | Use the four bulk JOIN queries defined above; never call get_post_tags() per post |
| `fetch()` fails on local file:// | MEDIUM | Add note in deployment instructions panel; this is expected behavior |
| index.html inline JS becomes hard to maintain | MEDIUM | Keep JS under 200 lines; use clear function names; add inline comments |
| `get_all_with_embedded()` not added to PostsRepository | HIGH | Wave 1 adds the method and tests it before Wave 2 StaticExportService uses it |
| `media_urls` / `link_urls` double-parsed | LOW | `_row_to_dict_with_embedded()` already handles JSON parsing; StaticExportService passes through the already-parsed list |
| Tests create stale test files | LOW | Use `tmp_path` pytest fixture for all output directory tests (not `data/`) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | netlify.toml `Cache-Control: max-age=0, must-revalidate` causes Netlify CDN to revalidate JSON on every request | Netlify Configuration | If Netlify ignores this, users who re-export may see stale data; mitigation: user can manually purge Netlify cache |
| A2 | netlify.toml `publish = "."` makes `netlify deploy --dir data/static-export/` treat the directory as root | Netlify Configuration | If Netlify ignores the toml when using --dir flag, the behavior is unchanged (Netlify deploy --dir already sets the root); low risk |

All other claims in this research are [VERIFIED] against source files in this session.

---

## Sources

### Primary (HIGH confidence)
- `src/repositories/posts.py` — VERIFIED: `_row_to_dict()` fields, `_row_to_dict_with_embedded()` structure, `get_all()`, `get_paginated_with_embedded()` LEFT JOIN pattern
- `src/repositories/tags.py` — VERIFIED: `list_tags()`, `get_post_tags()`, `get_posts_by_tag()` signatures
- `src/repositories/topics.py` — VERIFIED: `list_topics()`, `get_post_topics()`, `get_posts_by_topic()` signatures
- `src/repositories/review_state.py` — VERIFIED: `get_state()`, `get_stats()` signatures; no `get_all()` exists
- `src/repositories/embedded_posts.py` — VERIFIED: `_row_to_dict()` fields including `available` bool
- `src/services/export.py` — VERIFIED: `ExportService` scoped to PostsRepository only, `_format_post_for_export()` field list
- `src/cli/main.py` — VERIFIED: `@app.command("export")` pattern, Progress/Table/Panel usage, `get_database_path()` usage
- `src/config/settings.py` — VERIFIED: `get_database_path()` function signature and behavior
- `src/db/connection.py` — VERIFIED: `get_connection()` signature and PRAGMA settings
- `src/db/schema.py` — VERIFIED: V6 schema `embedded_posts` table; V4 `post_tags`/`post_topics`/`tags`/`topics` tables; V5 `post_review_state` table
- `tests/conftest.py` — VERIFIED: existing fixtures `temp_db`, `temp_db_v4`, `temp_db_v5` available to extend
- `tests/test_export_service.py` — VERIFIED: existing test patterns with CliRunner, temp SQLite, PostsRepository
- `pyproject.toml` — VERIFIED: pytest config, test paths, no `nyquist_validation` override needed

### Tertiary (ASSUMED, see Assumptions Log)
- Netlify `Cache-Control` header behavior (A1, A2) — standard Netlify documentation pattern, not dynamically verified in this session

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — no new libraries; all existing dependencies
- Repository queries: HIGH — read actual source, identified missing methods precisely
- Architecture: HIGH — consistent with all 13 prior phases' patterns
- JSON schema: HIGH — derived from actual `_row_to_dict()` implementations
- index.html/JS: MEDIUM — vanilla JS date math is standard but not executed/tested
- Netlify config: MEDIUM — standard pattern, two ASSUMED claims flagged

**Research date:** 2026-06-13
**Valid until:** 2026-09-13 (stable stack; Python stdlib + existing project patterns)

## RESEARCH COMPLETE
