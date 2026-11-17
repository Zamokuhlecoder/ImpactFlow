# ADR 0001: Start with a client-side dashboard foundation

- Status: Accepted
- Date: 2026-11-17

## Context

The project is being built incrementally, with a polished frontend foundation before backend and data-engineering phases. Dashboard examples must not be mistaken for live nonprofit data.

## Decision

Use Vite, React, TypeScript, Tailwind CSS, React Router, Recharts, Lucide React, Axios, and TanStack Query for the initial client application. Use deterministic synthetic dashboard data and label it in the UI. Configure the API client without making unimplemented API calls.

## Consequences

The frontend can be run and validated independently. Backend, storage, authentication, ingestion, scheduling, and reporting integrations remain future work and must not be represented as operational.
