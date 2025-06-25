FROM python:3.13-slim AS python-deps

# Install system dependencies needed for Python packages
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    build-essential \
    libpq-dev &&
    rm -rf /var/lib/apt/lists/*

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory first
WORKDIR /app

# Set UV environment variables
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Copy only dependency files first for better caching
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-group dev --group prod --group test

# Build stage for Node.js assets
FROM node:20-alpine AS node-build

WORKDIR /app

# Copy only package files first for better caching
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Copy source files needed for Tailwind build
COPY static/ static/
COPY templates/ templates/
COPY apps/ apps/

# Build Tailwind CSS
RUN npm run tailwind:build

# Final production image
FROM python:3.13-slim AS production

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    libpq5 &&
    rm -rf /var/lib/apt/lists/* &&
    apt-get clean

# Install UV for runtime (needed for proper venv activation)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user
RUN groupadd -r fyndora &&
    useradd -r -d /app -g fyndora -N fyndora

# Set working directory
WORKDIR /app

# Copy Python virtual environment from build stage
COPY --from=python-deps --chown=fyndora:fyndora /app/.venv /app/.venv

# Copy application source
COPY --chown=fyndora:fyndora . .

# Copy built CSS from node build stage
COPY --from=node-build --chown=fyndora:fyndora /app/static/css/output.css /app/static/css/output.css

# Set UV environment variables and update PATH for virtualenv
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER fyndora

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD uv run python manage.py check --deploy || exit 1

# Run the application
CMD ["uv", "run", "gunicorn", "fyndora.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
