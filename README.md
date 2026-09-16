# Business Lead Finder

A multi-agent pipeline that turns a plain-English ideal customer profile (ICP)
into a ranked, verified spreadsheet of real business leads with contact info.

```
ICP + location
     │
     ▼
1. SearchStrategyAgent   → generates web-search & Google Maps queries
2. DiscoveryAgent        → runs queries, dedupes candidate businesses
3. ExtractionAgent       → scrapes sites, extracts industry/description
4. EnrichmentAgent       → finds emails, LinkedIn, decision-maker info
5. QualificationAgent    → filters out clear ICP mismatches
6. ScoringAgent          → ranks leads 0-100 (fit + contact completeness)
7. VerificationAgent     → sanity-checks emails/websites
8. OutputAgent           → exports .xlsx + writes an executive summary
```

## Setup

```bash
git clone <this-repo>
cd business_lead_finder
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add your keys:

| Variable | Required? | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Powers every reasoning/extraction/scoring step |
| `SERPAPI_API_KEY` | Recommended | Web search discovery ([serpapi.com](https://serpapi.com)) |
| `GOOGLE_MAPS_API_KEY` | Recommended | Local business discovery via Places API |
| `HUNTER_API_KEY` | Optional | Fallback email discovery ([hunter.io](https://hunter.io)) |

The app runs without the optional keys, just with reduced discovery/enrichment coverage
(warnings are shown in the UI).

## Run

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints, describe your ICP (e.g. *"Small e-commerce
brands, 10-50 employees, selling apparel, who'd benefit from a Shopify loyalty app"*),
set a location, and click **Find Leads**. Results appear in-app and as a downloadable
`.xlsx` in `output/`.

### CLI / scripting use

You can also drive the pipeline directly, without Streamlit:

```python
from workflow.lead_workflow import LeadWorkflow

workflow = LeadWorkflow()
result = workflow.run(
    icp_description="Boutique law firms (5-30 lawyers) that need better client intake software",
    location="Lahore, Pakistan",
    max_leads=25,
)

print(result["summary"])
print(f"Saved to {result['excel_path']}")
```

## Project layout

```
app.py                     Streamlit UI entrypoint
agents/                    One file per pipeline stage (see diagram above)
tools/                     Thin wrappers around external APIs / scraping / Excel export
workflow/lead_workflow.py  Orchestrates the agents end to end
models/lead_schema.py      Canonical Lead data model (pydantic)
utils/                     Config loading, logging, deduplication helpers
output/                    Generated .xlsx files land here (git-ignored)
```

## Notes & known limitations

- Web scraping is best-effort: JS-heavy sites, sites behind bot protection, or sites
  with unusual link structures may return little/no text. The pipeline degrades
  gracefully in this case rather than failing.
- Email discovery is heuristic (regex over scraped text, optional Hunter.io fallback).
  Always double-check before mass outreach, and respect each site's terms of service
  and applicable anti-spam laws (e.g. CAN-SPAM, GDPR) when using discovered contacts.
- The Google Maps Places "Text Search" + "Place Details" calls used here incur cost
  beyond Google's free tier at higher volumes - check current Google Cloud pricing.
- Swap `tools/search_api.py` for a different provider (Bing, Tavily, Google Custom
  Search) by keeping the same `search(query, num_results) -> list[dict]` interface.

## License

Use, modify, and extend freely for your own projects.
