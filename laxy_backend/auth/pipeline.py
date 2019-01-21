import json
from ..view_auth import gravatar_url, create_or_get_userprofile

import logging
logger = logging.getLogger(__name__)


def ensure_user_profile_exists(func):
    def wrapper(*args, **kwargs):
        user = kwargs.get('user', None)
        if user:
            create_or_get_userprofile(user)

        func(*args, **kwargs)

    return wrapper


@ensure_user_profile_exists
def set_social_avatar(backend, strategy, details, response, user=None, *args, **kwargs):
    url = None
    logger.debug("set_social_avatar response data: " + json.dumps(response))
    if backend.name == 'twitter':
        url = response.get('profile_image_url', '').replace('_normal', '')
    if backend.name == 'google-oauth2':
        url = response.get('picture', None)
    if url:
        user.profile.image_url = url
        user.save()
    else:
        user.profile.image_url = gravatar_url(user.email)
        user.save()
