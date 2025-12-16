# Laxy Development Commands
# Run `just` to see available commands

# Default recipe shows help
default:
    @just --list

# Start servers (optionally specify service name)
up service='':
    #!/usr/bin/env bash
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    if [ -z "{{service}}" ]; then
        echo "🚀 Starting Laxy development environment..."
        docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" up -d
        echo "✅ Services starting... Check logs with 'just logs'"
        echo "   Frontend: http://localhost:8002"
        echo "   Backend:  http://localhost:8001"
    else
        echo "🚀 Starting service: {{service}}..."
        docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" up -d {{service}}
    fi

# Stop servers (optionally specify service name)
down service='':
    #!/usr/bin/env bash
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    if [ -z "{{service}}" ]; then
        echo "🛑 Stopping Laxy development environment..."
        docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" down
    else
        echo "🛑 Stopping service: {{service}}..."
        docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" stop {{service}}
    fi

# Show container logs. Optionally pass a service name.
logs service='':
    #!/usr/bin/env bash
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    if [ -z "{{service}}" ]; then
        docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" logs --tail 50 -f
    else
        docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" logs --tail 50 -f {{service}}
    fi

# Build Docker images
build:
    #!/usr/bin/env bash
    echo "🔨 Building Docker images..."
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" build

# Run unit tests (fast, isolated)
test-unit:
    #!/usr/bin/env bash
    echo "🧪 Running unit tests..."
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" exec django python manage.py test --noinput

# Run integration tests (requires running environment)
test-integration:
    #!/usr/bin/env bash
    echo "🔗 Running integration tests..."
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" exec django python tests/integration/run_integration_tests.py

# Run individual integration test suite
test-jwt:
    #!/usr/bin/env bash
    echo "🔐 Testing JWT authentication..."
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" exec django python tests/integration/test_jwt_auth.py

test-files:
    #!/usr/bin/env bash
    echo "📁 Testing file operations..."
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" exec django python tests/integration/test_file_operations.py

test-external:
    #!/usr/bin/env bash
    echo "🔗 Testing external integrations..."
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" exec django python tests/integration/test_external_integrations.py

# Run all tests (unit + integration)
test-all: test-unit test-integration

# Alias for test-all
test: test-all

# Run database migrations
migrate:
    #!/usr/bin/env bash
    echo "🗃️  Running database migrations..."
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" exec django python manage.py migrate

# Create Django superuser
superuser:
    #!/usr/bin/env bash
    echo "👤 Creating Django superuser..."
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" exec django python manage.py createsuperuser

# 🔍 Code Quality Commands

# Setup local virtual environment with production dependencies
setup-venv:
    #!/usr/bin/env bash
    echo "📦 Setting up local virtual environment (production dependencies)..."
    if [ ! -d ".venv" ]; then
        uv venv
    fi
    source .venv/bin/activate && uv pip install -r requirements.txt
    echo "✅ Virtual environment ready!"

# Setup local virtual environment with development dependencies
setup-venv-dev:
    #!/usr/bin/env bash
    echo "📦 Setting up local virtual environment (development dependencies)..."
    if [ ! -d ".venv" ]; then
        uv venv
    fi
    source .venv/bin/activate && uv pip install -r requirements-dev.txt
    echo "✅ Virtual environment ready!"

# Run code linting
lint: setup-venv-dev
    @echo "🔍 Running linters..."
    @.venv/bin/ruff check --select=E9,F63,F7,F82 laxy_backend/
    @.venv/bin/ruff check --select=E9,F63,F7,F82 laxy_pipeline_apps/

# Format code with ruff
format: setup-venv-dev
    @echo "🎨 Formatting code..."
    @.venv/bin/ruff format laxy_backend/
    @.venv/bin/ruff format laxy_pipeline_apps/

# Run type checking with mypy
typecheck: setup-venv-dev
    @echo "🔬 Running type checks..."
    @.venv/bin/mypy laxy_backend/ --ignore-missing-imports

# Check system requirements
check:
    #!/usr/bin/env bash
    echo "🔍 Checking system requirements..."
    
    # Check Docker
    if command -v docker >/dev/null 2>&1; then
        echo "✅ Docker: $(docker --version)"
    else
        echo "❌ Docker not found"
        exit 1
    fi
    
    # Check Docker Compose
    if docker compose version >/dev/null 2>&1; then
        echo "✅ Docker Compose: $(docker compose version)"
    else
        echo "❌ Docker Compose not found"
        exit 1
    fi
    
    # Check Python
    if command -v python3 >/dev/null 2>&1; then
        echo "✅ Python: $(python3 --version)"
    else
        echo "❌ Python 3 not found"
        exit 1
    fi
    
    # Check uv
    if command -v uv >/dev/null 2>&1; then
        echo "✅ uv: $(uv --version)"
    else
        echo "❌ uv not found (install from https://docs.astral.sh/uv/getting-started/installation/)"
        exit 1
    fi
    
    echo "🎉 All requirements satisfied!"

# Show service status
status:
    #!/usr/bin/env bash
    echo "📊 Service Status:"
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" ps

# Open useful URLs
open:
    #!/usr/bin/env bash
    echo "🌐 Opening Laxy URLs..."
    if command -v open >/dev/null 2>&1; then
        # macOS
        open http://localhost:8002  # Frontend
        open http://localhost:8001/admin  # Admin
    elif command -v xdg-open >/dev/null 2>&1; then
        # Linux
        xdg-open http://localhost:8002
        xdg-open http://localhost:8001/admin
    else
        echo "   Frontend: http://localhost:8002"
        echo "   Admin:    http://localhost:8001/admin"
        echo "   API:      http://localhost:8001/api/v1/"
        echo "   Swagger:  http://localhost:8001/swagger/v1/"
    fi

# Execute shell in Django container
django-shell:
    #!/usr/bin/env bash
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" exec django python manage.py shell

# Execute bash in Django container
bash:
    #!/usr/bin/env bash
    export LAXY_ENV=${LAXY_ENV:-local-dev}
    COMPOSE_FILE="docker-compose.${LAXY_ENV}.yml"
    docker compose -f docker-compose.yml -f "${COMPOSE_FILE}" exec django bash

# Full setup for new developers
setup:
    @echo "🚀 Setting up Laxy development environment..."
    just check
    just setup-venv-dev
    just build
    just up
    @echo "⏳ Waiting for services to start..."
    @sleep 10
    just status
    @echo "🎉 Setup complete! Run 'just open' to access the application"
    just open

# Complete test suite for CI/CD
ci: check test-all

restart: down up 