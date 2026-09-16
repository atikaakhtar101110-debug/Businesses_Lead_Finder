"""
Finds emails two ways:
1. Regex scan over scraped page text/HTML (free, no API).
2. Optional Hunter.io domain-search fallback for higher hit rate.
"""
import re
import requests
from utils.config import config
from utils.logger import get_logger

logger = get_logger("tools.email_finder")

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Filter out obvious junk / image-asset false positives commonly picked up from HTML
JUNK_SUBSTRINGS = ["example.com", "sentry.io", ".png", ".jpg", ".jpeg", ".gif", ".svg", "wixpress.com"]

HUNTER_ENDPOINT = "https://api.hunter.io/v2/domain-search"


class EmailFinder:
    def __init__(self, hunter_api_key: str = None):
        self.hunter_api_key = hunter_api_key or config.hunter_api_key

    def find_in_text(self, *texts: str) -> list:
        found = set()
        for text in texts:
            if not text:
                continue
            for match in EMAIL_REGEX.findall(text):
                email = match.lower().strip().strip(".")
                if any(junk in email for junk in JUNK_SUBSTRINGS):
                    continue
                found.add(email)
        return sorted(found)

    def find_via_hunter(self, domain: str) -> list:
        if not self.hunter_api_key or not domain:
            return []
        try:
            resp = requests.get(
                HUNTER_ENDPOINT,
                params={"domain": domain, "api_key": self.hunter_api_key, "limit": 5},
                timeout=config.request_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            emails = [e["value"] for e in data.get("data", {}).get("emails", []) if e.get("value")]
            return emails
        except Exception as e:  # noqa: BLE001
            logger.debug("Hunter.io lookup failed for %s: %s", domain, e)
            return []

    def best_email(self, domain: str, scraped_texts: list) -> str:
        """Prefer emails found on-site; fall back to Hunter.io; prefer role-based
        addresses (info@/contact@/sales@) as a safe generic contact point."""
        on_site = self.find_in_text(*scraped_texts)
        candidates = on_site or self.find_via_hunter(domain)
        if not candidates:
            return ""

        priority = ["sales@", "contact@", "info@", "hello@", "support@"]
        for prefix in priority:
            for email in candidates:
                if email.startswith(prefix):
                    return email
        return candidates[0]
