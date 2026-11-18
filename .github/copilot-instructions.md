# ImpactFlow contributor instructions

## Project intent

ImpactFlow is a phased portfolio project for enterprise data engineering and programme intelligence in a synthetic South African nonprofit scenario. Keep the implementation and documentation honest about what is real, simulated, planned, or unavailable.

## Current phase boundary

The current deliverable includes the React/TypeScript/Vite dashboard foundation and a FastAPI/PostgreSQL health-check foundation. Dashboard values are synthetic and disconnected from the API. Do not imply that business data APIs, application persistence, authentication, ingestion, pipelines, alerts, or external integrations work until they are implemented and tested. Verify PostgreSQL runtime availability before describing it as operational.

Complete only the phase the user approved. After a phase, run relevant tests/builds, update directly related documentation, report remaining phases, and wait before advancing to a later major phase.

## Frontend conventions

- Use React with TypeScript and strict typing; keep UI components, types, and data generation separate.
- Preserve the ImpactFlow tokens in `frontend/src/index.css` and visual patterns in `frontend/src/App.css`.
- Reuse existing components and Lucide icons. Keep layouts responsive and accessible, including focus states and reduced-motion support.
- Do not add controls that claim actions they do not perform. Clearly label planned module views as non-operational previews.
- Keep synthetic development data deterministic for a fixed seed and reference date and never use real beneficiary or children's personal data.

## Repository practices

- Keep changes surgical and update docs when implementation changes.
- Store secrets in environment variables; never commit credentials or real personal data.
- For frontend changes, run `npm run build`, `npm run lint`, and relevant `npm test` commands from `frontend/`.
