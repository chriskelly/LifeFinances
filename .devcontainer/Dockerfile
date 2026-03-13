FROM python:3.10

COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /uvx /bin/

ENV NVM_DIR="/root/.nvm"

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash \
    && \. "$NVM_DIR/nvm.sh" \
    && nvm install 24 \
    && nvm alias default 24 \
    && NODE_VERSION=$(node --version) \
    && ln -s "$NVM_DIR/versions/node/${NODE_VERSION}/bin/node" /usr/local/bin/node \
    && ln -s "$NVM_DIR/versions/node/${NODE_VERSION}/bin/npm" /usr/local/bin/npm \
    && ln -s "$NVM_DIR/versions/node/${NODE_VERSION}/bin/npx" /usr/local/bin/npx \
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
