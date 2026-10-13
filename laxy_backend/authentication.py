"""DRF authentication for named UserApiKey Bearer tokens."""

from __future__ import annotations

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from laxy_backend.models import UserApiKey


class UserApiKeyAuthentication(BaseAuthentication):
    """Accept ``Authorization: Bearer laxy_<prefix>_<secret>``.

    Non-``laxy_`` Bearer tokens are ignored so JWTAuthentication can try next.
    """

    keyword = b"bearer"

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword or len(auth) != 2:
            return None
        try:
            token = auth[1].decode("utf-8")
        except UnicodeDecodeError:
            return None
        if not token.startswith(f"{UserApiKey.KEY_SCHEME}_"):
            return None
        user = UserApiKey.authenticate(token)
        if user is None:
            raise AuthenticationFailed("Invalid or expired API key")
        return (user, token)

    def authenticate_header(self, request):
        return "Bearer"
