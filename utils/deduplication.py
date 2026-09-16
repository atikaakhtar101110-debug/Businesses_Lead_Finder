"""
Deduplication helpers. Leads are considered duplicates if they share
a normalized domain, a normalized phone number, or an identical
(normalized) company name + address pair.
"""
import re
import tldextract


def normalize_domain(url: str) -> str:
    if not url:
        return ""
    ext = tldextract.extract(url)
    if not ext.domain:
        return ""
    return f"{ext.domain}.{ext.suffix}".lower().strip()


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    return re.sub(r"\D", "", phone)


def normalize_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = re.sub(r"\b(inc|llc|ltd|corp|co|group|company)\b", "", name)
    return re.sub(r"\s+", " ", name).strip()


def dedupe_leads(leads: list) -> list:
    """
    Accepts a list of dict-like leads (or objects with attribute access via .get / getattr)
    and returns a deduplicated list, keeping the most complete record when duplicates are found.
    """
    seen_keys = {}

    def get(lead, field_):
        if isinstance(lead, dict):
            return lead.get(field_, "")
        return getattr(lead, field_, "")

    def completeness(lead):
        if isinstance(lead, dict):
            return sum(1 for v in lead.values() if v)
        return sum(1 for v in vars(lead).values() if v)

    for lead in leads:
        domain = normalize_domain(get(lead, "website"))
        phone = normalize_phone(get(lead, "phone"))
        name_key = normalize_name(get(lead, "company_name"))

        key = domain or phone or name_key
        if not key:
            key = f"__unkeyed_{id(lead)}"

        if key not in seen_keys:
            seen_keys[key] = lead
        else:
            # Keep whichever record has more populated fields
            if completeness(lead) > completeness(seen_keys[key]):
                seen_keys[key] = lead

    return list(seen_keys.values())
