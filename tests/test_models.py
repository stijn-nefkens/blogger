"""Tests for core.models (de)serialization, incl. the YAML 1.2 guarantee."""

from datetime import date

from core import models

_HAND_AUTHORED = """\
---
title: Hand Authored
slug: hand-authored
description: A post a human typed by hand.
date: 2026-06-06
updated: 2026-06-06
status: published
tags: [no, yes, on, meta]
---

Body content.
"""


def test_yaml12_keeps_ambiguous_tags_as_strings():
    """Under YAML 1.1, unquoted `no`/`yes`/`on` parse as booleans; YAML 1.2
    (py-yaml12) keeps them as strings, which is what a human meant."""
    post = models.parse(_HAND_AUTHORED)
    assert post.tags == ["no", "yes", "on", "meta"]


def test_dates_parse_to_date_objects():
    post = models.parse(_HAND_AUTHORED)
    assert post.date == date(2026, 6, 6)
    assert isinstance(post.date, date)


def test_dump_then_parse_round_trips():
    post = models.Post(
        title="Title",
        slug="title",
        description="desc",
        date=date(2026, 6, 6),
        updated=date(2026, 6, 6),
        status="draft",
        tags=["no", "meta"],  # includes an ambiguous tag
        body="Some **markdown**.",
    )
    assert models.parse(models.dump(post)) == post


def test_dump_quotes_ambiguous_scalars():
    """Files we write stay portable: ambiguous tags are quoted so even a YAML 1.1
    reader gets strings, not booleans."""
    post = models.Post(
        title="T", slug="t", description="d",
        date=date(2026, 6, 6), updated=date(2026, 6, 6),
        status="draft", tags=["no"], body="b",
    )
    assert '"no"' in models.dump(post)
