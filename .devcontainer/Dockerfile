FROM python:3.10

COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /uvx /bin/

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install dependencies first for caching
COPY backend/pyproject.toml backend/uv.lock /workspace/backend/
RUN uv sync --locked --project /workspace/backend

COPY . /workspace

ENV PATH="/workspace/backend/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command
CMD ["/bin/bash"]
