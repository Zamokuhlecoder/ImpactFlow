# ImpactFlow

**ImpactFlow — Enterprise Data Engineering & Intelligence Platform**

Transforming Operational Data into Actionable Intelligence.

ImpactFlow is a staged portfolio project for demonstrating how operational data can be collected, validated, governed, modelled, and turned into programme intelligence. The scenario is a South African nonprofit organisation supporting education, healthcare, youth employment, and community development.

## Current status

**Current status:** The database-backed overview and Phase 3 imports are available. Phase 4 adds a Pandas standardisation/validation pipeline, local Bronze/Silver/Gold files, quarantine, quality reports, run history, and the ETL Processing page. Phase 5 adds a PostgreSQL-compatible analytical star schema, idempotent Silver-to-warehouse loading, load history, and warehouse-backed programme and provincial analytics. Phase 6 adds Airflow DAG definitions, an optional Airflow REST proxy, orchestration run correlation, and a live orchestration workspace. Docker/Airflow must be started separately; this environment does not include Docker. Only fields present in the supported Silver schemas are loaded; expenditure, assessments, gender, registration dates, and district/municipality remain unavailable until source schemas support them.

**Security:** The demo user is a browser-only identity, not authentication. Sign-out only changes the local browser view; it does not protect the API. Anyone who can reach the API can read, change or delete database records and upload files. Run it only on a trusted local machine with synthetic data; do not expose it to a network or use it for production.

## Start the frontend

Requirements: Node.js 20.19+ or 22.12+ and npm.

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`).

The demo user stays active in the browser until **Sign out of demo** is selected. Continue again without a password; the database is shared, not owned by that identity. Select **Browser CSV** for the illustrative CSV view. **Upload programme CSV** replaces it in browser storage across reloads, not in PostgreSQL or other browsers; **Use example data** removes that saved upload. Download the example CSV for the required columns. Only upload synthetic aggregate counts, never personal data. The separate World Bank national population indicator requires internet access and is not a programme result.

Other frontend commands:

```powershell
npm run build
npm run lint
npm test
```

## Frontend foundation (Phase 1)

- React, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Axios, Lucide React, Recharts, and Framer Motion foundation.
- Responsive dark layout, collapsible grouped navigation, module previews, navigation/execution search, and activity display.
- The API view includes pipeline, quality, programme, ingestion, and beneficiary charts and a searchable pipeline execution table.
- The no-sign-in CSV view shows programme counts, targets, reach, and provincial totals without inventing pipeline or quality metrics.
- Seeded synthetic data generation covering all nine South African provinces; supply a reference date as well as a seed for repeatable timestamps.
- Starter architecture documentation and contributor instructions.

## Planned platform architecture

Backend setup, database migrations, file ingestion, connector configuration, worker operation, ETL processing, warehouse loading, orchestration, and synthetic database fixtures are documented in [backend/README.md](backend/README.md) and [airflow/README.md](airflow/README.md). Local PostgreSQL and Airflow can be started with Docker Compose, or the API can use a Neon connection string supplied through a private environment file. The World Bank population lookup is browser-only public-data context, not an ingestion pipeline. Distributed processing, managed object storage, dbt, governance, and Power BI remain later-phase capabilities.

See [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) and [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) for phase status and diagrams.
