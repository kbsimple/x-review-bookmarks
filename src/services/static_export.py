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
from typing import Any

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

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._posts_repo = PostsRepository(conn)
        self._review_repo = ReviewStateRepository(conn)
        self._tags_repo = TagsRepository(conn)
        self._topics_repo = TopicsRepository(conn)

    def export(self, output_dir: Path) -> StaticExportResult:
        """Export all data to output_dir.

        Creates output_dir if it does not exist. Silently overwrites on re-run.

        Args:
            output_dir: Directory to write all export files into.

        Returns:
            StaticExportResult with counts and list of files written.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        exported_at = datetime.now(timezone.utc).isoformat()

        # Load all data once -- bulk queries only
        posts = self._posts_repo.get_all_with_embedded()
        tag_map = self._build_post_tag_map()
        topic_map = self._build_post_topic_map()

        files: list[Path] = []
        files.append(self._write_posts_json(output_dir, posts, tag_map, topic_map, exported_at))
        files.append(self._write_tags_json(output_dir, exported_at))
        files.append(self._write_topics_json(output_dir, exported_at))
        files.append(self._write_review_state_json(output_dir, exported_at))
        files.append(self._write_search_index_json(output_dir, posts, tag_map, topic_map, exported_at))

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
