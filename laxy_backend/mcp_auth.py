"""Bearer-token verification for the Laxy MCP endpoint.

Accepts a named UserApiKey (``laxy_…``), a SimpleJWT access token, or a
DRF authtoken key via ``Authorization: Bearer <token>``. DRF tokens normally
use the ``Token`` scheme; accepting them over Bearer is intentional so MCP
clients can paste a long-lived credential without a refresh hook (JWT access
tokens expire after 14 days). Prefer a named API key from the Laxy UI.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from mcp.server.auth.provider import AccessToken
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from laxy_backend.models import UserApiKey

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

User = get_user_model()

# Real OS threads (not gevent greenlets) so Django ORM is outside any event loop.
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="laxy-mcp-auth")


class LaxyTokenVerifier:
    """Verify Laxy named API keys, JWT, or DRF tokens for MCP bearer auth."""

    async def verify_token(self, token: str) -> AccessToken | None:
        user = await self._resolve_user(token)
        if user is None or not user.is_active:
            return None
        return AccessToken(
            token=token,
            client_id=str(user.pk),
            scopes=["laxy"],
            subject=str(user.pk),
            claims={"username": user.get_username()},
        )

    async def resolve_user(self, token: str) -> AbstractBaseUser | None:
        return await self._resolve_user(token)

    async def _resolve_user(self, token: str) -> AbstractBaseUser | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_executor, self._resolve_user_sync, token)

    def _resolve_user_sync(self, token: str) -> AbstractBaseUser | None:
        # Gunicorn --worker-class gevent monkey-patches ThreadPoolExecutor to
        # greenlets, so Django still sees a running event loop here. Allow the
        # sync ORM call in this dedicated auth path (tools themselves run via
        # the MCP SDK worker pool). Prefer gthread/sync workers for MCP in prod.
        import os

        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        close_old_connections()
        try:
            user = self._user_from_api_key(token)
            if user is not None:
                return user
            user = self._user_from_jwt(token)
            if user is not None:
                return user
            return self._user_from_drf_token(token)
        finally:
            close_old_connections()

    def _user_from_api_key(self, token: str) -> AbstractBaseUser | None:
        return UserApiKey.authenticate(token)

    def _user_from_jwt(self, token: str) -> AbstractBaseUser | None:
        auth = JWTAuthentication()
        try:
            validated = auth.get_validated_token(token)
            return auth.get_user(validated)
        except (InvalidToken, TokenError, User.DoesNotExist):
            return None

    def _user_from_drf_token(self, token: str) -> AbstractBaseUser | None:
        try:
            return Token.objects.select_related("user").get(key=token).user
        except Token.DoesNotExist:
            return None
