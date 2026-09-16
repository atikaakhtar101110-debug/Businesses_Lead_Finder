"""
Lightweight, no-paid-API-required company enrichment. Looks for
employee-count / team-size signals in scraped text (e.g. LinkedIn
badge text, "our team of 50+", careers page language). This is a
heuristic layer that runs *before* the LLM-based enrichment agent
adds its own inference, so the agent has real signal to work with.
"""
import re
from utils.logger import get_logger

logger = get_logger("tools.company_enrichment")

EMPLOYEE_PATTERNS = [
    re.compile(r"team of (?:over )?(\d{1,5})\+?", re.I),
    re.compile(r"(\d{1,5})\+?\s+employees", re.I),
    re.compile(r"(\d{1,5})\+?\s+people", re.I),
    re.compile(r"(\d{1,5})-(\d{1,5})\s+employees", re.I),
]

LINKEDIN_REGEX = re.compile(r"https?://(www\.)?linkedin\.com/company/[a-zA-Z0-9\-_%]+", re.I)


class CompanyEnrichment:
    def guess_employee_count(self, *texts: str) -> str:
        for text in texts:
            if not text:
                continue
            for pattern in EMPLOYEE_PATTERNS:
                match = pattern.search(text)
                if match:
                    return "-".join(match.groups()) if len(match.groups()) > 1 else match.group(1)
        return ""

    def find_linkedin_url(self, *texts: str) -> str:
        for text in texts:
            if not text:
                continue
            match = LINKEDIN_REGEX.search(text)
            if match:
                return match.group(0)
        return ""
