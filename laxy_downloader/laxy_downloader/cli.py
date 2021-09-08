#!/usr/bin/env python3

import sys
import os
import logging
import argparse
import tarfile
from typing import List
import xmlrpc
import psutil
import platform

import trio

from .secrets import get_secret_key
from .downloader import (
    get_default_cache_path,
    sanitize_filename,
    trio_wait_with_progress,
    init_cache,
    is_cache_path,
    clean_cache,
    parse_pipeline_config,
    get_urls_from_pipeline_config,
    download_concurrent,
    is_tarfile,
    is_zipfile,
    untar,
    unzip,
    find_filename_and_size_from_url,
    url_to_cache_key,
    get_url_cached_path,
    create_symlink_to_cache,
    create_copy_from_cache,
    is_tar_url_with_fragment,
    untar_from_url_fragment,
    notify_event,
    async_notify_event,
)

from . import aria

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(levelname)s: %(asctime)s -- %(message)s", level=logging.INFO
)


def add_commandline_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    def _split_comma_sep_args(txt: str) -> List[str]:
        return txt.split(",")

    subparsers = parser.add_subparsers(help="sub-command help", dest="command")

    dl_parser = subparsers.add_parser("download", help="Download files.")
    cache_parser = subparsers.add_parser(
        "expire-cache",
        help="Remove files older than --cache-age and exit. "
        "Don't download anything. Useful for cleaning the cache via a cron job. "
        "WARNING: Assumes the --cache-path only contains cache files - "
        "any file in this path may be DELETED.",
    )

    cache_parser.add_argument(
        "urls",
        nargs="*",
        default=list(),
        help="URL(s) to remove from cache. --cache-age is ignored in this case.",
    )

    killaria_parser = subparsers.add_parser(
        "kill-aria",
        help="Stop all downloads and shutdown the download daemon (Aria2c).",
    )

    dl_parser.add_argument("urls", nargs="*", default=list())

    dl_parser.add_argument(
        "--pipeline-config",
        help="Path to a pipeline_config.json file from Laxy. You must provide this if URLs aren't "
        "specified on the commandline",
        type=argparse.FileType("r"),
    )
    dl_parser.add_argument(
        "--type-tags",
        help="When using --pipeline-config, only download files tagged with all these type_tags "
        "('--type-tag=tag_one,tag_two' means must have both tag_one _and_ tag_two). ",
        type=_split_comma_sep_args,
        default=None,
    )
    dl_parser.add_argument(
        "--unpack",
        "--untar",
        help="Unpack any tar or archives to --destination-path",
        action="store_true",
    )
    dl_parser.add_argument(
        "--parallel-downloads",
        help="The maximum number of files to download concurrently.",
        type=int,
        default=8,
    )
    dl_parser.add_argument(
        "--queue-then-exit",
        help="Rather than block waiting for downloads to finish, exit after queuing."
        "Aria2 daemon will continue downloading in the background.",
        action="store_true",
    )
    dl_parser.add_argument(
        "--copy-from-cache",
        help="When using a file from the local cache, copy it to the download location rather than "
        "symlinking.",
        action="store_true",
    )
    dl_parser.add_argument(
        "--destination-path",
        help="Symlink / copy downloaded files to this directory.",
        default=None,
        type=str,
    )
    dl_parser.add_argument(
        "--skip-existing",
        help="If a destination filename already exists, skip downloading it.",
        action="store_true",
    )
    dl_parser.add_argument(
        "--create-missing-directories",
        help="If the destination path directories are missing, recursively create them.",
        action="store_true",
    )
    dl_parser.add_argument(
        "--proxy",
        help="Specify the HTTP (and FTP) proxy to use in the format: "
        "[http://][USER:PASSWORD@]HOST[:PORT]",
        type=str,
        default=None,
    )
    dl_parser.add_argument(
        "--no-progress", help="Don't show progress bar ...", action="store_true"
    )
    dl_parser.add_argument(
        "--ignore-self-signed-ssl-certificate",
        help="Ignore SSL certificate verification errors - useful for "
        "testing in development. UNSAFE in production (enables "
        "man-in-the-middle attacks).",
        action="store_true",
    )
    dl_parser.add_argument(
        "--sanitize-filenames",
        help="Sanitize output filenames (eg remove spaces and cruft). "
        "Otherwise a best effort is made to use the 'real' filename "
        "based on the Content-Disposition headers or URL. If sanitized_filename "
        "fields are provided in pipeline_config.json, they are always used "
        "irrespective of this flag.",
        action="store_true",
    )

    url_to_cachekey_parser = subparsers.add_parser(
        "get-cache-key",
        help="Return the cache key associated with a URL. Useful if you'd like to verify if a URL exists in the cache directory.",
    )
    url_to_cachekey_parser.add_argument(
        "url", nargs=1, default=str, help="URL to find cache key for.",
    )
    url_to_cachekey_parser.add_argument(
        "--cache-path",
        help="If provided, returns the full path to the cache file if it exists, or nothing and a non-zero exit code otherwise.",
        default=None,
        type=str,
    )

    # Add common options to the main parser and most subparsers
    for p in [parser, dl_parser, cache_parser]:
        p.add_argument(
            "--no-aria2c",
            help="Download natively without using the Aria2c daemon.",
            dest="use_aria",
            action="store_false",
        )
        p.add_argument(
            "--cache-path",
            help="Path to the laxydl cache directory.",
            default=get_default_cache_path(),
            type=str,
        )
        p.add_argument(
            "--cache-age",
            help="Remove local cached files older than this (in days) when downloader runs",
            type=int,
            default=30,
        )
        p.add_argument(
            "--event-notification-url",
            help="Laxy API URL to send progress events to.",
            default=None,
            type=str,
        )
        p.add_argument(
            "--event-notification-auth-file",
            help="The path to a file containing authorization headers required for"
            "event notifications (curl-style, single line with 'Authorization: Bearer eyBigLongToken')",
            type=argparse.FileType("r"),
        )

        p.add_argument(
            "--quiet", help="Minimal output to stdout/stderr", action="store_true"
        )
        p.add_argument(
            "-vvv",
            help="Extra increased verbosity (debug logging)",
            action="store_true",
        )

    return parser


