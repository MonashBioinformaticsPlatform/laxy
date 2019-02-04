from typing import Dict
import logging
from datetime import datetime
import uuid
import jwt
from rest_framework_jwt.settings import api_settings
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

# from .models import User
from django.contrib.auth import get_user_model
User = get_user_model()

logger = logging.getLogger(__name__)


def decode(encoded_token):
    """
    A wrapper around jwt.decode that uses the secret key defined in Django
    settings.

    :param encoded_token: A JWT encoded token.
    :type encoded_token: str
    :return: The decoded JSON payload, as a Python dict.
    :rtype: dict
    """
    return jwt.decode(encoded_token, key=settings.JWT_AUTH['JWT_SECRET_KEY'])


def create_jwt_user_token(username):
    jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
    jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

    class DummyUser:
        pk = -1
        username = ''
        email = ''

    user = DummyUser()
    if username:
        user = User.objects.get(username=username)

    payload = jwt_payload_handler(user)
    token = jwt_encode_handler(payload)

    return token, payload


def create_object_access_jwt(obj, ttl=None):
    """
    Create a JWT token representing an access claim to any Django object,
    discovered by id and ContentType.

    :param obj: The token will be authorized to modify this object. Requires
                an id attribute and a registered ContentType.
    :type obj: django.db.models.Model
    :param ttl: The length of time the key will be valid for. Defaults to
                JWT_EXPIRATION_DELTA from settings.
    :type ttl: datetime.timedelta
    :return: The signed JWT token.
    :rtype: str
    """
    if not ttl:
        ttl = settings.JWT_AUTH['JWT_EXPIRATION_DELTA']

    now = datetime.utcnow()
    expiry = now + ttl
    content_type = ContentType.objects.get_for_model(obj).model
    token = jwt.encode({'id': obj.id,
                        'content_type': content_type,
                        # The 'permission' field is currently unused, but
                        # could be used to determine access type (eg read/write)
                        'permission': 'rw',
                        'exp': expiry,
                        'iat': now,
                        'nbf': now,
                        # The 'jti' field is currently a placeholder, unused.
                        # It is a unique identifier for the token.
                        # We would use it if we wanted to revoke keys prior
                        # to expiration (eg upon job completion). This would
                        # require storing every JWT (+jti) issued (or
                        # associating the jti with the Job model, eg via a
                        # GenericForeignKey), and doing a database lookup for
                        # revoked keys when we verify for decode incoming JWTs.
                        'jti': uuid.uuid4().hex,
                        },
                       settings.JWT_AUTH['JWT_SECRET_KEY'],
                       settings.JWT_AUTH['JWT_ALGORITHM'])
    return token


def make_jwt_header_dict(token) -> Dict:
    return {u'Authorization': u'%s %s' % (
        settings.JWT_AUTH.get('JWT_AUTH_HEADER_PREFIX', u'Bearer'),
        token)}


def get_jwt_user_header_dict(username) -> Dict:
    return make_jwt_header_dict(create_jwt_user_token(username)[0])


def get_jwt_user_header_str(username) -> str:
    """
    Return a string with a JWT auth header:

      Authorization: Bearer xxxJWT.XxxX.XXX

    :param username:
    :type username:
    :return:
    :rtype:
    """
    header = ': '.join(*get_jwt_user_header_dict(username).items())
    logger.debug("get_jwt_user_header_str: %s", header)
    return header
