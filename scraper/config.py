"""
Configuration for the Defence Intelligence Bot.
Field mappings, extraction prompts, and API settings.
"""
import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o"

EXCEL_COLUMNS = [
    "Company Name", "Country", "Field", "Activity", "Locations", "Founded",
    "N° employees", "Key people", "Type Ownership", "Confidence Index",
    "Business Overview", "Business relationships", "Capability", "Notes",
]

EXTRACTION_SYSTEM_PROMPT = """You are a defence industry analyst. Given raw web content about a company,
extract structured information and return ONLY a JSON object with these exact keys:

{
    "company_name": "string",
    "country": "string",
    "field": "string (domains separated by ' / ')",
    "activity": "string (1-2 sentences)",
    "locations": "string (City, Country)",
    "founded": "string (year)",
    "employees": "string (number or range)",
    "key_people": "string (CEO, key executives)",
    "type_ownership": "string (Public/Private/State-owned/JV)",
    "business_overview": "string (3 bullet points max)",
    "business_relationships": "string (key partners, customers)",
    "capability": "string (core industrial capabilities)",
    "notes": "string (additional context, sources)"
}

Be factual. If information is unavailable, use null or 'Unknown'. Never fabricate data."""

SCRAPE_TIMEOUT = 15
MAX_RETRIES = 3
USER_AGENT = "Mozilla/5.0 (research bot)"

SEARCH_TEMPLATES = [
    "{company} defence capabilities overview",
    "{company} revenue employees annual report",
    "{company} partnerships contracts defence",
]
