FROM python:3.10

COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /uvx /bin/

WORKDIR /app

# Install dependencies first for caching
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked

COPY backend/pyrightconfig.json ./
COPY backend/run.py ./
COPY backend/app ./app
COPY backend/tests ./tests

ENV PATH="/app/.venv/bin:$PATH"
