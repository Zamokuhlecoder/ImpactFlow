# Project overview

## Purpose

ImpactFlow is a portfolio platform for demonstrating data engineering and business intelligence in a synthetic South African nonprofit scenario. The target organisation coordinates education, healthcare, youth employment, and community development programmes.

## Current deliverable

Phase 2 provides the browser-based dark React dashboard and navigable design previews from Phase 1, plus a FastAPI service foundation with PostgreSQL configuration and liveness/readiness endpoints. The dashboard still generates synthetic examples for records, sources, pipeline history, data-quality trends, programme targets, and beneficiaries across the nine provinces; it is not connected to the API. The API has no business-data endpoints, models, or migrations. The interface identifies its snapshot as demonstration data and its other modules as non-operational previews.

## Phase roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Repository structure, documentation, design system, configuration | Foundation established |
| 1 | React layout, navigation, charts, synthetic overview dashboard | Implemented |
| 2 | FastAPI and PostgreSQL foundation (health checks and migration scaffolding) | Implemented; PostgreSQL runtime not verified |
| 3 | Source management and ingestion | Not started |
| 4 | ETL engine and medallion data lake | Not started |
| 5 | Warehouse, dbt, and M&E indicators | Not started |
| 6 | Airflow and pipeline monitoring | Not started |
| 7 | Data quality and governance | Not started |
| 8 | Power BI documentation and reporting | Not started |
| 9 | Azure deployment, CI/CD, and predictive analytics | Not started |

Later phases require approval before implementation. Integration names in the roadmap describe intended work only. Local PostgreSQL startup and database-backed readiness require Docker/PostgreSQL and have not been verified in this environment.

## Data safety

Use synthetic, reproducible test data only. Do not add real beneficiary information or children's personal data. Treat privacy, security, and POPIA design as future implementation requirements, not as controls already provided by this frontend.
