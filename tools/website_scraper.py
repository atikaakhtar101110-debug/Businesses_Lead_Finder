"""
Lightweight, polite website scraper. Pulls visible text and common
"contact"/"about"/"team" subpages so downstream agents have enough
context to extract emails, industry, and decision-maker names.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.config import config
from utils.logger import get_logger

logger = get_logger("tools.website_scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BusinessLeadFinderBot/1.0; +https://example.com/bot)"
}

INTERESTING_PATH_KEYWORDS = ["contact", "about", "team", "our-team", "leadership", "people"]


class WebsiteScraper:
    def __init__(self, timeout: int = None):
        self.timeout = timeout or config.request_timeout

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=6))
    def fetch(self, url: str) -> str:
        """Fetch raw HTML for a single URL. Returns '' on failure."""
        if not url:
            return ""
        if not url.startswith("http"):
            url = "https://" + url
        try:
            resp = requests.get(url, headers=HEADERS, timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as e:  # noqa: BLE001
            logger.debug("fetch failed for %s: %s", url, e)
            return ""

    def extract_text(self, html: str, max_chars: int = 6000) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:max_chars]

    def discover_subpages(self, base_url: str, html: str, limit: int = 3) -> list:
        """Find links on the homepage that look like contact/about/team pages."""
        if not html:
            return []
        soup = BeautifulSoup(html, "lxml")
        found = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full = urljoin(base_url, href)
            path = urlparse(full).path.lower()
            if any(kw in path for kw in INTERESTING_PATH_KEYWORDS) and full not in seen:
                seen.add(full)
                found.append(full)
            if len(found) >= limit:
                break
        return found

    def scrape_site(self, url: str) -> dict:
        """
        Scrapes homepage + a few relevant subpages.
        Returns {"url": ..., "homepage_text": ..., "subpages": {url: text}, "raw_html": homepage_html}
        """
        homepage_html = self.fetch(url)
        homepage_text = self.extract_text(homepage_html)
        subpage_urls = self.discover_subpages(url, homepage_html)

        subpages = {}
        for sub_url in subpage_urls:
            html = self.fetch(sub_url)
            if html:
                subpages[sub_url] = self.extract_text(html)

        return {
            "url": url,
            "homepage_text": homepage_text,
            "raw_html": homepage_html,
            "subpages": subpages,
        }
