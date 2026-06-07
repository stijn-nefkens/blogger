"""Test the composed app's startup behavior (the deployment contract).

A fresh container has an empty /data and no index file; the app must rebuild the
search index from the committed posts/ on startup so search isn't empty.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app
from core import store


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path / "posts"))
    monkeypatch.setenv("BLOG_INDEX_PATH", str(tmp_path / "index.sqlite"))
    return tmp_path


def test_startup_rebuilds_index_when_missing(isolated):
    # A published post is on disk; remove the index to mimic a fresh container.
    store.create_post("Fresh Boot", "d", "findme", status="published")
    (isolated / "index.sqlite").unlink()

    with TestClient(app) as client:  # entering the context runs the lifespan
        results = client.get("/api/search", params={"q": "findme"}).json()

    assert [p["slug"] for p in results] == ["fresh-boot"]


def test_static_files_are_served():
    """A committed image under static/ is reachable at /static/... ."""
    client = TestClient(app)
    asset = Path("static/memes/__test_serve__.png")
    asset.write_bytes(b"\x89PNG fake-image-bytes")
    try:
        resp = client.get("/static/memes/__test_serve__.png")
        assert resp.status_code == 200
        assert resp.content == b"\x89PNG fake-image-bytes"
    finally:
        asset.unlink()

