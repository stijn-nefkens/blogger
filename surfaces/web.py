"""Web surface — reader-facing HTML, plus the RSS feed.

Reads only; renders via core. Listing, tag pages, and the feed show published
posts only — what readers and feed consumers expect. A single post page renders
whatever exists so the author can preview a draft by visiting its URL.

Styling is a single inline <style> block (below) rather than a static file: it
keeps the surface self-contained with no extra route, dependency, or build step,
which matches the rest of the app. Links use BLOG_BASE_URL (default
http://localhost:8000) so the feed carries absolute URLs.
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
    posts = store.list_posts(status="published", as_of=store.today_utc())
    inner = '<h1 class="sr-only">Blog</h1>\n' + _post_list(posts)
    return HTMLResponse(_layout("Blog", inner))


@router.get("/posts/{slug}", response_class=HTMLResponse)
def post_page(slug: str):
    post = store.get_post(slug, as_of=store.today_utc())
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    meta = f'<time datetime="{post.date.isoformat()}">{_human_date(post.date)}</time>'
    tags = _tag_links(post.tags)
    if tags:
        meta += f'<span class="tags">{tags}</span>'
    inner = (
        "<article>\n"
        f"<h1>{html.escape(post.title)}</h1>\n"
        f'<div class="post-meta">{meta}</div>\n'
        f'<div class="post-body">{render.render_post(post)}</div>\n'
        "</article>\n"
        '<a class="back" href="/">← All posts</a>'
    )
    return HTMLResponse(_layout(post.title, inner, description=post.description))


@router.get("/tags/{tag}", response_class=HTMLResponse)
def tag_page(tag: str):
    posts = store.list_posts(status="published", tag=tag, as_of=store.today_utc())
    heading = f"Posts tagged #{html.escape(tag)}"
    inner = f'<h1 class="page-title">{heading}</h1>\n' + _post_list(posts)
    return HTMLResponse(_layout(f"#{tag}", inner))


@router.get("/feed.xml")
def feed():
    base = _base_url()
    posts = store.list_posts(status="published", as_of=store.today_utc())
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
    meta = (
        f'<meta name="description" content="{html.escape(description)}">\n'
        if description
        else ""
    )
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"{meta}"
        '<link rel="alternate" type="application/rss+xml" title="RSS" href="/feed.xml">\n'
        f"<style>{_STYLE}</style>\n"
        "</head>\n<body>\n"
        '<header class="site-header wrap">'
        '<a class="brand" href="/">Blog</a>'
        '<nav class="site-nav"><a href="/feed.xml">RSS</a></nav>'
        "</header>\n"
        f'<main class="wrap">\n{inner}\n</main>\n'
        '<footer class="site-footer wrap">'
        "<span>Plain Markdown files on disk.</span>"
        '<a href="/feed.xml">RSS feed</a>'
        "</footer>\n"
        "</body>\n</html>\n"
    )


def _post_list(posts: list[Post]) -> str:
    if not posts:
        return '<p class="empty">No posts yet.</p>'
    items = "\n".join(_summary(p) for p in posts)
    return f'<ul class="post-list">\n{items}\n</ul>'


def _summary(post: Post) -> str:
    return (
        '<li class="post-list-item">'
        f'<h2 class="title"><a href="/posts/{post.slug}">{html.escape(post.title)}</a></h2>'
        f'<p class="meta"><time datetime="{post.date.isoformat()}">{_human_date(post.date)}</time></p>'
        f'<p class="desc">{html.escape(post.description)}</p>'
        "</li>"
    )


def _tag_links(tags: list[str]) -> str:
    return "".join(
        f'<a href="/tags/{html.escape(t)}">#{html.escape(t)}</a>' for t in tags
    )


def _human_date(d: date) -> str:
    return f"{d:%B} {d.day}, {d.year}"


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


# --- styles ------------------------------------------------------------------

_STYLE = """
:root {
  --bg: #faf9f5;
  --text: #292723;
  --muted: #6c6760;
  --accent: #c2603d;
  --accent-soft: #f0e7df;
  --border: #e7e2d7;
  --code-bg: #f2efe8;
  --maxw: 44rem;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1c1b19;
    --text: #ece8e0;
    --muted: #a39d92;
    --accent: #e0926f;
    --accent-soft: #322e29;
    --border: #34312c;
    --code-bg: #28251f;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI",
    Roboto, Helvetica, Arial, sans-serif;
  font-size: 1.0625rem;
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
  /* Sticky footer: fill at least the viewport so the footer sits at the bottom
     on short pages instead of floating mid-screen. */
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.wrap {
  width: 100%; max-width: var(--maxw); margin: 0 auto;
  padding-left: 1.25rem; padding-right: 1.25rem;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
h1, h2, h3 { line-height: 1.25; letter-spacing: -0.02em; }

.site-header {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 1rem; padding-top: 1.75rem; padding-bottom: 1.25rem;
}
.brand {
  font-weight: 650; font-size: 1.05rem; letter-spacing: -0.01em;
  color: var(--text);
}
.brand:hover { color: var(--accent); text-decoration: none; }
.site-nav a { color: var(--muted); font-size: 0.9rem; }

main { padding-top: 1.5rem; padding-bottom: 4rem; flex: 1 0 auto; }

.page-title { font-size: 1.9rem; margin: 0.25rem 0 2rem; }

.post-list {
  list-style: none; padding: 0; margin: 0;
  display: flex; flex-direction: column; gap: 2.25rem;
}
.post-list-item .title {
  font-size: 1.3rem; font-weight: 620; margin: 0 0 0.15rem;
  letter-spacing: -0.01em;
}
.post-list-item .title a { color: var(--text); }
.post-list-item .title a:hover { color: var(--accent); text-decoration: none; }
.meta { color: var(--muted); font-size: 0.85rem; margin: 0; }
.post-list-item .desc { margin: 0.3rem 0 0; }

article h1 { font-size: 2.1rem; margin: 0.25rem 0 0.5rem; }
.post-meta {
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem 0.85rem;
  color: var(--muted); font-size: 0.85rem; margin-bottom: 2.25rem;
}
.tags { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.tags a {
  font-size: 0.78rem; color: var(--muted); background: var(--accent-soft);
  padding: 0.1rem 0.6rem; border-radius: 999px;
}
.tags a:hover { color: var(--accent); text-decoration: none; }

.post-body > :first-child { margin-top: 0; }
.post-body p, .post-body ul, .post-body ol { margin: 0 0 1.25rem; }
.post-body h2 { font-size: 1.5rem; margin: 2.25rem 0 0.8rem; }
.post-body h3 { font-size: 1.2rem; margin: 1.85rem 0 0.6rem; }
.post-body li { margin: 0.3rem 0; }
.post-body a { text-decoration: underline; text-underline-offset: 2px; }
.post-body img { max-width: 100%; height: auto; border-radius: 8px; }
.post-body blockquote {
  margin: 1.5rem 0; padding: 0.2rem 1.1rem;
  border-left: 3px solid var(--accent); color: var(--muted); font-style: italic;
}
.post-body hr { border: none; border-top: 1px solid var(--border); margin: 2.5rem 0; }
.post-body table { border-collapse: collapse; width: 100%; margin: 1.25rem 0; font-size: 0.95rem; }
.post-body th, .post-body td { border: 1px solid var(--border); padding: 0.5rem 0.7rem; text-align: left; }
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.9em; background: var(--code-bg); padding: 0.15em 0.4em; border-radius: 5px;
}
pre {
  background: var(--code-bg); padding: 1rem 1.1rem; border-radius: 10px;
  overflow-x: auto; line-height: 1.5; border: 1px solid var(--border);
}
pre code { background: none; padding: 0; font-size: 0.875rem; }

.back { display: inline-block; margin-top: 3rem; color: var(--muted); }
.back:hover { color: var(--accent); }
.empty { color: var(--muted); }

.site-footer {
  display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
  flex-shrink: 0;
  border-top: 1px solid var(--border); margin-top: 2rem;
  padding-top: 1.5rem; padding-bottom: 2.5rem; color: var(--muted); font-size: 0.85rem;
}
.site-footer a { color: var(--muted); }

.sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}
"""
