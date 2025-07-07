#!/usr/bin/env python

# TODO: Filesender links of use:
# - https://filesender.org/software/
# - https://github.com/filesender/filesender/blob/master/scripts/client/filesender.py
# - https://support.aarnet.edu.au/hc/en-us/articles/235972948-FileSender-API
# - https://docs.filesender.org/filesender/v2.0/rest/#signed-request

import argparse
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

def download_html(url: str) -> str:
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def parse_html(html_content: str) -> List[Dict]:
    soup = BeautifulSoup(html_content, "html.parser")
    files_data = []

    for file_div in soup.find_all("div", class_="file"):
        file_info = {
            "filename": file_div.get("data-name"),
            "size": file_div.get("data-size"),
            "direct_link": file_div.find("span", class_="directlink")
            .get_text(strip=True)
            .replace("Direct Link: ", ""),
        }

        token_match = re.search(r"token=([0-9a-f-]+)", file_info["direct_link"])
        file_info["token"] = token_match.group(1) if token_match else None
        files_data.append(file_info)

    return files_data

def main(url: str):
    html_content = download_html(url)
    files_data = parse_html(html_content)
    print(files_data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and parse HTML to extract file information."
    )
    parser.add_argument("url", help="URL of the HTML page to be parsed")
    args = parser.parse_args()
    main(args.url)
