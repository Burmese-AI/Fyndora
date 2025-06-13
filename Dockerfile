# syntax=docker/dockerfile:1.9
FROM ubuntu:25.10 AS build

SHELL ["sh", "-exc"]
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies including Node.js
RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    build-essential \
    ca-certificates \
    curl \
    python3-setuptools \
    python3.13-dev \
    nodejs \
    npm
EOT

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set UV environment variables
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/bin/python3.13 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Copy dependency files and install Python deps
COPY pyproject.toml uv.lock /_lock/
RUN --mount=type=cache,target=/root/.cache \
    cd /_lock && \
    uv sync --locked --no-group dev --group prod --group test

# Copy full source for building Tailwind
WORKDIR /app
COPY . .

# Install Node.js deps and build Tailwind CSS
RUN <<EOT
npm install
npm run tailwind:build
EOT

# Production image
FROM ubuntu:25.10
SHELL ["sh", "-exc"]
ENV DEBIAN_FRONTEND=noninteractive

# Create non-root user
RUN <<EOT
groupadd -r fyndora
useradd -r -d /app -g fyndora -N fyndora
EOT

# Install Python runtime
RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    python3.13 \
    libpython3.13
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
EOT

# Set working directory
WORKDIR /app

# Copy built Python virtualenv
COPY --from=build --chown=fyndora:fyndora /app/.venv /app/.venv

# Copy application source (includes built CSS)
COPY --from=build --chown=fyndora:fyndora /app /app

# Update PATH for virtualenv
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER fyndora

# Run the application
CMD ["gunicorn", "fyndora.wsgi:application", "--bind", "0.0.0.0:8000"]
