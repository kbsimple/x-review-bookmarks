"""StaticExportService -- exports bookmarks to static JSON files for Netlify hosting.

EXPORT-01: Generates JSON files for posts, tags, topics, and review state.
EXPORT-03: Generates pre-built search index with denormalized fields.

Usage:
    from src.services.static_export import StaticExportService
    from src.db import get_connection, init_database

    conn = init_database(db_path)
    service = StaticExportService(conn)
    result = service.export(Path("data/static-export/"))
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..repositories.posts import PostsRepository
from ..repositories.review_state import ReviewStateRepository
from ..repositories.tags import TagsRepository
from ..repositories.topics import TopicsRepository


@dataclass
class StaticExportResult:
    """Result of a static export operation."""
    output_dir: Path
    post_count: int
    tag_count: int
    topic_count: int
    review_state_count: int
    exported_at: str
    files: list[Path] = field(default_factory=list)


class StaticExportService:
    """Exports all bookmark data to static JSON files for Netlify deployment.

    Reads all database tables via bulk JOIN queries (never N+1 per-post queries)
    and writes five JSON files plus index.html and netlify.toml.

    Args:
        conn: SQLite connection opened with init_database() or get_connection().
    """

    VERSION = "1.0"
    SOURCE = "xbm-static"

    _NETLIFY_TOML = """\
