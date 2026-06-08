"""Tests for the web surface: reader HTML and the RSS feed.

Includes the cross-surface check from the build order: a post created via the
API appears on the web page and in the feed.
"""

import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from app import app

TOKEN = "secret-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path / "posts"))
    monkeypatch.setenv("BLOG_INDEX_PATH", str(tmp_path / "index.sqlite"))
    monkeypatch.setenv("BLOG_WRITE_TOKEN", TOKEN)
    monkeypatch.setenv("BLOG_BASE_URL", "https://example.com")


@pytest.fixture
def client():
    return TestClient(app)


def _create(client, title, status="published", **kw):
    body = {"title": title, "description": f"{title} summary", "body": "Body **md**", "status": status, **kw}
    return client.post("/api/posts", json=body, headers=AUTH)


def test_index_lists_published_only(client):
    _create(client, "Published One")
    _create(client, "A Draft", status="draft")

    html = client.get("/").text
    assert "Published One" in html
    assert '/posts/published-one' in html
    assert "A Draft" not in html  # drafts excluded from the listing


def test_post_created_via_api_appears_on_web(client):
    _create(client, "Cross Surface")  # created through the API...
    html = client.get("/posts/cross-surface").text  # ...rendered on the web
    assert "<h1>Cross Surface</h1>" in html
    assert "<strong>md</strong>" in html  # markdown body rendered to HTML
    assert '<meta name="description"' in html


def test_post_body_renders_static_image(client):
    _create(client, "Memey", body="![a meme](/static/memes/memey.png)")
    html = client.get("/posts/memey").text
    assert '<img src="/static/memes/memey.png" alt="a meme" />' in html


def test_post_page_has_meme_fallback_for_broken_images(client):
    # Memes are hotlinked GIFs; a broken one should swap to the outlived-Google line.
    _create(client, "Memey", body="![a meme](https://media.tenor.com/dead.gif)")
    html = client.get("/posts/memey").text
    # The meme still renders; the browser only swaps it if it 404s.
    assert '<img src="https://media.tenor.com/dead.gif" alt="a meme" />' in html
    # The client-side handler is wired to post-body images with the exact line.
    assert "it appears that the blog outlived google" in html
    assert '.post-body img' in html


def test_listing_has_no_meme_fallback(client):
    # The fallback is scoped to post pages, not the listing.
    _create(client, "Memey", body="![a meme](https://media.tenor.com/dead.gif)")
    assert "it appears that the blog outlived google" not in client.get("/").text


def test_home_header_shows_site_name_not_a_back_link(client):
    html = client.get("/").text
    assert '<span class="brand">Blog</span>' in html
    assert "← All posts" not in html  # no link pointing at the page you're on


def test_post_header_has_back_link_and_title_suffix(client):
    _create(client, "Hello")
    html = client.get("/posts/hello").text
    assert '<a class="home-link" href="/">← All posts</a>' in html
    assert "<title>Hello — Blog</title>" in html


def test_pages_have_a_favicon(client):
    assert 'rel="icon"' in client.get("/").text


def test_post_page_renders_tags_as_links(client):
    _create(client, "Tagged", tags=["python", "meta"])
    html = client.get("/posts/tagged").text
    assert '<a href="/tags/python">#python</a>' in html


def test_tag_page_filters(client):
    _create(client, "Has Tag", tags=["x"])
    _create(client, "No Tag", tags=["y"])
    html = client.get("/tags/x").text
    assert "Has Tag" in html
    assert "No Tag" not in html


def test_missing_post_is_404(client):
    assert client.get("/posts/ghost").status_code == 404


def test_feed_is_valid_rss_with_published_newest_first(client):
    # Two published posts (created same day; slug breaks the tie deterministically)
    _create(client, "Apple")
    _create(client, "Banana")
    _create(client, "Hidden Draft", status="draft")

    resp = client.get("/feed.xml")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/rss+xml")

    root = ET.fromstring(resp.text)  # well-formed XML or this raises
    channel = root.find("channel")
    titles = [item.find("title").text for item in channel.findall("item")]

    assert "Hidden Draft" not in titles  # drafts excluded
    assert set(titles) == {"Apple", "Banana"}

    # Links are absolute, built from BLOG_BASE_URL.
    first_link = channel.find("item").find("link").text
    assert first_link.startswith("https://example.com/posts/")

    # Each item carries a pubDate and a description.
    for item in channel.findall("item"):
        assert item.find("pubDate").text
        assert item.find("description").text


def test_feed_handles_empty_blog(client):
    resp = client.get("/feed.xml")
    assert resp.status_code == 200
    root = ET.fromstring(resp.text)
    assert root.find("channel").findall("item") == []
