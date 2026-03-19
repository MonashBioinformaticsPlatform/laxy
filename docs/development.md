# Laxy Development Guide

This guide covers the development setup, workflows, and tools for the Laxy project.

## 🚀 Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- [Just](https://github.com/casey/just#installation) command runner (recommended)

### One-Command Setup
```bash
git clone --recurse-submodules https://github.com/MonashBioinformaticsPlatform/laxy.git
cd laxy

# Set this when developing locally
export LAXY_ENV=local-dev
just setup
```

This will:
1. Check system requirements
2. Build Docker images
3. Start all services
4. Show service status
5. Display access URLs

Setting `LAXY_ENV=local-dev` ensures the `justfile` uses settings appropriate for a local docker compose setup (running using `docker-compose.local-dev.yml`, among other things). I might be a good idea to add `export LAXY_ENV=local-dev` to your `~/.bashrc` or `~/.zshrc` so this is always set on your development machine.

## 🛠️ Development Commands

We use [Just](https://just.systems/) as our command runner (modern alternative to Make).

### Environment Management
```bash
# Set this when developing locally
export LAXY_ENV=local-dev

just up        # Start development environment
just down      # Stop development environment
just logs      # Show logs from all services
just status        # Show service status
just restart       # Rebuild and restart everything
```

### Testing
```bash
just test              # Fast unit tests only (alias for just test-unit)
just test-unit         # Fast unit tests only
just test-integration  # Integration tests (requires running environment)

# Individual integration test suites
just test-jwt          # JWT authentication tests
just test-files        # File operations tests
just test-external     # External integration tests
```

### Code Quality
```bash
just lint          # Run linters (flake8, black)
just format        # Auto-format code with black
just typecheck     # Run mypy type checking
```

### Utilities
```bash
just shell         # Django shell in container
just bash          # Bash shell in Django container
just logs django   # Show logs for specific service
just open          # Open browser to Laxy URLs
just migrate       # Run database migrations
just superuser     # Create Django superuser
```

### Development Setup
```bash
just install       # Install Python dependencies
just build         # Build Docker images
just clean         # Clean up Docker resources
just check         # Verify system requirements
```

## 🧪 Testing Strategy

### Test Types

| Type | Command | Speed | Dependencies |
|------|---------|-------|--------------|
| **Unit Tests** | `just test-unit` | Fast (seconds) | Django TestCase only |
| **Integration Tests** | `just test-integration` | Slower (minutes) | Running Laxy environment |

### Unit Tests
- Located in `laxy_backend/tests/`
- Test individual functions/classes in isolation
- Use Django's TestCase with test database
- Run with:

```bash
pytest -vvv --showlocals --tb=auto                 # runs unit tests by default
pytest -vvv --showlocals --tb=auto --integration   # include integration tests as well
```

### Integration Tests
- Located in `tests/integration/`
- Test complete workflows and component integration
- Require running Laxy development environment
- Test real HTTP requests and external services

### Test Workflow
```bash
# Start environment
just up

# Run tests
just test          # Unit tests only
just test-unit     # Unit tests only
just test-jwt      # Just JWT tests

# View test results
just logs      # Check for any issues
```

## 🐳 Docker Development

### Services
- **django**: Main Django backend
- **db**: PostgreSQL database
- **rabbitmq**: Message broker for Celery
- **queue-high/queue-low**: Celery workers
- **dev-frontend-server**: Vue.js development server
- **fake-cluster**: Simulated compute cluster

### Useful Docker Commands
```bash
# View all containers
just status

# Follow logs for specific service
just logs django
just logs dev-frontend-server

# Execute commands in containers
just shell                    # Django shell
just bash                     # Bash in Django container
docker compose exec db psql   # PostgreSQL shell
```

## 🔗 URLs and Access

- **Frontend**: http://localhost:8002
- **Backend API**: http://localhost:8001/api/v1/
- **Django Admin**: http://localhost:8001/admin
- **API Docs**: http://localhost:8001/swagger/v1/
- **RabbitMQ**: http://localhost:15672 (guest/guest)

## 🆚 Why Just Instead of Make?

| Feature | Make | Just |
|---------|------|------|
| **Syntax** | Arcane, whitespace-sensitive | Clean, modern |
| **Cross-platform** | GNU Make differences | Consistent everywhere |
| **String handling** | Painful escaping | Natural string literals |
| **Error messages** | Cryptic | Clear and helpful |
| **Documentation** | Minimal | Built-in help with comments |
| **Dependencies** | Complex | Simple and clear |

### Just Advantages
```bash
# Beautiful, self-documenting recipes
dev-up:
    #!/usr/bin/env bash
    echo "🚀 Starting Laxy development environment..."
    export LAXY_ENV=local-dev
    docker compose -f docker-compose.yml -f docker-compose.local-dev.yml up -d

# vs Make's cryptic syntax
dev-up:
	@echo "🚀 Starting Laxy development environment..."
	@export LAXY_ENV=local-dev && \
	docker compose -f docker-compose.yml -f docker-compose.local-dev.yml up -d
```

## 🚀 Development Workflows

### Daily Development
```bash
just up       # Start services
just test-unit    # Quick test
# ... make changes ...
just test-all     # Unit + integration before commit
just down     # Stop services
```

### Adding New Features
```bash
just up
just test-unit        # Ensure baseline works
# ... develop feature ...
just test-integration # Test integration
just lint            # Check code quality
```

### Debugging Issues
```bash
just status          # Check service health
just logs        # View all logs
just logs django     # Focus on specific service
just shell           # Interactive debugging
```

### CI/CD Pipeline
```bash
just ci              # Complete test suite for CI/CD
# Equivalent to: just check test-all
```

## 📚 Additional Resources

- [Just Manual](https://just.systems/man/en/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Laxy API Documentation](http://localhost:8001/swagger/v1/) 