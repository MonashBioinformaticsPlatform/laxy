import logging
import os
import re
from fnmatch import fnmatch
from typing import List, Union, Pattern
from contextlib import closing
from urllib.parse import (
    urljoin,
    urlparse,
    urlunparse,
    parse_qs,
    unquote,
    quote,
    quote_plus,
)
from pathlib import Path
import asyncio
import concurrent.futures
import requests
from bs4 import BeautifulSoup
import webdav3.client

from django.conf import settings

from .storage.http_remote import is_archive_link

logger = logging.getLogger(__name__)

# BACKEND = 'splash'
# BACKEND = 'simple'
# BACKEND = 'pyppeteer'
BACKEND = getattr(settings, "WEB_SCRAPER_BACKEND", "simple")
SPLASH_HOST = getattr(settings, "WEB_SCRAPER_SPLASH_HOST", "http://localhost:8050")


def render_page(url: str, backend=None) -> str:
    if backend is None:
        backend = BACKEND

    if backend == "simple":
        return render_simple(url)
    elif backend == "splash":
        return render_with_splash(url)
    # elif backend == 'pyppeteer':
    #     return render_with_pyppeteer(url)
    else:
        raise ValueError(f"Unknown HTML rendering backend: {backend}")


def render_simple(url: str, max_size: int = 10 * 1024 * 1024):
    from .tasks.download import request_with_retries

    try:
        with closing(request_with_retries("GET", url, allow_redirects=True)) as resp:
            resp.raise_for_status()

            text = []
            chunk_size = 1024
            size = 0
            for chunk in resp.iter_content(chunk_size=chunk_size, decode_unicode=True):
                text.append(chunk)
                size += chunk_size
                if size > max_size:
                    raise MemoryError(f"File is too large (> {max_size} bytes)")

            try:
                text = "".join(text)
                return text
            except TypeError as ex:
                raise ValueError(f"File doesn't look like sane HTML")

    except BaseException as e:
        raise e


def render_with_splash(
    url: str,
    fallback_backend=None,
    timeout: float = 10,
    wait: float = 0.5,
    fetch_images: bool = False,
) -> str:
    fetch_images = {True: "1", False: "0"}[fetch_images]
    try:
        text = requests.get(
            f"{SPLASH_HOST}/render.html?"
            f"url={quote(url)}&"
            f"timeout={timeout}&"
            f"wait={wait}&"
            f"images={fetch_images}"
        ).text
    except requests.exceptions.ConnectionError as ex:
        if fallback_backend is not None:
            text = render_page(url, backend=fallback_backend)
        else:
            raise ex

    # logger.debug(resp.text)
    return text


"""
# pyppeteer backend currently isn't working (see render_with_pyppeteer comments below)
#
# For BACKEND='pyppeteer", you'll need to install pyppeteer:
# pip3 install pyppeteer
#
# Pre-install Chromium:
# pyppeteer-install
#
# Required packages for libX11-xcb.so.1:
# sudo apt-get install gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 \
# libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 \
# libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 \
# libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release \
# xdg-utils wget


from pyppeteer import launch

async def _render_in_headless_chromium(url):
    browser = await launch()
    page = await browser.newPage()
    await page.goto(url, waitUntil='networkidle0')
    # await page.screenshot({'path': 'screenshot.png'})
    html = await page.content()
    await browser.close()
    return html


# TODO: This doesn't work in Django due to async issues with the main thread
#  Potential fixes?: https://stackoverflow.com/questions/41594266/asyncio-with-django/46140106
def render_with_pyppeteer(url: str):
    loop = asyncio.new_event_loop()
    # loop = asyncio.SelectorEventLoop()
    asyncio.set_event_loop(loop)
    # future = asyncio.ensure_future(main(url))
    coroutine = _render_in_headless_chromium(url)
    try:
        # task, _ = loop.run_until_complete(asyncio.wait([main(url)]))
        task = loop.run_until_complete(coroutine)
    finally:
        loop.close()
    return task
    # return task.pop().result()
    # return asyncio.get_event_loop().run_until_complete(main(url))
"""


def _make_url_absolute(href, url):
    if url is not None and "://" not in href:
        return urljoin(url, href)
    return href


def parse_links(text: str, url=None) -> List[str]:
    """
    Parses <a href=""> links from HTML. Only returns non-empty non-anchor link href values.
    If `url` is provided, converts relative URLs to absolute URLs, otherwise returns href values unmodified.
    :param text:
    :type text:
    :param url:
    :type url:
    :return:
    :rtype:
    """
    soup = BeautifulSoup(text, "html.parser")

    links = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if href is None:
            continue

        u = str(href)
        if u.strip() == "" or u.startswith("#"):
            continue

        # convert to full URL, not just path
        links.append(_make_url_absolute(u, url))

    return links


def is_apache_index_page(url, text):
    soup = BeautifulSoup(text, "html.parser")
    title = soup.select("title")
    footer = soup.select("address")
    logger.info(f"{title}, {footer}")
    if (
        title
        and footer
        and len(title)
        and len(footer)
        and title[0].text.startswith("Index of")
        and footer[0].text.startswith("Apache/")
    ):
        return True

    return False


