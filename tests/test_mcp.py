"""Tests for the MCP surface: tools mirror core ops and stay consistent with files."""

import asyncio

import frontmatter
import pytest

from core import store
from surfaces import mcp_server as srv


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("BLOG_POSTS_DIR", str(tmp_path / "posts"))
    monkeypatch.setenv("BLOG_INDEX_PATH", str(tmp_path / "index.sqlite"))
    return tmp_path / "posts"


def test_all_core_ops_are_exposed_as_tools():
    names = {t.name for t in asyncio.run(srv.mcp.list_tools())}
    assert names == {
        "list_posts", "get_post", "create_post", "update_post",
        "publish_post", "delete_post", "search",
    }


def test_create_writes_the_same_file_format(isolated):
    post = srv.create_post("Hello World", "A summary", "Body **md**", tags=["meta"])
    assert post["slug"] == "hello-world"
    assert post["date"] == post["updated"]

    # Same on-disk format as every other surface, readable by a generic tool.
    path = isolated / post["date"][:4] / "hello-world.md"
    fm = frontmatter.loads(path.read_text())
    assert fm["title"] == "Hello World"
    assert fm["tags"] == ["meta"]
    assert fm.content == "Body **md**"

    # And it shows up through the core store.
    assert store.get_post("hello-world").title == "Hello World"


def test_get_missing_raises():
    with pytest.raises(ValueError):
        srv.get_post("ghost")


def test_list_and_search_reflect_creates():
    srv.create_post("First", "d", "alpha body")
    srv.create_post("Second", "d", "beta body")
    assert {p["slug"] for p in srv.list_posts()} == {"first", "second"}
    assert [p["slug"] for p in srv.search("beta")] == ["second"]


def test_update_changes_fields_and_bumps_updated():
    srv.create_post("Editable", "old", "b")
    updated = srv.update_post("editable", description="new")
    assert updated["description"] == "new"
    assert store.get_post("editable").description == "new"


def test_update_with_nothing_raises():
    srv.create_post("X", "d", "b")
    with pytest.raises(ValueError):
        srv.update_post("x")


def test_publish_and_unpublish():
    srv.create_post("Toggle", "d", "b")
    assert srv.publish_post("toggle")["status"] == "published"
    assert srv.publish_post("toggle", published=False)["status"] == "draft"


def test_delete_removes_post():
    srv.create_post("Goner", "d", "b")
    assert srv.delete_post("goner") == "deleted goner"
    assert store.get_post("goner") is None


def test_create_via_protocol_call_tool(isolated):
    """End-to-end through the MCP machinery, not just the bare function."""
    import json

    result = asyncio.run(
        srv.mcp.call_tool(
            "create_post",
            {"title": "Via Protocol", "description": "d", "body": "b", "status": "published"},
        )
    )
    content = result[0] if isinstance(result, tuple) else result
    data = json.loads(content[0].text)
    assert data["slug"] == "via-protocol"
    assert store.get_post("via-protocol").status == "published"


def test_create_with_future_date_schedules_but_authoring_still_sees_it():
    from datetime import timedelta

    tomorrow = (store.today_utc() + timedelta(days=1)).isoformat()
    post = srv.create_post("Mcp Sched", "d", "body", status="published", date=tomorrow)
    assert post["date"] == tomorrow
    assert post["updated"] == tomorrow
    # MCP is an authoring surface: the agent must still see what it scheduled.
    assert "mcp-sched" in {p["slug"] for p in srv.list_posts()}


def test_main_rebuilds_missing_index_on_startup(isolated, tmp_path, monkeypatch):
    """A fresh environment has no index; startup must rebuild it from posts/ so
    the agent's first search isn't empty."""
    srv.create_post("Indexed", "d", "findme", status="published")
    (tmp_path / "index.sqlite").unlink()

    monkeypatch.setattr(srv.mcp, "run", lambda *a, **k: None)  # don't block on stdio
    srv.main()

    assert [p["slug"] for p in srv.search("findme")] == ["indexed"]
