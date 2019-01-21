import json
from social_core.exceptions import AuthAlreadyAssociated

import logging
logger = logging.getLogger(__name__)


def social_user_uid_swap(backend, uid, user=None, *args, **kwargs):
    """
    This pipeline function migrates UserSocialAuth.uid from an email address to using the 'large int' UID,
    as provided by Google OAuth2. This is specifically intended for use where a production instance was started with
    `settings.SOCIAL_AUTH_GOOGLE_OAUTH2_USE_UNIQUE_USER_ID = False` (the default) and then was switched to `True`.
    It will transparently migrate the existing UserSocialAuth record upon login to use the correct uid, maintaining
    User foreign key associations.

    It is intended to be inserted in settings.SOCIAL_AUTH_PIPELINE after 'social_core.pipeline.social_auth.social_uid'.
    """

    provider = backend.name
    email = kwargs.get('response', {}).get('email', None)
    # logger.debug(f'social_user_lookup_and_uid_swap uid: {uid}')
    # logger.debug(f'social_user_lookup_and_uid_swap email: {email}')
    # logger.debug(f'social_user_lookup_and_uid_swap args: {args}')
    # logger.debug(f'social_user_lookup_and_uid_swap kwargs: {kwargs}')
    # logger.debug(f'social_user_lookup_and_uid_swap backend: {dir(backend)}')

    social = backend.strategy.storage.user.get_social_auth(provider, uid)
    if not social and backend.setting('USE_UNIQUE_USER_ID', False) and email is not None:
        social = backend.strategy.storage.user.get_social_auth(provider, email)
        if social:
            social.uid = uid
            social.save()

    if social:
        if user and social.user != user:
            msg = 'This account is already in use.'
            raise AuthAlreadyAssociated(backend, msg)
        elif not user:
            user = social.user
    return {'social': social,
            'user': user,
            'is_new': user is None,
            'new_association': social is None}
