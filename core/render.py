"""Markdown -> HTML rendering.

The body passed in here is already frontmatter-free: core.models.parse splits
the YAML frontmatter off into Post fields and leaves Post.body as plain Markdown.
So rendering a post means rendering its body, and the frontmatter never appears
in the output.

Uses markdown-it-py with the default CommonMark preset. Raw HTML in the source
is escaped (html disabled) — a safe, boring default.
"""

from __future__ import annotations

from markdown_it import MarkdownIt

from core.models import Post

_md = MarkdownIt()


def render(text: str) -> str:
    """Render plain Markdown text to an HTML fragment."""
    return _md.render(text)


def render_post(post: Post) -> str:
    """Render a post's body to HTML. Frontmatter is excluded by construction."""
    return render(post.body)


