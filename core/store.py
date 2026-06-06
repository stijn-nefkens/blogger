"""All operations over the posts/ files. This is the shared contract every
surface calls. It knows nothing about HTTP, MCP, or CLI — and nothing about the
SQLite index yet (search arrives with core/index.py).

Files are the source of truth. Each post is one Markdown file at
posts/<year>/<slug>.md, where <year> comes from the post's created date.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from core.models import Post, dump, parse, slugify
from core import index

# Fields a caller may change via update_post. `slug` and `date` are permanent
# (the slug is the stable URL; the date is the creation date), so they're out.
_UPDATABLE = {"title", "description", "body", "tags", "status"}


def list_posts(status: str | None = None, tag: str | None = None) -> list[Post]:
    """All posts, newest-first by date, optionally filtered by status and/or tag."""
    posts = []
    for path in _posts_dir().glob("*/*.md"):
        post = parse(path.read_text(encoding="utf-8"))
        if status is not None and post.status != status:
            continue
        if tag is not None and tag not in post.tags:
            continue
        posts.append(post)
    # Newest-first by date, with slug as a stable tiebreaker for same-date posts.
    posts.sort(key=lambda p: p.slug)
    posts.sort(key=lambda p: p.date, reverse=True)
    return posts


def get_post(slug: str) -> Post | None:
    """The post with this slug, or None if it doesn't exist."""
    path = _find_path(slug)
    if path is None:
        return None
    return parse(path.read_text(encoding="utf-8"))


def create_post(
    title: str,
    description: str,
    body: str,
    tags: list[str] | None = None,
    status: str = "draft",
) -> Post:
    """Create a new post. The slug is derived from the title and must be unique."""
    slug = slugify(title)
    if _find_path(slug) is not None:
        raise ValueError(f"a post with slug '{slug}' already exists")
    today = date.today()
    post = Post(
        title=title,
        slug=slug,
        description=description,
        date=today,
        updated=today,
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
    post.updated = date.today()
    _write(post)
    return post


def delete_post(slug: str) -> None:
    """Remove the post's file, then drop it from the index."""
    path = _find_path(slug)
    if path is None:
        raise ValueError(f"no such post: {slug}")
    path.unlink()
    index.remove_post(slug)


def set_status(slug: str, status: str) -> Post:
    """Toggle a post between draft and published."""
    return update_post(slug, status=status)


def search(query: str) -> list[Post]:
    """Posts matching the query, via the SQLite index, newest-first."""
    return index.search(query)


# --- internals ---------------------------------------------------------------


def _posts_dir() -> Path:
    return Path(os.environ.get("BLOG_POSTS_DIR", "posts"))


def _write(post: Post) -> None:
    path = _posts_dir() / str(post.date.year) / f"{post.slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(post), encoding="utf-8")  # files first...
    index.index_post(post)  # ...then the cache


def _find_path(slug: str) -> Path | None:
    for path in _posts_dir().glob(f"*/{slug}.md"):
        return path
    return None
