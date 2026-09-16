"""
Business Lead Finder - Streamlit UI

Run with:
    streamlit run app.py
"""
import os
import pandas as pd
import streamlit as st

from utils.config import config
from workflow.lead_workflow import LeadWorkflow

st.set_page_config(page_title="Business Lead Finder", page_icon="🎯", layout="wide")

STAGES = [
    ("search_strategy", "Planning search strategy"),
    ("discovery", "Discovering candidate businesses"),
    ("extraction", "Extracting company details from websites"),
    ("enrichment", "Finding emails & decision-makers"),
    ("qualification", "Qualifying against your ICP"),
    ("scoring", "Scoring & ranking leads"),
    ("verification", "Verifying contact details"),
    ("output", "Building your spreadsheet"),
]
STAGE_ORDER = [s[0] for s in STAGES]


def main():
    st.title("🎯 Business Lead Finder")
    st.caption("Multi-agent pipeline: search strategy → discovery → extraction → enrichment → qualification → scoring → verification → export")

    warnings = config.validate()
    if warnings:
        with st.expander("⚠️ Configuration warnings", expanded=True):
            for w in warnings:
                st.warning(w)
            st.markdown("Copy `.env.example` to `.env` and fill in your API keys.")

    with st.form("lead_search_form"):
        icp_description = st.text_area(
            "Describe your ideal customer profile (ICP)",
            placeholder="e.g. Small e-commerce brands (10-50 employees) selling apparel, "
                        "who would benefit from a custom Shopify app for loyalty rewards.",
            height=120,
        )
        col1, col2 = st.columns(2)
        with col1:
            location = st.text_input("Target location (city, region, or country)", placeholder="e.g. Lahore, Pakistan")
        with col2:
            max_leads = st.number_input("Max leads to return", min_value=5, max_value=100, value=config.max_leads, step=5)

        drop_unqualified = st.checkbox("Drop leads that don't clearly match the ICP", value=True)
        submitted = st.form_submit_button("🔍 Find Leads", use_container_width=True)

    if submitted:
        if not icp_description.strip():
            st.error("Please describe your ideal customer profile first.")
            return

        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def on_stage(stage_name, info):
            idx = STAGE_ORDER.index(stage_name) if stage_name in STAGE_ORDER else 0
            progress_bar.progress((idx + 1) / len(STAGE_ORDER))
            label = dict(STAGES).get(stage_name, stage_name)
            status_text.info(f"{label}... ({info.get('count', '')} leads so far)" if "count" in info else f"{label}...")

        workflow = LeadWorkflow()
        try:
            with st.spinner("Running the lead-finding pipeline - this can take a few minutes..."):
                result = workflow.run(
                    icp_description=icp_description,
                    location=location,
                    max_leads=int(max_leads),
                    drop_unqualified=drop_unqualified,
                    on_stage=on_stage,
                )
        except RuntimeError as e:
            st.error(str(e))
            return
        except Exception as e:  # noqa: BLE001
            st.error(f"Pipeline failed: {e}")
            return

        status_text.empty()
        progress_bar.progress(1.0)

        st.success(f"Found {result['total_leads']} leads ({result['verified_leads']} fully verified).")
        st.markdown("### Summary")
        st.write(result["summary"])

        rows = [lead.to_row() for lead in result["leads"]]
        df = pd.DataFrame(rows)
        st.markdown("### Leads")
        st.dataframe(df, use_container_width=True)

        if os.path.exists(result["excel_path"]):
            with open(result["excel_path"], "rb") as f:
                st.download_button(
                    "⬇️ Download Excel",
                    data=f,
                    file_name=os.path.basename(result["excel_path"]),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )


if __name__ == "__main__":
    main()
