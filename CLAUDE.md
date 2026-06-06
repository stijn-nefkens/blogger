# CLAUDE.md

Build spec and behavioral guidelines for a minimal, AI-native blogging application.
This file is the source of truth for *what* to build and *how* to behave while building it.

---

## Part 1 — Behavioral Guidelines

These bias toward caution and simplicity over speed. Follow them throughout.

### Think before coding
- State assumptions explicitly. If uncertain, ask before implementing.
- If multiple interpretations exist, surface them — don't silently pick one.
- If a simpler approach exists than what's described here, say so and push back.

### Simplicity first (this project is explicitly KISS)
- Write the minimum code that solves the problem. Nothing speculative.
- No features beyond this spec. No abstractions for single-use code.
- No configurability, plugin systems, or "flexibility" that wasn't requested.
- No error handling for impossible scenarios.
- If a file grows large or clever, stop and simplify. A senior engineer reviewing
  this should call it boring and obvious, not impressive.

### Surgical changes
- Touch only what the current task requires.
- Match existing style. Don't refactor working code unasked.
- Every changed line should trace to a requirement in this spec.

### Goal-driven execution
- Turn each task into a verifiable goal with a test or check.
- For multi-step work, state a brief plan with a verification step per item, then loop until verified.

---

## Part 2 — What We're Building

A personal blogging application with two non-negotiable design goals:

1. **Replaceable by design.** The app must be trivial to abandon for a different
   app in the future. This is achieved by keeping all data *out of the application*:
   blog posts are plain files on disk, and the app is only a viewer/editor over them.
2. **AI-native.** Humans and AI agents perform the same operations through different
   thin surfaces over one shared core. MCP server is the priority machine surface.

### The core principle that satisfies both goals
**Files are the source of truth → one core library of operations → thin surfaces on top.**
Swap any surface, or the whole app, and the content is untouched.

---

## Part 3 — Architecture

```
blog/
  posts/                  # SOURCE OF TRUTH. one .md per post, YAML frontmatter.
    2026/
      my-first-post.md
  core/                   # all logic. knows NOTHING about HTTP / MCP / CLI.
    models.py             # Post dataclass + frontmatter parsing
    store.py              # list/get/create/update/delete/search over posts/ files
    render.py             # Markdown -> HTML
    index.py              # build/rebuild the disposable SQLite cache
  surfaces/               # thin adapters. each translates input -> core calls.
    web.py                # FastAPI routes that render posts for human readers
    api.py                # FastAPI JSON endpoints (canonical machine surface)
    mcp_server.py         # MCP server exposing core ops as tools
    cli.py                # CLI for the author + for agents shelling out
  app.py                  # composes FastAPI (web + api) into one process
  index.sqlite            # disposable cache, gitignored, rebuilt from posts/
  pyproject.toml
  tests/
```

### Tech choices (decided — do not substitute)
- Python 3.11+
- FastAPI for web + REST in one process
- MCP server as the priority AI surface (use the official Python MCP SDK)
- SQLite for the search/listing index ONLY — never authoritative
- Markdown library: `markdown` or `markdown-it-py`; frontmatter via `python-frontmatter`
- CLI via `typer`
- Serving: **live, rendered on request**, from the same process as the core.
  No static build step. A small cache (the SQLite index) avoids re-parsing every request.

---

## Part 4 — Data Format (the contract that outlives the app)

One Markdown file per post. Path: `posts/<year>/<slug>.md`.
Frontmatter is standard and tool-agnostic — encode nothing app-specific.

```markdown
---
title: My First Post
slug: my-first-post
description: A one-line summary used in listings, link previews, and the RSS feed.
date: 2026-06-06         # created date
updated: 2026-06-06      # last revised; equals date until edited
status: published        # or: draft
tags: [meta, hello]
---

Body content in plain Markdown.
```

Field notes:
- `description` — short blurb. Powers the listing page, the HTML `<meta>` description,
  and the feed. Don't auto-truncate the body as a fallback; require it on create.
- `updated` — set equal to `date` on creation; bump it whenever the post body or
  metadata changes. Both reads and feeds use it.

Rules:
- The file is authoritative for everything. Metadata lives only in frontmatter.
- `slug` is the stable identifier. Filenames derive from slug.
- **Slugs are permanent.** Once a post is published, its slug (and therefore its URL)
  must not change — external links and the feed depend on it. Pick carefully at creation.
  Renaming later would require a redirect, which is out of scope for now.
- Posts are listed newest-first (reverse-chronological) by `date` — the default
  behavior readers expect.
- Any Markdown-aware tool must be able to read these files with zero knowledge of this app.

---

## Part 5 — The Core Operations (the shared contract)

`core/store.py` exposes exactly these. Every surface calls these — no surface
reimplements logic or touches files directly.

- `list_posts(status=None, tag=None) -> list[Post]`
- `get_post(slug) -> Post | None`
- `create_post(title, description, body, tags=[], status="draft") -> Post`
- `update_post(slug, **fields) -> Post`
- `delete_post(slug) -> None`
- `set_status(slug, status) -> Post`   # draft <-> published
- `search(query) -> list[Post]`        # uses the SQLite index

