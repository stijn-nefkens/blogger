"""The Post dataclass and (de)serialization to a Markdown file with YAML frontmatter.

This module knows the data *shape* and how it maps to/from file text. It does no
file I/O — that lives in store.py. The frontmatter is standard and tool-agnostic
so any Markdown-aware tool can read these files with zero knowledge of this app.

We parse and emit the frontmatter with a YAML 1.2 engine (py-yaml12) instead of
PyYAML's YAML 1.1, so hand-authored files don't hit 1.1 quirks — most notably an
unquoted tag like `no`/`yes`/`on` being read as a boolean.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import frontmatter
import yaml12
from frontmatter.default_handlers import YAMLHandler

# Frontmatter keys, in the order we write them (matches the spec's example).
_FIELDS = ["title", "slug", "description", "date", "updated", "status", "tags"]


class _Yaml12Handler(YAMLHandler):
    """Drive python-frontmatter's frontmatter splitting with a YAML 1.2 engine."""

    def load(self, fm: str, **kwargs: object):
        return yaml12.parse_yaml(fm)

    def export(self, metadata: dict, **kwargs: object) -> str:
        return yaml12.format_yaml(metadata).strip()


_HANDLER = _Yaml12Handler()


@dataclass
class Post:
    title: str
    slug: str
    description: str
    date: date
    updated: date
    status: str
    tags: list[str]
    body: str


def slugify(title: str) -> str:
    """Derive a URL-safe slug from a title: lowercase, alphanumerics, hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def parse(text: str) -> Post:
    """Parse Markdown-with-frontmatter text into a Post."""
    fm = frontmatter.loads(text, handler=_HANDLER)
    m = fm.metadata
    return Post(
        title=m["title"],
        slug=m["slug"],
        description=m["description"],
        date=_as_date(m["date"]),
        updated=_as_date(m["updated"]),
        status=m["status"],
        tags=list(m.get("tags") or []),
        body=fm.content,
    )


def dump(post: Post) -> str:
    """Serialize a Post to Markdown-with-frontmatter text."""
    meta = {f: getattr(post, f) for f in _FIELDS}
    # py-yaml12 serializes scalars, not date objects; emit dates as ISO strings.
    meta["date"] = post.date.isoformat()
    meta["updated"] = post.updated.isoformat()
    fm = frontmatter.Post(post.body, **meta)
    return frontmatter.dumps(fm, handler=_HANDLER)


def _as_date(value) -> date:
    """YAML 1.2 reads dates as strings; accept an existing date object too."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
