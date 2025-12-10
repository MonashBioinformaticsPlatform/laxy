# Integration Tests

This directory contains **Integration Tests** and **API Tests** for the Laxy platform.

## 🧪 Test Types

### **API Integration Tests**
- Test REST API endpoints end-to-end
- Verify complete request/response workflows
- Test authentication and authorization

### **System Integration Tests** 
- Test integration between components (Django + Celery + RabbitMQ + PostgreSQL)
- Verify background task processing
- Test external service integrations

### **End-to-End Tests**
- Test complete user workflows
- Verify data flows through the entire system
- Test real HTTP requests against running services

## 📁 Test Files

| File | Purpose |
|------|---------|
| `test_jwt_auth.py` | JWT authentication workflows |
| `test_file_operations.py` | File upload, download, metadata operations |
| `test_celery_tasks.py` | Background task processing with Celery |
| `test_external_integrations.py` | External service integrations (Degust, WebDAV, social auth) |

## 🚀 Running Tests

These tests require a **running Laxy environment**:

```bash
# Start the development environment
just dev-up
# Or: export LAXY_ENV=local-dev && docker compose -f docker-compose.yml -f docker-compose.local-dev.yml up -d

# Run all integration tests
just test-integration

# Run individual test suites
just test-jwt          # JWT authentication
just test-files        # File operations
just test-celery       # Background tasks
just test-external     # External integrations

# Or run directly with Python
python tests/integration/test_jwt_auth.py
python tests/integration/run_integration_tests.py

# Or run with pytest
python -m pytest tests/integration/
```

## 🔧 Configuration

Tests use environment variables:
- `API_BASE_URL` - Laxy API base URL (default: http://localhost:8001)
- Test credentials are defined in each test file

## 📊 Test Results

These tests were created to validate the major dependency upgrade:
- Python 3.6 → 3.12
- Django 2.2 → 5.x  
- All major Python dependencies

See `TESTING_RESULTS_SUMMARY.md` for detailed results.

## ⚖️ vs Unit Tests

**Unit Tests** (`laxy_backend/tests/`):
- Test individual functions/classes in isolation
- Use Django's TestCase with test database
- Fast execution, no external dependencies

**Integration Tests** (this directory):
- Test multiple components working together
- Use real services and databases
- Slower execution, require running environment
- Test complete user workflows 