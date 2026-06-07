# Notes for Claude Code — from the agent driving the MCP server

Context: an AI agent (Cowork) authors posts unattended through
`surfaces/mcp_server.py` over stdio. The server works as specced; two small
changes would make unattended use robust. Per CLAUDE.md, this list is
deliberately minimal — nothing else is needed.

## 1. MCP server should rebuild a missing index on startup

`app.py` calls `index.rebuild_if_missing()` in its lifespan; the MCP server
doesn't. In a fresh environment (no `index.sqlite`), MCP writes work but
`search` silently returns nothing until the first write or a manual reindex —
confusing for an agent.

Fix: call `index.rebuild_if_missing()` in `mcp_server.py` before `mcp.run()`.

Verify: delete `index.sqlite`, start the MCP server, call `search` — published
posts are found.

## 2. Files-first error handling on writes

In `store._write`, the post file is written, then `index.index_post` runs. If
the index update raises — observed in practice: `sqlite3.OperationalError:
disk I/O error` when the repo sits on a virtualized/network mount that SQLite
can't lock — the whole call fails *after* the file was successfully written.
The agent gets an error for a write that actually succeeded.

The spec says the index is a disposable cache and files win, so an index
failure should not fail a write. Fix: in `_write` (and `delete_post`'s
`index.remove_post`), catch `sqlite3.OperationalError` around the index call
and continue — the next reindex heals the cache.

Verify: point `BLOG_INDEX_PATH` at an unwritable path; `create_post` still
returns the Post and the `.md` file exists.

## 3. Feature request: scheduled posts (date-gated visibility)

The author wants to schedule posts. Two ways to do it; the first needs your
code, the second needs none but is operationally fragile. Recommending the
first — push back if you disagree.

**Option A (recommended): future-dated posts are invisible until their date.**
Author writes the post with `status: published` and a future `date`, commits
and pushes immediately; the post appears on its date with no further action.
This fits the architecture: live rendering means visibility is computed per
request, production stays read-only, no daemon or cron, and the frontmatter
stays tool-agnostic (a future `date` is still plain YAML — no new
app-specific field).

Requirements:

- Public read surfaces (web listing, tag pages, single-post page, `/feed.xml`,
  public API reads) must not show a published post whose `date` is after
  today. Search included.
- Authoring surfaces (CLI, MCP) must still see scheduled posts, or an agent
  that created one would think it vanished. Suggest the visibility rule live
  in core (e.g. a parameter on `list_posts`/`get_post`), with the public
  surfaces opting in — logic in core, surfaces stay thin.
- `create_post` currently hardcodes `date=today`. It needs an optional date
  (which also determines the `posts/<year>/` folder).
- **Spec deviations to confirm with the author:** CLAUDE.md defines `date` as
  "created date" — this reuses it as "publish date" for future posts. Also
  decide timezone semantics (`date` is day-granular; suggest server-local or
  UTC, documented in the README).

Verify: a published post dated tomorrow is absent from `/`, `/feed.xml`, and
public API/search today; present in CLI/MCP listings; appears everywhere
tomorrow (or with a mocked clock) with no process restart.

**Option B (no code change, for contrast):** an external scheduled task flips
a draft to published via MCP at the target time, then commits and pushes.
Rejected as the default because it requires push credentials in the agent
environment and an agent awake at publish time; the post stays invisible if
either fails.

## No code needed (workarounds the agent already uses)

- On a mount SQLite can't lock, the agent sets `BLOG_INDEX_PATH` to a local
  path (e.g. `/tmp/index.sqlite`). Fine — the index is disposable.
- Posts created by writing files directly (bypassing the store) leave the
  index stale; `blog reindex` or `index.rebuild()` fixes it. Working as
  designed; agents should prefer the MCP tools.
