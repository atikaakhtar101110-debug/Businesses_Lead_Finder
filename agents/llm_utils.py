"""
Small shared helper so every agent talks to Claude the same way and
parses structured JSON output consistently. Not an agent itself -
just infrastructure the agents import.
"""
import json
import re
import anthropic
from utils.config import config
from utils.logger import get_logger

logger = get_logger("agents.llm_utils")

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not config.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        _client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    return _client


def call_claude(system: str, user_prompt: str, max_tokens: int = 1500, temperature: float = 0.3) -> str:
    """Single-turn call to Claude, returns raw text response."""
    client = get_client()
    response = client.messages.create(
        model=config.claude_model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    parts = [block.text for block in response.content if getattr(block, "type", "") == "text"]
    return "\n".join(parts).strip()


def call_claude_json(system: str, user_prompt: str, max_tokens: int = 1500, temperature: float = 0.2):
    """
    Calls Claude with an instruction to respond ONLY in JSON, then
    robustly parses the result (stripping markdown fences if present).
    Returns None if parsing fails (caller should handle the fallback).
    """
    strict_system = (
        f"{system}\n\nRespond with ONLY valid JSON. No preamble, no explanation, "
        "no markdown code fences - just the raw JSON value."
    )
    raw = call_claude(strict_system, user_prompt, max_tokens=max_tokens, temperature=temperature)
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to salvage a JSON array/object embedded in extra text
        match = re.search(r"(\[.*\]|\{.*\})", cleaned, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        logger.warning("Failed to parse JSON from Claude response: %s", cleaned[:300])
        return None
