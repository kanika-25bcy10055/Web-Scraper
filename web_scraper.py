# Note: Run pip install in a separate cell with !pip or %pip
# !pip install requests beautifulsoup4

import argparse
import json
import re
import sys
import textwrap
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/117.0.0.0 Safari/537.36"
)

def scrape_movies(url: str, timeout: int = 10, headers: dict = None) -> List[Dict[str, str]]:
    """Scrape movie summaries (title, rating, link, snippet, raw_html) from the given URL.

    Returns a list of dicts. Always returns a list (empty if nothing found).
    """
    if headers is None:
        headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(resp.content, "html.parser")

    # Try several likely selectors for movie blocks
    selectors = [
        "div.movie-item",
        "article.movie",
        "li.movie",
        "div.movie",
        "div[class*='movie']",
        "article",
        "li",
    ]

    movie_listings = []
    for sel in selectors:
        found = soup.select(sel)
        if found:
            movie_listings = found
            break

    if not movie_listings:
        headings = soup.find_all(re.compile(r"^h[1-6]$"))
        candidates = []
        for h in headings:
            parent = h.find_parent()
            if parent and parent not in candidates:
                candidates.append(parent)
        movie_listings = candidates

    movies_data = []
    for movie in movie_listings:
        title = None
        title_selectors = [".movie-title", "h2", "h3", "a.title", "a", ".title"]
        for ts in title_selectors:
            t_el = movie.select_one(ts)
            if t_el and t_el.get_text(strip=True):
                title = t_el.get_text(strip=True)
                break

        if not title:
            text = movie.get_text(separator=" ", strip=True)
            title = text.split("\n")[0].strip() if text else "N/A"

        rating = None
        rating_selectors = [".movie-rating", ".rating", ".score", "span[class*='rating']", "div[class*='rating']"]
        for rs in rating_selectors:
            r_el = movie.select_one(rs)
            if r_el and r_el.get_text(strip=True):
                rating = r_el.get_text(strip=True)
                break

        if not rating:
            text = movie.get_text(separator=" ", strip=True)
            m = re.search(r"([0-9]+(\.[0-9]+)?)/10|([0-9]+(\.[0-9]+)?)(?: out of 10)", text)
            if m:
                rating = m.group(0)
        if not rating:
            rating = "N/A"

        # Link heuristics
        link = None
        a = movie.select_one("a[href]")
        if a and a.get("href"):
            link = urljoin(url, a.get("href"))

        # Snippet: first paragraph or short text
        snippet = None
        p = movie.find("p")
        if p and p.get_text(strip=True):
            snippet = p.get_text(strip=True)
        else:
            text = movie.get_text(separator=" ", strip=True)
            snippet = text[:300] + ("..." if len(text) > 300 else "") if text else ""

        movies_data.append({
            "Title": title or "N/A",
            "Rating": rating,
            "Link": link,
            "Snippet": snippet or "",
            "RawHTML": str(movie),
        })

    return movies_data

def fetch_movie_details_from_page(url: str, timeout: int = 10, headers: dict = None) -> Dict[str, Optional[str]]:
    """Fetch additional details from a movie detail page (if available).

    Returns a dict with keys like Summary, Year, Duration, Additional.
    """
    if headers is None:
        headers = {"User-Agent": DEFAULT_USER_AGENT}

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except requests.exceptions.RequestException:
        return {"Summary": None, "Year": None, "Duration": None, "Additional": None}

    soup = BeautifulSoup(resp.content, "html.parser")
    # Summary: first meaningful paragraph
    summary = None
    for p in soup.find_all("p"):
        t = p.get_text(strip=True)
        if t and len(t) > 20:
            summary = t
            break

    full_text = soup.get_text(separator=" ", strip=True)
    year = None
    m = re.search(r"(19\d{2}|20\d{2})", full_text)
    if m:
        year = m.group(0)

    duration = None
    m2 = re.search(r"(\d{1,3})\s?min|(\d{1,3})\s?minutes", full_text, re.I)
    if m2:
        duration = m2.group(0)

    return {"Summary": summary, "Year": year, "Duration": duration, "Additional": None}

def extract_details_from_rawhtml(raw_html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(raw_html, "html.parser")
    # try similar extraction as detail page
    summary = None
    p = soup.find("p")
    if p and p.get_text(strip=True):
        summary = p.get_text(strip=True)
    full_text = soup.get_text(separator=" ", strip=True)
    year = None
    m = re.search(r"(19\d{2}|20\d{2})", full_text)
    if m:
        year = m.group(0)
    duration = None
    m2 = re.search(r"(\d{1,3})\s?min|(\d{1,3})\s?minutes", full_text, re.I)
    if m2:
        duration = m2.group(0)
    return {"Summary": summary, "Year": year, "Duration": duration, "Additional": None}

def interactive_menu(movies: List[Dict[str, str]], base_url: str):
    if not movies:
        print("No movies to display.")
        return

    print("\nFound the following movies:\n")
    for i, m in enumerate(movies, start=1):
        print(f"[{i}] {m['Title']}  |  Rating: {m.get('Rating','N/A')}")
        if m.get("Snippet"):
            print(textwrap.fill(m["Snippet"], width=80))
        print("-" * 60)

    # Only prompt if stdin is a TTY
    if not sys.stdin.isatty():
        print("Input not interactive; skipping selection.")
        return

    while True:
        try:
            choice = input("Enter the movie number for more details (or 0 to exit): ").strip()
            if not choice.isdigit():
                print("Please enter a valid number.")
                continue
            idx = int(choice)
            if idx == 0:
                print("Exiting.")
                break
            if idx < 1 or idx > len(movies):
                print("Number out of range.")
                continue

            selected = movies[idx - 1]
            print(f"\n--- Details for: {selected['Title']} ---")

            if selected.get("Link"):
                details = fetch_movie_details_from_page(selected["Link"]) or {}
                print(f"Link: {selected['Link']}")
            else:
                details = extract_details_from_rawhtml(selected.get("RawHTML",""))

            print(f"Rating: {selected.get('Rating','N/A')}")
            if details.get("Year"):
                print(f"Year: {details.get('Year')}")
            if details.get("Duration"):
                print(f"Duration: {details.get('Duration')}")
            if details.get("Summary"):
                print("\nSummary:\n")
                print(textwrap.fill(details.get("Summary"), width=80))

            print("\n" + ("=" * 60) + "\n")

        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple movie web scraper with interactive details")
    parser.add_argument("url", nargs="?", default="http://publicdomainmovie.net/", help="Target URL to scrape")
    parser.add_argument("--json", "-j", help="Path to save results as JSON")
    parser.add_argument("--no-interactive", action="store_true", help="Do not prompt for movie selection even if interactive")
    args = parser.parse_args()

    print(f"Scraping data from: {args.url}")
    scraped = scrape_movies(args.url)

    if not scraped:
        print("No movie data found or an error occurred.")
        sys.exit(1)

    print("\n--- Scraped Movie Data ---")
    for i, movie in enumerate(scraped, start=1):
        print(f"{i}. Title: {movie['Title']}, Rating: {movie['Rating']}")

    if args.json:
        # Save a JSON-serializable version (omit RawHTML if desired)
        try:
            serializable = [ {k: v for k, v in m.items() if k != 'RawHTML'} for m in scraped ]
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False, indent=2)
            print(f"Results written to {args.json}")
        except OSError as e:
            print(f"Failed to write JSON file: {e}", file=sys.stderr)

    if not args.no_interactive and sys.stdin.isatty():
        interactive_menu(scraped, args.url)

    print("Done.")