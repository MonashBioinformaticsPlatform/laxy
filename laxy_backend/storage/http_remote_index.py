from typing import List, Tuple, Pattern, Union
from urllib.parse import urljoin
import re
import requests
from bs4 import BeautifulSoup


def grab_links(url: str,
               regex: Union[str, Pattern] = '^https?://|^ftp://',
               ignore: str = '\/\?C=.;O=.') -> Tuple[List[str], List[str]]:
    """
    Parses a remote HTTP(s) index page containing links, returns
    a list of the links, filtered by provided `regex`. Works best
    with simple HTML pages of links, like the default Apache directory
    listing page.

    :param url: The index page URL.
    :type url: str
    :param regex: A regular expression (as compiled regex or string) that links
                  must match.
    :type regex: str | Pattern
    :param ignore: Ignore URLs matching this regex pattern
                   (compiled regex or string)
    :type ignore: str | Pattern
    :return: The filtered list of links (URLs) on the page, as a tuple. First
             element is the list (presumed) to be links to downloadable files,
             the second is a list of (presumed) 'directories' that are likely
             to lead to additional index pages.
    :rtype: Tuple[List[str], List[str]]
    """
    if isinstance(regex, str):
        regex = re.compile(regex)
    if isinstance(ignore, str):
        ignore = re.compile(ignore)

    try:
        text = requests.get(url).text
    except BaseException as e:
        raise e

    soup = BeautifulSoup(text, 'html.parser')

    file_urls = []
    dir_urls = []
    for a in soup.find_all('a'):
        href = a.get('href')
        u = str(href)
        if href is not None and "://" not in href:
            # convert to full URL, not just path
            u = urljoin(url, href)
        if regex.search(u) and not ignore.search(u):
            if u.endswith('/'):
                dir_urls.append(u)
            else:
                file_urls.append(u)

    return file_urls, dir_urls
