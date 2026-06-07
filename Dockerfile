# syntax=docker/dockerfile:1

# ---- Base: Python + uv ------------------------------------------------------
FROM python:3.13-slim AS base

# Copy the uv binary from the official image (faster than pip-installing it)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# uv runtime settings:
#  - bytecode compile for faster cold starts
#  - copy link mode (safe inside containers)
#  - don't install dev dependencies in the production image
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

WORKDIR /app

# ---- Dependency layer (cached unless lockfile changes) ----------------------
# Copy only the dependency manifests first so this layer is reused across
# code-only changes, keeping rebuilds fast.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

# ---- Application layer ------------------------------------------------------
# Now copy the rest of the source and install the project itself.
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Put the project's virtualenv binaries on PATH so we don't need `uv run`.
ENV PATH="/app/.venv/bin:$PATH"

# The index cache lives here; this directory is mounted as a persistent volume
# in Coolify so the SQLite index survives redeploys (it's only a cache, but
# keeping it avoids a rebuild on every deploy).
ENV BLOG_INDEX_PATH=/data/index.sqlite
RUN mkdir -p /data

EXPOSE 8000

# Bind to 0.0.0.0 (not localhost) so the container accepts external traffic,
# on the port Coolify will route to.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
