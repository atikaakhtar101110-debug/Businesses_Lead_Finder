"""
Central configuration for Business Lead Finder.
Loads settings from environment variables / .env file and exposes
a single `config` object used across agents and tools.
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    # LLM
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    claude_model: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"))

    # Search / Maps / Enrichment providers
    serpapi_api_key: str = field(default_factory=lambda: os.getenv("SERPAPI_API_KEY", ""))
    google_maps_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_MAPS_API_KEY", ""))
    hunter_api_key: str = field(default_factory=lambda: os.getenv("HUNTER_API_KEY", ""))

    # App behavior
    max_leads: int = field(default_factory=lambda: int(os.getenv("MAX_LEADS", "25")))
    request_timeout: int = field(default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT", "15")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    output_dir: str = field(default_factory=lambda: os.getenv("OUTPUT_DIR", "output"))

    def validate(self) -> list:
        """Returns a list of human-readable warnings about missing/optional config."""
        warnings = []
        if not self.anthropic_api_key:
            warnings.append("ANTHROPIC_API_KEY is not set. Agents that reason over data will fail.")
        if not self.serpapi_api_key:
            warnings.append("SERPAPI_API_KEY is not set. Web search discovery will be skipped.")
        if not self.google_maps_api_key:
            warnings.append("GOOGLE_MAPS_API_KEY is not set. Maps/Places discovery will be skipped.")
        if not self.hunter_api_key:
            warnings.append("HUNTER_API_KEY is not set. Email discovery will fall back to on-site scraping only.")
        return warnings


config = Config()
