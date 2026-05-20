"""
Defence Intelligence Bot — Main orchestrator.
Pipeline: Company list → Web scraping → GPT-4o extraction → Excel database

Usage:
    python -m scraper.bot --companies "TASL, Tonbo Imaging" --country "India"
    python -m scraper.bot --input companies.csv --output DataBase.xlsm
"""
import argparse, csv, logging, sys
from .web_scraper import scrape_company
from .llm_extractor import extract_with_retry
from .excel_writer import write_to_excel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def process_company(name: str, country: str, output_path: str) -> bool:
    logger.info(f"{'='*60}\nProcessing: {name} ({country})\n{'='*60}")
    scraped = scrape_company(name, country)
    if not scraped["raw_texts"]:
        logger.warning(f"No web content found for {name}")
        return False
    extracted = extract_with_retry(scraped["raw_texts"], name)
    if not extracted:
        return False
    extracted["sources"] = scraped["sources"]
    return write_to_excel(extracted, output_path)

def main():
    parser = argparse.ArgumentParser(description="Defence Intelligence Bot")
    parser.add_argument("--companies", type=str, help="Comma-separated company names")
    parser.add_argument("--country", type=str, default="", help="Country (with --companies)")
    parser.add_argument("--input", type=str, help="CSV file with 'company' and 'country' columns")
    parser.add_argument("--output", type=str, default="DataBase.xlsm", help="Output Excel path")
    args = parser.parse_args()
    if args.input:
        companies = []
        with open(args.input, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                n = row.get("company", row.get("name", "")).strip()
                if n: companies.append((n, row.get("country", "").strip()))
    elif args.companies:
        companies = [(n.strip(), args.country) for n in args.companies.split(",")]
    else:
        parser.error("Provide --companies or --input"); sys.exit(1)
    ok = sum(1 for n, c in companies if process_company(n, c, args.output))
    logger.info(f"DONE — {ok}/{len(companies)} succeeded")

if __name__ == "__main__":
    main()