def _parse_auth_header_file(fh):
    headers = {}
    for l in fh:
        if l.strip():
            k, v = l.split(":", 1)
            headers[k.strip()] = v.strip()
    return headers


def _run_download_cli(args, rpc_secret=None):
    _initial_queued_wait_delay = 10  # seconds
    _polling_delay = 30  # seconds

    if args.use_aria:
        daemon = aria.get_daemon(secret=rpc_secret)
        aria.log_status()

    sanitize_names = args.sanitize_filenames

    config_urls = set()
    url_filenames = dict()
    if args.pipeline_config:
        config = parse_pipeline_config(args.pipeline_config)
        url_filenames = get_urls_from_pipeline_config(
            config, required_type_tags=args.type_tags
        )
        config_urls = set(url_filenames.keys())

    if config_urls is not None and args.urls:
        logging.error(
            "Can't mix --pipeline-config with URLs specified as command line args."
        )
        sys.exit(1)

    urls = set(args.urls)
    if config_urls is not None:
        urls = config_urls

    api_url = args.event_notification_url
    api_auth_headers = None
    if args.event_notification_auth_file:
        api_auth_headers = _parse_auth_header_file(args.event_notification_auth_file)

    verify_ssl_certificate = not args.ignore_self_signed_ssl_certificate

    if urls:
        if args.cache_path:
            init_cache(args.cache_path)

        # Find filenames for each URL, optionally skip any existing files
        if args.destination_path is not None:
            if args.create_missing_directories:
                os.makedirs(args.destination_path, exist_ok=True)

            skip_urls = set()
            for url in urls:
                filename = url_filenames.get(url, None)
                if not filename:
                    filename, _ = find_filename_and_size_from_url(
                        url, sanitize_name=sanitize_names
                    )
                    url_filenames[url] = filename

                filepath = os.path.join(args.destination_path, filename)

                if args.skip_existing and os.path.isfile(filepath):
                    logger.info(f"{filename} exists, skipping download.")
                    skip_urls.add(url)
                    continue

            urls.difference_update(skip_urls)

        if urls and args.use_aria:
            daemon = aria.get_daemon(secret=rpc_secret)

            async def aria_dl_and_poll():
                _type_tag_txt = ""
                if len(args.type_tags) >= 1:
                    _type_tag_txt = f" ({args.type_tags[0]})"

                await async_notify_event(
                    api_url,
                    "INPUT_DATA_DOWNLOAD_STARTED",
                    message=f"Input data download started{_type_tag_txt}.",
                    auth_headers=api_auth_headers,
                    verify_ssl_certificate=verify_ssl_certificate,
                )

                gids = aria.download_urls(
                    urls,
                    cache_path=args.cache_path,
                    proxy=args.proxy,
                    concurrent_downloads=args.parallel_downloads,
                )

                if args.queue_then_exit:
                    logger.info("Download GIDs: %s" % (", ".join(gids)))
                    logger.info("Queued downloads, exiting.")
                    sys.exit()

                logging.debug("Waiting a moment for downloaded to become queued.")
                await trio_wait_with_progress(
                    _initial_queued_wait_delay, 1, quiet=args.quiet or args.no_progress
                )

                aria.log_status()
                while not aria.downloads_finished(gids):
                    await trio_wait_with_progress(
                        _polling_delay, 1, quiet=args.quiet or args.no_progress
                    )

                await async_notify_event(
                    api_url,
                    "INPUT_DATA_DOWNLOAD_FINISHED",
                    message=f"Input data download finished{_type_tag_txt}.",
                    auth_headers=api_auth_headers,
                    verify_ssl_certificate=verify_ssl_certificate,
                )

                aria.purge_results()

            trio.run(aria_dl_and_poll)
        elif urls:
            # trio.run(download, urls)
            notify_event(
                api_url,
                "INPUT_DATA_DOWNLOAD_STARTED",
                message="Input data download started.",
                auth_headers=api_auth_headers,
                verify_ssl_certificate=verify_ssl_certificate,
            )

            download_concurrent(
                urls, args.cache_path, concurrent_downloads=args.parallel_downloads
            )

            notify_event(
                api_url,
                "INPUT_DATA_DOWNLOAD_FINISHED",
                message="Input data download finished.",
                auth_headers=api_auth_headers,
                verify_ssl_certificate=verify_ssl_certificate,
            )
        else:
            logger.info(f"All files are already downloaded.")

        if args.destination_path is not None:
            for url in urls:
                cached = get_url_cached_path(url, args.cache_path)

                filename = url_filenames.get(url, None)
                if filename is None:
                    filename, _ = find_filename_and_size_from_url(
                        url, sanitize_name=sanitize_names
                    )

                if not os.path.exists(cached):
                    logger.error(
                        f"Failed to download {url} ({cached}), exiting with error."
                    )
                    sys.exit(1)

                if is_tar_url_with_fragment(url) and is_tarfile(cached) and args.unpack:
                    # TODO: It's probably more efficient to group all URLs for the same tar file
                    # and extract all #fragment files from their archive at once. But this works for now.
                    logger.info(f"Untarring file from {cached} ({url})")
                    untar_from_url_fragment(cached, args.destination_path, url)
                elif is_tarfile(cached) and args.unpack:
                    logger.info(f"Untarring {cached} ({url})")
                    untar(cached, args.destination_path)
                elif is_zipfile(cached) and args.unpack:
                    logger.info(f"Unzipping {cached} ({url})")
                    unzip(cached, args.destination_path)
                elif args.copy_from_cache:
                    logger.info(
                        f"Copying {cached} -> "
                        f"{os.path.join(args.destination_path, filename)} ({url})"
                    )
                    create_copy_from_cache(
                        url,
                        args.destination_path,
                        args.cache_path,
                        filename=filename,
                        sanitize_name=sanitize_names,
                    )
                else:
                    logger.info(
                        f"Creating symlink {cached} <- "
                        f"{os.path.join(args.destination_path, filename)} ({url})"
                    )
                    create_symlink_to_cache(
                        url,
                        args.destination_path,
                        args.cache_path,
                        filename=filename,
                        sanitize_name=sanitize_names,
                    )


