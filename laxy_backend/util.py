import random
import string
import uuid
import base64
from basehash import base62


def url_safe_base64_uuid():
    padded_base64_uuid = base64.urlsafe_b64encode(uuid.uuid4().bytes)
    return padded_base64_uuid.decode('ascii').replace('=', '')


def url_safe_base62_uuid():
    return base62().encode(uuid.uuid4().int).decode('ascii')


def generate_uuid():
    return url_safe_base62_uuid()


def generate_secret_key(length=255):
    return ''.join(
        [random.choice(string.letters + string.digits) for _ in range(length)]
    )


def b64uuid_to_uuid(b64uuid, regenerate_padding=True):
    if regenerate_padding:
        pad_chars = (24 - len(b64uuid)) * '='
        b64uuid += pad_chars
    as_str = str(b64uuid)
    as_bytes = base64.urlsafe_b64decode(as_str)
    return uuid.UUID(bytes=as_bytes)
