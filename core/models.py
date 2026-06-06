"""The Post dataclass and (de)serialization to a Markdown file with YAML frontmatter.

This module knows the data *shape* and how it maps to/from file text. It does no
file I/O — that lives in store.py. The frontmatter is standard and tool-agnostic
so any Markdown-aware tool can read these files with zero knowledge of this app.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

import frontmatter
import yaml

# Frontmatter keys, in the order we write them (matches the spec's example).
_FIELDS = ["title", "slug", "description", "date", "updated", "status", "tags"]


class _NoAliasDumper(yaml.SafeDumper):
    """Never emit YAML anchors/aliases. When `date` and `updated` are the same
    object, PyYAML would otherwise write `&id001`/`*id001` — valid, but ugly and
    surprising in a human-edited file. The frontmatter must stay plain."""

    def ignore_aliases(self, data) -> bool:
        return True


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
    fm = frontmatter.loads(text)
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
    fm = frontmatter.Post(post.body, **{f: getattr(post, f) for f in _FIELDS})
    return frontmatter.dumps(fm, Dumper=_NoAliasDumper, sort_keys=False)


def _as_date(value) -> date:
    """YAML usually parses dates already; accept ISO strings too."""
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