### Index discipline (protects Goal 1)
- `core/index.py` provides `rebuild()` that scans `posts/` and repopulates SQLite.
- The index is a cache. Deleting `index.sqlite` must lose nothing.
- Writes go to files first, then update the index. On any inconsistency, files win.

---

## Part 6 — Surfaces (keep each thin, ~tens of lines)

- **web.py** — HTML for readers: index/listing, single post, tag pages. Renders via `core`.
  For this first pass, emit **minimal, semantic, barely-styled HTML** — no CSS framework,
  no design system, no layout opinions. The goal is a correct, boring baseline that will
  be replaced once there's real content to design against; do not invest in visual design now.
  Also serves the **RSS/Atom feed** at `/feed.xml` — an XML rendering of recent published
  posts (title, description, link, date) built from `list_posts(status="published")`.
  This is the machine-readable "what's new" surface; treat it as first-class, not an
  afterthought — it directly serves the AI-native goal (agents discover posts without scraping).
- **api.py** — JSON mirror of the core operations. This is the canonical machine API.
- **mcp_server.py** — one MCP tool per core operation (`list_posts`, `get_post`,
  `create_post`, `update_post`, `delete_post`, `publish_post`, `search`). Tool
  descriptions should be clear enough for an agent to manage the blog unattended.
- **cli.py** — same operations for the author and for agents shelling out.

A surface that contains business logic is a bug. Push it into `core`.

---

## Part 7 — Build Order

1. `core/models.py` + `core/store.py` (files only, no index yet) → verify: unit tests for create/get/update/delete/list round-trip through real .md files.
2. `core/render.py` → verify: Markdown renders, frontmatter excluded from body.
3. `core/index.py` → verify: `rebuild()` reconstructs full state from `posts/` alone; deleting the db and rebuilding yields identical results.
4. `surfaces/cli.py` → verify: each command maps to a core op; manual smoke test.
5. `surfaces/api.py` + `surfaces/web.py` in `app.py` → verify: endpoints return correct data; a post created via API appears on the web page; `/feed.xml` validates and lists published posts newest-first.
6. `surfaces/mcp_server.py` → verify: tools callable; creating a post via MCP writes the same file format and shows up everywhere else.

Write tests alongside each step, not after.

---

## Part 8 — Success Criteria (the build is done when all hold)

- [ ] A post created through ANY surface (CLI, API, MCP) produces an identical `.md` file.
- [ ] Deleting `index.sqlite` and rebuilding loses no data.
- [ ] Pointing a generic Markdown tool (or a brand-new app) at `posts/` works with no migration.
- [ ] No business logic exists outside `core/`.
- [ ] No authorization logic exists in `core/` — it lives only in `surfaces/api.py`.
- [ ] Read endpoints are public; every write endpoint rejects requests without the valid token.
- [ ] An AI agent can list, create, publish, and search posts purely via MCP tools.
- [ ] The whole thing runs as one process with no build step.
- [ ] Total code is small and obvious. If a module feels clever, it's wrong.

---

## Part 9 — Explicit Non-Goals

Do NOT build (unless later asked): user accounts, passwords, login pages, sessions,
JWT/OAuth, a user table, comments, a WYSIWYG editor, themes/plugins, multi-user
support, a separate frontend SPA, a static-site build pipeline, or any database used
as the source of truth. (Write protection is a single shared token only — see Part 10.)

Keep these *external* to the app, never built in — they would couple the app to your
content and undermine Goal 1: comments (use a hosted service if ever wanted), analytics,
email newsletters. The app emits a feed; other tools consume it.

---

## Part 10 — Write Authorization

The threat model: anyone on the internet can reach the HTTP surface, so writes must
be guarded. There is exactly one author. The mechanism is therefore the simplest thing
that is still real — a single shared secret token. No accounts, no sessions, no hashing.

Rules:
- **Reads are public.** `list_posts`, `get_post`, `search`, and all web/HTML routes
  require no auth.
- **Writes require a token.** `create_post`, `update_post`, `delete_post`,
  `set_status`/`publish_post` require a valid bearer token on the HTTP surface.
- The token is read from an environment variable (e.g. `BLOG_WRITE_TOKEN`).
  Never hardcoded, never committed, never logged.
- Checked via `Authorization: Bearer <token>` (or `X-API-Key`), compared with
  `secrets.compare_digest` (constant-time — never `==`).
- **Auth lives ONLY in `surfaces/api.py`.** `core/` must remain completely
  auth-free, so a future replacement app inherits zero auth coupling. This protects Goal 1.

Surface-specific exposure:
- **CLI** — no auth. It runs on a machine the author already controls.
- **MCP server** — no auth *if it stays local* (gated by who can reach the process).
  If the MCP server is ever exposed remotely, it must enforce the same `BLOG_WRITE_TOKEN`
  check on its write tools. Note this as a TODO comment in `mcp_server.py` rather than
  building remote auth now.
- **HTTP API** — the token check described above.

Deployment note (state in the README, don't build): the API must run behind HTTPS in
production so the bearer token is never sent in cleartext.
