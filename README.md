# blog

A minimal, AI-native blogging app. **Files are the source of truth**: every post
is a plain Markdown file with YAML frontmatter under `posts/<year>/<slug>.md`.
The app is only a viewer/editor over those files, so it's trivial to abandon for
another tool — point any Markdown-aware app at `posts/` and nothing is lost.

## Architecture

- `core/` — all logic, knows nothing about HTTP/MCP/CLI. Models, file store,
  Markdown rendering, and a disposable SQLite search index.
- `surfaces/` — thin adapters over the core: `cli.py`, `api.py` (JSON), `web.py`
  (reader HTML + RSS feed), `mcp_server.py` (MCP tools for AI agents).
- `app.py` — composes the web + API surfaces into one FastAPI process.

## Run

```sh
pip install -e .            # or: pip install -e '.[dev]' for tests
uvicorn app:app            # serves web + API on http://localhost:8000
blog --help                # the CLI for the author
python -m surfaces.mcp_server   # the MCP server (stdio) for AI agents
```

The MCP server exposes one tool per core operation (`list_posts`, `get_post`,
`create_post`, `update_post`, `publish_post`, `delete_post`, `search`). It has no
auth and is intended to run locally; see the TODO in `surfaces/mcp_server.py`
before exposing it remotely.

There is no build step. The SQLite index (`index.sqlite`) is a cache rebuilt
from `posts/`; deleting it loses nothing (`blog reindex` repopulates it).

## Configuration (environment variables)

| Variable           | Default                 | Purpose                                    |
| ------------------ | ----------------------- | ------------------------------------------ |
| `BLOG_POSTS_DIR`   | `posts`                 | Where post files live (source of truth).   |
| `BLOG_INDEX_PATH`  | `index.sqlite`          | Disposable search cache.                   |
| `BLOG_BASE_URL`    | `http://localhost:8000` | Absolute base URL used in the RSS feed.    |
| `BLOG_WRITE_TOKEN` | _(unset)_               | Shared secret required for HTTP API writes. |

## Authorization

Reads are public. HTTP API writes (`POST/PATCH/DELETE`) require the bearer token:

```sh
curl -H "Authorization: Bearer $BLOG_WRITE_TOKEN" ...   # or: -H "X-API-Key: ..."
```

If `BLOG_WRITE_TOKEN` is unset, all writes are rejected. The CLI needs no auth
(it runs on the author's machine).

**Deploy behind HTTPS in production** so the bearer token is never sent in
cleartext.
