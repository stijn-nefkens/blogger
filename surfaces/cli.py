"""CLI surface — the same core operations for the author and for agents shelling out.

A thin adapter: each command parses input and calls one core function. No
business logic lives here, and no auth — the CLI runs on a machine the author
already controls (see CLAUDE.md Part 10).
"""

from __future__ import annotations

import typer

from core import index, store
from core.models import Post, dump

app = typer.Typer(help="Manage the blog. Files in posts/ are the source of truth.", add_completion=False)


@app.command("list")
def list_posts(
    status: str = typer.Option(None, help="Filter by status: draft or published."),
    tag: str = typer.Option(None, help="Filter by tag."),
) -> None:
    """List posts, newest-first."""
    for post in store.list_posts(status=status, tag=tag):
        typer.echo(_line(post))


@app.command()
def get(slug: str) -> None:
    """Print a post as its raw Markdown file (the source of truth)."""
    post = store.get_post(slug)
    if post is None:
        _fail(f"no such post: {slug}")
    typer.echo(dump(post))


@app.command()
def create(
    title: str = typer.Option(..., help="Post title; the slug is derived from it."),
    description: str = typer.Option(..., help="One-line summary for listings and the feed."),
    body: str = typer.Option(..., help="Post body in Markdown."),
    tag: list[str] = typer.Option(None, "--tag", help="Repeat to add multiple tags."),
    status: str = typer.Option("draft", help="draft or published."),
) -> None:
    """Create a new post."""
    post = _try(store.create_post, title, description, body, tags=tag, status=status)
    typer.echo(f"created {post.slug}")


@app.command()
def update(
    slug: str,
    title: str = typer.Option(None),
    description: str = typer.Option(None),
    body: str = typer.Option(None),
    tag: list[str] = typer.Option(None, "--tag", help="Replaces all tags; repeat for multiple."),
    status: str = typer.Option(None),
) -> None:
    """Update fields of an existing post (slug and date are permanent)."""
    fields = {
        k: v
        for k, v in {"title": title, "description": description, "body": body, "status": status}.items()
        if v is not None
    }
    if tag:  # only touch tags when at least one --tag was given
        fields["tags"] = tag
    if not fields:
        _fail("nothing to update; pass at least one field")
    post = _try(store.update_post, slug, **fields)
    typer.echo(f"updated {post.slug}")


@app.command()
def publish(slug: str) -> None:
    """Publish a post (status -> published)."""
    post = _try(store.set_status, slug, "published")
    typer.echo(f"published {post.slug}")


@app.command()
def unpublish(slug: str) -> None:
    """Unpublish a post (status -> draft)."""
    post = _try(store.set_status, slug, "draft")
    typer.echo(f"unpublished {post.slug}")


@app.command()
def delete(
    slug: str,
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Delete a post's file."""
    if not yes:
        typer.confirm(f"Delete post '{slug}'?", abort=True)
    _try(store.delete_post, slug)
    typer.echo(f"deleted {slug}")


@app.command()
def search(query: str) -> None:
    """Search posts by title, description, body, or tags."""
    for post in store.search(query):
        typer.echo(_line(post))


@app.command()
def reindex() -> None:
    """Rebuild the disposable search cache from posts/ (run after editing files by hand)."""
    index.rebuild()
    typer.echo("reindexed")


# --- helpers -----------------------------------------------------------------


def _line(post: Post) -> str:
    return f"[{post.status}] {post.date} {post.slug} — {post.title}"


def _fail(message: str):
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(1)


def _try(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        _fail(str(exc))


if __name__ == "__main__":
    app()
