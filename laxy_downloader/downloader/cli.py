#!/usr/bin/env python3

import sys
import os
import logging
import argparse
import tarfile

import trio

from .secrets import get_secret_key
from .downloader import (get_default_cache_path,
                         trio_wait_with_progress,
                         clean_cache,
                         parse_pipeline_config,
                         get_urls_from_pipeline_config,
                         download_concurrent,
                         untar,
                         find_filename_and_size_from_url,
                         get_url_cached_path,
                         create_symlink_to_cache,
                         create_copy_from_cache)

from . import aria

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(levelname)s: %(asctime)s -- %(message)s', level=logging.INFO)


def add_commandline_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    subparsers = parser.add_subparsers(help='sub-command help', dest='command')

    parser.add_argument("--cache-path",
                        help="URL to send progress events to",
                        default=get_default_cache_path(),
                        type=str)
    parser.add_argument("--cache-age",
                        help="Remove local cached files older than this (in seconds) when downloader runs",
                        type=int,
                        default=30)

    parser.add_argument("--quiet",
                        help="Minimal output to stdout/stderr",
                        action="store_true")
    parser.add_argument("-vvv",
                        help="Extra increased verbosity (debug logging)",
                        action="store_true")

    dl_parser = subparsers.add_parser('download',
                                      help='Download files.')
    cache_parser = subparsers.add_parser('expire-cache',
                                         help="Remove files older than --cache-age and exit. "
                                              "Don't download anything. Useful for cleaning the cache via a cron job. "
                                              "WARNING: Assumes the --cache-path only contains cache files - "
                                              "any file in this path may be DELETED.")

    killaria_parser = subparsers.add_parser('kill-aria',
                                            help="Stop all downloads and shutdown the download daemon (Aria2c).")

    # cache_parser.add_argument("--expire-cache-only",
    #                           help="Remove files older than --cache-age and exit. "
    #                                "Don't download anything. Useful for cleaning the cache via a cron job. "
    #                                "WARNING: Assumes the --cache-path only contains cache files - "
    #                                "any file in this path may be DELETED.",
    #                           action="store_true")

    dl_parser.add_argument('urls', nargs='*', default=list())

    dl_parser.add_argument('--pipeline-config',
                           help="Path to a pipeline_config.json file from Laxy. You must provide this if URLs aren't "
                                "specified on the commandline",
                           type=argparse.FileType('r'))
    dl_parser.add_argument("--untar",
                           help="Untar any tar archives to --destination-path",
                           action="store_true")
    dl_parser.add_argument("--parallel-downloads",
                           help="The maximum number of files to download concurrently.",
                           type=int,
                           default=8)
    dl_parser.add_argument("--no-aria2c",
                           help="Download natively without using the Aria2c daemon.",
                           action="store_true")
    # parser.add_argument("--event-notification-url",
    #                     help="URL to send progress events to",
    #                     type=str)
    dl_parser.add_argument("--queue-then-exit",
                           help="Rather than block waiting for downloads to finish, exit after queuing. Aria2 daemon will"
                                "continue downloading in the background.",
                           action="store_true")

    dl_parser.add_argument("--copy-from-cache",
                           help="When using a file from the local cache, copy it to the download location rather than "
                                "symlinking.",
                           action="store_true")

    dl_parser.add_argument("--destination-path",
                           help="Symlink / copy downloaded files to this directory.",
                           default=None,
                           type=str)
    dl_parser.add_argument("--proxy",
                           help="Specify the HTTP (and FTP) proxy to use in the format: "
                                "[http://][USER:PASSWORD@]HOST[:PORT]",
                           type=str,
                           default=None)
    dl_parser.add_argument("--no-progress",
                           help="Don't show progress bar ...",
                           action="store_true")

    return parser


