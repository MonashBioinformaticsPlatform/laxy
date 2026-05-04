import json
import re
from typing import List, Optional
from urllib.parse import quote, urlparse

import requests

from laxy_backend.storage.http_remote import is_archive_link

from . import RemoteBrowseSitePluginError, RemoteBrowseSitePluginResult

_ZENODO_HOSTS = frozenset({"zenodo.org", "www.zenodo.org"})


def extract_zenodo_record_id(url: str) -> Optional[str]:
    """
    Return the numeric Zenodo record id if ``url`` is a Zenodo record or API URL.

    Matches ``/records/{id}`` (including ``/records/{id}/files/...``) and
    ``/api/records/{id}``.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in _ZENODO_HOSTS:
        return None
    path = parsed.path or ""
    m = re.match(r"/records/(\d+)(?:/|$|\?)", path)
    if m:
        return m.group(1)
    m = re.match(r"/api/records/(\d+)(?:/|$|\?)", path)
    if m:
        return m.group(1)
    return None


def zenodo_record_file_listing(record_id: str, timeout: float = 30) -> List[dict]:
    """
    List depositor files for a Zenodo record using the Zenodo REST API.

    Download ``location`` values use the public form
    ``https://zenodo.org/records/{id}/files/{name}?download=1``.
    """
    api_url = f"https://zenodo.org/api/records/{record_id}"
    resp = requests.get(api_url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    files = data.get("files") or []
    listing: List[dict] = []
    for fmeta in files:
        key = fmeta.get("key")
        if not key:
            continue
        encoded = quote(key, safe="")
        loc = f"https://zenodo.org/records/{record_id}/files/{encoded}?download=1"
        listing.append(
            dict(
                type="file",
                name=key,
                location=loc,
                tags=["archive"] if is_archive_link(key) else [],
            )
        )
    return listing


def zenodo_remote_browse_plugin(
    original_url: str,
    resolved_url: str,
) -> Optional[RemoteBrowseSitePluginResult]:
    zenodo_id = extract_zenodo_record_id(resolved_url) or extract_zenodo_record_id(
        original_url
    )
    if zenodo_id is None:
        return None
    try:
        listing = zenodo_record_file_listing(zenodo_id)
    except requests.exceptions.HTTPError as ex:
        if ex.response is not None:
            status_code = ex.response.status_code
            reason = getattr(ex.response, "reason", None) or str(ex)
        else:
            status_code = 502
            reason = str(ex)
        raise RemoteBrowseSitePluginError(
            status_code=status_code,
            reason=reason,
            original_url=original_url,
        ) from ex
    except (requests.exceptions.RequestException, ValueError, json.JSONDecodeError) as ex:
        raise RemoteBrowseSitePluginError(
            status_code=502,
            reason=str(ex),
            original_url=original_url,
        ) from ex
    return RemoteBrowseSitePluginResult(listing=listing)
