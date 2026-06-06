"""Round-trip tests for core.store through real .md files on disk.

Each test points BLOG_POSTS_DIR at a fresh tmp_path, so we exercise the actual
filesystem the way every surface will.
"""

import frontmatter
import pytest

from core import store


@pytest.fixture(autouse=True)
def posts_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path / "posts"))
    monkeypatch.setenv("BLOG_INDEX_PATH", str(tmp_path / "index.sqlite"))
    return tmp_path / "posts"


def test_create_writes_a_real_markdown_file(posts_dir):
    post = store.create_post(
        title="My First Post",
        description="A one-line summary.",
        body="Hello **world**.",
        tags=["meta", "hello"],
    )

    # Path is posts/<year>/<slug>.md, derived from date and slug.
    path = posts_dir / str(post.date.year) / "my-first-post.md"
    assert path.exists()

    # A generic frontmatter tool can read it with no app knowledge.
    fm = frontmatter.loads(path.read_text())
    assert fm["title"] == "My First Post"
    assert fm["slug"] == "my-first-post"
    assert fm["description"] == "A one-line summary."
    assert fm["status"] == "draft"
    assert fm["tags"] == ["meta", "hello"]
    assert fm["date"] == fm["updated"]  # updated equals date on creation
    assert fm.content == "Hello **world**."


def test_create_then_get_round_trips(posts_dir):
    created = store.create_post("Round Trip", "desc", "body text", tags=["a"])
    fetched = store.get_post("round-trip")
    assert fetched == created


def test_get_missing_returns_none(posts_dir):
    assert store.get_post("nope") is None


def test_create_rejects_duplicate_slug(posts_dir):
    store.create_post("Same Title", "d", "b")
    with pytest.raises(ValueError):
        store.create_post("Same Title", "other", "other")


def test_update_changes_fields_and_bumps_updated(posts_dir, monkeypatch):
    from datetime import date

    created = store.create_post("To Edit", "old desc", "old body")

    # Force a later "today" so the updated bump is observable.
    later = date(2999, 1, 1)
    monkeypatch.setattr(store, "date", _FixedDate(later))

    edited = store.update_post(
        "to-edit", description="new desc", body="new body", status="published"
    )
    assert edited.description == "new desc"
    assert edited.body == "new body"
    assert edited.status == "published"
    assert edited.slug == created.slug  # slug is permanent
    assert edited.date == created.date  # created date is permanent
    assert edited.updated == later

    # Change is persisted to the file, not just the returned object.
    assert store.get_post("to-edit") == edited


def test_update_rejects_unknown_fields(posts_dir):
    store.create_post("Guarded", "d", "b")
    # `date` is permanent (the created date) and not updatable; the guard rejects it.
    with pytest.raises(ValueError):
        store.update_post("guarded", date="2099-01-01")


def test_update_missing_raises(posts_dir):
    with pytest.raises(ValueError):
        store.update_post("ghost", description="x")


def test_set_status_toggles(posts_dir):
    store.create_post("Toggle Me", "d", "b")
    assert store.get_post("toggle-me").status == "draft"
    store.set_status("toggle-me", "published")
    assert store.get_post("toggle-me").status == "published"


def test_delete_removes_file(posts_dir):
    post = store.create_post("Delete Me", "d", "b")
    path = posts_dir / str(post.date.year) / "delete-me.md"
    assert path.exists()
    store.delete_post("delete-me")
    assert not path.exists()
    assert store.get_post("delete-me") is None


def test_delete_missing_raises(posts_dir):
    with pytest.raises(ValueError):
        store.delete_post("ghost")


def test_list_is_empty_initially(posts_dir):
    assert store.list_posts() == []


def test_list_returns_newest_first(posts_dir, monkeypatch):
    from datetime import date

    monkeypatch.setattr(store, "date", _FixedDate(date(2024, 1, 1)))
    store.create_post("Older", "d", "b")
    monkeypatch.setattr(store, "date", _FixedDate(date(2026, 1, 1)))
    store.create_post("Newer", "d", "b")

    slugs = [p.slug for p in store.list_posts()]
    assert slugs == ["newer", "older"]


def test_list_filters_by_status_and_tag(posts_dir):
    store.create_post("Pub", "d", "b", tags=["x"], status="published")
    store.create_post("Draft", "d", "b", tags=["x"], status="draft")
    store.create_post("Other", "d", "b", tags=["y"], status="published")

    assert {p.slug for p in store.list_posts(status="published")} == {"pub", "other"}
    assert {p.slug for p in store.list_posts(tag="x")} == {"pub", "draft"}
    assert {p.slug for p in store.list_posts(status="published", tag="y")} == {"other"}


class _FixedDate:
    """Stand-in for the `date` module used inside store, with a fixed today()."""

    def __init__(self, today):
        self._today = today

    def today(self):
        return self._today
