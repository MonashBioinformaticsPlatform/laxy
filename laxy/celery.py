from __future__ import absolute_import

import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'laxy.settings')

from django.conf import settings

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration

if getattr(settings, 'SENTRY_DSN', False):
    sentry_sdk.init(dsn=settings.SENTRY_DSN, integrations=[CeleryIntegration()])

app = Celery('laxy')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
