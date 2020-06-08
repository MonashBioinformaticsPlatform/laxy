"""
Django settings for laxy project.

Generated by 'django-admin startproject' using Django 1.11.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""
import logging

import os
from datetime import timedelta
import tempfile
import subprocess
import json
from django.core.exceptions import ImproperlyConfigured
import environ
from celery.schedules import crontab

from laxy.utils import get_secret_key

logger = logging.getLogger(__name__)

APP_ENV_PREFIX = "LAXY_"


class PrefixedEnv(environ.Env):
    """
    Like environ.Env, except it adds the given prefix to the keys of each
    default environment variable specified upon instantiation.

    This means you can omit the prefix everywhere in settings.py /
    default_settings.py, but use the prefix in .env and actual environment
    variables.
    """

    def __init__(self, prefix, **scheme):
        # Add prefix to dictionary keys
        self.scheme = dict([("%s%s" % (prefix, k), v) for k, v in scheme.items()])


def permissive_json_loads(text: str):
    """
    Like json.loads, but returns an empty dict for an empty or whitespace string.

    :param text:
    :type text:
    :return:
    :rtype:
    """
    text = text.strip()
    if text:
        return json.loads(text)
    else:
        return {}


# Build paths inside the project like this: app_root.path('templates')
app_root = environ.Path(__file__) - 2
BASE_DIR = str(app_root)
envfile = app_root.path(".env")
# read the .env file - this does not clobber any environment variables already set,
# so 'real' environment variables take precedence to those defined in .env
environ.Env.read_env(envfile())

default_env = PrefixedEnv(
    APP_ENV_PREFIX,
    DEBUG=(bool, False),
    SECRET_KEY=(str, None),
    VERSION=(str, None),
    ENV=(str, ""),
    ADMIN_EMAIL=(str, None),
    ADMIN_USERNAME=(str, None),
    AWS_ACCESS_KEY_ID=(str, None),
    AWS_SECRET_ACCESS_KEY=(str, None),
    ALLOWED_HOSTS=(list, ["*"]),
    BROKER_URL=(str, "amqp://"),
    EMAIL_HOST_URL=("email_url", ""),
    EMAIL_HOST_USER=(str, ""),
    EMAIL_HOST_PASSWORD=(str, ""),
    STATIC_ROOT=(str, str(app_root.path("static")())),
    STATIC_URL=(str, "/static/"),
    MEDIA_ROOT=(str, str(app_root.path("uploads")())),
    MEDIA_URL=(str, "uploads/"),
    FRONTEND_API_URL=(str, ""),
    FILE_CACHE_PATH=(str, tempfile.gettempdir()),
    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=(str, ""),
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=(str, ""),
    SOCIAL_AUTH_WHITELISTED_DOMAINS=(list, []),
    SOCIAL_AUTH_WHITELISTED_EMAILS=(list, []),
    CORS_ORIGIN_WHITELIST=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    USE_SSL=(bool, False),
    SENTRY_DSN=(str, ""),
    JOB_EXPIRY_TTL_DEFAULT=(int, 30 * 24 * 60 * 60),  # 30 days
    JOB_EXPIRY_TTL_CANCELLED=(int, 1 * 60 * 60),  # 1 hour
    JOB_EXPIRY_TTL_FAILED=(int, 3 * 24 * 60 * 60),  # 3 days
    WEB_SCRAPER_BACKEND=(str, "simple"),
    WEB_SCRAPER_SPLASH_HOST=(str, "http://localhost:8050"),
    DEGUST_URL=(str, "http://degust.erc.monash.edu"),
    EMAIL_DOMAIN_ALLOWED_COMPUTE=(permissive_json_loads, {"*": ["*"]}),
)


def env(env_key=None, default=environ.Env.NOTSET, transform=None):
    """
    Return the value of a particular environment variable, pre-registered in `default_env`,
    automatically adding the APP_ENV_PREFIX.

    Eg, if
    ```python
    APP_ENV_PREFIX = "LAXY_"
    default_env = PrefixedEnv(APP_ENV_PREFIX, DEBUG=(bool, False))
    env('DEBUG') # will return the value of the environment variable `LAXY_DEBUG`.
    ```

    :param env_key:
    :type env_key: str
    :param default: A default value to return if the environment variable is missing (unset).
    :type default:
    :param transform: A function (eg lamda) that will be applied to the value before returning it.
                  Typically should return a modified (eg type-casted, filtered, escaped) version of the value.
    :type transform: Function
    :return: The value of the environment variable.
    :rtype:
    """
    value = default_env("%s%s" % (APP_ENV_PREFIX, env_key), default=default)
    if transform is not None:
        value = transform(value)
    return value


def _cleanup_env_list(l):
    """
    Remove quota characters and strip whitespace.
    Intended to cleanup environment variables that are comma-separated lists parsed by `environ`.

    >>> _cleanup_quoted_list(['" something'])
    ['something']

    :param l:
    :type l:
    :return:
    :rtype:
    """
    return [i.replace('"', "").replace("'", "").strip() for i in l]


def get_git_commit():
    git_commit = None
    try:
        git_commit = (
            subprocess.check_output(["git", "log", "-1", "--format=%h 2>/dev/null"])
            .strip()
            .decode("utf-8")
        )
    except:
        pass
    return git_commit


def get_version_txt():
    versionfilepath = os.path.join(os.getcwd(), "version.txt")
    version = None
    try:
        if os.path.exists(versionfilepath):
            version = open(versionfilepath, "r").read().strip()
            return version
    except:
        pass
    return version


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")
ENV = env("ENV")

# Take LAXY_VERSION from env vars, if set, else try to get the version.txt file, or git commit, else 'unspecified'
VERSION = env("VERSION")
if not VERSION:
    VERSION = get_version_txt()
if not VERSION:
    VERSION = get_git_commit()
if not VERSION:
    VERSION = "unspecified"


SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    SENTRY_RELEASE = f"{VERSION}"
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        release=SENTRY_RELEASE,
        environment=ENV,
        integrations=[DjangoIntegration()],
    )

JOB_EXPIRY_TTL_DEFAULT = env("JOB_EXPIRY_TTL_DEFAULT")
JOB_EXPIRY_TTL_CANCELLED = env("JOB_EXPIRY_TTL_CANCELLED")
JOB_EXPIRY_TTL_FAILED = env("JOB_EXPIRY_TTL_FAILED")

SFTP_STORAGE_PIPELINED = True

USE_SSL = env("USE_SSL")
FRONTEND_API_URL = env("FRONTEND_API_URL")

ADMIN_EMAIL = env("ADMIN_EMAIL")
ADMIN_USERNAME = env("ADMIN_USERNAME")
if ADMIN_EMAIL and ADMIN_USERNAME:
    ADMINS = [(ADMIN_USERNAME, ADMIN_EMAIL)]

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")

AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")

FILE_CACHE_PATH = env("FILE_CACHE_PATH")

DEFAULT_JOB_BASE_PATH = "/tmp"
"""
The base path where job directories will be created if `base_dir` isn't 
specified in ComputeResource.extra on the compute node for a job.
"""

WEB_SCRAPER_BACKEND = env("WEB_SCRAPER_BACKEND")
"""
Valid options are 'simple', 'splash' (and possibly 'pyppeteer' in the future)
"""

WEB_SCRAPER_SPLASH_HOST = env("WEB_SCRAPER_SPLASH_HOST")
"""
The URL to a Splash scraping server (eg https://splash.readthedocs.io/en/stable/api.html#render-html).
When running under docker-compose this might be 'http://splash:8050'.
"""

DEGUST_URL = env("DEGUST_URL")
"""
The base URL to the Degust instance you'd like to use (eg, could be changed to 
"http://degust-training.erc.monash.edu" or a dev instance of Degust)
"""

EMAIL_DOMAIN_ALLOWED_COMPUTE = env("EMAIL_DOMAIN_ALLOWED_COMPUTE")
"""
Maps user email domains to named compute resources they are allowed to use.
"*" wildcard means any domain or compute resource (this isn't a regex / glob).

Order of the ComputeResource names in the list doesn't matter - which one is chosen depends on
ComputeResource.priority (and maybe other factors).

Note that if you are using local Django accounts, you should use email address validation
for this setting to be effective, otherwise users could easily change their email address 
to one the don't actually own and access compute resources you don't intend them to access.
```json
{
    "important.edu.au": ["fast_hpc", "other_hpc", "*"],
    "gmail.com": ["slow_cloud"],
    "clinicalpeeps.com": ["extra_secure"],
    "*": ["slow_cloud"]
}
```

"""

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret !
try:
    SECRET_KEY = env("SECRET_KEY")
except ImproperlyConfigured:
    SECRET_KEY = get_secret_key()

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
DATABASES = {
    "default": default_env.db(
        f"{APP_ENV_PREFIX}DATABASE_URL", default="postgres:///postgres:postgres@db:5432"
    )
}

# We can set a longer than default timeout for the database, mostly so that
# Django waits longer for the database to come online when initially
# bringing up the Docker Compose stack.
# if 'postgres' in DATABASES['default'].get('ENGINE', ''):
#     DATABASES['default']['OPTIONS'] = {'connect_timeout': 10}

SITE_ID = 1

BROKER_URL = env("BROKER_URL")
CELERY_RESULT_BACKEND = "django-db"
# CELERY_RESULT_BACKEND = 'db+postgresql://postgres:postgres@db:5432/postgres'
# CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
# CELERY_RESULT_BACKEND = BROKER_URL
if DEBUG:
    CELERY_ALWAYS_EAGER = True
# CELERY_IGNORE_RESULT = True

# Tasks that run longer than this will raise a SoftTimeLimitExceeded exception,
# to save clogging up the queue with things that will probably never finish
_days = 60 * 60 * 24
CELERY_TASK_SOFT_TIME_LIMIT = 7 * _days

# Don't prefetch tasks, work on one at a time, only acknowledge task is done when it finishes
# (successfully or with exception). Tasks must be idempotent in this mode, since if a worker
# dies ungracefully without the task finishing, that task will be requeued later. This mode
# as lower throughput for many small short tasks, but make it less likely tasks will be lost
# and forgotten upon worker kill/restart.
# https://docs.celeryproject.org/en/latest/userguide/configuration.html#worker-prefetch-multiplier
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True  # no prefetching at all ! tasks must be idempotent

_prefetch_one = True
if _prefetch_one:
    # In this mode, only reserve one 'unacknowledged' task for every cpu/thread on the worker
    # ... so for every one executing, one 'unacknowledged' task will prefetched from RabbitMQ
    # and waiting on the worker.
    CELERY_WORKER_PREFETCH_MULTIPLIER = 1
    CELERY_TASK_ACKS_LATE = False  # default


# CELERY_TASK_DEFAULT_QUEUE = 'celery'
# CELERY_TASK_CREATE_MISSING_QUEUES = True

# TODO: Not yet working, so using explicit @shared_task(queue='low-priority')
#       on task functions instead
# CELERY_TASK_ROUTES = {
#     "laxy_backend.tasks.file.move_file_task": {"queue": "low-priority"},
#     "laxy_backend.tasks.file.copy_file_task": {"queue": "low-priority"},
#     "laxy_backend.tasks.file.verify_task": {"queue": "low-priority"},
#     "laxy_backend.tasks.job.estimate_job_tarball_size": {"queue": "low-priority"},
#     "laxy_backend.tasks.job.expire_old_job": {"queue": "low-priority"},
# }

CELERYBEAT_SCHEDULE = {
    "expire_old_jobs": {
        "task": "laxy_backend.tasks.job.expire_old_jobs",
        # "schedule": timedelta(minutes=15)
        "schedule": timedelta(hours=6)
        # "schedule": timedelta(seconds=60)
        # "schedule": crontab(minute='*/15')
    }
}

MEDIA_ROOT = str(env("MEDIA_ROOT"))
MEDIA_URL = str(env("MEDIA_URL"))

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/
STATIC_URL = str(env("STATIC_URL"))
STATIC_ROOT = str(env("STATIC_ROOT"))

# For whitenoise compression and name-mangling caching
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Application definition

# Required since Laxy overrides the default Django User model
AUTH_USER_MODEL = "laxy_backend.User"

INSTALLED_APPS = [
    # 'whitenoise.runserver_nostatic',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django_extensions",
    "django_celery_results",
    "django_celery_beat",
    "django.db.migrations",  # enables viewing of migrations in /admin
    "django_object_actions",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_openapi",
    "reversion",
    "storages",
    # for python-social-auth with DRF
    "oauth2_provider",
    "social_django",  # OAuth2 backends
    "rest_framework_social_oauth2",  # OAuth2 callback ('complete') endpoints
    "rest_social_auth",  # Login endpoints, hands off to social login services
    "laxy_backend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # 'whitenoise.middleware.WhiteNoiseMiddleware',
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "laxy.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [app_root.path("templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": True,  # to disable template caching
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

# Options for the django_extensions shell_plus Jupyter notebook
if DEBUG:
    NOTEBOOK_ARGUMENTS = [
        "--ip",
        "0.0.0.0",
        "--port",
        "8999",
        "--no-browser",
        "-y",
        "--allow-root",
    ]
    IPYTHON_ARGUMENTS = ["--debug"]
    # SHELL_PLUS_PRINT_SQL = False
    # SHELL_PLUS_PRINT_SQL_TRUNCATE = 2

# https://github.com/ottoyiu/django-cors-headers#configuration
CSRF_COOKIE_DOMAIN = env("CSRF_COOKIE_DOMAIN", "localhost")

CORS_ORIGIN_WHITELIST = env(
    "CORS_ORIGIN_WHITELIST",
    default=[
        "laxy.io",
        "api.laxy.io",
        "api.laxy.io:8001",
        "dev.laxy.io:8002",
        "dev.laxy.io",
        "dev-api.laxy.io",
    ],
    transform=_cleanup_env_list,
)

# Applies to HTTPS only
CSRF_TRUSTED_ORIGINS = env(
    "CSRF_TRUSTED_ORIGINS",
    default=["laxy.io", ".laxy.io",],
    transform=_cleanup_env_list,
)

CORS_ALLOW_CREDENTIALS = True

if DEBUG:
    # This will add the {Access-Control-Allow-Origin: *} header.
    # You probably never want with, since frontend client requests using withCredentials will fail when
    # {Access-Control-Allow-Origin: *} is present.
    # CORS_ORIGIN_ALLOW_ALL = True

    CORS_ORIGIN_WHITELIST += ["localhost:8002"]
    # Applies to HTTPS only
    CSRF_TRUSTED_ORIGINS += ["localhost"]

if USE_SSL:
    CORS_REPLACE_HTTPS_REFERER = True
    HOST_SCHEME = "https://"
    # Required so that request.build_absolute_uri works correctly when Django
    # is behind a reverse proxy (eg nginx) providing HTTPS.
    # Reverse proxy must send X-Forwarded-Host and X-Forwarded-Proto headers.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
    SECURE_SSL_REDIRECT = True
    # Only send session cookie on a secure HTTPS connection
    SESSION_COOKIE_SECURE = True
    # Only send CSRF cookie on a secure HTTPS connection
    CSRF_COOKIE_SECURE = True

    # Stricter options
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_HSTS_SECONDS = 600  # ~10 min  # 1000000  # ~11 days
    # SECURE_FRAME_DENY = True
    #
    # # https://docs.djangoproject.com/en/2.1/ref/middleware/#x-content-type-options-nosniff
    # If True, the Content-Type is not correctly set for eg HTML reports, which currently rely on browser sniffing
    # SECURE_CONTENT_TYPE_NOSNIFF = True
    # # https://docs.djangoproject.com/en/2.1/ref/middleware/#x-content-type-options-nosniff
    # SECURE_BROWSER_XSS_FILTER = True

AUTHENTICATION_BACKENDS = (
    # 'social_core.backends.open_id.OpenIdAuth',   # not required ?
    # 'social_core.backends.google.GoogleOpenId',  # not required ?
    "social_core.backends.google.GoogleOAuth2",
    # 'laxy.auth_backends.GoogleOAuth2NoState',
    "rest_framework_social_oauth2.backends.DjangoOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

SOCIAL_AUTH_RAISE_EXCEPTIONS = DEBUG
SOCIAL_AUTH_URL_NAMESPACE = "social"
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = str(env("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY"))
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = str(env("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET"))
SOCIAL_AUTH_GOOGLE_OAUTH2_FIELDS = ["email", "username"]
SOCIAL_AUTH_POSTGRES_JSONFIELD = True
# SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
SOCIAL_AUTH_GOOGLE_OAUTH2_USE_UNIQUE_USER_ID = True

# Note: this only applies to django-social-auth logins, not Django local accounts (which may be
#       created by eg django-registration)
if env("SOCIAL_AUTH_WHITELISTED_DOMAINS", default=[]):  # only if non-empty list
    SOCIAL_AUTH_WHITELISTED_DOMAINS = env(
        "SOCIAL_AUTH_WHITELISTED_DOMAINS", transform=_cleanup_env_list
    )
    # Do we need SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS ??

if env("SOCIAL_AUTH_WHITELISTED_EMAILS", default=[]):  # only if non-empty list
    SOCIAL_AUTH_WHITELISTED_EMAILS = env(
        "SOCIAL_AUTH_WHITELISTED_EMAILS", transform=_cleanup_env_list
    )

# https://github.com/st4lk/django-rest-social-auth#settings
REST_SOCIAL_OAUTH_REDIRECT_URI = "/"  # ''http://localhost:8002/'
REST_SOCIAL_DOMAIN_FROM_ORIGIN = True

# OAuth2 provider
DRFSO2_PROPRIETARY_BACKEND_NAME = "Laxy"
DRFSO2_URL_NAMESPACE = "laxy_backend:rest_framework_social_oauth2"

SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    # 'social_core.pipeline.social_auth.social_user',
    # An alternative `social_user` step - this pipeline step is only required if
    # SOCIAL_AUTH_GOOGLE_OAUTH2_USE_UNIQUE_USER_ID was changed from False to True and you want to transparently
    # migrate the uid fields on the UserSocialAuth records.
    # 'social_core.pipeline.social_auth.social_user' is a better option for new installations without this requirement.
    "laxy_backend.auth.pipeline_migration.social_user_uid_swap",
    "social_core.pipeline.user.get_username",
    # 'social_core.pipeline.mail.mail_validation',
    # 'social_core.pipeline.social_auth.associate_by_email',
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    # custom function to get avatar for different services
    "laxy_backend.auth.pipeline.set_social_avatar",
)

REST_FRAMEWORK = {
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_PERMISSION_CLASSES": (
        # 'rest_framework.permissions.AllowAny',
        # 'rest_framework.permissions.IsAdminUser',
        "rest_framework.permissions.IsAuthenticated",
        # Use Django's standard `django.contrib.auth` permissions,
        # or allow read-only access for unauthenticated users.
        # 'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
    ),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_jwt.authentication.JSONWebTokenAuthentication",
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
        "rest_framework_social_oauth2.authentication.SocialAuthentication",
    ),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    # 'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    # http://www.django-rest-framework.org/api-guide/pagination/#cursorpagination
    # 'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.CursorPagination',
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

# TODO: Apparently drf_openapi doesn't honor this setting.
#       File an issue ? Query on gitter chat ?
# SWAGGER_SETTINGS = {'SECURITY_DEFINITIONS': {
#     'basic': {'type': 'basic'}},
#     'api_key': {
#         'type': 'apiKey',
#         'name': 'api_key',
#         'in': 'header'
#     }
# }
# '''
# Used as extra information to generate the OpenAPI documentation / schema.
#
# These should match the authentication types available
# (eg from REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES)
#
# See https://django-rest-swagger.readthedocs.io/en/latest/settings/ and
# https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#security-definitions-object
# '''

WSGI_APPLICATION = "laxy.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

_pwlib = "django.contrib.auth.password_validation."
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": _pwlib + "UserAttributeSimilarityValidator",},
    {"NAME": _pwlib + "MinimumLengthValidator",},
    {"NAME": _pwlib + "CommonPasswordValidator",},
    {"NAME": _pwlib + "NumericPasswordValidator",},
]

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

JWT_AUTH = {
    # 'JWT_ENCODE_HANDLER':
    # 'rest_framework_jwt.utils.jwt_encode_handler',
    #
    # 'JWT_DECODE_HANDLER':
    # 'rest_framework_jwt.utils.jwt_decode_handler',
    #
    # 'JWT_PAYLOAD_HANDLER':
    # 'rest_framework_jwt.utils.jwt_payload_handler',
    #
    # 'JWT_PAYLOAD_GET_USER_ID_HANDLER':
    # 'rest_framework_jwt.utils.jwt_get_user_id_from_payload_handler',
    #
    # 'JWT_PAYLOAD_GET_USERNAME_HANDLER':
    # 'rest_framework_jwt.utils.jwt_get_username_from_payload_handler',
    # 'JWT_RESPONSE_PAYLOAD_HANDLER':
    # 'rest_framework_jwt.utils.jwt_response_payload_handler',
    "JWT_SECRET_KEY": SECRET_KEY,
    "JWT_ALGORITHM": "HS256",
    "JWT_VERIFY": True,
    "JWT_VERIFY_EXPIRATION": True,
    "JWT_LEEWAY": 0,
    "JWT_EXPIRATION_DELTA": timedelta(days=4),
    "JWT_AUDIENCE": None,
    "JWT_ISSUER": None,
    "JWT_ALLOW_REFRESH": True,
    "JWT_REFRESH_EXPIRATION_DELTA": timedelta(days=7),
    "JWT_AUTH_HEADER_PREFIX": "Bearer",
}
"""
See https://getblimp.github.io/django-rest-framework-jwt/
"""

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "default-memory-cache",
    },
    # For caching results of requests to the ENA REST API
    "ena-lookups": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ena-lookups-cache",
        # 'TIMEOUT': 24*60*60,
    },
    # For cache_memoize usage on small miscellaneous functions
    # (time consuming functions or those that use HTTP requests to
    # external services with mostly static responses)
    "memoize": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "memoize-cache",
        "OPTIONS": {"MAX_ENTRIES": 1000},
        # 'TIMEOUT': 3*60*60,
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "timestamped": {"format": "{asctime}\t{levelname}\t{message}", "style": "{",},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "timestamped",},
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            # 'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'),
            "level": env("LOG_LEVEL", "INFO"),
        },
        "laxy_backend": {
            "handlers": ["console"],
            "level": env("LOG_LEVEL", "DEBUG"),
            "propagate": True,
        },
        # '': {
        #     'handlers': ['console'],
        #     'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'),
        # },
    },
}
