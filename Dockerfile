FROM python:3.10

COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /uvx /bin/

WORKDIR /app

# Install dependencies first for caching
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

COPY run.py app/ tests/ ./

ENV PATH="/app/.venv/bin:$PATH"
