__version__ = '0.1'

import os

_sentry_dsn = os.environ.get('LAXY_SENTRY_DSN', None)

if _sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(_sentry_dsn)
    except:
        pass
