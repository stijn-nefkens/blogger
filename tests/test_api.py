"""Tests for the JSON API surface: core mirror + token-guarded writes."""

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


@pytest.fixture
def client():
    return TestClient(app)


def _create(client, title="Hello World", **kw):
    body = {"title": title, "description": "A summary", "body": "Some **md**", **kw}
    return client.post("/api/posts", json=body, headers=AUTH)


# --- auth --------------------------------------------------------------------


def test_writes_require_a_token(client):
    assert client.post("/api/posts", json={"title": "X", "description": "d", "body": "b"}).status_code == 401


def test_writes_reject_a_wrong_token(client):
    r = client.post(
        "/api/posts",
        json={"title": "X", "description": "d", "body": "b"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401


def test_x_api_key_header_also_works(client):
    r = client.post(
        "/api/posts",
        json={"title": "Via Key", "description": "d", "body": "b"},
        headers={"X-API-Key": TOKEN},
    )
    assert r.status_code == 201


def test_reads_are_public(client):
    _create(client)
    assert client.get("/api/posts").status_code == 200
    assert client.get("/api/posts/hello-world").status_code == 200
    assert client.get("/api/search", params={"q": "hello"}).status_code == 200


# --- CRUD --------------------------------------------------------------------


def test_create_returns_201_and_the_post(client):
    r = _create(client, tags=["meta"], status="published")
    assert r.status_code == 201
    data = r.json()
    assert data["slug"] == "hello-world"
    assert data["tags"] == ["meta"]
    assert data["status"] == "published"
    assert data["date"] == data["updated"]


def test_create_duplicate_slug_conflicts(client):
    _create(client)
    assert _create(client).status_code == 409


def test_get_missing_is_404(client):
    assert client.get("/api/posts/ghost").status_code == 404


def test_update_changes_fields(client):
    _create(client)
    r = client.patch("/api/posts/hello-world", json={"description": "new"}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["description"] == "new"
    assert client.get("/api/posts/hello-world").json()["description"] == "new"


def test_update_missing_is_404(client):
    assert client.patch("/api/posts/ghost", json={"description": "x"}, headers=AUTH).status_code == 404


def test_set_status_publishes(client):
    _create(client)
    r = client.post("/api/posts/hello-world/status", json={"status": "published"}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["status"] == "published"


def test_delete_removes_post(client):
    _create(client)
    assert client.delete("/api/posts/hello-world", headers=AUTH).status_code == 204
    assert client.get("/api/posts/hello-world").status_code == 404


def test_delete_requires_token(client):
    _create(client)
    assert client.delete("/api/posts/hello-world").status_code == 401


def test_search_finds_created_post(client):
    _create(client, title="Findable", body="needle here")
    results = client.get("/api/search", params={"q": "needle"}).json()
    assert [p["slug"] for p in results] == ["findable"]
