import argparse
import json
import sys
from typing import List, Dict
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/117.0.0.0 Safari/537.36"
)

DEFAULT_URL = "https://publicdomainmovie.net/"

def scrape_movies(url: str, timeout: int = 10, headers: dict = None) -> List[Dict[str, str]]:
    """Scrape movie summaries (title, link, snippet, raw_html) from the given URL."""
    if headers is None:
        headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}", file=sys.stderr)
        return []
    soup = BeautifulSoup(resp.content, "html.parser")
    found_movies = []
    # Adjust selectors as needed to match site structure
    for item in soup.select("div#main-content div.views-row") + soup.select("div.content div.views-row"):
        title = item.select_one("div.title, h3, h2, a")
        link = item.select_one("a[href]")
        snippet = item.select_one("div.field-content, .summary, p") or item.find("p")
        found_movies.append({
            "Title": title.text.strip() if title and title.text.strip() else "",
            "Link": urljoin(url, link.get("href")) if link and link.get("href") else "",
            "Snippet": snippet.text.strip() if snippet and snippet.text.strip() else "",
            "raw_html": str(item)
        })
    # Fallback for less structured content
    if not found_movies:
        for li in soup.select("li"):
            a = li.select_one("a[href]")
            if a and a.text.strip():
                found_movies.append({
                    "Title": a.text.strip(),
                    "Link": urljoin(url, a.get("href")),
                    "Snippet": "",
                    "raw_html": str(li)
                })
    return found_movies

def print_movies_with_description(movies: List[Dict[str, str]]):
    for m in movies:
        title = m['Title']
        snippet = m['Snippet']
        # Skip entirely if both title and snippet are empty
        if title and snippet:
            print(f"{title}: {snippet}\n")
        elif title:
            print(f"{title}\n")
        elif snippet:
            print(f"{snippet}\n")

def print_movies_with_description_lines(movies: List[Dict[str, str]]):
    for m in movies:
        title = m['Title']
        snippet = m['Snippet']
        if title:
            print(f"Title: {title}")
        if snippet:
            print(f"Description: {snippet}")
        if title or snippet:
            print()

def main():
    parser = argparse.ArgumentParser(description="Scrape and list movies from publicdomainmovie.net.")
    parser.add_argument("--url", type=str, default=DEFAULT_URL, help=f"URL to scrape (default: {DEFAULT_URL})")
    parser.add_argument("--colon", action="store_true", help="Show output as Title: Description (single line)")
    args = parser.parse_args()

    movies = scrape_movies(args.url)

    if args.colon:
        print_movies_with_description(movies)
    else:
        print_movies_with_description_lines(movies)

if __name__ == "__main__":
    main()
