"""
GPT-4o structured extraction module.
Takes raw web content and returns structured company data as JSON.
"""
import json
import logging
from typing import Optional
from openai import OpenAI
from .config import OPENAI_API_KEY, OPENAI_MODEL, EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def extract_company_data(raw_texts: list[str], company_name: str) -> Optional[dict]:
    """Send concatenated raw text to GPT-4o for structured extraction."""
    if not client:
        logger.error("OpenAI client not initialized — check OPENAI_API_KEY")
        return None
    if not raw_texts:
        logger.warning(f"No raw text provided for {company_name}")
        return None
    combined = "\n\n---\n\n".join(raw_texts)
    max_chars = 80_000
    if len(combined) > max_chars:
        combined = combined[:max_chars]
    user_prompt = f"Analyze the following web content about '{company_name}' and extract structured defence industry intelligence.\n\n--- RAW CONTENT ---\n{combined}\n--- END ---"
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": EXTRACTION_SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Extraction failed for {company_name}: {e}")
        return None

def extract_with_retry(raw_texts: list[str], company_name: str, max_retries: int = 2) -> Optional[dict]:
    """Retry extraction with simplified prompt on failure."""
    result = extract_company_data(raw_texts, company_name)
    if result:
        return result
    for attempt in range(max_retries):
        logger.info(f"Retry {attempt + 1}/{max_retries} for {company_name}")
        shortened = [t[:10_000] for t in raw_texts[:2]]
        result = extract_company_data(shortened, company_name)
        if result:
            return result
    return None
