"""
Canonical Lead schema. Every agent reads/writes this shape so the
pipeline stays consistent from discovery through to the final export.
"""
from typing import Optional
from pydantic import BaseModel, Field


class Lead(BaseModel):
    # Identity
    company_name: str = ""
    website: str = ""
    domain: str = ""

    # Contact / location
    address: str = ""
    city: str = ""
    country: str = ""
    phone: str = ""
    email: str = ""
    linkedin_url: str = ""

    # Firmographics
    industry: str = ""
    description: str = ""
    employee_count_estimate: str = ""

    # People
    decision_maker_name: str = ""
    decision_maker_title: str = ""

    # Pipeline metadata
    source: str = ""                       # e.g. "google_maps", "web_search"
    qualified: Optional[bool] = None
    qualification_reason: str = ""
    score: float = 0.0
    score_breakdown: str = ""
    verified: bool = False
    verification_notes: str = ""
    notes: str = ""

    class Config:
        extra = "allow"

    def to_row(self) -> dict:
        """Flat dict for Excel export, in a sensible column order."""
        return {
            "Company Name": self.company_name,
            "Website": self.website,
            "Industry": self.industry,
            "Description": self.description,
            "Employees (est.)": self.employee_count_estimate,
            "Decision Maker": self.decision_maker_name,
            "Title": self.decision_maker_title,
            "Email": self.email,
            "Phone": self.phone,
            "Address": self.address,
            "City": self.city,
            "Country": self.country,
            "LinkedIn": self.linkedin_url,
            "Score": self.score,
            "Qualified": self.qualified,
            "Qualification Reason": self.qualification_reason,
            "Verified": self.verified,
            "Verification Notes": self.verification_notes,
            "Source": self.source,
            "Notes": self.notes,
        }
