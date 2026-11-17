# ImpactFlow

**ImpactFlow — Enterprise Data Engineering & Intelligence Platform**

Transforming Operational Data into Actionable Intelligence.

ImpactFlow is a staged portfolio project for demonstrating how operational data can be collected, validated, governed, modelled, and turned into programme intelligence. The scenario is a South African nonprofit organisation supporting education, healthcare, youth employment, and community development.

## Current status

**Phase 1 foundation:** a responsive dark React dashboard and navigable module design previews using synthetic development data. No API, database, authentication, pipeline execution, or external integration is implemented yet. All module views are previews, not operational tools; dashboard values must not be interpreted as live organisational data.

## Start the frontend

Requirements: Node.js 20.19+ or 22.12+ and npm.

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`).

Other frontend commands:

```powershell
npm run build
npm run lint
npm test
```

## Implemented in this phase

- React, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Axios, Lucide React, Recharts, and Framer Motion foundation.
- Responsive dark layout, collapsible grouped navigation, module previews, navigation/execution search, and demo notification and account menus.
- Six animated KPI cards and six charts: pipeline runs, execution status, data quality, programme targets, ingestion, and beneficiary reach.
- Searchable, sortable, filterable, paginated demo execution table with CSV export and synthetic snapshot refresh.
- Date range changes the pipeline-run and ingestion charts; other metrics retain their stated periods. Comparisons and activity are illustrative.
- Seeded synthetic data generation covering all nine South African provinces; supply a reference date as well as a seed for repeatable timestamps.
- Starter architecture documentation and contributor instructions.

## Planned platform architecture

The target architecture is a React/TypeScript application with a Python/FastAPI service, PostgreSQL warehouse, and progressively introduced ingestion/ETL, medallion storage, dbt, Airflow, governance, monitoring, and Power BI documentation. Those services will be implemented in later phases; none are represented as operational by the current UI.

See [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) and [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) for phase status and diagrams.