# netlify.toml -- place in root of exported directory

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
"""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._posts_repo = PostsRepository(conn)
        self._review_repo = ReviewStateRepository(conn)
        self._tags_repo = TagsRepository(conn)
        self._topics_repo = TopicsRepository(conn)

    def export(
        self,
        output_dir: Path,
        rich_embeds: bool = False,
        on_oembed_progress: Any = None,
        limit: Optional[int] = None,
    ) -> StaticExportResult:
        """Export all data to output_dir.

        Creates output_dir if it does not exist. Silently overwrites on re-run.

        Args:
            output_dir: Directory to write all export files into.
            rich_embeds: If True, fetch oEmbed HTML from Twitter for each post
                and store it as oembed_html in posts.json. Requires internet
                access. Posts that are deleted or protected get oembed_html=null.
            on_oembed_progress: Optional callable(completed, total) for oEmbed
                fetch progress, passed through to OEmbedService.fetch_all().
            limit: If set, export only the N most recently bookmarked posts.

        Returns:
            StaticExportResult with counts and list of files written.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        exported_at = datetime.now(timezone.utc).isoformat()

        # Load all data once -- bulk queries only
        posts = self._posts_repo.get_all_with_embedded()
        if limit is not None:
            posts = posts[:limit]
        tag_map = self._build_post_tag_map()
        topic_map = self._build_post_topic_map()

        oembed_map: dict[str, Any] = {}
        if rich_embeds and posts:
            from .oembed import OEmbedService
            post_pairs = [(p['x_post_id'], p['author_username']) for p in posts]
            oembed_map = OEmbedService().fetch_all(post_pairs, on_progress=on_oembed_progress)

        files: list[Path] = []
        files.append(self._write_posts_json(output_dir, posts, tag_map, topic_map, exported_at, oembed_map))
        files.append(self._write_tags_json(output_dir, exported_at))
        files.append(self._write_topics_json(output_dir, exported_at))
        files.append(self._write_review_state_json(output_dir, exported_at))
        files.append(self._write_search_index_json(output_dir, posts, tag_map, topic_map, exported_at))
        files.append(self._write_index_html(output_dir))
        files.append(self._write_netlify_toml(output_dir))

        return StaticExportResult(
            output_dir=output_dir,
            post_count=len(posts),
            tag_count=len(self._tags_repo.list_tags()),
            topic_count=len(self._topics_repo.list_topics()),
            review_state_count=len(self._review_repo.get_all()),
            exported_at=exported_at,
            files=files,
        )

    def _build_post_tag_map(self) -> dict[str, list[str]]:
        """Build {post_id: [tag_name, ...]} via single JOIN query."""
        rows = self._conn.execute(
            """SELECT pt.post_id, t.name
               FROM post_tags pt
               JOIN tags t ON pt.tag_id = t.id
               ORDER BY pt.post_id, t.name"""
        ).fetchall()
        result: dict[str, list[str]] = {}
        for row in rows:
            result.setdefault(row[0], []).append(row[1])
        return result

    def _build_post_topic_map(self) -> dict[str, list[dict[str, Any]]]:
        """Build {post_id: [{id, name}, ...]} via single JOIN query."""
        rows = self._conn.execute(
            """SELECT pt.post_id, t.id, t.name
               FROM post_topics pt
               JOIN topics t ON pt.topic_id = t.id
               ORDER BY pt.post_id, t.name"""
        ).fetchall()
        result: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            result.setdefault(row[0], []).append({"id": row[1], "name": row[2]})
        return result

    def _write_posts_json(
        self,
        output_dir: Path,
        posts: list[dict[str, Any]],
        tag_map: dict[str, list[str]],
        topic_map: dict[str, list[dict[str, Any]]],
        exported_at: str,
        oembed_map: dict[str, Any] | None = None,
    ) -> Path:
        """Write posts.json -- all posts with tags, topics, embedded_post inline."""
        export_posts = []
        for p in posts:
            post_id = p['x_post_id']
            export_post: dict[str, Any] = {
                "x_post_id": post_id,
                "created_at": p['created_at'],
                "text": p['text'] or "",
                "author_id": p['author_id'],
                "author_username": p['author_username'],
                "author_display_name": p['author_display_name'],
                "media_urls": p['media_urls'],
                "link_urls": p['link_urls'],
                "bookmarked_at": p['bookmarked_at'],
                "note": p.get('note'),
                "post_type": p.get('post_type', 'original'),
                "tags": tag_map.get(post_id, []),
                "topics": topic_map.get(post_id, []),
                "embedded_post": p.get('embedded_post'),
            }
            if oembed_map:
                export_post["oembed_html"] = oembed_map.get(post_id)
            export_posts.append(export_post)

        payload = {
            "version": self.VERSION,
            "exported_at": exported_at,
            "source": self.SOURCE,
            "post_count": len(export_posts),
            "posts": export_posts,
        }
        path = output_dir / "posts.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def _write_tags_json(self, output_dir: Path, exported_at: str) -> Path:
        """Write tags.json -- all tags with post_ids lists."""
        rows = self._conn.execute(
            """SELECT t.id, t.name, pt.post_id
               FROM tags t
               LEFT JOIN post_tags pt ON t.id = pt.tag_id
               ORDER BY t.id"""
        ).fetchall()

        tags_map: dict[int, dict[str, Any]] = {}
        for row in rows:
            tag_id, tag_name, post_id = row[0], row[1], row[2]
            if tag_id not in tags_map:
                tags_map[tag_id] = {"id": tag_id, "name": tag_name, "post_ids": []}
            if post_id is not None:
                tags_map[tag_id]["post_ids"].append(post_id)

        payload = {
            "version": self.VERSION,
            "exported_at": exported_at,
            "tags": list(tags_map.values()),
        }
        path = output_dir / "tags.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def _write_topics_json(self, output_dir: Path, exported_at: str) -> Path:
        """Write topics.json -- all topics with post_ids lists."""
        rows = self._conn.execute(
            """SELECT t.id, t.name, t.description, t.parent_id, pt.post_id
               FROM topics t
               LEFT JOIN post_topics pt ON t.id = pt.topic_id
               ORDER BY t.id"""
        ).fetchall()

        topics_map: dict[int, dict[str, Any]] = {}
        for row in rows:
            topic_id, name, desc, parent_id, post_id = row[0], row[1], row[2], row[3], row[4]
            if topic_id not in topics_map:
                topics_map[topic_id] = {
                    "id": topic_id,
                    "name": name,
                    "description": desc,
                    "parent_id": parent_id,
                    "post_ids": [],
                }
            if post_id is not None:
                topics_map[topic_id]["post_ids"].append(post_id)

        payload = {
            "version": self.VERSION,
            "exported_at": exported_at,
            "topics": list(topics_map.values()),
        }
        path = output_dir / "topics.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def _write_review_state_json(self, output_dir: Path, exported_at: str) -> Path:
        """Write review_state.json -- all review states (no internal FSRS fields)."""
        states = self._review_repo.get_all()
        payload = {
            "version": self.VERSION,
            "exported_at": exported_at,
            "review_states": states,
        }
        path = output_dir / "review_state.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def _write_search_index_json(
        self,
        output_dir: Path,
        posts: list[dict[str, Any]],
        tag_map: dict[str, list[str]],
        topic_map: dict[str, list[dict[str, Any]]],
        exported_at: str,
    ) -> Path:
        """Write search-index.json -- denormalized entries for client-side Array.filter()."""
        entries = []
        for p in posts:
            post_id = p['x_post_id']
            created_at_str = p['created_at'] or ""
            try:
                dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                created_at_ts = int(dt.timestamp())
            except (ValueError, AttributeError):
                created_at_ts = 0

            tags_str = " ".join(sorted(tag_map.get(post_id, [])))
            topics_str = " ".join(sorted(t['name'] for t in topic_map.get(post_id, [])))

            entries.append({
                "id": post_id,
                "text": p['text'] or "",
                "author_username": p['author_username'] or "",
                "author_display_name": p['author_display_name'] or "",
                "tags": tags_str,
                "topics": topics_str,
                "created_at": created_at_str,
                "created_at_ts": created_at_ts,
                "post_type": p.get('post_type', 'original'),
            })

        payload = {
            "version": self.VERSION,
            "exported_at": exported_at,
            "entries": entries,
        }
        path = output_dir / "search-index.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def _write_netlify_toml(self, output_dir: Path) -> Path:
        """Write netlify.toml with cache headers for JSON files."""
        path = output_dir / "netlify.toml"
        path.write_text(self._NETLIFY_TOML, encoding="utf-8")
        return path

    def _write_index_html(self, output_dir: Path) -> Path:
        """Write index.html -- single-file static viewer with inline CSS + JS."""
        html = self._build_index_html()
        path = output_dir / "index.html"
        path.write_text(html, encoding="utf-8")
        return path

    def _build_index_html(self) -> str:
        """Build the complete index.html string with inline CSS and JS."""
        return """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>X Bookmarks</title>
<style>
/* -- CSS Variables (Design System) -- */
:root {
  --color-bg:        #0f172a;
  --color-card:      #1e293b;
  --color-accent:    #2563eb;
  --color-embedded:  #111827;
  --color-border:    #334155;
  --color-text:      #f1f5f9;
  --color-secondary: #94a3b8;
  --color-muted:     #64748b;
  --color-link:      #60a5fa;
  --color-error:     #ef4444;
  /* Spacing tokens */
  --xs:  4px;
  --sm:  8px;
  --sm2: 12px;
  --md:  16px;
  --lg:  24px;
  --xl:  32px;
  --2xl: 48px;
  --3xl: 64px;
}
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--color-bg);
  color: var(--color-text);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 15px;
  font-weight: 400;
  line-height: 1.6;
}
a { color: var(--color-link); text-decoration: none; }
a:hover { text-decoration: underline; }
/* -- Visually hidden (for accessible labels) -- */
.sr-only {
  position: absolute; width: 1px; height: 1px;
  padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}
/* -- Header -- */
#header {
  position: sticky; top: 0; z-index: 10;
  background: var(--color-card);
  border-bottom: 1px solid var(--color-border);
  padding: var(--md) var(--xl);
  display: flex; align-items: center; gap: var(--sm);
}
#header h1 {
  margin: 0; font-size: 18px; font-weight: 600; line-height: 1.3;
  color: var(--color-text);
}
#count-badge {
  background: var(--color-accent);
  color: #fff; font-size: 13px; font-weight: 600;
  padding: var(--xs) var(--sm);
  border-radius: 12px; white-space: nowrap;
}
/* -- Controls row -- */
#controls {
  background: var(--color-card);
  border-bottom: 1px solid var(--color-border);
  padding: var(--md) var(--xl);
  display: flex; gap: var(--md); align-items: center;
  max-width: 720px; margin: 0 auto;
}
#controls input, #controls select {
  background: var(--color-bg);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 0 var(--md);
  height: 40px; font-size: 13px;
  outline: none;
}
#controls input { flex: 1; }
#controls input:focus, #controls select:focus {
  outline: 2px solid var(--color-accent);
}
#controls select { width: 160px; cursor: pointer; }
/* -- Main content -- */
#main {
  max-width: 720px; margin: 0 auto;
  padding: var(--xl) var(--md);
}
/* -- Post cards -- */
.post-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--md);
  margin-bottom: var(--lg);
}
.post-meta {
  font-size: 13px; color: var(--color-secondary);
  line-height: 1.4; margin-bottom: var(--sm);
}
.post-type-label {
  font-size: 13px; font-weight: 600; color: var(--color-muted);
  line-height: 1.4; margin-bottom: var(--sm);
}
.post-text {
  font-size: 15px; color: var(--color-text);
  line-height: 1.6; white-space: pre-wrap; word-break: break-word;
  margin-bottom: var(--sm);
}
/* -- Embedded / nested card -- */
.embedded-card {
  background: var(--color-embedded);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: var(--sm2);
  margin-top: var(--sm2);
}
.embedded-meta {
  font-size: 13px; color: var(--color-secondary); margin-bottom: var(--xs);
}
.embedded-text {
  font-size: 15px; color: var(--color-text); opacity: 0.9;
  white-space: pre-wrap; word-break: break-word;
}
.unavailable-placeholder {
  font-size: 13px; color: var(--color-muted); font-style: italic;
}
/* -- Tags and topics -- */
.pills-row { display: flex; flex-wrap: wrap; gap: var(--xs); margin-top: var(--sm); }
.pill {
  display: inline-block;
  background: var(--color-accent);
  color: #fff; font-size: 13px; font-weight: 400;
  padding: var(--xs) var(--sm);
  border-radius: 12px; line-height: 1.4;
}
.topic-pill { opacity: 0.8; }
/* -- Review badge -- */
.review-badge {
  display: inline-block; font-size: 13px; font-weight: 600;
  color: var(--color-secondary); margin-top: var(--xs);
}
/* -- Media grid -- */
.media-grid { margin-top: var(--sm); }
.media-grid img {
  display: block; width: 100%; object-fit: cover;
  border-radius: 6px; cursor: pointer;
}
.media-grid.count-1 img { max-height: 320px; }
.media-grid.count-2 { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sm); }
.media-grid.count-2 img { max-height: 240px; }
.media-grid.count-3, .media-grid.count-4 {
  display: grid; grid-template-columns: 1fr 1fr; gap: var(--sm);
}
.media-grid.count-3 img, .media-grid.count-4 img { max-height: 200px; }
/* -- Card footer: View on X -- */
.card-footer { display: flex; justify-content: flex-end; margin-top: var(--sm); }
.view-on-x {
  color: var(--color-link); font-size: 13px; font-weight: 400;
  text-decoration: none;
}
.view-on-x:hover { text-decoration: underline; }
/* -- oEmbed (native Twitter widget) card -- */
.oembed-card { padding: var(--sm) var(--sm) var(--xs); }
.oembed-container { max-width: 550px; margin: 0 auto; }
.oembed-container .twitter-tweet { margin: 0 auto !important; }
/* -- Loading -- */
#loading {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: var(--2xl) 0;
  color: var(--color-secondary); font-size: 15px;
}
.spinner {
  width: 40px; height: 40px; border-radius: 50%;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  animation: spin 0.8s linear infinite;
  margin-bottom: var(--md);
}
@keyframes spin { to { transform: rotate(360deg); } }
/* -- Empty / Error states -- */
#empty-state, #error-state {
  text-align: center; padding: var(--2xl) 0;
}
#empty-state h2, #error-state h2 { font-size: 18px; font-weight: 600; margin-bottom: var(--sm); }
#error-state h2 { color: var(--color-error); }
#empty-state p, #error-state p { color: var(--color-secondary); font-size: 15px; }
/* -- Footer -- */
#footer {
  background: var(--color-card);
  border-top: 1px solid var(--color-border);
  padding: var(--md) var(--xl);
  text-align: center;
  font-size: 13px; color: var(--color-muted);
}
/* -- Mode switcher (pill group in header) -- */
.mode-switcher {
  display: flex; margin-left: auto; gap: 2px;
  border: 1px solid var(--color-border); border-radius: 6px; overflow: hidden;
}
.mode-btn {
  background: transparent;
  color: var(--color-muted);
  border: none;
  padding: 6px var(--md);
  font-size: 13px; font-weight: 400; min-height: 32px;
  cursor: pointer;
}
.mode-btn.active {
  background: var(--color-accent);
  color: #fff; font-weight: 600;
}
/* -- Carousel nav controls row -- */
#carousel-nav {
  display: flex; align-items: center; justify-content: center;
  gap: var(--lg); margin-top: var(--lg);
}
.carousel-btn {
  display: inline-flex; align-items: center;
  background: transparent;
  color: var(--color-link);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: var(--xs) var(--md);
  font-size: 13px; min-height: 44px; cursor: pointer;
}
.carousel-btn:disabled {
  opacity: 0.3; cursor: not-allowed; pointer-events: none;
}
.carousel-counter {
  font-size: 13px; color: var(--color-secondary);
}
/* -- Carousel mode: wider max-width -- */
.carousel-mode #main {
  max-width: 860px;
}
</style>
</head>
<body>

<div id="header">
  <h1>X Bookmarks</h1>
  <span id="count-badge">...</span>
  <div class="mode-switcher">
    <button class="mode-btn active" data-mode="stream" onclick="setMode('stream')">Stream</button>
    <button class="mode-btn" data-mode="carousel" onclick="setMode('carousel')">Carousel</button>
  </div>
</div>

<div id="controls">
  <label for="search-input" class="sr-only">Search</label>
  <input type="text" id="search-input"
         placeholder="Search posts, authors, tags, topics..."
         autocomplete="off">
  <label for="date-filter" class="sr-only">Date filter</label>
  <select id="date-filter">
    <option value="">All dates</option>
    <option value="this_week">This week</option>
    <option value="last_week">Last week</option>
    <option value="this_month">This month</option>
    <option value="last_month">Last month</option>
    <option value="last_3_months">Last 3 months</option>
    <option value="this_year">This year</option>
    <option value="older">Older</option>
  </select>
  <label for="sort-order" class="sr-only">Sort</label>
  <select id="sort-order">
    <option value="newest">Newest first</option>
    <option value="oldest">Oldest first</option>
    <option value="random">Random</option>
    <option value="author">By author</option>
  </select>
</div>

<div id="main">
  <div id="loading">
    <div class="spinner"></div>
    Loading bookmarks...
  </div>
  <div id="error-state" style="display:none"></div>
  <div id="empty-state" style="display:none"></div>
  <div id="post-list"></div>
</div>

<div id="footer"></div>

<script>
'use strict';

// -- HTML escaping helper (CRITICAL: all user content must be escaped) --
function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// -- Linkify: convert URLs in text to clickable links --
function linkify(text) {
  if (!text) return '';
  return String(text).split(/(https?:\/\/[^\s]+)/g).map((part, i) => {
    if (i % 2 === 1) {
      const escaped = esc(part);
      return `<a href="${escaped}" target="_blank" rel="noopener noreferrer">${escaped}</a>`;
    }
    return esc(part);
  }).join('');
}

// -- Profile link: @username -> x.com link --
function profileLink(username) {
  if (!username) return '';
  return `<a href="https://x.com/${esc(username)}" target="_blank" rel="noopener noreferrer">@${esc(username)}</a>`;
}

// -- Global state --
let allPosts = {};
let searchIndex = [];
let reviewMap = new Map();
let totalPostCount = 0;
let exportedDate = '';
let debounceTimer = null;
let currentMode = localStorage.getItem('xbm_mode') || 'stream';
let carouselIndex = 0;
let savedScrollY = 0;

// -- Date helpers --
function getDateRange(filter) {
  const now = new Date();
  const ts = Math.floor(now.getTime() / 1000);
  switch (filter) {
    case 'this_week':     return [ts - 7 * 86400, ts];
    case 'last_week':     return [ts - 14 * 86400, ts - 7 * 86400];
    case 'this_month': {
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      return [Math.floor(start.getTime() / 1000), ts];
    }
    case 'last_month': {
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const end   = new Date(now.getFullYear(), now.getMonth(), 1);
      return [Math.floor(start.getTime() / 1000), Math.floor(end.getTime() / 1000)];
    }
    case 'last_3_months': return [ts - 90 * 86400, ts];
    case 'this_year': {
      const start = new Date(now.getFullYear(), 0, 1);
      return [Math.floor(start.getTime() / 1000), ts];
    }
    case 'older':         return [0, ts - 365 * 86400];
    default:              return null;
  }
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  try {
    return new Date(isoStr).toLocaleDateString('en-US', {year:'numeric', month:'short', day:'numeric'});
  } catch(e) { return isoStr; }
}

// -- Filter + sort --
function filterAndSort() {
  const query = document.getElementById('search-input').value.toLowerCase().trim();
  const dateFilter = document.getElementById('date-filter').value;
  const sortOrder = document.getElementById('sort-order').value;

  let results = searchIndex;
  if (query) {
    results = results.filter(e =>
      (e.text || '').toLowerCase().includes(query) ||
      (e.author_username || '').toLowerCase().includes(query) ||
      (e.tags || '').toLowerCase().includes(query) ||
      (e.topics || '').toLowerCase().includes(query)
    );
  }
  if (dateFilter) {
    const range = getDateRange(dateFilter);
    if (range) {
      const [from, to] = range;
      results = results.filter(e => e.created_at_ts >= from && e.created_at_ts <= to);
    }
  }
  results = [...results];
  if (sortOrder === 'oldest') {
    results.sort((a, b) => a.created_at_ts - b.created_at_ts);
  } else if (sortOrder === 'author') {
    results.sort((a, b) => (a.author_username || '').localeCompare(b.author_username || ''));
  } else if (sortOrder === 'random') {
    for (let i = results.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [results[i], results[j]] = [results[j], results[i]];
    }
  } else {
    results.sort((a, b) => b.created_at_ts - a.created_at_ts);
  }
  return results;
}

// -- Rendering --
function renderTagPill(tagName) {
  return `<span class="pill">#${esc(tagName)}</span>`;
}
function renderTopicPill(topicName) {
  return `<span class="pill topic-pill">Topic: ${esc(topicName)}</span>`;
}
function renderReviewBadge(reviewState) {
  if (!reviewState || !reviewState.scheduled_for) return '';
  const dateStr = (reviewState.scheduled_for || '').split('T')[0];
  return `<span class="review-badge">Review due ${esc(dateStr)}</span>`;
}
function renderMediaGrid(mediaUrls) {
  if (!mediaUrls || mediaUrls.length === 0) return '';
  const count = Math.min(mediaUrls.length, 4);
  const imgs = mediaUrls.slice(0, 4)
    .map(url => `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer"><img src="${esc(url)}" alt="Post image" loading="lazy"></a>`)
    .join('');
  return `<div class="media-grid count-${count}">${imgs}</div>`;
}
function renderEmbeddedCard(ep) {
  if (!ep) return '';
  if (!ep.available) {
    return `<div class="embedded-card">
      <div class="unavailable-placeholder">
        Original post unavailable${ep.author_username ? ' &middot; ' + profileLink(ep.author_username) : ''}
      </div>
    </div>`;
  }
  return `<div class="embedded-card">
    <div class="embedded-meta">${profileLink(ep.author_username)} &middot; ${formatDate(ep.created_at)}</div>
    <div class="embedded-text">${linkify(ep.text || '')}</div>
    ${renderMediaGrid(ep.media_urls)}
  </div>`;
}

function renderCardFooter(post) {
  const url = `https://x.com/i/web/status/${esc(post.x_post_id)}`;
  return `<div class="card-footer">
    <a href="${url}" target="_blank" rel="noopener noreferrer" class="view-on-x">View on X</a>
  </div>`;
}

function renderPillsRow(tags, topics) {
  if ((!tags || !tags.length) && (!topics || !topics.length)) return '';
  const tagHtml = (tags || []).map(t => renderTagPill(t)).join('');
  const topicHtml = (topics || []).map(t => renderTopicPill(t.name)).join('');
  return `<div class="pills-row">${tagHtml}${topicHtml}</div>`;
}

function renderOriginalCard(post, reviewState) {
  return `<div class="post-card">
    <div class="post-meta">${profileLink(post.author_username)} &middot; ${formatDate(post.created_at)}</div>
    <div class="post-text">${linkify(post.text || '')}</div>
    ${renderMediaGrid(post.media_urls)}
    ${renderPillsRow(post.tags, post.topics)}
    ${renderReviewBadge(reviewState)}
    ${renderCardFooter(post)}
  </div>`;
}

function renderRetweetCard(post, reviewState) {
  return `<div class="post-card">
    <div class="post-meta">${profileLink(post.author_username)} &middot; ${formatDate(post.created_at)}</div>
    <div class="post-type-label">Reposted from ${profileLink(post.embedded_post ? post.embedded_post.author_username : '')}</div>
    ${renderEmbeddedCard(post.embedded_post)}
    ${renderPillsRow(post.tags, post.topics)}
    ${renderReviewBadge(reviewState)}
    ${renderCardFooter(post)}
  </div>`;
}

function renderQuoteCard(post, reviewState) {
  return `<div class="post-card">
    <div class="post-meta">${profileLink(post.author_username)} &middot; ${formatDate(post.created_at)}</div>
    <div class="post-type-label">Quoting ${profileLink(post.embedded_post ? post.embedded_post.author_username : '')}</div>
    <div class="post-text">${linkify(post.text || '')}</div>
    ${renderMediaGrid(post.media_urls)}
    ${renderEmbeddedCard(post.embedded_post)}
    ${renderPillsRow(post.tags, post.topics)}
    ${renderReviewBadge(reviewState)}
    ${renderCardFooter(post)}
  </div>`;
}

// -- oEmbed (native Twitter widget) rendering --
let _twitterWidgetLoaded = false;
function loadTwitterWidget() {
  if (_twitterWidgetLoaded) return;
  _twitterWidgetLoaded = true;
  const s = document.createElement('script');
  s.src = 'https://platform.twitter.com/widgets.js';
  s.async = true;
  s.charset = 'utf-8';
  document.head.appendChild(s);
}

function renderOEmbedCard(post, reviewState) {
  return `<div class="post-card oembed-card">
    <div class="oembed-container">${post.oembed_html}</div>
    ${renderPillsRow(post.tags, post.topics)}
    ${renderReviewBadge(reviewState)}
  </div>`;
}

function renderPost(post, reviewState) {
  if (post.oembed_html) return renderOEmbedCard(post, reviewState);
  const type = post.post_type || 'original';
  if (type === 'retweet') return renderRetweetCard(post, reviewState);
  if (type === 'quote')   return renderQuoteCard(post, reviewState);
  return renderOriginalCard(post, reviewState);
}

function setMode(mode) {
  if (mode === currentMode) return;
  if (mode === 'carousel') { savedScrollY = window.scrollY; }
  if (mode === 'stream')   { requestAnimationFrame(() => window.scrollTo(0, savedScrollY)); }
  currentMode = mode;
  localStorage.setItem('xbm_mode', mode);
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
  document.body.classList.toggle('carousel-mode', mode === 'carousel');
  renderView();
}

function renderCarousel(results, idx) {
  const entry = results[idx];
  const post = allPosts[entry.id];
  const rs = reviewMap.get(entry.id) || null;
  const cardHtml = renderPost(post, rs);
  const total = results.length;
  const prevDisabled = idx === 0         ? 'disabled' : '';
  const nextDisabled = idx === total - 1 ? 'disabled' : '';
  const nav = `<div id="carousel-nav">
    <button class="carousel-btn" id="carousel-prev" ${prevDisabled}>&larr; Prev</button>
    <span class="carousel-counter">${idx + 1} / ${total} posts</span>
    <button class="carousel-btn" id="carousel-next" ${nextDisabled}>Next &rarr;</button>
  </div>`;
  document.getElementById('post-list').innerHTML = cardHtml + nav;
  document.getElementById('carousel-prev').addEventListener('click', () => {
    if (carouselIndex > 0) { carouselIndex--; renderView(); window.scrollTo(0, 0); }
  });
  document.getElementById('carousel-next').addEventListener('click', () => {
    if (carouselIndex < results.length - 1) { carouselIndex++; renderView(); window.scrollTo(0, 0); }
  });
  if (post.oembed_html) {
    loadTwitterWidget();
    if (window.twttr && window.twttr.widgets) {
      window.twttr.widgets.load(document.getElementById('post-list'));
    }
  }
}

function showError(message) {
  document.getElementById('loading').style.display = 'none';
  const el = document.getElementById('error-state');
  el.style.display = 'block';
  el.innerHTML = `<h2>Could not load bookmark data</h2>
    <p>Make sure you're viewing this file from Netlify, not by opening it directly. Direct file:// access does not support fetch().</p>
    <p style="color:var(--color-muted);font-size:13px;">${esc(message)}</p>`;
}

function showEmptyState(reason) {
  const el = document.getElementById('empty-state');
  el.style.display = 'block';
  if (reason === 'no_posts') {
    el.innerHTML = `<h2>No bookmarks found</h2>
      <p>Run <code>xbm sync</code> to fetch your bookmarks, then <code>xbm export-static</code> to regenerate this viewer.</p>`;
  } else {
    el.innerHTML = `<h2>No posts match your search</h2>
      <p>Try different keywords or clear the date filter.</p>`;
  }
}

function renderView() {
  const results = filterAndSort();
  const filtered = results.length;
  const total = totalPostCount;
  const badge = filtered === total
    ? `${total} posts`
    : `${filtered} of ${total} posts`;
  document.getElementById('count-badge').textContent = badge;

  const container = document.getElementById('post-list');
  const emptyEl = document.getElementById('empty-state');
  emptyEl.style.display = 'none';

  if (total === 0) {
    showEmptyState('no_posts');
    container.innerHTML = '';
    return;
  }
  if (filtered === 0) {
    showEmptyState('no_results');
    container.innerHTML = '';
    return;
  }

  if (currentMode === 'carousel') {
    if (carouselIndex >= results.length) carouselIndex = 0;
    renderCarousel(results, carouselIndex);
    return;
  }

  // Stream mode (original path — unchanged)
  container.innerHTML = results
    .map(entry => {
      const post = allPosts[entry.id];
      if (!post) return '';
      const rs = reviewMap.get(entry.id) || null;
      return renderPost(post, rs);
    })
    .join('');

  if (results.some(e => allPosts[e.id] && allPosts[e.id].oembed_html)) {
    loadTwitterWidget();
    if (window.twttr && window.twttr.widgets) {
      window.twttr.widgets.load(container);
    }
  }
}

// -- Event listeners --
document.getElementById('search-input').addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(renderView, 150);
});
document.getElementById('date-filter').addEventListener('change', renderView);
document.getElementById('sort-order').addEventListener('change', renderView);
document.addEventListener('keydown', (e) => {
  if (currentMode !== 'carousel') return;
  if (document.activeElement === document.getElementById('search-input')) return;
  const results = filterAndSort();
  if (e.key === 'ArrowRight' && carouselIndex < results.length - 1) {
    carouselIndex++; renderView(); window.scrollTo(0, 0);
  } else if (e.key === 'ArrowLeft' && carouselIndex > 0) {
    carouselIndex--; renderView(); window.scrollTo(0, 0);
  } else if (e.key === 'Escape') {
    setMode('stream');
  }
});

// -- Bootstrap: fetch all JSON files --
Promise.all([
  fetch('search-index.json').then(r => { if (!r.ok) throw new Error('search-index.json: ' + r.status); return r.json(); }),
  fetch('posts.json').then(r => { if (!r.ok) throw new Error('posts.json: ' + r.status); return r.json(); }),
  fetch('tags.json').then(r => { if (!r.ok) throw new Error('tags.json: ' + r.status); return r.json(); }),
  fetch('topics.json').then(r => { if (!r.ok) throw new Error('topics.json: ' + r.status); return r.json(); }),
  fetch('review_state.json').then(r => { if (!r.ok) throw new Error('review_state.json: ' + r.status); return r.json(); }),
]).then(([indexData, postsData, tagsData, topicsData, reviewData]) => {
  searchIndex = indexData.entries || [];
  totalPostCount = postsData.post_count || 0;
  exportedDate = (postsData.exported_at || '').split('T')[0];

  (postsData.posts || []).forEach(p => { allPosts[p.x_post_id] = p; });
  reviewMap = new Map((reviewData.review_states || []).map(r => [r.post_id, r]));

  document.getElementById('footer').textContent =
    `Exported ${exportedDate} · ${totalPostCount} posts`;

  document.getElementById('loading').style.display = 'none';
  renderView();
}).catch(err => {
  showError(err.message || String(err));
});
</script>
</body>
</html>"""
