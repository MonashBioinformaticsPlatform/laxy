#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "laxy.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)

    # Start the remote debugger for PyCharm if in debug mode
    # You must pip install the exact version of pydevd-pycharm matching your IDE version
    # eg:  pip install pydevd-pycharm~=192.6262.63
    #
    # from django.conf import settings
    # if settings.DEBUG and sys.argv[1] == 'runserver':
    #     import pydevd_pycharm
    #     debug_host = 'host.docker.internal'
    #     pydevd_pycharm.settrace(debug_host, port=21001,
    #                             suspend=False,
    #                             stdoutToServer=True, stderrToServer=True)
    #     print("Initialized debugger client that will connect to: ", debug_host)
    #     print("Insert code the `import pydevd_pycharm; pydevd_pycharm.settrace()` to trigger the debugger.")
