"""
Wrapper around Geoapify's Places API for local-business discovery,
e.g. "marketing agencies in Lahore". Geoapify is used instead of
Google Places because it has a genuinely free tier (3,000 credits/day,
commercial use allowed) with no credit card or billing account
required to get a key - see https://www.geoapify.com/places-api/

This module makes plain HTTP calls via `requests`, so there's no
extra SDK dependency (unlike the old googlemaps client, which also
validated API key *format* client-side and crashed the whole app on
startup if the key was missing/malformed - this version fails soft
instead).
"""
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from utils.config import config
from utils.logger import get_logger

logger = get_logger("tools.maps_api")

GEOCODE_ENDPOINT = "https://api.geoapify.com/v1/geocode/search"
PLACES_ENDPOINT = "https://api.geoapify.com/v2/places"

# A reasonable default search radius (meters) around the geocoded location
# when the caller doesn't need anything more precise than "in this city".
DEFAULT_RADIUS_METERS = 20000


class MapsAPI:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.geoapify_api_key

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _geocode(self, location: str):
        """Turns a free-text location ('Lahore, Pakistan') into lat/lon."""
        if not location:
            return None
        resp = requests.get(
            GEOCODE_ENDPOINT,
            params={"text": location, "apiKey": self.api_key, "limit": 1},
            timeout=config.request_timeout,
        )
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            return None
        lon, lat = features[0]["geometry"]["coordinates"]
        return lat, lon

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def search_places(self, query: str, location: str = "", max_results: int = 20) -> list:
        if not self.enabled:
            logger.warning("GEOAPIFY_API_KEY not configured; skipping maps/places search")
            return []

        params = {
            "apiKey": self.api_key,
            "categories": self._guess_category(query),
            "name": query,
            "limit": max_results,
        }

        coords = self._geocode(location) if location else None
        if coords:
            lat, lon = coords
            params["filter"] = f"circle:{lon},{lat},{DEFAULT_RADIUS_METERS}"
            params["bias"] = f"proximity:{lon},{lat}"
        elif location:
            logger.debug("Could not geocode location %r; searching without a geographic filter", location)

        try:
            resp = requests.get(PLACES_ENDPOINT, params=params, timeout=config.request_timeout)
            resp.raise_for_status()
        except requests.HTTPError as e:  # noqa: BLE001
            logger.warning("Geoapify places search failed for %r: %s", query, e)
            return []

        features = resp.json().get("features", [])
        results = []
        for feature in features[:max_results]:
            props = feature.get("properties", {})
            results.append({
                "company_name": props.get("name", ""),
                "address": props.get("formatted", ""),
                "phone": props.get("contact", {}).get("phone", "") if isinstance(props.get("contact"), dict) else "",
                "website": props.get("website", "") or props.get("datasource", {}).get("raw", {}).get("website", ""),
                "maps_url": props.get("place_id", ""),
                "source": "geoapify",
            })

        logger.info("search_places(%r, %r) -> %d results", query, location, len(results))
        return results

    def _guess_category(self, query: str) -> str:
        """
        Geoapify uses a fixed category taxonomy (commercial.*, office.*, etc.)
        rather than free-text business types like Google. We fall back to a
        broad 'commercial' category and rely on the `name` param (fuzzy
        matched against place names) to do the real filtering - good enough
        for lead-gen discovery without hand-mapping every possible ICP to a
        specific Geoapify category.
        See the full category list: https://apidocs.geoapify.com/docs/places/#categories
        """
        return "commercial,office,service"
