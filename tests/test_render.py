"""Tests for core.render: Markdown converts to HTML, frontmatter never leaks."""

from core import render
from core.models import parse

_FILE = """\
---
title: My First Post
slug: my-first-post
description: A summary.
date: 2026-06-06
updated: 2026-06-06
status: published
tags: [meta]
---

# Hello

Some **bold** text and a [link](https://example.com).
"""


def test_renders_markdown_to_html():
    html = render.render("Some **bold** and *italic*.")
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_render_post_excludes_frontmatter():
    post = parse(_FILE)
    html = render.render_post(post)

    # The body rendered...
    assert "<h1>Hello</h1>" in html
    assert "<strong>bold</strong>" in html
    assert '<a href="https://example.com">link</a>' in html

    # ...but no frontmatter field or its delimiter leaked into the output.
    assert "---" not in html
    assert "slug" not in html
    assert "my-first-post" not in html
    assert "status" not in html
