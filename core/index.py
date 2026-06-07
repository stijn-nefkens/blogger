"""The disposable SQLite cache for search and listing.

This is ONLY a cache. Files in posts/ are the source of truth; deleting
index.sqlite and calling rebuild() must lose nothing. On any inconsistency,
files win — so search() returns Post objects loaded from files, not from here.

The index path is configurable via BLOG_INDEX_PATH (defaults to ./index.sqlite).
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from core.models import Post

_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    slug        TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    body        TEXT NOT NULL,
    tags        TEXT NOT NULL,
    status      TEXT NOT NULL,
    date        TEXT NOT NULL
);
"""


def rebuild() -> None:
    """Drop the cache and repopulate it by scanning posts/ alone."""
    from core import store  # local import avoids an import cycle

    with _connect() as conn:
        conn.execute("DROP TABLE IF EXISTS posts")
        conn.execute(_SCHEMA)
        for post in store.list_posts():
            _insert(conn, post)


def rebuild_if_missing() -> None:
    """Build the cache from posts/ if the index file doesn't exist yet.

    On a fresh container with an empty /data (no persisted volume), the index
    file is absent; without this, search would return nothing until a write or
    an explicit reindex. The index is disposable, so this simply repopulates it
    from the source-of-truth files. If the file already exists, it's left as-is.
    """
    if not _db_path().exists():
        rebuild()



def index_post(post: Post) -> None:
    """Add or replace a single post in the cache (called after a file write)."""
    with _connect() as conn:
        _insert(conn, post)


def remove_post(slug: str) -> None:
    """Drop a single post from the cache (called after a file delete)."""
    with _connect() as conn:
        conn.execute("DELETE FROM posts WHERE slug = ?", (slug,))


def search(query: str) -> list[Post]:
    """Posts matching query in title/description/body/tags, newest-first.

    The cache only tells us *which* posts match; the Post data itself is loaded
    from files, so files remain authoritative even if the cache is stale.
    """
    from core import store  # local import avoids an import cycle

    like = f"%{query}%"
    with _connect() as conn:
        rows = conn.execute(
            "SELECT slug FROM posts "
            "WHERE title LIKE ? OR description LIKE ? OR body LIKE ? OR tags LIKE ? "
            "ORDER BY date DESC, slug ASC",
            (like, like, like, like),
        ).fetchall()

    posts = []
    for (slug,) in rows:
        post = store.get_post(slug)
        if post is not None:  # skip entries the cache has but files no longer do
            posts.append(post)
    return posts


# --- internals ---------------------------------------------------------------


def _db_path() -> Path:
    return Path(os.environ.get("BLOG_INDEX_PATH", "index.sqlite"))


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Open a connection, commit on success, and always close it.

    Closing matters: a lingering connection keeps the SQLite file open, which on
    Windows prevents deleting/rebuilding index.sqlite (and leaks handles
    everywhere). sqlite3's own `with conn` only commits — it never closes.
    """
    conn = sqlite3.connect(_db_path())
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _insert(conn: sqlite3.Connection, post: Post) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO posts "
        "(slug, title, description, body, tags, status, date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            post.slug,
            post.title,
            post.description,
            post.body,
            " ".join(post.tags),
            post.status,
            post.date.isoformat(),
        ),
    )
