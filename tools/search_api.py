"""
Thin wrapper around SerpAPI's Google Search endpoint.
Swap this out for Bing/Google Custom Search/Tavily etc. if you prefer -
just keep the `search()` return shape the same: list[dict] with
keys: title, link, snippet.
"""
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.config import config
from utils.logger import get_logger

logger = get_logger("tools.search_api")

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


class SearchAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.serpapi_api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def search(self, query: str, num_results: int = 10) -> list:
        if not self.enabled:
            logger.warning("SERPAPI_API_KEY not configured; skipping web search for query=%r", query)
            return []

        params = {
            "q": query,
            "api_key": self.api_key,
            "num": num_results,
            "engine": "google",
        }
        resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=config.request_timeout)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("organic_results", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        logger.info("search(%r) -> %d results", query, len(results))
        return results
