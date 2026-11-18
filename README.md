# ImpactFlow

**ImpactFlow — Enterprise Data Engineering & Intelligence Platform**

Transforming Operational Data into Actionable Intelligence.

ImpactFlow is a staged portfolio project for demonstrating how operational data can be collected, validated, governed, modelled, and turned into programme intelligence. The scenario is a South African nonprofit organisation supporting education, healthcare, youth employment, and community development.

## Current status

**Phase 2 foundation:** a responsive dark React dashboard with synthetic development data, plus a FastAPI service, PostgreSQL configuration, and liveness/readiness checks. The API does not yet expose business data, and the dashboard remains disconnected from it. Authentication, pipeline execution, and external integrations are not implemented. Module views remain previews, and dashboard values are not live organisational data.

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

The current backend foundation is documented in [backend/README.md](backend/README.md). PostgreSQL can be started locally with Docker Compose; database readiness is reported separately from liveness. There are not yet business models or migrations. The target architecture also includes progressively introduced ingestion/ETL, medallion storage, dbt, Airflow, governance, monitoring, and Power BI documentation; those capabilities are future phases, not operational features.

See [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) and [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) for phase status and diagrams.
