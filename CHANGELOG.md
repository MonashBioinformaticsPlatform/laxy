# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Integration test suite in `tests/integration/` for JWT auth, file operations, Celery tasks, and external integrations
- `justfile` for common development commands (`just dev-up`, `just test`, etc.)
- PostgreSQL upgrade documentation in `POSTGRES_UPGRADE_PLAN.md`
- OpenAPI documentation via drf-spectacular at `/api/v1/schema/`, `/api/v1/schema/swagger-ui/`, `/api/v1/schema/redoc/`
- `--skip-alignment` option in nf-core-rnaseq v3.18.0 pipeline UI

### Fixed
- Added `setuptools` to requirements for Python 3.12 compatibility (`pkg_resources` needed by `coreapi`)
- Nextcloud/ownCloud shared folder file downloads now use the new-style `/public.php/dav/files/{token}/` WebDAV endpoint (Nextcloud 29+), with automatic fallback to the legacy `/public.php/webdav/` endpoint for older instances

### Changed
- **Django 5.2.11** - Pinned to 5.2.11 release
- **Python 3.6 to 3.12** - Major Python version upgrade
- **Django 2.2 to 5.x** - Major Django version upgrade with all compatibility fixes
- **PostgreSQL 10 to 15** - Database upgrade (requires data migration, see `POSTGRES_UPGRADE_PLAN.md`)
- **Celery 5.5** - Task queue upgrade with updated configuration
- **Django REST Framework 3.16** - API framework upgrade
- **Authentication & Authorization Dependencies**:
    - `django-oauth-toolkit` updated to 3.x
    - `drf-social-oauth2` updated and verified
    - JWT authentication migrated from `rest_framework_jwt` to `djangorestframework-simplejwt`
- **WebDAV client** - Replaced `webdavclient3` with `webdav4` for Python 3.12 compatibility
- **Web scraping** - Replaced `robobrowser` with `robox` for Python 3.12 compatibility
- **OpenAPI schema** - Replaced `drf_openapi` with `drf-spectacular`
- **Code Modernization**:
    - Django storage API updated from `get_storage_class()` to `import_string()`
    - Django `force_text` replaced with `force_str` throughout codebase
    - Django `unique_together` replaced with `UniqueConstraint` in `FileLocation` model
    - `django-guardian` configuration updated to use `GUARDIAN_MONKEY_PATCH_USER = False`
    - AppConfig classes updated with explicit labels for Django 5.x strict validation
    - Signal handlers optimized to check `update_fields` to prevent unnecessary database writes
    - f-strings used instead of `%s` formatting in many files
- GitHub Actions workflows updated to use `actions/checkout@v4` and GHCR (`ghcr.io`)
- Development dependencies modernised (pytest 8.x, ruff, black 24.x)

### Fixed
- **API Compatibility**:
    - Refactored Views to use `get_request_serializer()` and `get_response_serializer()` methods instead of direct attribute access (DRF 3.x compatibility)
    - Fixed `permission_denied()` method signature compatibility in `JSONView`
    - Resolved `JobCreate` serialization issues by implementing distinct `JobSerializerResponse`
- **Authentication & CSRF**:
    - Applied `csrf_exempt` decorators to Login and Logout API views to support Django 5.x CSRF protection
    - configured `CSRF_TRUSTED_ORIGINS` to include port numbers (e.g., `localhost:8002`)
    - Fixed OAuth2 social login flows and token conversion endpoints
- **File Operations**:
    - File creation API auto-populates `name` and `path` from `location` URL
    - `JobFileView.put()` uses partial update for existing files
    - `FileCreate.post()` returns response with `id` field

### Removed
- `drf_openapi` package (replaced by drf-spectacular)
- `rest_framework_jwt` package (replaced by djangorestframework-simplejwt)
- `robobrowser` package (replaced by robox)
- `webdavclient3` package (replaced by webdav4)
- `django-allauth` package (was unused)
- `shell-notebook` (generally unused)

### Security
- Password hashers updated to prioritise Argon2
- JWT token handling modernised with djangorestframework-simplejwt
- CORS and CSRF configurations tightened to require proper URL schemes

## [Previous Versions]

See git history for changes prior to the major dependency upgrade.