"""
EnrichmentAgent
---------------
Fills in contact details (email, LinkedIn, employee estimate) using
the heuristic tools, then asks Claude to infer the most likely
decision-maker title to target for this ICP (e.g. "Head of Marketing"
for a marketing-tools ICP) based on whatever team/about page text was
scraped.
"""
from agents.llm_utils import call_claude_json
from tools.email_finder import EmailFinder
from tools.company_enrichment import CompanyEnrichment
from utils.deduplication import normalize_domain
from utils.logger import get_logger

logger = get_logger("agents.enrichment")

SYSTEM_PROMPT = """You are identifying the most relevant decision-maker at a company for a
specific sales outreach purpose. Given the ideal customer profile (ICP)/offer, and any
team/about page text scraped from the target company's site, return JSON:
{
  "decision_maker_name": "...",   // a real name found in the text, else ""
  "decision_maker_title": "..."   // the actual title found, OR if none found, the most
                                    // likely title to target at this type of company (e.g.
                                    // "Marketing Manager", "Owner", "Head of Operations")
}
Never invent a person's name. Only use decision_maker_name if it is explicitly present
in the provided text."""


class EnrichmentAgent:
    def __init__(self, email_finder: EmailFinder = None, company_enrichment: CompanyEnrichment = None):
        self.email_finder = email_finder or EmailFinder()
        self.company_enrichment = company_enrichment or CompanyEnrichment()

    def enrich(self, leads: list, icp_description: str) -> list:
        for lead in leads:
            scraped_texts = getattr(lead, "_scraped_texts", [])
            domain = lead.domain or normalize_domain(lead.website)
            lead.domain = domain

            if not lead.email:
                lead.email = self.email_finder.best_email(domain, scraped_texts)

            if not lead.linkedin_url:
                lead.linkedin_url = self.company_enrichment.find_linkedin_url(*scraped_texts)

            if not lead.employee_count_estimate:
                lead.employee_count_estimate = self.company_enrichment.guess_employee_count(*scraped_texts)

            if scraped_texts:
                result = call_claude_json(
                    SYSTEM_PROMPT,
                    f"ICP/offer: {icp_description}\n\n"
                    f"Company: {lead.company_name}\n\n"
                    f"Scraped text:\n{' '.join(scraped_texts)[:4000]}",
                    max_tokens=300,
                )
                if result:
                    lead.decision_maker_name = result.get("decision_maker_name", "") or lead.decision_maker_name
                    lead.decision_maker_title = result.get("decision_maker_title", "") or lead.decision_maker_title

        logger.info("Enrichment complete for %d leads", len(leads))
        return leads
