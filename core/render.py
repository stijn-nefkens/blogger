"""Markdown -> HTML rendering.

The body passed in here is already frontmatter-free: core.models.parse splits
the YAML frontmatter off into Post fields and leaves Post.body as plain Markdown.
So rendering a post means rendering its body, and the frontmatter never appears
in the output.

Uses markdown-it-py with the default CommonMark preset. Raw HTML in the source
is escaped (html disabled) — a safe, boring default. A standalone image (one
alone in its paragraph) is turned into a <figure> with its alt text as a
<figcaption>, so memes get a tidy caption.
"""

from __future__ import annotations

import re

from markdown_it import MarkdownIt

from core.models import Post

_md = MarkdownIt()

# A paragraph whose entire content is a single image -> promote it to a figure.
_LONE_IMAGE = re.compile(r'<p>(<img [^>]*?alt="([^"]*)"[^>]*?/?>)</p>')


def render(text: str) -> str:
    """Render plain Markdown text to an HTML fragment."""
    return _figures(_md.render(text))


def render_post(post: Post) -> str:
    """Render a post's body to HTML. Frontmatter is excluded by construction."""
    return render(post.body)


def _figures(html: str) -> str:
    def repl(match: re.Match) -> str:
        img, alt = match.group(1), match.group(2)
        caption = f"<figcaption>{alt}</figcaption>" if alt else ""
        return f"<figure>{img}{caption}</figure>"

    return _LONE_IMAGE.sub(repl, html)

