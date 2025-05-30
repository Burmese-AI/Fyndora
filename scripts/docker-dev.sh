#!/bin/bash

# Development Docker management script

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
    docker compose exec web python manage.py migrate
    echo "Development environment ready at http://localhost:8000"
    ;;
"down")
    echo "Stopping development environment..."
    docker compose down
    ;;
"logs")
    docker compose logs -f "${2:-web}"
    ;;
"shell")
    docker compose exec web python manage.py shell
    ;;
"migrate")
    docker compose exec web python manage.py migrate
    ;;
"makemigrations")
    docker compose exec web python manage.py makemigrations
    ;;
"collectstatic")
    docker compose exec web python manage.py collectstatic --noinput
    ;;
"createsuperuser")
    docker compose exec web python manage.py createsuperuser
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
    echo "Usage: $0 {up|down|logs|shell|migrate|makemigrations|collectstatic|createsuperuser|generate-secret}"
    echo ""
    echo "Commands:"
    echo "  up              - Start development environment"
    echo "  down            - Stop development environment"
    echo "  logs [service]  - Show logs (default: web)"
    echo "  shell           - Open Django shell"
    echo "  migrate         - Run database migrations"
    echo "  makemigrations  - Create new migrations"
    echo "  collectstatic   - Collect static files"
    echo "  createsuperuser - Create Django superuser"
    echo "  generate-secret - Generate Django secret key"
    exit 1
    ;;
esac
