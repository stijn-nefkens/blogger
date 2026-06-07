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

Tooling is [uv](https://docs.astral.sh/uv/). `uv sync` creates the virtualenv
and installs everything from `uv.lock`.

```sh
uv sync                          # create .venv and install deps (+ dev group)
uv run uvicorn app:app           # serves web + API on http://localhost:8000
uv run blog --help               # the CLI for the author
uv run python -m surfaces.mcp_server   # the MCP server (stdio) for AI agents
uv run pytest                    # run the tests
uv run ruff check .              # lint
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

## Deployment

The repo ships a `Dockerfile` (uv-based) that builds a runnable image: it
installs from `uv.lock` with `--locked`, puts `.venv/bin` on `PATH`, and runs
`uvicorn app:app --host 0.0.0.0 --port 8000`. The MCP server is local-only and
is **not** part of the deployed process.

Git is the single source of truth: posts under `posts/` are committed, and
production runs with `BLOG_WRITE_TOKEN` **unset**, so all HTTP writes are
rejected and the deployed instance never diverges from the repo. Authoring is
edit → commit → push → redeploy.

The search index is disposable: on startup the app rebuilds it from `posts/` if
`BLOG_INDEX_PATH` doesn't exist, so a fresh container (empty `/data`, no volume)
still serves a populated blog.
