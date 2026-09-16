"""
OutputAgent
-----------
Writes the final lead list to Excel and produces a short natural-
language executive summary of the run (counts, top picks, gaps)
for display in the UI/CLI.
"""
import os
from datetime import datetime
from agents.llm_utils import call_claude
from tools.excel import ExcelExporter
from utils.config import config
from utils.logger import get_logger

logger = get_logger("agents.output")

SYSTEM_PROMPT = """You write a short, plain-English executive summary (4-6 sentences) of a
lead-generation run for a busy salesperson. Mention how many leads were found, how many
were fully verified/contact-ready, call out the top 2-3 leads by name, and mention any
notable gaps (e.g. many missing emails) if relevant. No headers, no bullet points, no markdown."""


class OutputAgent:
    def __init__(self, exporter: ExcelExporter = None):
        self.exporter = exporter or ExcelExporter()

    def generate_report(self, leads: list, icp_description: str, filename: str = None) -> dict:
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"leads_{timestamp}.xlsx"

        path = os.path.join(config.output_dir, filename)
        self.exporter.export_leads(leads, path)

        top = sorted(leads, key=lambda l: l.score, reverse=True)[:5]
        top_summary = "\n".join(
            f"- {l.company_name} (score {l.score}, verified={l.verified}, email={l.email or 'none'})"
            for l in top
        )
        verified_count = sum(1 for l in leads if l.verified)

        stats_prompt = (
            f"ICP: {icp_description}\n\n"
            f"Total leads: {len(leads)}\n"
            f"Fully verified: {verified_count}\n\n"
            f"Top leads:\n{top_summary if top_summary else 'none'}"
        )

        try:
            summary = call_claude(SYSTEM_PROMPT, stats_prompt, max_tokens=400)
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not generate LLM summary: %s", e)
            summary = (
                f"Found {len(leads)} leads, {verified_count} fully verified. "
                f"See the exported spreadsheet for full details."
            )

        logger.info("Report generated: %s", path)
        return {
            "excel_path": path,
            "summary": summary,
            "total_leads": len(leads),
            "verified_leads": verified_count,
        }
