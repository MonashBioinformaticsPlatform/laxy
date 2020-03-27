#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "laxy.settings")
    try:
        from django.core.management import execute_from_command_line

        from django.conf import settings

        # Start the remote debugger for VSCode/PyCharm if in debug mode
        if settings.DEBUG and sys.argv[1] == 'runserver':
            import traceback

            try:
                if os.environ.get('RUN_MAIN') or os.environ.get('WERKZEUG_RUN_MAIN'):  # prevent reattach on hot reload
                    debugger_port = 21001

                    # Visual Studio Code debugging
                    import json
                    import ptvsd

                    ptvsd.enable_attach(address=('0.0.0.0', debugger_port))
                    # ptvsd.enable_attach(settings.SECRET_KEY, address=('0.0.0.0', 21001))
                    # ptvsd.wait_for_attach()
                    _vscode_launch_json = {
                          "name": "Remote Django App (Laxy)",
                          "type": "python",
                          "request": "attach",
                          "pathMappings": [
                              {
                                  "localRoot": "${workspaceFolder}",
                                  "remoteRoot": "/app"
                              }
                          ],
                          "port": debugger_port,
                          "host": "localhost"
                    }
                    print("Visual Studio Code debugger launch.json snippet to add:")
                    print(json.dumps(_vscode_launch_json, indent=4))

                    # PyCharm debugging
                    # You must pip install the exact version of pydevd-pycharm matching your IDE version
                    # eg:  pip install pydevd-pycharm~=192.6262.63
                    #
                    # import pydevd_pycharm
                    #
                    # debug_host = 'host.docker.internal'
                    # pydevd_pycharm.settrace(debug_host, port=debugger_port,
                    #                         suspend=False,
                    #                         stdoutToServer=True, stderrToServer=True)
                    # print("Initialized debugger client that will connect to: ", debug_host)
                    # print("Insert code the `import pydevd_pycharm; pydevd_pycharm.settrace()` "
                    #       "to trigger the debugger.")
            except Exception as ex:
                print(traceback.format_exc())

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