def _run_download_cli(args, rpc_secret):
    _initial_queued_wait_delay = 10  # seconds
    _polling_delay = 30  # seconds

    if not args.no_aria2c:
        daemon = aria.get_daemon(secret=rpc_secret)
        aria.log_status()

    config_urls = None
    if args.pipeline_config:
        config = parse_pipeline_config(args.pipeline_config)
        config_urls = get_urls_from_pipeline_config(config)

    if config_urls is not None and args.urls:
        logging.error("Can't mix --pipeline-config with URLs specified as command line args.")
        sys.exit(1)

    urls = args.urls
    if config_urls is not None:
        urls = config_urls

    if urls:
        if not args.no_aria2c:
            daemon = aria.get_daemon(secret=rpc_secret)

            async def aria_dl_and_poll():
                gids = aria.download_urls(urls,
                                          cache_path=args.cache_path,
                                          proxy=args.proxy,
                                          concurrent_downloads=args.parallel_downloads)

                if args.queue_then_exit:
                    logger.info('Download GIDs: %s' % (', '.join(gids)))
                    logger.info('Queued downloads, exiting.')
                    sys.exit()

                logging.debug("Waiting a moment for downloaded to become queued.")
                await trio_wait_with_progress(_initial_queued_wait_delay, 1, quiet=args.quiet or args.no_progress)

                aria.log_status()
                while not aria.downloads_finished(gids):
                    await trio_wait_with_progress(_polling_delay, 1, quiet=args.quiet or args.no_progress)

                aria.purge_results()

            trio.run(aria_dl_and_poll)
        else:
            # trio.run(download, urls)
            download_concurrent(urls,
                                args.cache_path,
                                concurrent_downloads=args.parallel_downloads)

        if args.destination_path is not None:
            for url in urls:
                cached = get_url_cached_path(url, args.cache_path)
                filename, _ = find_filename_and_size_from_url(url)
                if tarfile.is_tarfile(cached) and args.untar:
                    logger.info(f"Untarring {cached} ({url})")
                    untar(cached, args.destination_path)
                elif args.copy_from_cache:
                    logger.info(
                        f"Copying {cached} -> "
                        f"{os.path.join(args.destination_path, filename)} ({url})")
                    create_copy_from_cache(url,
                                           args.destination_path,
                                           args.cache_path,
                                           filename=filename)
                else:
                    logger.info(f"Creating symlink {cached} <- "
                                f"{os.path.join(args.destination_path, filename)} ({url})")
                    create_symlink_to_cache(url,
                                            args.destination_path,
                                            args.cache_path,
                                            filename=filename)


def main():
    parser = add_commandline_args(argparse.ArgumentParser())
    args = parser.parse_args()

    if args.quiet:
        logging.basicConfig(format='%(levelname)s: %(asctime)s -- %(message)s', level=logging.WARNING)
        logger.setLevel(logging.INFO)
    elif args.vvv:
        logging.basicConfig(format='%(levelname)s: %(asctime)s -- %(message)s', level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    if args.command == 'expire-cache':
        try:
            clean_cache(args.cache_path, cache_age=args.cache_age)
        except Exception as ex:
            logger.exception(ex)
            sys.exit(1)
        sys.exit()

    rpc_secret_path = os.path.join(args.cache_path, '.aria2_rpc_secret')
    rpc_secret = get_secret_key(rpc_secret_path)

    if args.command == 'kill_aria':
        logger.info("Stopping all downloads and shuttting down Aria2c.")
        daemon = aria.get_daemon(secret=rpc_secret)
        try:
            aria.stop_all()
        except Exception as ex:
            sys.exit(1)
        try:
            os.remove(rpc_secret_path)
        except (IOError, FileNotFoundError) as ex:
            logger.warning(f"Unable to remove RPC secret file at {rpc_secret_path} (wrong permissions or missing).")
        sys.exit()

    if args.command == 'download':
        if (not args.pipeline_config and
                not args.urls):
            parser.print_help()
            sys.exit(1)

        _run_download_cli(args, rpc_secret)


if __name__ == '__main__':
    main()
