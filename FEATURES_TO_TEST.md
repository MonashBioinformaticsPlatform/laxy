# Features to test

These are features we need to test after the major dependency updates.
The list may not be exhaustive, but includes features and systems we know we have modified, or are likely to be impacted.

Prefer writing unit / integration tests where practical. Otherwise, manual testing is required.

## ✅ **VERIFIED WORKING** - Core System Functionality

- ✅ Django 5.x startup and basic API functionality 
- ✅ PostgreSQL 15 database connectivity and queries
- ✅ REST API endpoints and JSON responses  
- ✅ Basic pagination (`/api/v1/jobs/` returns proper paginated structure)
- ✅ Docker containerization and stack deployment
- ✅ Python 3.12 compatibility across all dependencies

## 🔄 **READY FOR TESTING** - Authentication & Authorization

- JWT token generation and validation (after `rest_framework_jwt` → `djangorestframework-simplejwt` migration)
  - **JWT endpoint available**: `/api/v1/auth/jwt/get/` responds to requests (405 for GET is expected)
  - **Need to test**: POST requests with valid credentials for token creation
  - **Need to test**: Token validation and refresh functionality
  - **Need to test**: API authentication using JWT tokens
- User login flows
- API authentication with tokens
- Social authentication (django-allauth integrations)
  - **Updated to**: `rest-social-auth` v9.0.0 compatibility with Django 5.x
  - **Need to verify**: Google OAuth2 integration still works
  - **Need to verify**: Social auth pipelines and user creation

## 🔄 **READY FOR TESTING** - File Processing & External Integrations  

- **✅ Fixed**: Degust upload functionality (`laxy_backend.views.SendFileToDegust`)
  - **Updated**: `robobrowser` → `robox` migration completed
  - **Need to test**: Form submission with file uploads
  - **Need to test**: URL parsing and redirection  
  - **Need to test**: Response status code handling
  - **Need to test**: Integration with external Degust service
- File uploads and download functionality
- SFTP storage backend compatibility
- External web scraping utilities
  - **Fixed**: `webdav3` → `webdav4` migration for WebDAV endpoints

## 🔧 **NEEDS ATTENTION** - API Documentation

- **Issue**: OpenAPI/Swagger documentation (returns 500 error)
  - **Migration**: `drf_openapi` removed → DRF built-in OpenAPI
  - **Need to fix**: Schema generation configuration
  - **Need to test**: API documentation accessibility
  - **Low priority**: Core API functionality works independently

## 🔄 **READY FOR TESTING** - Background Task Processing

- Celery 5.5 task execution and scheduling
- RabbitMQ message broker connectivity
- Background file processing tasks  
- Job queue management (high/low priority)
- Task monitoring with Flower

## 🔄 **READY FOR TESTING** - Data Processing & Pipeline Integration

- Job creation and execution workflows
- Pipeline configuration and parameter handling
- File metadata and processing
- Database model operations (after JSONField updates)

## 🔄 **READY FOR TESTING** - Frontend Integration

- API compatibility with existing frontend client
- CORS configuration with updated URLs (fixed schemes)
- WebSocket connections (if applicable)
- Static file serving

## Test Priority

### **HIGH PRIORITY** (Core Functionality):
1. JWT authentication end-to-end testing
2. Database operations and model functionality  
3. Background task processing with Celery
4. File upload/download operations

### **MEDIUM PRIORITY** (Integration):
1. Social authentication flows
2. External service integrations (Degust, WebDAV)
3. Frontend API compatibility
4. Pipeline and job workflows

### **LOW PRIORITY** (Documentation & Polish):
1. OpenAPI/Swagger documentation fix
2. Template warnings resolution
3. Performance optimization testing

## Success Criteria

- All high-priority features work without breaking changes
- Authentication systems maintain security and functionality
- Background processing operates reliably
- File operations complete successfully
- External integrations remain functional