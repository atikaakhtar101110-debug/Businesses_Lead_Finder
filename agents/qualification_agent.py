"""
QualificationAgent
-------------------
Judges each lead against the ICP description and marks it
qualified / not qualified with a short reason, so obviously
mismatched leads (wrong industry, clearly too small/large, etc.)
get filtered out before scoring.
"""
from agents.llm_utils import call_claude_json
from utils.logger import get_logger

logger = get_logger("agents.qualification")

SYSTEM_PROMPT = """You are qualifying a sales lead against an ideal customer profile (ICP).
Given the ICP and the facts known about a company, decide if it's a plausible fit.
Return JSON:
{
  "qualified": true or false,
  "reason": "one short sentence explaining the decision"
}
Be reasonably lenient - if there isn't enough information to be sure, lean toward
qualified=true so the lead can be reviewed manually rather than dropped silently.
Only mark qualified=false when there is a clear, specific mismatch with the ICP."""


class QualificationAgent:
    def qualify(self, leads: list, icp_description: str) -> list:
        qualified_leads = []
        for lead in leads:
            if not lead.company_name:
                continue  # extraction failed entirely - drop silently

            facts = (
                f"Company: {lead.company_name}\n"
                f"Industry: {lead.industry}\n"
                f"Description: {lead.description}\n"
                f"Employees (est.): {lead.employee_count_estimate}\n"
                f"Location: {lead.city}, {lead.country}"
            )
            result = call_claude_json(
                SYSTEM_PROMPT,
                f"ICP:\n{icp_description}\n\nCompany facts:\n{facts}",
                max_tokens=200,
            )

            if result and "qualified" in result:
                lead.qualified = bool(result["qualified"])
                lead.qualification_reason = result.get("reason", "")
            else:
                lead.qualified = True
                lead.qualification_reason = "Could not evaluate automatically; included for manual review."

            qualified_leads.append(lead)

        kept = [l for l in qualified_leads if l.qualified]
        logger.info("Qualification: %d/%d leads passed", len(kept), len(qualified_leads))
        return qualified_leads
