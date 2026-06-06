"""Compose the web + JSON API surfaces into one FastAPI process.

Live, rendered on request from the same process as core — no build step. Run
with: uvicorn app:app
"""

from fastapi import FastAPI

from surfaces.api import router as api_router
from surfaces.web import router as web_router

app = FastAPI(title="Blog")
app.include_router(api_router)
app.include_router(web_router)
