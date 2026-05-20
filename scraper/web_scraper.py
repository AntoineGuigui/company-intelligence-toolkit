"""
Web scraping utilities for defence company research.
Fetches public web pages and extracts raw text content.
"""
import time
import logging
from typing import Optional
import requests
from bs4 import BeautifulSoup
from .config import SCRAPE_TIMEOUT, MAX_RETRIES, USER_AGENT, SEARCH_TEMPLATES

logger = logging.getLogger(__name__)

def search_company(company_name: str, country: str = "") -> list[str]:
    """Build search query strings for a given company."""
    return [t.format(company=f"{company_name} {country}".strip()) for t in SEARCH_TEMPLATES]

def fetch_page(url: str, retries: int = MAX_RETRIES) -> Optional[str]:
    """Fetch a web page and return cleaned text content."""
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=SCRAPE_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines)
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    logger.error(f"All {retries} attempts failed for {url}")
    return None

def scrape_company(company_name: str, country: str = "") -> dict:
    """
    Scrape multiple sources for a company and return combined raw text.
    
    ⚠️  TEMPLATE — Replace the search implementation below with your own
    (e.g. Google Custom Search API, SerpAPI, or direct URL construction).
    """
    queries = search_company(company_name, country)
    raw_texts = []
    sources = []
    for query in queries:
        # ── REPLACE WITH YOUR SEARCH IMPLEMENTATION ──
        # Example:
        #   urls = google_search(query, num_results=3)
        #   for url in urls:
        #       text = fetch_page(url)
        #       if text:
        #           raw_texts.append(text)
        #           sources.append(url)
        pass
    return {"company": company_name, "country": country, "raw_texts": raw_texts, "sources": sources}