def parse_simple_index_links(
    text: str,
    url=None,
    url_regex: Union[str, Pattern] = "^https?://|^ftp://",
    ignore_regex: Union[str, Pattern] = "\/\?C=.;O=.",
    fileglob: str = "*",
) -> List[dict]:
    """
    Parse the text of a simple HTML index page (eg Apache) for links.
    """

    if isinstance(url_regex, str):
        url_regex = re.compile(url_regex)
    if isinstance(ignore_regex, str):
        ignore_regex = re.compile(ignore_regex)

    links = parse_links(text, url=url)

    file_urls = []
    dir_urls = []
    # For simple Apache-style index pages ...
    links = parse_links(text, url)
    for link in links:
        if url_regex.search(link) and not ignore_regex.search(link):
            if urlparse(link).path.endswith("/"):
                dir_urls.append(link)
            else:
                file_urls.append(link)

    listing = []
    for i in file_urls:
        name = Path(urlparse(i).path).name
        if not fnmatch(name, fileglob):
            continue
        listing.append(
            dict(
                type="file",
                name=unquote(name),
                location=i,
                tags=["archive"] if is_archive_link(name) else [],
            )
        )
    for i in dir_urls:
        name = Path(urlparse(i).path).name
        listing.append(
            dict(
                type="directory",
                name=unquote(name),
                location=f'{i.rstrip("/")}/',
                tags=[],
            )
        )
    return listing


def parse_nextcloud_links(text: str, url=None) -> List[dict]:
    """
    Parse Nextcloud / ownCloud shared folder page (without using WebDAV).

    :param text: Rendered page text (must have be rendered with Javascript enabled, eg via Splash)
    :type text: str
    :param url: The URL to the page
    :type url: str
    :return: A list of dicts describing the files and directories
    :rtype: List[dict]
    """
    soup = BeautifulSoup(text, "html.parser")

    links = []
    for d in soup.select('tr[data-type="dir"]'):
        name = d.get("data-file")
        first_link = d.select("a[href]")[0]
        u = _make_url_absolute(first_link.get("href"), url)
        u = f"{u}?path=/{name}"
        links.append(dict(type="directory", name=unquote(name), location=u, tags=[]))

    for f in soup.select('tr[data-type="file"]'):
        name = f.get("data-file")
        first_link = f.select("a[href]")[0]
        href = first_link.get("href")
        if href is None:
            continue

        u = str(href)
        if u.strip() == "" or u.startswith("#"):
            continue

        # convert to full URL, not just path
        u = _make_url_absolute(u, url)
        links.append(
            dict(
                type="file",
                name=unquote(name),
                location=u,
                tags=["archive"] if is_archive_link(name) else [],
            )
        )

    return links


def parse_nextcloud_webdav(text: Union[str, None] = None, url=None) -> List[dict]:
    """
    Return the file and directory listing for a ownCloud/Nextcloud WebDAV shared link,
    via WebDAV. `text` is ignored but included for link parser plugin compatibility.

    :param text: Usused, included for link parser plugin compatibility.
    :type text: str
    :param url: The public share URL (eg https://somenextcloud.net/s/lnSmyyug1fexY8l)
    :type url: str
    :return: A list of dicts describing the files and directories
    :rtype: List[dict]
    """

    _base_url = urlparse(url)
    base_url = urlunparse((_base_url.scheme, _base_url.netloc, "", "", "", ""))

    webdav_server = f"{base_url}/public.php/webdav/"
    # eg, for the URL "https://somenextcloud.net/s/lnSmyyug1fexY8l", share_id = 'lnSmyyug1fexY8l'
    share_id = list(os.path.split(urlparse(url).path)).pop()
    path = parse_qs(urlparse(url).query).get("path", ["/"])[0].strip("/")
    _pathparts = list(os.path.split(path))
    last_dir_in_path = "%s/" % _pathparts[-1:][0].strip("/")
    up_dir = "/".join(_pathparts[:-1])

    options = {
        "webdav_hostname": webdav_server,
        "webdav_login": share_id,
        "webdav_password": "null",
    }
    client = webdav3.client.Client(options)
    ls = client.list(remote_path=path)
    is_top_level = path in ["/", ""] and "webdav/" in ls

    links = []

    # Add a '..' if we aren't in the top-level directory
    if not is_top_level:
        links.append(
            dict(
                type="directory",
                name="..",
                location=f"{base_url}/s/{share_id}?path=/{quote(up_dir)}",
                tags=[],
            )
        )
    for name in ls:
        if is_top_level and name == "webdav/":
            # Don't add the root 'webdav/' directory
            continue

        if name == last_dir_in_path:
            # The final directory in remote_path is listed by name (equivalent to '.' from ls),
            # be we don't want to see it
            continue

        if name.endswith("/"):
            name = name.rstrip("/")
            full_path = os.path.join(path, name)
            links.append(
                dict(
                    type="directory",
                    name=name,
                    location=f"{base_url}/s/{share_id}?path=/{quote(full_path)}",
                    tags=[],
                )
            )
        else:
            links.append(
                dict(
                    type="file",
                    name=name,
                    location=f"{base_url}/s/{share_id}/download?path=/{quote(path)}&files={quote(name)}",
                    tags=["archive"] if is_archive_link(name) else [],
                )
            )

    return links


if __name__ == "__main__":
    # eg:
    # python -m laxy_backend.scraping "https://cloudstor.aarnet.edu.au/plus/s/lnSmyyug1fexY8l" pyppeteer

    import sys

    url = sys.argv[1]
    if len(sys.argv) >= 3:
        BACKEND = sys.argv[2]

    html = render_page(url)
    # html = render_with_splash(url)
    # html = render_with_pyppeteer(url)
    print(html)
