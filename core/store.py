"""All operations over the posts/ files. This is the shared contract every
surface calls. It knows nothing about HTTP, MCP, or CLI — and nothing about the
SQLite index yet (search arrives with core/index.py).

Files are the source of truth. Each post is one Markdown file at
posts/<year>/<slug>.md, where <year> comes from the post's created date.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from core.models import Post, dump, parse, slugify
from core import index

logger = logging.getLogger(__name__)

# Fields a caller may change via update_post. `slug` and `date` are permanent
# (the slug is the stable URL; the date anchors the URL's year), so they're out.
_UPDATABLE = {"title", "description", "body", "tags", "status"}


def today_utc() -> date:
    """Today's date in UTC — the cutoff for scheduled-post visibility."""
    return datetime.now(timezone.utc).date()


def list_posts(
    status: str | None = None,
    tag: str | None = None,
    as_of: date | None = None,
) -> list[Post]:
    """All posts, newest-first by date, optionally filtered.

    `as_of` gates scheduled posts: when given, posts dated after it are excluded.
    Public surfaces pass today_utc(); authoring surfaces (CLI, MCP) omit it so
    they still see future-dated posts.
    """
    posts = []
    for path in _posts_dir().glob("*/*.md"):
        post = parse(path.read_text(encoding="utf-8"))
        if status is not None and post.status != status:
            continue
        if tag is not None and tag not in post.tags:
            continue
        if as_of is not None and post.date > as_of:
            continue
        posts.append(post)
    # Newest-first by date, with slug as a stable tiebreaker for same-date posts.
    posts.sort(key=lambda p: p.slug)
    posts.sort(key=lambda p: p.date, reverse=True)
    return posts


def get_post(slug: str, as_of: date | None = None) -> Post | None:
    """The post with this slug, or None if it doesn't exist (or, when `as_of` is
    given, if it's scheduled for after that date)."""
    path = _find_path(slug)
    if path is None:
        return None
    post = parse(path.read_text(encoding="utf-8"))
    if as_of is not None and post.date > as_of:
        return None
    return post


def create_post(
    title: str,
    description: str,
    body: str,
    tags: list[str] | None = None,
    status: str = "draft",
    date: date | None = None,
) -> Post:
    """Create a new post. The slug is derived from the title and must be unique.

    `date` is the publish date (defaults to today, UTC); a future date schedules
    the post — it stays hidden from public surfaces until that day. It also picks
    the posts/<year>/ folder.
    """
    slug = slugify(title)
    if _find_path(slug) is not None:
        raise ValueError(f"a post with slug '{slug}' already exists")
    when = date if date is not None else today_utc()
    post = Post(
        title=title,
        slug=slug,
        description=description,
        date=when,
        updated=when,
        status=status,
        tags=list(tags or []),
        body=body,
    )
    _write(post)
    return post


def update_post(slug: str, **fields) -> Post:
    """Change one or more updatable fields and bump `updated` to today."""
    unknown = set(fields) - _UPDATABLE
    if unknown:
        raise ValueError(f"cannot update fields: {sorted(unknown)}")
    post = get_post(slug)
    if post is None:
        raise ValueError(f"no such post: {slug}")
    for key, value in fields.items():
        setattr(post, key, value)
    post.updated = today_utc()
    _write(post)
    return post


def delete_post(slug: str) -> None:
    """Remove the post's file, then drop it from the index."""
    path = _find_path(slug)
    if path is None:
        raise ValueError(f"no such post: {slug}")
    path.unlink()  # files first...
    _try_index(lambda: index.remove_post(slug))  # ...then the cache


def set_status(slug: str, status: str) -> Post:
    """Toggle a post between draft and published."""
    return update_post(slug, status=status)


def search(query: str, as_of: date | None = None) -> list[Post]:
    """Posts matching the query, via the SQLite index, newest-first.

    `as_of` gates scheduled posts the same way list_posts does.
    """
    posts = index.search(query)
    if as_of is not None:
        posts = [p for p in posts if p.date <= as_of]
    return posts


# --- internals ---------------------------------------------------------------


def _posts_dir() -> Path:
    return Path(os.environ.get("BLOG_POSTS_DIR", "posts"))


def _write(post: Post) -> None:
    path = _posts_dir() / str(post.date.year) / f"{post.slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(post), encoding="utf-8")  # files first...
    _try_index(lambda: index.index_post(post))  # ...then the cache


def _try_index(update) -> None:
    """Run a cache update, but never let a cache failure fail a file operation.

    Files are the source of truth and the index is a disposable cache (the next
    reindex heals it), so a SQLite error here — e.g. a virtualized/network mount
    SQLite can't lock — must not undo a write that already hit disk.
    """
    try:
        update()
    except sqlite3.OperationalError as exc:
        logger.warning("index update skipped; will heal on next reindex: %s", exc)


def _find_path(slug: str) -> Path | None:
    for path in _posts_dir().glob(f"*/{slug}.md"):
        return path
    return None
