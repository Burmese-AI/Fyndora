# Fyndora

A modular finance and compliance platform built to support decentralized fundraising networks.

## Quick Start

### Development Setup

1. **Configure environment variables:**

   ```bash
   # Copy example environment file
   cp .env.example .env

   # Generate a secure Django secret key
   ./scripts/docker-dev.sh generate-secret

   # Edit your environment settings
   vi .env  # or use any editor you prefer
   ```

2. **Start the development environment:**

   ```bash
   ./scripts/docker-dev.sh up
   ```

3. **Access your services:**

   * Web app: `http://localhost:8000`
   * PostgreSQL: `localhost:5432`
   * Redis: `localhost:6379`

### Production Setup

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Development Commands

```bash
# Start dev environment
./scripts/docker-dev.sh up

# Stop services
./scripts/docker-dev.sh down

# Tail logs
./scripts/docker-dev.sh logs

# Run DB migrations
./scripts/docker-dev.sh migrate

# Create new migrations
./scripts/docker-dev.sh makemigrations

# Access Django shell
./scripts/docker-dev.sh shell

# Collect static files
./scripts/docker-dev.sh collectstatic
```

## Project Structure

```bash
fyndora/
├── fyndora/                     # Django project settings
├── scripts/                     # Developer utilities
├── Dockerfile                   # Production Docker image
├── docker-compose.yml           # Base Docker Compose config
├── docker-compose.override.yml # Dev overrides (auto-loaded)
├── docker-compose.prod.yml     # Production config
├── pyproject.toml               # Project metadata and UV config
├── uv.lock                      # Locked dependency versions
└── README.md                    # You're here
```

## Technology Stack

* **Python**: 3.13
* **Django**: 5.2+
* **Database**: PostgreSQL 15
* **Cache & Queue**: Redis 7 + Celery
* **Package Manager**: [UV](https://github.com/astral-sh/uv)
* **Containerization**: Docker & Docker Compose
* **Frontend**: HTMX + TailwindCSS (with daisyUI)

## Docker Configuration

### Development Mode

* Uses `docker-compose.override.yml` (auto-applied)
* Mounts local source code for hot reloading
* Exposes all ports
* Runs Django’s development server

### Production Mode

* Uses `docker-compose.prod.yml`
* Secure & performance-optimized
* Only web ports are exposed
* Runs via Gunicorn with production settings

## Environment Variables

Managed using `.env` files:

### Required

* `POSTGRES_PASSWORD` – Database password (**required**)
* `DJANGO_SECRET_KEY` – Django secret key (**required**)

### Optional (Defaults in `.env.example`)

* `POSTGRES_DB=fyndora`
* `POSTGRES_USER=fyndora`
* `POSTGRES_HOST=db`
* `POSTGRES_PORT=5432`
* `DEBUG=1` – Use `0` in production
* `DJANGO_ALLOWED_HOSTS` – Comma-separated list of allowed hosts

### File Naming Conventions

* `.env.example` – Template (committed)
* `.env` – Local (ignored)
* `.env.local` – Local overrides (ignored)
* `.env.production` – Prod configuration (ignored)

## Security Notes

* Based on Ubuntu 25.10 with zero known CVEs
* Non-root container execution
* Split development and production configs
* Use strong, rotated secrets for production
* Regularly audit and patch base images

### Local Development

```bash
# Install dependencies
uv sync

# Add a production dependency
uv add package-name

# Add a development-only dependency
uv add --group dev package-name
```

### In Docker

* Dependencies are automatically installed by UV inside Docker
* `uv.lock` ensures consistent environments

## Deployment Guide

1. **Set environment variables**

2. **Run production containers:**

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Apply database migrations:**

   ```bash
   docker compose exec web python manage.py migrate
   ```

4. **Collect static assets:**

   ```bash
   docker compose exec web python manage.py collectstatic --noinput
   ```
