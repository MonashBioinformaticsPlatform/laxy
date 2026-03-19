# Integration Tests

This directory contains **Integration Tests** and **API Tests** for the Laxy platform.

## Test Files

| File | Purpose |
|------|---------|
| `test_jwt_auth.py` | JWT authentication workflows |
| `test_file_operations.py` | File upload, download, metadata operations |
| `test_external_integrations.py` | External service integrations (Degust, WebDAV, social auth) |

## 🚀 Running Tests

These tests require a **running Laxy environment** - the are run inside the container environment via docker compose:

```bash
# Start the development environment
cd ../..
export LAXY_ENV=local-dev
just up

# Or: export LAXY_ENV=local-dev && docker compose -f docker-compose.yml -f docker-compose.local-dev.yml up -d

# Run all integration tests
just test-integration

# Run individual test suites
just test-jwt          # JWT authentication
just test-files        # File operations
just test-external     # External integrations
```

Note: integration tests are guarded by the root pytest configuration and require `--integration` to be set.
The `just test-integration` and `just test-{jwt,files,external}` recipes already pass this flag.

## Configuration

Tests use environment variables:
- `LAXY_API_BASE_URL` - Laxy API base URL (default: http://localhost:8001)
- Test credentials are defined in each test file
