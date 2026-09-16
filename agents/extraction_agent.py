"""
ExtractionAgent
---------------
For each candidate lead with a website, scrapes the site and uses
Claude to extract clean structured facts (industry, description,
better company name) from the raw page text.
"""
from agents.llm_utils import call_claude_json
from tools.website_scraper import WebsiteScraper
from utils.logger import get_logger

logger = get_logger("agents.extraction")

SYSTEM_PROMPT = """You are extracting structured company information from raw website text.
Given the text scraped from a company's homepage (and possibly an about/contact page),
return a JSON object with exactly this shape:
{
  "company_name": "...",     // the real/official company name, cleaned up
  "industry": "...",         // e.g. "Digital Marketing Agency", "SaaS - HR Tech"
  "description": "...",      // 1-2 sentence plain-English summary of what they do
  "city": "...",             // best-guess city if mentioned, else ""
  "country": "..."           // best-guess country if mentioned, else ""
}
If the text is empty, junk, or clearly not a real business site, set company_name to "".
Do not invent facts that aren't supported by the text."""


class ExtractionAgent:
    def __init__(self, scraper: WebsiteScraper = None):
        self.scraper = scraper or WebsiteScraper()

    def extract(self, leads: list) -> list:
        enriched = []
        for lead in leads:
            if not lead.website:
                enriched.append(lead)
                continue

            scraped = self.scraper.scrape_site(lead.website)
            combined_text = scraped["homepage_text"]
            for sub_text in scraped["subpages"].values():
                combined_text += " " + sub_text

            if not combined_text.strip():
                logger.debug("No text scraped for %s, keeping as-is", lead.website)
                lead.notes = (lead.notes + " | site unreachable during extraction").strip(" |")
                enriched.append(lead)
                continue

            result = call_claude_json(
                SYSTEM_PROMPT,
                f"Website: {lead.website}\n\nScraped text:\n{combined_text[:5000]}",
                max_tokens=500,
            )

            if result and result.get("company_name"):
                lead.company_name = result.get("company_name") or lead.company_name
                lead.industry = result.get("industry", "") or lead.industry
                lead.description = result.get("description", "") or lead.description
                lead.city = result.get("city", "") or lead.city
                lead.country = result.get("country", "") or lead.country

            # Stash raw scraped text on the lead object (not exported) for the enrichment stage
            setattr(lead, "_scraped_texts", [combined_text] + list(scraped["subpages"].values()))
            enriched.append(lead)

        logger.info("Extraction complete for %d leads", len(enriched))
        return enriched
