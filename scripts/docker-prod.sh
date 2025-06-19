#!/bin/bash

# Enable BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

case "$1" in
"deploy")
    log_info "Starting production deployment..."

    # Pre-flight checks
    if [ ! -f .env.prod ]; then
        log_error "No .env.prod file found. Please create production environment file."
        exit 1
    fi

    log_info "Building production images with optimizations..."

    # Build with cache optimization
    docker build \
        --target production \
        --cache-from fyndora:latest \
        --cache-from fyndora:python-deps \
        --cache-from fyndora:node-build \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        -t fyndora:latest \
        -t fyndora:$(date +%Y%m%d-%H%M%S) \
        .

    if [ $? -ne 0 ]; then
        log_error "Build failed!"
        exit 1
    fi

    log_success "Build completed successfully"

    # Deploy with production compose file
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

    # Wait for health checks
    log_info "Waiting for health checks to pass..."
    sleep 10

    # Check if services are healthy
    if docker compose -f docker-compose.yml -f docker-compose.prod.yml ps | grep -q "unhealthy"; then
        log_error "Some services are unhealthy!"
        docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
        exit 1
    fi

    log_success "Production deployment completed successfully!"
    ;;

"build-optimized")
    log_info "Building with maximum optimization..."

    # Build dependency layers first for better caching
    log_info "Building Python dependencies layer..."
    docker build --target python-deps -t fyndora:python-deps .

    log_info "Building Node.js build layer..."
    docker build --target node-build -t fyndora:node-build .

    log_info "Building final production image..."
    docker build \
        --target production \
        --cache-from fyndora:python-deps \
        --cache-from fyndora:node-build \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        -t fyndora:latest \
        .

    log_success "Optimized build completed!"
    ;;

"rollback")
    if [ -z "$2" ]; then
        log_error "Please specify image tag to rollback to"
        echo "Available tags:"
        docker images fyndora --format "table {{.Tag}}\t{{.CreatedAt}}"
        exit 1
    fi

    log_info "Rolling back to fyndora:$2..."
    docker tag fyndora:$2 fyndora:latest
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d web

    log_success "Rollback completed!"
    ;;

"health-check")
    log_info "Checking service health..."

    # Check web service
    if curl -f http://localhost:8000/health/ >/dev/null 2>&1; then
        log_success "Web service is healthy"
    else
        log_error "Web service is not responding"
    fi

    # Check database
    if docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db pg_isready -U fyndora >/dev/null 2>&1; then
        log_success "Database is healthy"
    else
        log_error "Database is not responding"
    fi

    # Check Redis
    if docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T redis redis-cli ping >/dev/null 2>&1; then
        log_success "Redis is healthy"
    else
        log_error "Redis is not responding"
    fi
    ;;

"logs")
    docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f "${2:-web}"
    ;;

"stop")
    log_info "Stopping production services..."
    docker compose -f docker-compose.yml -f docker-compose.prod.yml stop
    log_success "Production services stopped"
    ;;

"down")
    log_warning "This will stop and remove all production containers!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose -f docker-compose.yml -f docker-compose.prod.yml down
        log_success "Production environment stopped and removed"
    fi
    ;;

"backup-db")
    log_info "Creating database backup..."
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="backup_${timestamp}.sql"

    docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
        pg_dump -U fyndora fyndora >"backups/${backup_file}"

    if [ $? -eq 0 ]; then
        log_success "Database backup saved to backups/${backup_file}"
    else
        log_error "Database backup failed!"
    fi
    ;;

"restore-db")
    if [ -z "$2" ]; then
        log_error "Please specify backup file to restore"
        echo "Available backups:"
        ls -la backups/
        exit 1
    fi

    log_warning "This will restore database from $2 and overwrite current data!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
            psql -U fyndora -d fyndora <"backups/$2"
        log_success "Database restored from $2"
    fi
    ;;

"monitor")
    log_info "Starting resource monitoring..."
    watch -n 2 'docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"'
    ;;

"cleanup")
    log_info "Cleaning up unused Docker resources..."

    # Remove old images (keep last 5)
    old_images=$(docker images fyndora --format "{{.Repository}}:{{.Tag}}" | grep -E '^fyndora:[0-9]{8}-[0-9]{6}$' | tail -n +6)
    if [ ! -z "$old_images" ]; then
        echo "$old_images" | xargs docker rmi
        log_success "Removed old images"
    fi

    # Clean up build cache
    docker builder prune -f

    log_success "Cleanup completed!"
    ;;

*)
    echo "Usage: $0 {command}"
    echo ""
    echo "🚀 Deployment Commands:"
    echo "  deploy          - Full production deployment with health checks"
    echo "  build-optimized - Build with maximum optimization"
    echo "  rollback <tag>  - Rollback to specific image tag"
    echo ""
    echo "🔧 Management Commands:"
    echo "  stop            - Stop production services"
    echo "  down            - Stop and remove production containers"
    echo "  logs [service]  - Show logs"
    echo "  health-check    - Check service health"
    echo "  monitor         - Monitor resource usage"
    echo ""
    echo "💾 Database Commands:"
    echo "  backup-db       - Create database backup"
    echo "  restore-db <file> - Restore database from backup"
    echo ""
    echo "🧹 Maintenance Commands:"
    echo "  cleanup         - Clean up old images and build cache"
    exit 1
    ;;
esac
