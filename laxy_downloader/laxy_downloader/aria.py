from typing import List, Collection
import backoff

import xmlrpc
from pyaria2 import PyAria2, AriaServerSettings

from .downloader import logger, url_to_cache_key

__aria2daemon__ = None


def get_daemon(secret=None):
    global __aria2daemon__

    if __aria2daemon__ is None:
        aria_settings = AriaServerSettings()
        aria_settings.continue_flag = True

        if secret is not None:
            aria_settings.rpc_secret = secret

        __aria2daemon__ = PyAria2(aria_settings)
    return __aria2daemon__


def purge_results():
    daemon = get_daemon()
    return daemon.purgeDownloadResult()


def get_active_uris():
    aria = get_daemon()
    active_uris = set()
    for active in aria.tellActive():
        for f in active["files"]:
            for u in f["uris"]:
                active_uris.add(u["uri"])

    return active_uris


def download_urls(
    urls: Collection, cache_path=None, proxy=None, concurrent_downloads=8
):
    aria = get_daemon()
    default_options = {
        "continue": "true",
        "allow-overwrite": "true",
        "always-resume": "true",
        "max-tries": "8",
        "retry-wait": "30",
        "max-file-not-found": "1",
        "optimize-concurrent-downloads": "true",
        "max-concurrent-downloads": concurrent_downloads,
        "file-allocation": "none",
    }
    if proxy is not None:
        default_options["all-proxy"] = proxy

    active_uris = get_active_uris()

    download_ids = []
    for url in set(urls) - active_uris:

        options = dict(default_options)
        if cache_path is not None:
            options["dir"] = cache_path
            options["out"] = url_to_cache_key(url)

        download_ids.append(aria.addUri([url], options=options))
        logger.info(f"Added download: {url} ({url_to_cache_key(url)})")

    return download_ids


def downloads_finished(download_ids):
    aria = get_daemon()
    statuses = []
    for gid in download_ids:
        try:
            statuses.append(aria.tellStatus(gid))
        except xmlrpc.client.Fault as ex:
            logger.error(ex.faultString)

    if not statuses:
        return False

    done = all(
        [
            dl.get("status", None) == "complete"
            or dl.get("status", None) == "error"
            or dl.get("status", None) == "removed"
            for dl in statuses
        ]
    )
    return done


def stop_all():
    global __aria2daemon__
    aria = get_daemon()

    for active in aria.tellActive():
        aria.remove(active["gid"])

    aria.shutdown()
    __aria2daemon__ = None


def stop_url_download(url: str):
    aria = get_daemon()
    statuses = aria.tellActive() + aria.tellWaiting(0, 999) + aria.tellStopped(0, 999)

    for active in statuses:
        if active["files"][0]["uris"][0]["uri"] == url:
            aria.remove(active["gid"])

    aria.shutdown()


@backoff.on_exception(
    backoff.expo, (ConnectionRefusedError,), max_tries=8, jitter=backoff.full_jitter
)
def log_status():
    aria = get_daemon()
    statuses = aria.tellActive() + aria.tellWaiting(0, 999) + aria.tellStopped(0, 999)

    for dl in statuses:
        options = aria.getOption(dl["gid"])
        url = dl["files"][0]["uris"][0]["uri"]
        logger.info(f"Downloading: {url} ({url_to_cache_key(url)})")
        logger.debug(f"Status -- {dl} -- {options}")
