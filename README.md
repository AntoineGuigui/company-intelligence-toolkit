# 🔍 Company Intelligence Toolkit

**End-to-end competitive intelligence platform for company analysis.**

Built during an industrial strategy alternance — this toolkit automates the full pipeline from web research to structured company profiles, replacing hours of manual work per company with a one-click workflow.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-000000?logo=flask)
![OpenAI](https://img.shields.io/badge/GPT--4o-Extraction-412991?logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🏗️ Architecture

```
[Intelligence Generator]  →  DataBase.xlsx  →  [Profile Generator]  →  PPTX slides
  (Streamlit + GPT-4o)                           (this repo)
```

This repo is **Module 2** of a two-part pipeline — it reads a structured Excel database and generates formatted PowerPoint company profiles via a Flask web interface.

Use the [Company Intelligence Generator](https://github.com/AntoineGuigui/company-intelligence) (Module 1) to automatically populate `DataBase.xlsx` via web scraping + LLM extraction.

---

## 📸 Screenshots

| Main Interface | Company Detail | Admin Panel |
|---|---|---|
| ![](docs/screenshots/interface.png) | ![](docs/screenshots/detail.png) | ![](docs/screenshots/admin.png) |

## 🚀 Quick Start

### Prerequisites

- Python 3.8+

### Installation

```bash
git clone https://github.com/AntoineGuigui/company-intelligence-toolkit.git
cd company-intelligence-toolkit
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run

```bash
python app.py
# Open http://localhost:8080
```

---

## 📁 Project Structure

```
company-intelligence-toolkit/
│
├── app.py                          # Flask server + field clustering + batch generation
├── company_profile_generator.py    # PowerPoint generation engine
│
├── templates/
│   ├── index.html                  # Main 3-column dark-themed interface
│   └── admin.html                  # Field clustering admin panel
│
├── static/                         # Static assets
├── docs/
│   └── DATABASE_SCHEMA.md          # Excel column reference
│
├── requirements.txt
├── run_windows.bat                 # One-click launcher for Windows
├── .env.example
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

## 🖥️ Company Profile Generator

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

This tool was built in a **fully offline Windows environment** (no internet access). Design constraints:

- No external package downloads at runtime
- No CDN or external font loading
- All assets (logos, flags, templates) stored locally
- Shared via a network drive — no Git on the work machine

---

## 📊 Impact

- **80+ companies** profiled across **9 countries**
- **~3h → ~10min** per company profile (end-to-end)
- Profiles used for strategic briefings
- Adopted by colleagues in the industrial strategy team

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.8+, Flask |
| Frontend | Vanilla HTML/CSS/JS (zero frameworks) |
| NLP/Clustering | scikit-learn (TF-IDF, Agglomerative), scipy |
| Excel I/O | pandas, openpyxl |
| PowerPoint | python-pptx, Pillow |
| PPTX merging | lxml (ZIP-level XML manipulation) |

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
