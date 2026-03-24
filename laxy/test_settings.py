import sys
from unittest.mock import MagicMock

from django.db.models import JSONField as DjangoJSONField


# Patch jsonfield before any Django imports
class MockJSONField(DjangoJSONField):
    pass


mock_jsonfield = MagicMock()
mock_jsonfield.JSONField = MockJSONField
sys.modules["jsonfield"] = mock_jsonfield
sys.modules["jsonfield.fields"] = mock_jsonfield
sys.modules["jsonfield.forms"] = mock_jsonfield

from .default_settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

SECRET_KEY = "test-secret-key-for-testing-only"

BROKER_URL = "memory://"
CELERY_TASK_ALWAYS_EAGER = True
