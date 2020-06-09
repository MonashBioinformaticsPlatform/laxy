from __future__ import absolute_import

import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "laxy.settings")

from django.conf import settings

if getattr(settings, "SENTRY_DSN", False):
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        release=settings.VERSION,
        environment=settings.ENV,
        integrations=[CeleryIntegration(), DjangoIntegration(),],
    )

app = Celery("laxy")

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object("django.conf:settings")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


# We don't start the debugger when CELERY_ALWAYS_EAGER is True to avoid attempting to
# open the debugger port twice (With CELERY_ALWAYS_EAGER celery jobs run as blocking
# function calls on the Django app rather than a seperate worker process)
if settings.DEBUG and not settings.CELERY_ALWAYS_EAGER:
    import traceback

    try:
        debugger_port = os.environ.get("DEBUGGER_PORT", 21001)

        # Visual Studio Code debugging
        import json
        import ptvsd

        ptvsd.enable_attach(address=("0.0.0.0", debugger_port))
        # ptvsd.enable_attach(settings.SECRET_KEY, address=('0.0.0.0', 21001))
        # ptvsd.wait_for_attach()
        _vscode_launch_json = {
            "name": "Remote Celery Worker (Laxy)",
            "type": "python",
            "request": "attach",
            "pathMappings": [{"localRoot": "${workspaceFolder}", "remoteRoot": "/app"}],
            "port": debugger_port,
            "host": "localhost",
        }
        print("Visual Studio Code debugger launch.json snippet to add:")
        print(json.dumps(_vscode_launch_json, indent=4))

    except Exception as ex:
        print(traceback.format_exc())


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))
