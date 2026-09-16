"""
LeadWorkflow
------------
Orchestrates the full multi-agent pipeline end to end:

  1. SearchStrategyAgent  - turn ICP + location into search queries
  2. DiscoveryAgent       - run queries against web search + Maps, dedupe
  3. ExtractionAgent      - scrape sites, pull structured company facts
  4. EnrichmentAgent      - find emails, LinkedIn, decision-maker info
  5. QualificationAgent   - filter out clear ICP mismatches
  6. ScoringAgent         - rank remaining leads 0-100
  7. VerificationAgent    - sanity-check contact details
  8. OutputAgent          - export to Excel + write a summary

Each stage accepts/returns `list[Lead]` (except the first, which
returns the query-strategy dict), so stages can be swapped, tested,
or re-ordered independently.
"""
from typing import Callable, Optional
from agents import (
    SearchStrategyAgent,
    DiscoveryAgent,
    ExtractionAgent,
    EnrichmentAgent,
    QualificationAgent,
    ScoringAgent,
    VerificationAgent,
    OutputAgent,
)
from utils.config import config
from utils.logger import get_logger

logger = get_logger("workflow")


class LeadWorkflow:
    def __init__(self):
        self.search_strategy_agent = SearchStrategyAgent()
        self.discovery_agent = DiscoveryAgent()
        self.extraction_agent = ExtractionAgent()
        self.enrichment_agent = EnrichmentAgent()
        self.qualification_agent = QualificationAgent()
        self.scoring_agent = ScoringAgent()
        self.verification_agent = VerificationAgent()
        self.output_agent = OutputAgent()

    def run(
        self,
        icp_description: str,
        location: str = "",
        max_leads: int = None,
        drop_unqualified: bool = True,
        on_stage: Optional[Callable[[str, dict], None]] = None,
    ) -> dict:
        """
        Runs the full pipeline.

        on_stage: optional callback(stage_name, info_dict) fired after each stage,
                  useful for driving a progress bar in a UI (see app.py).
        """
        max_leads = max_leads or config.max_leads

        def notify(stage, **info):
            logger.info("Stage complete: %s | %s", stage, info)
            if on_stage:
                on_stage(stage, info)

        strategy = self.search_strategy_agent.generate_queries(icp_description, location)
        notify("search_strategy", queries=strategy)

        leads = self.discovery_agent.discover(strategy, location, max_leads)
        notify("discovery", count=len(leads))

        leads = self.extraction_agent.extract(leads)
        notify("extraction", count=len(leads))

        leads = self.enrichment_agent.enrich(leads, icp_description)
        notify("enrichment", count=len(leads))

        leads = self.qualification_agent.qualify(leads, icp_description)
        if drop_unqualified:
            leads = [l for l in leads if l.qualified]
        notify("qualification", count=len(leads))

        leads = self.scoring_agent.score(leads, icp_description)
        notify("scoring", count=len(leads))

        leads = self.verification_agent.verify(leads)
        notify("verification", count=len(leads))

        leads = leads[:max_leads]

        report = self.output_agent.generate_report(leads, icp_description)
        notify("output", **{k: v for k, v in report.items() if k != "summary"})

        return {
            "leads": leads,
            "excel_path": report["excel_path"],
            "summary": report["summary"],
            "total_leads": report["total_leads"],
            "verified_leads": report["verified_leads"],
        }
