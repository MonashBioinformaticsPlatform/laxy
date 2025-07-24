# Laxy Dependency Upgrade Plan

This document outlines the plan to upgrade Laxy from Python 3.6 to Python 3.12 and update all major dependencies including Django, Django REST Framework, Celery, and authentication packages. This is a major undertaking that will require significant code changes and testing.

## Reference Documentation and Changelogs

### Core Dependencies
- **Python 3.12**
  - [What's New in Python 3.12](https://docs.python.org/3/whatsnew/3.12.html)
  - [Python 3.12 Documentation](https://docs.python.org/3.12/)

- **Django 5.1**
  - [Django 5.1 Release Notes](https://docs.djangoproject.com/en/5.1/releases/5.1/)
  - [Django Documentation](https://docs.djangoproject.com/en/5.1/)
  - [Django 5.0 Release Notes](https://docs.djangoproject.com/en/5.0/releases/5.0/)

- **Django REST Framework 3.16**
  - [DRF 3.16 Release Notes](https://www.django-rest-framework.org/community/3.16-announcement/)
  - [DRF Documentation](https://www.django-rest-framework.org/)
  - [PyPI Package](https://pypi.org/project/djangorestframework/)

- **Celery 5.5**
  - [Celery 5.5 Changelog](https://docs.celeryq.dev/en/latest/changelog.html)
  - [Celery Documentation](https://docs.celeryq.dev/en/latest/)

### Authentication Packages
- **django-allauth 65.x**
  - [django-allauth Release Notes](https://docs.allauth.org/en/dev/release-notes/recent.html)
  - [django-allauth Changelog (GitHub)](https://github.com/pennersr/django-allauth/blob/main/ChangeLog.rst)
  - [django-allauth Documentation](https://docs.allauth.org/)

- **django-oauth-toolkit 3.x**
  - [GitHub Repository](https://github.com/jazzband/django-oauth-toolkit)
  - Documentation shows support for Django 4.2, 5.0, and 5.1

- **drf-social-oauth2**
  - [GitHub Repository](https://github.com/wagnerdelima/drf-social-oauth2)
  - Uses `python-social-auth` (superseded by `social-auth-app-django`)

## Dependency Upgrade Plan

### Phase 1: Environment and Infrastructure
1. **Python Version Upgrade**
   - Update `docker/laxy/Dockerfile` from Python 3.6 to Python 3.12
   - Update CI/CD pipelines to use Python 3.12
   - Update development environment setup documentation

2. **Compatibility Assessment**
   - Review all dependencies for Python 3.12 compatibility
   - Identify deprecated Python features used in codebase
   - Update syntax and imports for Python 3.12

### Phase 2: Core Framework Updates
1. **Django Upgrade (2.2.28 → 5.1)**
   - Major version jump requiring careful migration
   - Review deprecated features and breaking changes
   - Update URL patterns, middleware, and settings
   - Database migration review and testing

2. **Django REST Framework Upgrade (3.x → 3.16)**
   - Remove `drf_openapi` dependency (replaced by built-in OpenAPI support)
   - Update serializers and viewsets for new DRF features
   - Review pagination, filtering, and authentication changes
   - Update API documentation generation

3. **Celery Upgrade (5.x → 5.5)**
   - Review task definitions and decorators
   - Update broker configuration
   - Test distributed task execution
   - Update monitoring and logging

### Phase 3: Authentication System Overhaul
1. **Authentication Package Updates**
   - Update `django-allauth` to latest version (65.x)
   - Evaluate `rest-social-auth` vs `drf-social-oauth2` 
   - Update `django-oauth-toolkit` to 3.x
   - Consider migration to `social-auth-app-django`

2. **Remove drf_openapi**
   - Replace with Django REST Framework's built-in OpenAPI support
   - Update `views.py` to use new OpenAPI schema generation
   - Remove custom OpenAPI configurations
   - Update API documentation

### Phase 4: Code Modernization
1. **Python Code Updates**
   - Update to f-strings where appropriate
   - Use new typing features (Python 3.9+)
   - Replace deprecated imports and functions
   - Update exception handling patterns

2. **Django Code Updates**
   - Update to new Django patterns and best practices
   - Review and update model definitions
   - Update admin configurations
   - Review security settings

## Upgrade Checklist

### [ ] Phase 1: Environment Setup
- [x] **Python Environment**
  - [x] Update `docker/laxy/Dockerfile` to use Python 3.12
  - [x] Fix pip version compatibility (remove hardcoded pip==21.3.1, use latest)
  - [x] Fix django-environ compatibility (update to 0.12.0, fix PrefixedEnv class)
  - [x] Fix Django 5.x app label validation (add valid labels to AppConfig classes)
  - [x] Fix django-guardian deprecated setting (GUARDIAN_MONKEY_PATCH_USER)
  - [x] Fix Django storage API compatibility (replace get_storage_class with import_string)
  - [x] Fix missing WebDAV dependencies (replace webdavclient3 with webdav4)
  - [x] Fix Django force_text deprecation (replace with force_str)
  - [ ] Update `requirements.txt` with Python 3.12 compatible versions
  - [ ] Update CI/CD configurations
  - [ ] Test Docker build process
  - [ ] Update development setup documentation

- [ ] **Compatibility Review**
  - [ ] Audit all dependencies for Python 3.12 support
  - [ ] Identify deprecated Python 3.6 features in use
  - [ ] Create compatibility matrix for all packages
  - [ ] Test basic application startup

### [ ] Phase 2: Core Dependencies
- [ ] **Django 5.1 Upgrade**
  - [ ] Review Django 3.x → 4.x breaking changes
  - [ ] Review Django 4.x → 5.x breaking changes
  - [ ] Update `MIDDLEWARE` settings
  - [ ] Update URL patterns (`path()` vs `url()`)
  - [ ] Update model field definitions
  - [ ] Update admin configurations
  - [ ] Run Django system checks
  - [ ] Create and test database migrations
  - [ ] Update security settings (`ALLOWED_HOSTS`, CSRF, etc.)
  - [ ] Test user authentication flows

- [ ] **Django REST Framework 3.16 Upgrade**
  - [ ] Update serializer imports and definitions
  - [ ] Review viewset and permission changes
  - [ ] Update pagination configurations
  - [ ] Test API endpoint functionality
  - [ ] Update filtering and search implementations
  - [ ] Review throttling configurations
  - [ ] Test API authentication

- [ ] **Celery 5.5 Upgrade**
  - [ ] Update Celery configuration
  - [ ] Review task decorators and definitions
  - [ ] Update broker settings (Redis/RabbitMQ)
  - [ ] Test task execution and monitoring
  - [ ] Update worker configuration
  - [ ] Test distributed task processing
  - [ ] Update beat scheduler configuration

### [ ] Phase 3: Authentication System
- [ ] **Remove drf_openapi**
  - [ ] Remove `drf_openapi` from `requirements.txt`
  - [ ] Remove `drf_openapi` imports from `views.py`
  - [ ] Remove custom OpenAPI configurations
  - [ ] Test application without drf_openapi

- [ ] **django-allauth Upgrade**
  - [ ] Update to django-allauth 65.x
  - [ ] Review breaking changes in changelogs
  - [ ] Update authentication settings
  - [ ] Test social authentication flows
  - [ ] Update templates if needed
  - [ ] Test email verification flows
  - [ ] Test password reset functionality

- [ ] **OAuth System Update**
  - [ ] Evaluate keeping `django-rest-framework-social-oauth2` vs migration
  - [ ] Update `django-oauth-toolkit` to 3.x
  - [ ] Test OAuth2 token generation and validation
  - [ ] Update API authentication middleware
  - [ ] Test social media login integrations

- [ ] **Django REST Framework OpenAPI Integration**
  - [ ] Configure DRF's built-in OpenAPI schema generation
  - [ ] Update `views.py` with proper schema decorators
  - [ ] Configure schema view and URL patterns
  - [ ] Test OpenAPI documentation generation
  - [ ] Update frontend API documentation consumption
  - [ ] Compare feature parity with previous drf_openapi setup

### [ ] Phase 4: Code Modernization
- [ ] **Python Code Updates**
  - [ ] Replace `%` string formatting with f-strings
  - [ ] Update import statements for moved modules
  - [ ] Add type hints using modern Python typing
  - [ ] Update exception handling patterns
  - [ ] Replace deprecated standard library functions
  - [ ] Update async/await patterns if used

- [ ] **Django Code Updates**
  - [ ] Update model `Meta` configurations
  - [ ] Review and update signal handlers
  - [ ] Update middleware implementations
  - [ ] Review custom management commands
  - [ ] Update template tags and filters
  - [ ] Review custom form implementations

### [ ] Phase 5: Testing and Validation
- [ ] **Unit Tests**
  - [ ] Update test requirements and configurations
  - [ ] Fix failing tests due to API changes
  - [ ] Add tests for new functionality
  - [ ] Test coverage analysis and improvement
  - [ ] Performance regression testing

- [ ] **Integration Tests**
  - [ ] Test complete authentication flows
  - [ ] Test API endpoints with new DRF version
  - [ ] Test Celery task execution
  - [ ] Test social authentication integrations
  - [ ] Test database operations and migrations

- [ ] **System Tests**
  - [ ] End-to-end user workflow testing
  - [ ] Load testing with new versions
  - [ ] Security testing and vulnerability assessment
  - [ ] Performance benchmarking
  - [ ] Cross-browser testing for frontend changes

### [ ] Phase 6: Documentation and Deployment
- [ ] **Documentation Updates**
  - [ ] Update installation instructions
  - [ ] Update API documentation
  - [ ] Update development setup guide
  - [ ] Update deployment documentation
  - [ ] Update troubleshooting guides

- [ ] **Deployment Preparation**
  - [ ] Update production Docker configurations
  - [ ] Plan database migration strategy
  - [ ] Prepare rollback procedures
  - [ ] Update monitoring and alerting
  - [ ] Schedule maintenance window

## Risk Assessment and Mitigation

### High-Risk Areas
1. **Authentication System**: Major changes to auth packages could break user login
2. **Database Migrations**: Django 2.2 → 5.1 may have complex migration requirements
3. **API Compatibility**: DRF changes might break frontend/client integrations
4. **Celery Tasks**: Changes in task execution could affect background processing

### Mitigation Strategies
1. **Comprehensive Testing**: Extensive testing at each phase before proceeding
2. **Staging Environment**: Full replica of production for validation
3. **Gradual Rollout**: Phase-by-phase deployment with ability to rollback
4. **Documentation**: Detailed upgrade notes and rollback procedures
5. **Backup Strategy**: Full system backup before beginning upgrade process

## Timeline Estimate

- **Phase 1 (Environment)**: 1-2 weeks
- **Phase 2 (Core Dependencies)**: 3-4 weeks  
- **Phase 3 (Authentication)**: 2-3 weeks
- **Phase 4 (Code Modernization)**: 2-3 weeks
- **Phase 5 (Testing)**: 2-3 weeks
- **Phase 6 (Documentation/Deployment)**: 1-2 weeks

**Total Estimated Time**: 11-17 weeks

## Immediate Fixes Applied

### Fixed: Docker Build Failure with Python 3.12
**Problem**: Build was failing with `AttributeError: module 'pkgutil' has no attribute 'ImpImporter'` because the Dockerfile was hardcoded to use pip 21.3.1, which is incompatible with Python 3.12.

**Solution**: Updated `docker/laxy/Dockerfile` to use the latest pip version instead of the hardcoded old version:
```diff
- pip3 install -U pip==21.3.1 && \
+ pip3 install -U pip && \
```

**Explanation**: Python 3.12 removed `pkgutil.ImpImporter` as part of the deprecation of the old import system. pip 21.3.1 still relied on this deprecated functionality, but newer pip versions (22.3+) are compatible with Python 3.12.

**Status**: ✅ FIXED - Docker build now progresses past pip installation.

### Current Issue: django-environ Compatibility
**Problem**: Build now fails with `AttributeError: 'PrefixedEnv' object has no attribute 'prefix'` during Django collectstatic, indicating compatibility issues between django-environ and newer Django versions.

**Status**: ✅ FIXED - Updated django-environ to 0.12.0 and fixed PrefixedEnv class compatibility.

**Solution Applied**:
1. Updated `django-environ==0.12.0` in requirements.txt
2. Fixed PrefixedEnv class in `laxy/default_settings.py` to properly call parent constructor and set prefix attribute
3. Fixed double-prefixing issue in env() function

### Current Issue: Django 5.x App Label Validation
**Problem**: Build fails with `ImproperlyConfigured: The app label 'nf-core-rnaseq' is not a valid Python identifier` because Django 5.x has stricter validation for app labels and doesn't allow hyphens.

**Status**: ✅ FIXED - Updated app labels in AppConfig classes and used explicit AppConfig references in INSTALLED_APPS.

**Solution Applied**:
1. Added `label` attributes to AppConfig classes with valid Python identifiers (underscores instead of hyphens)
2. Updated INSTALLED_APPS to reference AppConfig classes directly instead of module names

### Fixed: django-guardian Configuration
**Problem**: django-guardian was using deprecated `GUARDIAN_MONKEY_PATCH` setting.

**Status**: ✅ FIXED - Updated to `GUARDIAN_MONKEY_PATCH_USER = False`.

### Fixed: Django Storage API Compatibility
**Problem**: `get_storage_class()` function was removed in Django 5.1, causing import errors.

**Status**: ✅ FIXED - Replaced with `import_string()` from `django.utils.module_loading`.

**Solution Applied**:
1. Replaced `from django.core.files.storage import get_storage_class` with `from django.utils.module_loading import import_string`
2. Updated all `get_storage_class()` calls to use `import_string()` with proper None checking

### Fixed: Missing WebDAV Dependencies
**Problem**: Build failed with `ModuleNotFoundError: No module named 'webdav3'` because `webdavclient3==3.14.6` doesn't support Python 3.12.

**Status**: ✅ FIXED - Replaced with `webdav4` which supports Python 3.12.

**Solution Applied**:
1. Replaced `webdavclient3==3.14.6` with `webdav4>=0.10.0` in requirements.txt  
2. Replaced git+https://github.com/pansapiens/webdav-client-python.git with `webdav4` in requirements.txt
3. Updated import from `import webdav3.client` to `from webdav4.client import Client as WebDAVClient`
4. Updated API calls to match webdav4 syntax

### Fixed: Django force_text Deprecation
**Problem**: Build failed with `ImportError: cannot import name 'force_text' from 'django.utils.encoding'` because `force_text` was removed in Django 5.x.

**Status**: ✅ FIXED - Replaced with `force_str`.

**Solution Applied**:
1. Updated import from `from django.utils.encoding import force_text` to `from django.utils.encoding import force_str`
2. Replaced all `force_text()` calls with `force_str()`

### Fixed: Werkzeug Compatibility / RoboBrowser Replacement
**Problem**: Build fails with `ImportError: cannot import name 'cached_property' from 'werkzeug'` from the `robobrowser` package.

**Status**: ✅ FIXED - Replaced `robobrowser` with `robox`.

**Solution Applied**:
1. Replaced `robobrowser` with `robox` in requirements.txt and requirements-thawed.txt
2. Updated import from RoboBrowser to Robox in views.py (already completed)
3. Removed commented-out RoboBrowser code
4. Updated TODO comments to reference Robox instead of RoboBrowser

## Notes

- This upgrade involves multiple major version jumps and will require careful testing
- Consider setting up a dedicated upgrade environment for development and testing
- Regular backups and the ability to rollback at each phase are essential
- Some features may need to be temporarily disabled during the upgrade process
- Frontend changes may be required if API structures change significantly
- Refer and add to `FEATURES_TO_TEST.md` for features and systems that require additional testing after the updates (unit tests or manual testing)