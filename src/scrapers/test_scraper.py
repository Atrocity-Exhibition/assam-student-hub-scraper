import requests

from bs4 import BeautifulSoup


def run():
    url = "https://example.com"

    response = requests.get(
        url,
        timeout=10,
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    title = soup.title.text

    print(
        f"Scraped title: {title}"
    )
