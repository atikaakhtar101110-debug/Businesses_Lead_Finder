"""
VerificationAgent
------------------
Final sanity pass before export: checks that the email domain matches
the company website domain, that the website actually responds, and
flags leads missing critical fields - so the exported sheet clearly
shows which rows are safe to act on immediately vs. need a manual
double-check.
"""
import requests
from utils.deduplication import normalize_domain
from utils.config import config
from utils.logger import get_logger

logger = get_logger("agents.verification")


class VerificationAgent:
    def _website_reachable(self, url: str) -> bool:
        if not url:
            return False
        target = url if url.startswith("http") else f"https://{url}"
        try:
            resp = requests.head(target, timeout=config.request_timeout, allow_redirects=True)
            if resp.status_code >= 400:
                # Some servers reject HEAD; retry with a light GET before giving up.
                resp = requests.get(target, timeout=config.request_timeout, stream=True)
            return resp.status_code < 400
        except Exception as e:  # noqa: BLE001
            logger.debug("Website unreachable %s: %s", target, e)
            return False

    def verify(self, leads: list) -> list:
        for lead in leads:
            notes = []

            website_ok = self._website_reachable(lead.website)
            if lead.website and not website_ok:
                notes.append("website did not respond")

            if lead.email:
                email_domain = lead.email.split("@")[-1].lower()
                site_domain = normalize_domain(lead.website)
                if site_domain and email_domain not in site_domain and site_domain not in email_domain:
                    notes.append(f"email domain ({email_domain}) doesn't match site domain ({site_domain})")
            else:
                notes.append("no email found")

            if not lead.phone:
                notes.append("no phone found")

            lead.verified = website_ok and bool(lead.email) and not any(
                "doesn't match" in n for n in notes
            )
            lead.verification_notes = "; ".join(notes) if notes else "all checks passed"

        verified_count = sum(1 for l in leads if l.verified)
        logger.info("Verification: %d/%d leads fully verified", verified_count, len(leads))
        return leads
