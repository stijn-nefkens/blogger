"""Compose the web + JSON API surfaces into one FastAPI process.

Live, rendered on request from the same process as core — no build step. Run
with: uvicorn app:app

On startup we rebuild the disposable search index if it's missing, so a fresh
container (empty /data, no persisted volume) serves a populated blog from the
committed posts/ files rather than an empty search.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from core import index
from surfaces.api import router as api_router
from surfaces.web import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    index.rebuild_if_missing()
    yield


app = FastAPI(title="Blog", lifespan=lifespan)
app.include_router(api_router)
app.include_router(web_router)
