# Project overview

## Purpose

ImpactFlow is a portfolio platform for demonstrating data engineering and business intelligence in a synthetic South African nonprofit scenario. The target organisation coordinates education, healthcare, youth employment, and community development programmes.

## Current deliverable

The current deliverable includes a React dashboard, FastAPI/PostgreSQL metadata and dashboard APIs, and CSV, XLSX, XLS and JSON file imports. Overview defaults to API data; the browser-only CSV and public World Bank population context remain available. The browser demo identity is not authentication. Other unfinished modules remain previews. No individual beneficiary records are modeled. General-purpose pipeline execution is not implemented.

## Phase roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Repository structure, documentation, design system, configuration | Foundation established |
| 1 | React layout, navigation, charts, synthetic overview dashboard | Implemented |
| 2 | FastAPI/PostgreSQL, authentication, core models, and business/dashboard APIs | API and database foundation implemented; authentication and access control removed at user request |
| 3 | Source management and ingestion | File uploads, source management, local Bronze storage, history, and configured REST/PostgreSQL connectors implemented; external connections require local configuration |
| 4 | ETL engine and medallion data lake | Not started |
| 5 | Warehouse, dbt, and M&E indicators | Not started |
| 6 | Airflow and pipeline monitoring | Not started |
| 7 | Data quality and governance | Not started |
| 8 | Power BI documentation and reporting | Not started |
| 9 | Azure deployment, CI/CD, and predictive analytics | Not started |

Later phases require approval before implementation. Integration names in the roadmap describe intended work only. Confirm database connectivity and migrations separately in each configured environment.

## Data safety

Use synthetic demonstration and test data only. Do not add real beneficiary information or children's personal data. The API has no authentication or authorization; anyone who can reach it can read and modify data. Keep it local and do not deploy it publicly.
