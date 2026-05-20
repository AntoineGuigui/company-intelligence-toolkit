# Database Schema — DataBase.xlsm

## Main Sheet: `DataBase`

| Column | Type | Description |
|---|---|---|
| Company Name | string | Official company name |
| Country | string | Country of headquarters |
| Field | string | Activity domains, separated by `/` |
| Activity | string | Description of main activities |
| Locations | string | HQ and key locations |
| Founded | string | Year of establishment |
| N° employees | string | Employee count or range |
| Key people | string | CEO, key executives |
| Type Ownership | string | Public / Private / State-owned / JV |
| Confidence Index | int (1-5) | Data reliability rating |
| Business Overview | text | Summary of business model |
| Business relationships | text | Key partners, customers, alliances |
| Capability | text | Core industrial capabilities |
| Notes | text | Additional context, analyst notes |

## Financial Sheets

Each financial sheet has the same structure:

| Column | Type |
|---|---|
| Company | string (must match `Company Name` in DataBase) |
| 2020, 2021, 2022, ... | float (year columns) |

**Financial sheets:** `Revenue`, `EBIT`, `Net Profit`, `EBIT Margin`, `Net Profit Margin`

Values are in EUR millions. Margins are percentages (e.g. `12.5` = 12.5%).
