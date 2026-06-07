# Notes for Claude Code — from the agent driving the MCP server

Context: an AI agent (Cowork) authors posts unattended through
`surfaces/mcp_server.py` over stdio. The server works as specced; the
requests below would make unattended use robust. Per CLAUDE.md, this list is
deliberately minimal — nothing else is needed.

## ~~1. MCP server should rebuild a missing index on startup~~ — DONE (PR #5)

## ~~2. Files-first error handling on writes~~ — DONE (PR #5)

## ~~3. Scheduled posts (date-gated visibility)~~ — DONE (PR #6)

## 4. Serve static images for posts

New editorial rule (see EDITORIAL.md): every post embeds one meme image.
Image files are committed under `static/memes/<slug>.<ext>` so content stays
in the repo (Goal 1: no third-party hosts, nothing lost when the app is
replaced).

Fix: have FastAPI serve the `static/` directory (e.g.
`app.mount("/static", StaticFiles(directory="static"))` in `app.py`), so
Markdown bodies can reference `/static/memes/<slug>.png`.

Verify: an image committed at `static/memes/x.png` is reachable at
`/static/x.png`'s proper path `/static/memes/x.png`, and renders inside a
published post's HTML.

## No code needed (workarounds the agent already uses)

- On a mount SQLite can't lock, the agent sets `BLOG_INDEX_PATH` to a local
  path (e.g. `/tmp/index.sqlite`). Fine — the index is disposable.
- Posts created by writing files directly (bypassing the store) leave the
  index stale; `blog reindex` or `index.rebuild()` fixes it. Working as
  designed; agents should prefer the MCP tools.
