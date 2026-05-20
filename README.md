# 🛡️ Defence Intelligence Toolkit

**End-to-end competitive intelligence platform for defence industry analysis.**

Built during an industrial strategy alternance — this toolkit automates the full pipeline from web research to structured company profiles, replacing hours of manual work per company with a one-click workflow.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-000000?logo=flask)
![OpenAI](https://img.shields.io/badge/GPT--4o-Extraction-412991?logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🏗️ Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   Intelligence Bot   │────▶│   Excel Database      │────▶│  Company Profile    │
│   (Web Scraping +    │     │   (DataBase.xlsm)     │     │  Generator (Flask)  │
│    GPT-4o Extraction)│     │                        │     │                     │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
        Module 1                   Shared Data                  Module 2
   scraper/bot.py                                         app.py + templates/
```

Two modules share a common Excel database:

1. **Intelligence Bot** — Scrapes the web for defence company data, uses GPT-4o for structured entity extraction, and populates the Excel database with standardised fields.

2. **Company Profile Generator** — Flask web app that reads the database and generates formatted PowerPoint company profile sheets via a dark-themed three-column interface.

---

## 📸 Screenshots

> _Add screenshots of the Flask interface here: `docs/screenshots/`_

| Main Interface | Company Detail | Admin Panel |
|---|---|---|
| Three-column layout with real-time search | Company card with confidence stars | Field clustering & manual merges |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key (for the Intelligence Bot only — the Profile Generator works fully offline)

### Installation

```bash
git clone https://github.com/AntoineGuigui/defence-intelligence-toolkit.git
cd defence-intelligence-toolkit
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run the Profile Generator (Module 2)

```bash
python app.py
# Open http://localhost:8080
```

### Run the Intelligence Bot (Module 1)

```bash
cp .env.example .env
# Edit .env with your OpenAI API key

python -m scraper.bot --companies "Company A, Company B" --country "India"
python -m scraper.bot --input companies.csv --output DataBase.xlsm
```

---

## 📁 Project Structure

```
defence-intelligence-toolkit/
│
├── scraper/                        # Module 1: Intelligence Bot
│   ├── __init__.py
│   ├── bot.py                      # CLI orchestrator (scrape → extract → write)
│   ├── web_scraper.py              # Web scraping (requests + BeautifulSoup)
│   ├── llm_extractor.py            # GPT-4o structured JSON extraction
│   ├── excel_writer.py             # Append to DataBase.xlsm (openpyxl)
│   └── config.py                   # Prompts, schema, field mappings
│
├── company_profile_generator.py    # Module 2: PowerPoint generation engine
├── app.py                          # Flask server + field clustering + batch generation
│
├── templates/
│   ├── index.html                  # Main 3-column dark-themed interface
│   └── admin.html                  # Field clustering admin panel
│
├── static/                         # Static assets (logos, etc.)
├── docs/
│   └── DATABASE_SCHEMA.md          # Excel column reference
│
├── requirements.txt
├── run_windows.bat                 # One-click launcher for Windows
├── .env.example                    # Environment variables template
├── .gitignore
└── LICENSE
```

**Not in repo** (git-ignored, proprietary):
- `DataBase.xlsm` — Excel database
- `Template.pptx` — PowerPoint template
- `logo/` — Company logo images
- `Flags/` — Country flag images
- `Sorties/` — Generated PowerPoints

---

## 🔧 Module 1 — Intelligence Bot

### What it does

Given a list of company names and countries, the bot:

1. **Scrapes** public web sources (company websites, registries, financial databases)
2. **Extracts** structured data via GPT-4o with a strict JSON schema enforcing field-by-field output
3. **Writes** clean, standardised rows into `DataBase.xlsm`

### Key design decisions

- **Prompt engineering**: Structured system prompt enforces JSON output matching the Excel schema, reducing hallucination
- **Retry logic**: Failed extractions are retried with shortened input
- **Multi-country support**: Tested across 9 countries (Belgium, Brazil, Canada, Denmark, Spain, Greece, India, Norway, Romania) covering 84+ companies

---

## 🖥️ Module 2 — Company Profile Generator

### What it does

A Flask web application that:

1. Reads `DataBase.xlsm` on startup (all sheets: main data + 5 financial sheets)
2. Serves a **three-column dark-themed interface**:
   - **Left**: Searchable company list
   - **Center**: Company detail card with "Generate PPTX" button
   - **Right**: Multi-criteria filters (country, domain, location)
3. Generates PowerPoint profiles from `Template.pptx` with:
   - Company logos & country flags auto-positioned
   - Financial tables (Revenue, EBIT, Net Profit, margins)
   - Confidence Index as red/grey star rating
   - Speaker Notes from database

### Features

- **TF-IDF field clustering**: Activity domains are automatically grouped using TF-IDF (char + word n-grams) + Agglomerative Clustering with cosine distance
- **Manual merge admin panel**: Override automatic clustering at `/admin`
- **Batch country generation**: Generate all profiles for a country into a single merged PPTX (ZIP-level XML merging with lxml)
- **Multi-value field splitting**: Fields separated by `/` are split for per-domain filtering
- **Location normalisation**: Similar location strings grouped automatically
- **Offline-first**: Zero external dependencies — no CDN, no Google Fonts, fully air-gapped

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Main interface |
| `/admin` | GET | Field clustering admin |
| `/api/companies` | GET | All companies with metadata |
| `/api/countries` | GET | Unique country list |
| `/api/fields` | GET | Clustered field values |
| `/api/locations` | GET | Normalised locations |
| `/api/field_clusters` | GET | All fields with cluster mappings |
| `/api/merge_fields` | POST | Merge fields under canonical name |
| `/api/unmerge_field` | POST | Undo a manual merge |
| `/api/generate` | POST | Generate single company PPTX |
| `/api/generate_country` | POST | Generate merged PPTX for country |
| `/api/download/<name>` | GET | Download generated PPTX |

---

## 🏭 Built For

This tool was built in a **fully offline Windows environment** (no internet access) at a defence company. Design constraints:

- No external package downloads at runtime
- No CDN or external font loading
- All assets (logos, flags, templates) stored locally
- Shared via a network drive — no Git on the work machine

---

## 📊 Impact

- **84+ companies** profiled across **9 countries**
- **~3h → ~10min** per company profile (end-to-end)
- Profiles used for **COMEX-level strategic briefings**
- Adopted by colleagues in the industrial strategy team

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.8+, Flask |
| Frontend | Vanilla HTML/CSS/JS (zero frameworks) |
| Data pipeline | requests, BeautifulSoup, OpenAI GPT-4o |
| NLP/Clustering | scikit-learn (TF-IDF, Agglomerative), scipy |
| Excel I/O | pandas, openpyxl |
| PowerPoint | python-pptx, Pillow |
| PPTX merging | lxml (ZIP-level XML manipulation) |

---

## 🔗 Integration with Company Intelligence Generator

This tool is **Module 2** of a two-part pipeline:

```
[Intelligence Generator]  →  DataBase.xlsx  →  [Profile Generator]  →  PPTX slides
  (Streamlit + GPT-4o)                           (this repo)
```

Use the [Company Intelligence Generator](https://github.com/AntoineGuigui/company-intelligence) to automatically populate `DataBase.xlsx` via web scraping + LLM extraction, then this toolkit reads it and generates PowerPoint slides.

---

## ⚠️ Setup Notes

The following files are **not included** in the repository (they contain proprietary data):

| File | What to do |
|---|---|
| `DataBase.xlsm` | Create your own Excel with columns matching [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) |
| `Template.pptx` | Your PowerPoint template with `[Company Name]`, `[Country]`, `[Activity]`, `[Business Overview]`, `[Business relationships]`, `[Capability]` placeholders |
| `logo/` | Company logo images (PNG/JPG), named `company_name.png` |
| `Flags/` | Country flag images, named `country_name.png` |

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 👤 Author

**Antoine Guigui**
CentraleSupélec '26 — Supply Chain & Data Analytics
[LinkedIn](https://www.linkedin.com/in/antoine-guigui-846266132/)
