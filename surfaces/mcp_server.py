"""MCP server — the priority AI surface. One tool per core operation.

A thin adapter: each tool parses input and calls one core function, exactly like
the other surfaces. Tool descriptions are written so an agent can manage the blog
unattended.

Auth: none. This is safe ONLY while the server is local (gated by who can reach
the process), per CLAUDE.md Part 10.
TODO: if this MCP server is ever exposed remotely, enforce the same
BLOG_WRITE_TOKEN check on the write tools (create/update/delete/publish) that
surfaces/api.py uses.
"""

from __future__ import annotations

import dataclasses
from datetime import date as _date

from mcp.server.fastmcp import FastMCP

from core import index, store
from core.models import Post

mcp = FastMCP("blog")


@mcp.tool()
def list_posts(status: str | None = None, tag: str | None = None) -> list[dict]:
    """List posts newest-first. Optionally filter by status ("draft" or
    "published") and/or by a single tag."""
    return [_post(p) for p in store.list_posts(status=status, tag=tag)]


@mcp.tool()
def get_post(slug: str) -> dict:
    """Get a single post by its slug, including its full Markdown body."""
    post = store.get_post(slug)
    if post is None:
        raise ValueError(f"no such post: {slug}")
    return _post(post)


@mcp.tool()
def create_post(
    title: str,
    description: str,
    body: str,
    tags: list[str] | None = None,
    status: str = "draft",
    date: str | None = None,
) -> dict:
    """Create a new post. The slug is derived from the title and is permanent, so
    choose the title carefully. `description` is a required one-line summary used
    in listings and the feed. `body` is Markdown. New posts default to "draft";
    pass status="published" to publish immediately.

    To schedule a post, set status="published" and `date` to a future day
    (YYYY-MM-DD): it stays hidden from the public site until that date, in UTC.
    `date` defaults to today (UTC) when omitted."""
    when = _date.fromisoformat(date) if date else None
    return _post(
        store.create_post(title, description, body, tags=tags, status=status, date=when)
    )


@mcp.tool()
def update_post(
    slug: str,
    title: str | None = None,
    description: str | None = None,
    body: str | None = None,
    tags: list[str] | None = None,
    status: str | None = None,
) -> dict:
    """Update one or more fields of an existing post. Only the fields you pass are
    changed; the slug and created date are permanent and cannot be changed. The
    post's `updated` date is bumped automatically. Passing `tags` replaces all
    tags."""
    fields = {
        k: v
        for k, v in {
            "title": title,
            "description": description,
            "body": body,
            "tags": tags,
            "status": status,
        }.items()
        if v is not None
    }
    if not fields:
        raise ValueError("nothing to update; pass at least one field")
    return _post(store.update_post(slug, **fields))


@mcp.tool()
def publish_post(slug: str, published: bool = True) -> dict:
    """Publish a post (set status to "published"), or pass published=False to move
    it back to "draft"."""
    return _post(store.set_status(slug, "published" if published else "draft"))


@mcp.tool()
def delete_post(slug: str) -> str:
    """Delete a post's file permanently. This cannot be undone."""
    store.delete_post(slug)
    return f"deleted {slug}"


@mcp.tool()
def search(query: str) -> list[dict]:
    """Search posts by title, description, body, or tags. Returns matches
    newest-first."""
    return [_post(p) for p in store.search(query)]


def _post(post: Post) -> dict:
    """A JSON-serializable view of a Post (dates as ISO strings)."""
    data = dataclasses.asdict(post)
    data["date"] = post.date.isoformat()
    data["updated"] = post.updated.isoformat()
    return data


def main() -> None:
    # Rebuild the disposable index if it's missing (fresh environment), so an
    # agent's first `search` finds published posts instead of nothing — same
    # behavior app.py gives the web/API process.
    index.rebuild_if_missing()
    mcp.run()


if __name__ == "__main__":
    main()
