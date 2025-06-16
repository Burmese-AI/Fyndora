#!/bin/bash

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

case "$1" in
"up")
    echo "Starting development environment..."

    # Check if .env file exists
    if [ ! -f .env ]; then
        echo "⚠️  No .env file found. Creating one from .env.example..."
        if [ -f .env.example ]; then
            cp .env.example .env
            echo "📝 Please edit .env file with your actual values before continuing."
            echo "💡 At minimum, set a secure POSTGRES_PASSWORD and DJANGO_SECRET_KEY"
            exit 1
        else
            echo "❌ No .env.example file found. Please create .env file manually."
            exit 1
        fi
    fi

    docker compose up -d --build

    echo "Waiting for database to be ready..."
    until docker compose exec db pg_isready -U fyndora -d fyndora; do
        echo "Waiting for PostgreSQL..."
        sleep 2
    done

    echo "Running migrations..."
    docker compose exec web uv run python manage.py migrate
    echo "Development environment ready at http://localhost:8000"
    ;;
"up-prod")
    echo "Starting production environment..."
    echo "Building production image with full optimizations..."
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

    echo "Waiting for services to be ready..."
    until docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py check --deploy; do
        echo "Waiting for application..."
        sleep 3
    done

    echo "Production environment ready at http://localhost:8000"
    ;;
"build-cache")
    echo "Pre-building dependency layers for faster subsequent builds..."
    docker build --target python-deps -t fyndora:python-deps .
    docker build --target node-build -t fyndora:node-build .
    echo "Cache layers built successfully"
    ;;
"build-prod")
    echo "Building production image..."
    docker build --target production -t fyndora:latest .
    echo "Production image built successfully"
    ;;
"down")
    echo "Stopping development environment..."
    docker compose down
    ;;
"down-prod")
    echo "Stopping production environment..."
    docker compose -f docker-compose.yml -f docker-compose.prod.yml down
    ;;
"logs")
    docker compose logs -f "${2:-web}"
    ;;
"logs-prod")
    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f "${2:-web}"
    ;;
"shell")
    docker compose exec web uv run python manage.py shell
    ;;
"bash")
    docker compose exec web bash
    ;;
"migrate")
    docker compose exec web uv run python manage.py migrate
    ;;
"makemigrations")
    docker compose exec web uv run python manage.py makemigrations
    ;;
"collectstatic")
    docker compose exec web uv run python manage.py collectstatic --noinput
    ;;
"createsuperuser")
    docker compose exec web uv run python manage.py createsuperuser
    ;;
"test")
    echo "Running tests..."
    docker compose exec web uv run python manage.py test
    ;;
"tailwind-watch")
    echo "Starting Tailwind CSS watcher..."
    npm run tailwind:watch
    ;;
"tailwind-build")
    echo "Building Tailwind CSS..."
    npm run tailwind:build
    ;;
"clean")
    echo "Cleaning up Docker resources..."
    docker compose down -v --remove-orphans
    docker system prune -f
    docker volume prune -f
    echo "Cleanup completed"
    ;;
"status")
    echo "Docker container status:"
    docker compose ps
    echo ""
    echo "Docker image sizes:"
    docker images | grep fyndora
    echo ""
    echo "Docker volumes:"
    docker volume ls | grep fyndora
    ;;
"generate-secret")
    echo "Generating Django secret key..."
    python3 -c "
import secrets
import string
chars = string.ascii_letters + string.digits + '-_!@#%^*()+=[]{}|;:,.<>?'
secret = ''.join(secrets.choice(chars) for _ in range(50))
print(secret)
"
    ;;
*)
    echo "Usage: $0 {command}"
    echo ""
    echo "Environment Commands:"
    echo "  up              - Start development environment (fast build)"
    echo "  up-prod         - Start production environment"
    echo "  down            - Stop development environment"
    echo "  down-prod       - Stop production environment"
    echo ""
    echo "Build Commands:"
    echo "  build-cache     - Pre-build dependency layers for faster builds"
    echo "  build-prod      - Build production image"
    echo ""
    echo "Django Commands:"
    echo "  shell           - Open Django shell"
    echo "  bash            - Open bash shell in container"
    echo "  migrate         - Run database migrations"
    echo "  makemigrations  - Create new migrations"
    echo "  collectstatic   - Collect static files"
    echo "  createsuperuser - Create Django superuser"
    echo "  test            - Run tests"
    echo ""
    echo "Frontend Commands:"
    echo "  tailwind-watch  - Start Tailwind CSS watcher"
    echo "  tailwind-build  - Build Tailwind CSS"
    echo ""
    echo "Utility Commands:"
    echo "  logs [service]  - Show logs (default: web)"
    echo "  logs-prod       - Show production logs"
    echo "  status          - Show container and image status"
    echo "  clean           - Clean up Docker resources"
    echo "  generate-secret - Generate Django secret key"
    exit 1
    ;;
esac
