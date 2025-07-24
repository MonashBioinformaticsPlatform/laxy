# Features to test

These are features we need to test after the major dependency updates.
The list may not be exhaustive, but includes features and systems we know we have modified, or are likely to be impacted.

Prefer writing unit / integration tests where practical. Otherwise, manual testing is required.

## Authentication & Authorization
- ✅ JWT token generation and validation (after `rest_framework_jwt` → `djangorestframework-simplejwt` migration)
  - **Test JWT token creation**: Verify `create_jwt_user_token()` function works with Simple JWT
  - **Test JWT authentication**: Ensure API endpoints accept Simple JWT tokens
  - **Test token refresh**: Verify refresh token functionality works
  - **Test token verification**: Ensure token verification endpoint works
  - **Test backward compatibility**: Verify existing JWT helper functions still work
  - **Test API integration**: Ensure frontend can still obtain and use JWT tokens
- User login flows
- API authentication with tokens  
- Social authentication (django-allauth integrations)

## File Processing & External Integrations  
- Degust upload functionality (`laxy_backend.views.SendFileToDegust`)
  - Form submission with file uploads
  - URL parsing and redirection
  - Response status code handling
  - Integration with the Robox browser automation library
- WebDAV client operations (after webdav3 → webdav4 migration)
  - File listing and navigation
  - Remote file access

## Storage & File Management
- File storage backends (after `get_storage_class` → `import_string` migration)
- SFTP storage operations
- File upload and download flows
- Metadata handling

## Django App Configuration
- Pipeline app loading (nf-core-rnaseq, nf-core-rnaseq-brbseq, openfold, etc.)
- App label validation
- Django admin functionality

## Environment & Settings
- Environment variable handling (after django-environ upgrade and PrefixedEnv fixes)
- Settings validation and loading
- Guardian permissions (after GUARDIAN_MONKEY_PATCH_USER change)