"""Tests for the CLI surface: each command maps to a core op and round-trips."""

import pytest
from typer.testing import CliRunner

from surfaces.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path / "posts"))
    monkeypatch.setenv("BLOG_INDEX_PATH", str(tmp_path / "index.sqlite"))


def run(*args, **kwargs):
    result = runner.invoke(app, list(args), **kwargs)
    return result


def test_create_then_list_and_get():
    assert run("create", "--title", "Hello World", "--description", "Hi",
               "--body", "Body **here**", "--tag", "meta").exit_code == 0

    listed = run("list")
    assert listed.exit_code == 0
    assert "hello-world" in listed.output

    got = run("get", "hello-world")
    assert got.exit_code == 0
    assert "slug: hello-world" in got.output      # raw markdown source
    assert "Body **here**" in got.output


def test_create_duplicate_slug_fails():
    run("create", "--title", "Dup", "--description", "d", "--body", "b")
    result = run("create", "--title", "Dup", "--description", "d", "--body", "b")
    assert result.exit_code == 1
    assert "already exists" in result.output


def test_get_missing_fails():
    result = run("get", "ghost")
    assert result.exit_code == 1
    assert "no such post" in result.output


def test_create_with_date_schedules_post():
    from datetime import timedelta

    from core import store

    tomorrow = (store.today_utc() + timedelta(days=1)).isoformat()
    assert run("create", "--title", "Scheduled", "--description", "d",
               "--body", "b", "--status", "published", "--date", tomorrow).exit_code == 0
    # CLI is an authoring surface: it lists the scheduled post.
    assert "scheduled" in run("list").output
    assert store.get_post("scheduled").date.isoformat() == tomorrow


def test_create_with_bad_date_fails():
    result = run("create", "--title", "Bad", "--description", "d",
                 "--body", "b", "--date", "not-a-date")
    assert result.exit_code == 1
    assert "invalid date" in result.output


def test_publish_and_unpublish_filter_in_list():
    run("create", "--title", "Toggle", "--description", "d", "--body", "b")
    assert "toggle" not in run("list", "--status", "published").output

    run("publish", "toggle")
    assert "toggle" in run("list", "--status", "published").output

    run("unpublish", "toggle")
    assert "toggle" not in run("list", "--status", "published").output


def test_update_changes_fields():
    run("create", "--title", "Editable", "--description", "old", "--body", "b")
    assert run("update", "editable", "--description", "new").exit_code == 0
    assert "description: new" in run("get", "editable").output


def test_update_with_no_fields_fails():
    run("create", "--title", "X", "--description", "d", "--body", "b")
    result = run("update", "x")
    assert result.exit_code == 1
    assert "nothing to update" in result.output


def test_search_matches_body():
    run("create", "--title", "Findable", "--description", "d", "--body", "needle in here")
    result = run("search", "needle")
    assert result.exit_code == 0
    assert "findable" in result.output


def test_delete_with_confirmation():
    run("create", "--title", "Goner", "--description", "d", "--body", "b")
    # Decline first: the post survives.
    declined = run("delete", "goner", input="n\n")
    assert declined.exit_code == 1
    assert "goner" in run("list").output
    # Confirm with --yes: it's gone.
    assert run("delete", "goner", "--yes").exit_code == 0
    assert "goner" not in run("list").output


def test_reindex_recovers_from_a_deleted_cache(tmp_path):
    run("create", "--title", "Cached", "--description", "d", "--body", "searchterm")
    assert "cached" in run("search", "searchterm").output

    (tmp_path / "index.sqlite").unlink()
    assert "cached" not in run("search", "searchterm").output

    assert run("reindex").exit_code == 0
    assert "cached" in run("search", "searchterm").output
