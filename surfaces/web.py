"""Web surface — minimal, semantic HTML for readers, plus the RSS feed.

Barely-styled on purpose: a correct, boring baseline to be redesigned once there
is real content (CLAUDE.md Part 6). Reads only; renders via core. Listing, tag
pages, and the feed show published posts only — what readers and feed consumers
expect. A single post page renders whatever exists so the author can preview a
draft by visiting its URL.

Links use BLOG_BASE_URL (default http://localhost:8000) so the feed carries
absolute URLs.
"""

from __future__ import annotations

import html
import os
from datetime import date, datetime, timezone
from email.utils import format_datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from core import render, store
from core.models import Post

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index():
    posts = store.list_posts(status="published")
    return HTMLResponse(_layout("Blog", _summaries(posts, "Blog")))


@router.get("/posts/{slug}", response_class=HTMLResponse)
def post_page(slug: str):
    post = store.get_post(slug)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    tags = " ".join(
        f'<a href="/tags/{html.escape(t)}">#{html.escape(t)}</a>' for t in post.tags
    )
    inner = (
        "<article>\n"
        f"<h1>{html.escape(post.title)}</h1>\n"
        f'<time datetime="{post.date.isoformat()}">{post.date.isoformat()}</time>\n'
        f"<div>{render.render_post(post)}</div>\n"
        + (f"<p>{tags}</p>\n" if tags else "")
        + "</article>\n"
        '<p><a href="/">← all posts</a></p>'
    )
    return HTMLResponse(_layout(post.title, inner, description=post.description))


@router.get("/tags/{tag}", response_class=HTMLResponse)
def tag_page(tag: str):
    posts = store.list_posts(status="published", tag=tag)
    heading = f"Posts tagged #{html.escape(tag)}"
    return HTMLResponse(_layout(f"#{tag}", _summaries(posts, heading)))


@router.get("/feed.xml")
def feed():
    base = _base_url()
    posts = store.list_posts(status="published")
    last = _rfc822(posts[0].date if posts else date.today())
    items = "".join(_feed_item(p, base) for p in posts)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n<channel>\n'
        f"<title>{_x('Blog')}</title>\n"
        f"<link>{_x(base + '/')}</link>\n"
        f"<description>{_x('Recent posts')}</description>\n"
        f"<lastBuildDate>{last}</lastBuildDate>\n"
        f"{items}"
        "</channel>\n</rss>\n"
    )
    return Response(content=xml, media_type="application/rss+xml")


# --- HTML helpers ------------------------------------------------------------


def _layout(title: str, inner: str, description: str | None = None) -> str:
    meta = f'<meta name="description" content="{html.escape(description)}">\n' if description else ""
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"{meta}"
        '<link rel="alternate" type="application/rss+xml" title="RSS" href="/feed.xml">\n'
        "</head>\n<body>\n"
        f"{inner}\n"
        "</body>\n</html>\n"
    )


def _summaries(posts: list[Post], heading: str) -> str:
    if not posts:
        return f"<h1>{html.escape(heading)}</h1>\n<p>No posts yet.</p>"
    items = "\n".join(_summary(p) for p in posts)
    return f"<h1>{html.escape(heading)}</h1>\n<ul>\n{items}\n</ul>"


def _summary(post: Post) -> str:
    return (
        "<li>"
        f'<a href="/posts/{post.slug}">{html.escape(post.title)}</a> '
        f'<time datetime="{post.date.isoformat()}">{post.date.isoformat()}</time>'
        f"<p>{html.escape(post.description)}</p>"
        "</li>"
    )


# --- feed helpers ------------------------------------------------------------


def _feed_item(post: Post, base: str) -> str:
    url = f"{base}/posts/{post.slug}"
    return (
        "<item>\n"
        f"<title>{_x(post.title)}</title>\n"
        f"<link>{_x(url)}</link>\n"
        f'<guid isPermaLink="true">{_x(url)}</guid>\n'
        f"<description>{_x(post.description)}</description>\n"
        f"<pubDate>{_rfc822(post.date)}</pubDate>\n"
        "</item>\n"
    )


def _base_url() -> str:
    return os.environ.get("BLOG_BASE_URL", "http://localhost:8000").rstrip("/")


def _rfc822(d: date) -> str:
    return format_datetime(datetime(d.year, d.month, d.day, tzinfo=timezone.utc))


def _x(text: str) -> str:
    return html.escape(text, quote=True)
