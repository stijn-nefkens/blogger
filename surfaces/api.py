"""HTTP JSON API — the canonical machine surface. A thin mirror of core ops.

This is the ONLY place authorization lives. Reads are public; writes require a
bearer token (or X-API-Key) compared in constant time against BLOG_WRITE_TOKEN.
Keeping auth here means core/ stays auth-free, so a future replacement app
inherits zero auth coupling (CLAUDE.md Part 10).

Deployment: run behind HTTPS in production so the bearer token is never sent in
cleartext.
"""

from __future__ import annotations

import dataclasses
import os
import secrets
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from core import store

router = APIRouter(prefix="/api")


# --- authorization -----------------------------------------------------------


def require_token(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None),
) -> None:
    """Reject the request unless it carries the valid write token."""
    expected = os.environ.get("BLOG_WRITE_TOKEN")
    if authorization and authorization.startswith("Bearer "):
        provided = authorization[len("Bearer ") :]
    else:
        provided = x_api_key
    if not expected or not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="missing or invalid write token")


# --- schemas -----------------------------------------------------------------


class PostOut(BaseModel):
    title: str
    slug: str
    description: str
    date: date
    updated: date
    status: str
    tags: list[str]
    body: str


class CreateIn(BaseModel):
    title: str
    description: str
    body: str
    tags: list[str] = []
    status: str = "draft"


class UpdateIn(BaseModel):
    title: str | None = None
    description: str | None = None
    body: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class StatusIn(BaseModel):
    status: str


# --- reads (public) ----------------------------------------------------------


@router.get("/posts", response_model=list[PostOut])
def list_posts(status: str | None = None, tag: str | None = None):
    return [_out(p) for p in store.list_posts(status=status, tag=tag)]


@router.get("/posts/{slug}", response_model=PostOut)
def get_post(slug: str):
    return _out(_get_or_404(slug))


@router.get("/search", response_model=list[PostOut])
def search(q: str):
    return [_out(p) for p in store.search(q)]


# --- writes (token required) -------------------------------------------------


@router.post("/posts", response_model=PostOut, status_code=201, dependencies=[Depends(require_token)])
def create_post(data: CreateIn):
    try:
        post = store.create_post(
            data.title, data.description, data.body, tags=data.tags, status=data.status
        )
    except ValueError as exc:  # duplicate slug
        raise HTTPException(status_code=409, detail=str(exc))
    return _out(post)


@router.patch("/posts/{slug}", response_model=PostOut, dependencies=[Depends(require_token)])
def update_post(slug: str, data: UpdateIn):
    _get_or_404(slug)
    fields = data.model_dump(exclude_unset=True, exclude_none=True)
    return _out(store.update_post(slug, **fields))


@router.post("/posts/{slug}/status", response_model=PostOut, dependencies=[Depends(require_token)])
def set_status(slug: str, data: StatusIn):
    _get_or_404(slug)
    return _out(store.set_status(slug, data.status))


@router.delete("/posts/{slug}", status_code=204, dependencies=[Depends(require_token)])
def delete_post(slug: str):
    _get_or_404(slug)
    store.delete_post(slug)


# --- helpers -----------------------------------------------------------------


def _out(post) -> PostOut:
    return PostOut(**dataclasses.asdict(post))


def _get_or_404(slug: str):
    post = store.get_post(slug)
    if post is None:
        raise HTTPException(status_code=404, detail="no such post")
    return post
