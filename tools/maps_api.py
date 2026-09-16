"""
Wrapper around Google Maps Places API (Text Search) for local-business
discovery, e.g. "marketing agencies in Lahore".
"""
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.config import config
from utils.logger import get_logger

logger = get_logger("tools.maps_api")

try:
    import googlemaps
except ImportError:  # pragma: no cover
    googlemaps = None


class MapsAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.google_maps_api_key
        self._client = None
        if self.enabled and googlemaps is not None:
            self._client = googlemaps.Client(key=self.api_key)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key) and googlemaps is not None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def search_places(self, query: str, location: str = "", max_results: int = 20) -> list:
        if not self.enabled:
            logger.warning("GOOGLE_MAPS_API_KEY not configured (or googlemaps not installed); skipping maps search")
            return []

        full_query = f"{query} in {location}" if location else query
        places = []
        response = self._client.places(query=full_query)
        places.extend(response.get("results", []))

        # Follow pagination up to max_results
        while response.get("next_page_token") and len(places) < max_results:
            import time
            time.sleep(2)  # Google requires a short delay before the token is valid
            response = self._client.places(query=full_query, page_token=response["next_page_token"])
            places.extend(response.get("results", []))

        results = []
        for place in places[:max_results]:
            details = {}
            try:
                details = self._client.place(
                    place_id=place["place_id"],
                    fields=["name", "formatted_address", "international_phone_number",
                            "website", "url", "business_status"],
                ).get("result", {})
            except Exception as e:  # noqa: BLE001
                logger.debug("place details lookup failed for %s: %s", place.get("name"), e)

            results.append({
                "company_name": details.get("name", place.get("name", "")),
                "address": details.get("formatted_address", place.get("formatted_address", "")),
                "phone": details.get("international_phone_number", ""),
                "website": details.get("website", ""),
                "maps_url": details.get("url", ""),
                "source": "google_maps",
            })

        logger.info("search_places(%r, %r) -> %d results", query, location, len(results))
        return results
