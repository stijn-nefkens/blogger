"""Scheduled posts: a future `date` hides a published post until that day (UTC).

Visibility is computed per request (live rendering), so a post appears on its
date with no process restart — exercised here by advancing the clock via
store.today_utc().
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import app
from core import store

TOKEN = "tok"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path / "posts"))
    monkeypatch.setenv("BLOG_INDEX_PATH", str(tmp_path / "index.sqlite"))
    monkeypatch.setenv("BLOG_WRITE_TOKEN", TOKEN)


@pytest.fixture
def client():
    return TestClient(app)


# --- core gating -------------------------------------------------------------


def test_create_defaults_to_today_utc():
    post = store.create_post("Now", "d", "b")
    assert post.date == store.today_utc()
    assert post.updated == post.date  # updated equals date on creation


def test_core_gates_future_posts_only_for_public_callers():
    today = store.today_utc()
    tomorrow = today + timedelta(days=1)
    store.create_post("Past", "d", "visible body", status="published", date=today)
    store.create_post("Future", "d", "embargoed body", status="published", date=tomorrow)

    # Authoring (no as_of) sees everything, including the scheduled post.
    assert {p.slug for p in store.list_posts()} == {"past", "future"}
    assert store.get_post("future") is not None
    assert [p.slug for p in store.search("embargoed")] == ["future"]

    # Public (as_of=today) hides the future post across list/get/search.
    assert {p.slug for p in store.list_posts(as_of=today)} == {"past"}
    assert store.get_post("future", as_of=today) is None
    assert store.get_post("past", as_of=today) is not None
    assert store.search("embargoed", as_of=today) == []


def test_future_date_round_trips_through_the_file():
    from datetime import date

    store.create_post("NYE 2099", "d", "b", status="published", date=date(2099, 12, 31))
    assert store.get_post("nye-2099").date == date(2099, 12, 31)


# --- web surface -------------------------------------------------------------


def test_scheduled_post_hidden_then_appears_on_web(client, monkeypatch):
    tomorrow = store.today_utc() + timedelta(days=1)
    store.create_post("Tomorrow News", "soon", "body", status="published", date=tomorrow)

    # Hidden everywhere public today.
    assert "Tomorrow News" not in client.get("/").text
    assert "tomorrow-news" not in client.get("/feed.xml").text
    assert client.get("/posts/tomorrow-news").status_code == 404

    # Advance the clock to the publish date — visible, no restart.
    monkeypatch.setattr(store, "today_utc", lambda: tomorrow)
    assert "Tomorrow News" in client.get("/").text
    assert "tomorrow-news" in client.get("/feed.xml").text
    assert client.get("/posts/tomorrow-news").status_code == 200


# --- API surface -------------------------------------------------------------


def test_api_hides_scheduled_from_public_but_author_can_manage(client):
    tomorrow = store.today_utc() + timedelta(days=1)
    created = client.post(
        "/api/posts",
        json={
            "title": "Api Sched", "description": "d", "body": "secret words",
            "status": "published", "date": tomorrow.isoformat(),
        },
        headers=AUTH,
    )
    assert created.status_code == 201
    assert created.json()["date"] == tomorrow.isoformat()

    # Public reads gate it.
    assert client.get("/api/posts/api-sched").status_code == 404
    assert "api-sched" not in [p["slug"] for p in client.get("/api/posts").json()]
    assert client.get("/api/search", params={"q": "secret"}).json() == []

    # The author (write token) can still update and delete the scheduled post.
    assert client.patch(
        "/api/posts/api-sched", json={"description": "changed"}, headers=AUTH
    ).status_code == 200
    assert client.delete("/api/posts/api-sched", headers=AUTH).status_code == 204
