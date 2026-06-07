"""Tests for core.index: the SQLite cache is disposable and files always win."""

import pytest

from core import index, store


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path / "posts"))
    monkeypatch.setenv("BLOG_INDEX_PATH", str(tmp_path / "index.sqlite"))
    return tmp_path


def test_search_finds_by_title_description_body_and_tags():
    store.create_post("Python Tips", "About snakes", "Use list comprehensions.",
                      tags=["coding"])
    store.create_post("Garden Log", "Tomatoes update", "Watered the plants.",
                      tags=["outdoors"])

    assert [p.slug for p in store.search("python")] == ["python-tips"]      # title
    assert [p.slug for p in store.search("tomatoes")] == ["garden-log"]     # description
    assert [p.slug for p in store.search("comprehensions")] == ["python-tips"]  # body
    assert [p.slug for p in store.search("outdoors")] == ["garden-log"]     # tags


def test_search_is_case_insensitive_and_newest_first():
    from datetime import date

    store.create_post("Older Note", "d", "shared keyword here", date=date(2024, 1, 1))
    store.create_post("Newer Note", "d", "SHARED keyword too", date=date(2026, 1, 1))

    assert [p.slug for p in store.search("KEYWORD")] == ["newer-note", "older-note"]


def test_search_returns_empty_when_no_match():
    store.create_post("Only Post", "d", "b")
    assert store.search("nothing-matches") == []


def test_delete_removes_post_from_search():
    store.create_post("Findable", "d", "unique-term")
    assert len(store.search("unique-term")) == 1
    store.delete_post("findable")
    assert store.search("unique-term") == []


def test_update_refreshes_the_index():
    store.create_post("Mutable", "original", "body")
    assert len(store.search("original")) == 1
    store.update_post("mutable", description="rewritten")
    assert store.search("original") == []
    assert [p.slug for p in store.search("rewritten")] == ["mutable"]


def test_rebuild_reconstructs_from_files_alone(isolated):
    store.create_post("First", "alpha", "body one", tags=["t1"])
    store.create_post("Second", "beta", "body two", tags=["t2"])

    before = store.search("body")

    # Blow the cache away entirely — files are untouched.
    (isolated / "index.sqlite").unlink()
    assert store.search("body") == []  # cache gone, nothing indexed

    index.rebuild()
    after = store.search("body")

    assert after == before
    assert {p.slug for p in after} == {"first", "second"}


def test_rebuild_is_idempotent():
    store.create_post("One", "d", "b")
    index.rebuild()
    first = store.search("b")
    index.rebuild()
    assert store.search("b") == first


def test_rebuild_if_missing_builds_when_absent(isolated):
    store.create_post("Solo", "d", "needle")
    (isolated / "index.sqlite").unlink()
    assert not (isolated / "index.sqlite").exists()  # mimic a fresh container

    index.rebuild_if_missing()  # don't touch the index before this; connecting
    assert (isolated / "index.sqlite").exists()      # creates the file
    assert [p.slug for p in store.search("needle")] == ["solo"]


def test_rebuild_if_missing_keeps_existing_data(isolated):
    store.create_post("Keep", "d", "keepterm")
    assert len(store.search("keepterm")) == 1
    index.rebuild_if_missing()  # file present -> no-op, data intact
    assert len(store.search("keepterm")) == 1
