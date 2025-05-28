# syntax=docker/dockerfile:1.9
FROM ubuntu:25.10 AS build

SHELL ["sh", "-exc"]

# Ensure apt-get doesn't open a menu
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN <<EOT
apt-get update -qy
apt-get install -qyy \
    -o APT::Install-Recommends=false \
    -o APT::Install-Suggests=false \
    build-essential \
    ca-certificates \
    python3-setuptools \
    python3.13-dev
EOT

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set UV environment variables
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/bin/python3.13 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Copy dependency files to a temporary location
COPY pyproject.toml uv.lock /_lock/

# Synchronize dependencies
RUN --mount=type=cache,target=/root/.cache \
    cd /_lock && \
    uv sync \
        --locked \
        --no-group dev \
        --group prod

# Production image
FROM ubuntu:25.10
SHELL ["sh", "-exc"]

# Create non-root user
RUN <<EOT
groupadd -r fyndora
useradd -r -d /app -g fyndora -N fyndora
EOT

# Install runtime dependencies
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

# Copy the virtual environment from build stage
COPY --from=build --chown=fyndora:fyndora /app /app

# Copy the Django project files
COPY --chown=fyndora:fyndora . .

# Make sure we use the virtualenv python/gunicorn by default
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER fyndora

# Run the application
CMD ["gunicorn", "fyndora.wsgi:application", "--bind", "0.0.0.0:8000"] 