"""
DiscoveryAgent
--------------
Runs the queries produced by SearchStrategyAgent against the web
search tool and the Google Maps tool, normalizes the raw hits into
partial Lead dicts, and deduplicates them.
"""
from models.lead_schema import Lead
from tools.search_api import SearchAPI
from tools.maps_api import MapsAPI
from utils.deduplication import dedupe_leads, normalize_domain
from utils.logger import get_logger

logger = get_logger("agents.discovery")


class DiscoveryAgent:
    def __init__(self, search_api: SearchAPI = None, maps_api: MapsAPI = None):
        self.search_api = search_api or SearchAPI()
        self.maps_api = maps_api or MapsAPI()

    def _from_maps(self, maps_queries: list, location: str, max_results: int) -> list:
        candidates = []
        per_query = max(3, max_results // max(len(maps_queries), 1))
        for q in maps_queries:
            for place in self.maps_api.search_places(q, location, max_results=per_query):
                candidates.append(Lead(
                    company_name=place.get("company_name", ""),
                    website=place.get("website", ""),
                    domain=normalize_domain(place.get("website", "")),
                    address=place.get("address", ""),
                    phone=place.get("phone", ""),
                    source="google_maps",
                    notes=place.get("maps_url", ""),
                ))
        return candidates

    def _from_web_search(self, web_queries: list, max_results: int) -> list:
        candidates = []
        per_query = max(3, max_results // max(len(web_queries), 1))
        for q in web_queries:
            for hit in self.search_api.search(q, num_results=per_query):
                link = hit.get("link", "")
                if not link:
                    continue
                candidates.append(Lead(
                    company_name=hit.get("title", "")[:120],
                    website=link,
                    domain=normalize_domain(link),
                    description=hit.get("snippet", ""),
                    source="web_search",
                ))
        return candidates

    def discover(self, strategy: dict, location: str, max_leads: int) -> list:
        maps_candidates = self._from_maps(strategy.get("maps_queries", []), location, max_leads)
        web_candidates = self._from_web_search(strategy.get("web_search_queries", []), max_leads)

        all_candidates = maps_candidates + web_candidates
        deduped = dedupe_leads(all_candidates)

        logger.info(
            "Discovery: %d from maps, %d from web search, %d after dedup",
            len(maps_candidates), len(web_candidates), len(deduped),
        )
        return deduped[:max_leads * 2]  # keep some headroom for later filtering stages
