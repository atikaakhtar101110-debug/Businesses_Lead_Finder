"""
ScoringAgent
------------
Produces a 0-100 fit/priority score per lead by combining cheap,
deterministic signals (do we have an email? a name? a website?) with
an LLM judgment of how well the company matches the ICP. Rule-based
signals keep the score stable and explainable; the LLM component
captures nuance rule-based logic would miss.
"""
from agents.llm_utils import call_claude_json
from utils.logger import get_logger

logger = get_logger("agents.scoring")

SYSTEM_PROMPT = """You are scoring how well a company fits an ideal customer profile (ICP),
purely on strategic/business fit (ignore contact-completeness - that's scored separately).
Return JSON:
{
  "fit_score": <integer 0-100>,
  "rationale": "one short sentence"
}"""

# Deterministic "reachability" signals, weighted to total 40 points max.
CONTACT_WEIGHTS = {
    "email": 15,
    "phone": 10,
    "website": 5,
    "decision_maker_name": 10,
}


class ScoringAgent:
    def _contact_score(self, lead) -> int:
        score = 0
        if lead.email:
            score += CONTACT_WEIGHTS["email"]
        if lead.phone:
            score += CONTACT_WEIGHTS["phone"]
        if lead.website:
            score += CONTACT_WEIGHTS["website"]
        if lead.decision_maker_name:
            score += CONTACT_WEIGHTS["decision_maker_name"]
        return score

    def score(self, leads: list, icp_description: str) -> list:
        for lead in leads:
            contact_score = self._contact_score(lead)  # up to 40

            facts = (
                f"Company: {lead.company_name}\n"
                f"Industry: {lead.industry}\n"
                f"Description: {lead.description}\n"
                f"Employees (est.): {lead.employee_count_estimate}"
            )
            result = call_claude_json(
                SYSTEM_PROMPT,
                f"ICP:\n{icp_description}\n\nCompany facts:\n{facts}",
                max_tokens=200,
            )

            if result and "fit_score" in result:
                fit_score = max(0, min(100, int(result["fit_score"])))
                rationale = result.get("rationale", "")
            else:
                fit_score = 50
                rationale = "Default score - LLM fit evaluation unavailable."

            # Fit score is scaled to 60 points max, contact completeness fills the other 40.
            final_score = round((fit_score * 0.6) + contact_score, 1)
            lead.score = final_score
            lead.score_breakdown = (
                f"fit={fit_score}/100 (weighted 60%), contact_completeness={contact_score}/40. {rationale}"
            )

        leads.sort(key=lambda l: l.score, reverse=True)
        logger.info("Scoring complete for %d leads", len(leads))
        return leads
