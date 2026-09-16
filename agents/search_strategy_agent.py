"""
SearchStrategyAgent
--------------------
Takes a free-text description of the ideal customer profile (ICP) and
a target location, and produces a diverse set of search queries -
both general web-search queries and Google Maps/Places-style queries -
to maximize discovery coverage in the next stage.
"""
from agents.llm_utils import call_claude_json
from utils.logger import get_logger

logger = get_logger("agents.search_strategy")

SYSTEM_PROMPT = """You are a B2B lead-generation strategist. Given a description of an
ideal customer profile (ICP) and a target location, generate a focused set of search
queries that will surface real, matching businesses online.

Return a JSON object with exactly this shape:
{
  "web_search_queries": ["...", "..."],   // 4-6 queries for a general web search engine
  "maps_queries": ["...", "..."]          // 3-5 short queries suited to Google Maps/Places
                                            // (e.g. "digital marketing agency", "boutique law firm")
}
Keep maps_queries short (2-5 words, no location - location is applied separately).
Make web_search_queries specific enough to surface company websites and directories,
not just news articles."""


class SearchStrategyAgent:
    def generate_queries(self, icp_description: str, location: str) -> dict:
        user_prompt = (
            f"Ideal customer profile:\n{icp_description}\n\n"
            f"Target location: {location or 'no specific location - global/remote is fine'}"
        )
        result = call_claude_json(SYSTEM_PROMPT, user_prompt, max_tokens=800)

        if not result or "web_search_queries" not in result:
            logger.warning("Falling back to naive query generation.")
            base = icp_description.strip().split(".")[0][:80]
            result = {
                "web_search_queries": [
                    f"{base} companies {location}".strip(),
                    f"{base} businesses {location} contact".strip(),
                ],
                "maps_queries": [base],
            }

        logger.info(
            "Generated %d web queries and %d maps queries",
            len(result.get("web_search_queries", [])),
            len(result.get("maps_queries", [])),
        )
        return result
