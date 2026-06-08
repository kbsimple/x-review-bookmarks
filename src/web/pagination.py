"""Cursor-based pagination for posts.

WEB-04: User can browse posts with cursor-based pagination.
"""

import base64
import json
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class Cursor:
    """Pagination cursor for stable ordering.

    Uses created_at and x_post_id for deterministic pagination.
    """

    created_at: str
    x_post_id: str

    def encode(self) -> str:
        """Encode cursor to base64 string.

        Returns:
            Base64-encoded cursor string.
        """
        data = json.dumps({
            "created_at": self.created_at,
            "x_post_id": self.x_post_id,
        })
        return base64.urlsafe_b64encode(data.encode()).decode()

    @classmethod
    def decode(cls, encoded: str) -> Optional["Cursor"]:
        """Decode cursor from base64 string.

        Args:
            encoded: Base64-encoded cursor string.

        Returns:
            Cursor object or None if invalid.
        """
        try:
            data = json.loads(
                base64.urlsafe_b64decode(encoded.encode()).decode()
            )
            return cls(
                created_at=data["created_at"],
                x_post_id=data["x_post_id"],
            )
        except (ValueError, KeyError, json.JSONDecodeError):
            return None


@dataclass
class Page:
    """A page of results with pagination metadata."""

    items: list[Any]
    next_cursor: Optional[str] = None
    has_more: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response.

        Returns:
            Dictionary with items and pagination metadata.
        """
        return {
            "items": self.items,
            "next_cursor": self.next_cursor,
            "has_more": self.has_more,
        }


__all__ = ["Cursor", "Page"]