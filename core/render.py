"""Markdown -> HTML rendering.

The body passed in here is already frontmatter-free: core.models.parse splits
the YAML frontmatter off into Post fields and leaves Post.body as plain Markdown.
So rendering a post means rendering its body, and the frontmatter never appears
in the output.
"""

from __future__ import annotations

import markdown

from core.models import Post


def render(text: str) -> str:
    """Render plain Markdown text to an HTML fragment."""
    return markdown.markdown(text)


def render_post(post: Post) -> str:
    """Render a post's body to HTML. Frontmatter is excluded by construction."""
    return render(post.body)