def main():
    parser = add_commandline_args(argparse.ArgumentParser())

    if len(sys.argv) == 1:
        parser.print_help()

    rpc_secret = None
    args = parser.parse_args()

    if args.quiet:
        logging.basicConfig(
            format="%(levelname)s: %(asctime)s -- %(message)s", level=logging.WARNING
        )
        logger.setLevel(logging.INFO)
    elif args.vvv:
        logging.basicConfig(
            format="%(levelname)s: %(asctime)s -- %(message)s", level=logging.DEBUG
        )
        logger.setLevel(logging.DEBUG)

    if args.command == "get-cache-key":
        if args.cache_path:
            _c_path = get_url_cached_path(args.url[0], args.cache_path)
            if os.path.exists(_c_path) and os.path.isfile(_c_path):
                print(_c_path)
            else:
                logger.error(f"URL is not in cache, {_c_path} does not exist.")
                sys.exit(1)
        else:
            print(url_to_cache_key(args.url[0]))
            sys.exit(0)

    if args.cache_path:
        if not (os.path.exists(args.cache_path) and os.path.isdir(args.cache_path)):
            logger.error(
                f"--cache-path was specified but {args.cache_path} does not exist."
            )
            sys.exit(1)

        if args.use_aria:
            hostname = platform.node()
            rpc_secret_path = os.path.join(
                args.cache_path, f".aria2_rpc_secret-{hostname}"
            )
            rpc_secret = get_secret_key(rpc_secret_path)

            logger.debug(f"RPC secret is at: {rpc_secret_path}")
            daemon = aria.get_daemon(secret=rpc_secret)

    if args.command == "expire-cache":
        if not is_cache_path(args.cache_path):
            logger.info(
                f"Path {args.cache_path} doesn't look like a laxydl download cache directory "
                f"(there's no .laxydl_cache file). "
                f"If you are REALLY sure, you can `touch {os.path.join(args.cache_path, '.laxydl_cache')}` "
                f"and try again, AT YOUR OWN RISK."
            )
            sys.exit(1)
        if args.urls:
            for url in args.urls:
                filepath = get_url_cached_path(url, args.cache_path)
                try:
                    if args.use_aria:
                        aria.stop_url_download(url)
                    if os.path.exists(filepath) and os.path.isfile(filepath):
                        os.remove(filepath)
                        logger.info(f"Removed cached download: ")
                    else:
                        logger.info(
                            f"Not deleting - cached file does not exist: {filepath} ({url})"
                        )
                except Exception as ex:
                    logger.exception(ex)
                    sys.exit(1)
        else:
            try:
                result = clean_cache(args.cache_path, cache_age=args.cache_age)
                result.check_returncode()
                num_deleted = len(result.stdout.decode("utf-8").split("\n")) - 1
                logger.info(f"Deleted {num_deleted} cached files.")
            except Exception as ex:
                logger.exception(ex)
                sys.exit(1)
        sys.exit()

    if args.command == "kill_aria":
        logger.info("Stopping all downloads and shuttting down Aria2c.")
        try:
            aria.stop_all()
        except Exception as ex:
            sys.exit(1)
        try:
            os.remove(rpc_secret_path)
        except (IOError, FileNotFoundError) as ex:
            logger.warning(
                f"Unable to remove RPC secret file at {rpc_secret_path} (wrong permissions or missing)."
            )
        sys.exit()

    if args.command == "download":
        if not args.pipeline_config and not args.urls:
            parser.print_help()
            sys.exit(1)

        try:
            _run_download_cli(args, rpc_secret=rpc_secret)
        except xmlrpc.client.Fault as ex:

            def get_processes_by_name(name):
                return [
                    p
                    for p in psutil.process_iter(attrs=["name"])
                    if p.info["name"] == name
                ]

            logger.error(
                f"Error communicating with aria2c backend: {ex.faultString} (code {ex.faultCode})"
            )
            logger.error("You may want to try:  laxydl kill-aria")
            aria_pids = " ".join([str(p.pid) for p in get_processes_by_name("aria2c")])
            logger.error(
                f"Or if that fails, try killing the aria2c process(es):  kill {aria_pids}"
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
