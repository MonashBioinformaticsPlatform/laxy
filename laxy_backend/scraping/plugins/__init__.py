"""
Site-specific handlers for ``RemoteBrowseView`` HTTP(S) URLs.

Each plugin is a callable ``(original_url, resolved_url) -> Optional[RemoteBrowseSitePluginResult]``.
Return ``None`` if the URL is not handled by this plugin. Built-in plugins (eg Zenodo) are
registered first; add more via ``settings.REMOTE_BROWSE_SITE_PLUGINS`` (dotted import paths).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from django.conf import settings
from django.http import JsonResponse
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


@dataclass
class RemoteBrowseSitePluginResult:
    """Non-empty outcome when a site plugin handles the URL."""

    listing: List[dict]


class RemoteBrowseSitePluginError(Exception):
    """Raised when a plugin recognises the URL but cannot produce a listing."""

    def __init__(
        self,
        *,
        status_code: int,
        reason: str,
        original_url: str,
    ) -> None:
        self.status_code = status_code
        self.reason = reason
        self.original_url = original_url
        super().__init__(reason)


RemoteBrowseSitePlugin = Callable[
    [str, str],
    Optional[RemoteBrowseSitePluginResult],
]


def _builtin_remote_browse_site_plugins() -> List[RemoteBrowseSitePlugin]:
    from .zenodo import zenodo_remote_browse_plugin

    return [zenodo_remote_browse_plugin]


def get_remote_browse_site_plugins() -> List[RemoteBrowseSitePlugin]:
    plugins: List[RemoteBrowseSitePlugin] = []
    plugins.extend(_builtin_remote_browse_site_plugins())
    for path in getattr(settings, "REMOTE_BROWSE_SITE_PLUGINS", []):
        try:
            plugins.append(import_string(path))
        except Exception:
            logger.exception(
                "REMOTE_BROWSE_SITE_PLUGINS: failed to import %r", path
            )
            raise
    return plugins


def _plugin_error_response(exc: RemoteBrowseSitePluginError) -> JsonResponse:
    return JsonResponse(
        {
            "remote_server_response": {
                "url": exc.original_url,
                "status": exc.status_code,
                "reason": exc.reason,
            }
        },
        status=exc.status_code,
        reason=exc.reason,
    )


def run_remote_browse_site_plugins(
    original_url: str,
    resolved_url: str,
) -> Tuple[Optional[List[dict]], Optional[JsonResponse]]:
    """
    Run registered site plugins until one returns a result or raises
    :class:`RemoteBrowseSitePluginError`.

    :return: ``(listing, None)`` if handled, ``(None, JsonResponse)`` on plugin error,
        or ``(None, None)`` if no plugin applied.
    """
    for plugin in get_remote_browse_site_plugins():
        try:
            outcome = plugin(original_url, resolved_url)
        except RemoteBrowseSitePluginError as exc:
            return None, _plugin_error_response(exc)
        if outcome is not None:
            return outcome.listing, None
    return None, None
