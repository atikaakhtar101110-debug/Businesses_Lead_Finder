"""
Small shared helper so every agent talks to the LLM the same way and
parses structured JSON output consistently. Not an agent itself -
just infrastructure the agents import.

Uses the OpenAI API. Function names (call_claude / call_claude_json)
are kept as-is even though this now calls OpenAI under the hood, so
none of the eight agent files that import them needed to change.
"""
import json
import re
from openai import OpenAI
from utils.config import config
from utils.logger import get_logger

logger = get_logger("agents.llm_utils")

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not config.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to your .env file.")
        _client = OpenAI(api_key=config.openai_api_key)
    return _client


def call_claude(system: str, user_prompt: str, max_tokens: int = 1500, temperature: float = 0.3) -> str:
    """Single-turn call to the LLM (OpenAI Chat Completions), returns raw text response."""
    client = get_client()
    response = client.chat.completions.create(
        model=config.openai_model,
        max_completion_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
    )
    return (response.choices[0].message.content or "").strip()


def call_claude_json(system: str, user_prompt: str, max_tokens: int = 1500, temperature: float = 0.2):
    """
    Calls the LLM with an instruction to respond ONLY in JSON, then
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
        logger.warning("Failed to parse JSON from LLM response: %s", cleaned[:300])
        return None

