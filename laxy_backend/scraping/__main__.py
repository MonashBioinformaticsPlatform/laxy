"""
CLI: python -m laxy_backend.scraping <url> [backend]

Example:
    python -m laxy_backend.scraping "https://cloudstor.aarnet.edu.au/plus/s/lnSmyyug1fexY8l" pyppeteer
"""

import sys

from laxy_backend.scraping import render_page


def main() -> None:
    url = sys.argv[1]
    backend = sys.argv[2] if len(sys.argv) >= 3 else None
    html = render_page(url, backend=backend)
    print(html)


if __name__ == "__main__":
    main()
