# InsightAI BI

InsightAI BI is a portfolio-grade Business Intelligence product that combines AI-assisted querying, deterministic insight generation, persistent dashboards, scheduled refresh, PDF export, and secure public sharing in one workflow.

The product pitch is simple: make analytics feel as fast as AI chat without losing the structure, persistence, and operational safety expected from real BI software.

## Why This Project Exists

Traditional BI tools are strong at dashboards but slow for ad hoc exploration. Pure AI chat tools feel fast, but they usually lack auditability, persistence, and repeatable execution.

InsightAI BI is designed to bridge that gap:

- upload a CSV dataset
- profile and semantically classify columns
- ask SQL-backed questions through Ask AI
- generate ranked insights automatically
- save results into persistent dashboards
- refresh widgets manually or on schedule
- export dashboards to PDF
- share dashboards through secure read-only links

## Main Features

- Ask AI with SQL-backed answers, result tables, and chart suggestions
- deterministic Insight Engine for top performers, distributions, correlations, and outliers
- feature selection to prioritize analytically useful columns
- ranking and deduplication so low-value or repetitive insights do not dominate
- persistent dashboards with saved widget layout
- dashboard narrative summary
- manual refresh and scheduled refresh with freshness metadata
- read-only public share links with expiration and revocation
- export dashboard to PDF
- public `/demo` route for interviews and portfolio walkthroughs

## Demo

- Public demo route: `/demo`
- Local URL after startup: `http://localhost:5173/demo`
- Demo script: [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)

The demo mode is the fastest way to present the project. It loads a prebuilt experience with Ask AI results, ranked insights, narrative, and a saved dashboard layout without requiring authentication.

## Screenshots / Walkthrough Assets

This repository does not currently include committed screenshots. Recommended captures for a portfolio page:

1. `/demo` overview with dataset summary and suggested prompts
2. Ask AI result with SQL, chart, and table
3. Insight Engine output with ranked cards and narrative
4. Dashboard detail with widget grid, freshness status, and narrative
5. Shared read-only dashboard view

If you want a live walkthrough instead of static images, use the demo route above.

## Architecture

High-level product flow:

```text
CSV upload
-> schema profiling
-> semantic column typing
-> feature selection
-> Insight Engine generation
-> ranking + deduplication
-> dashboard widgets
-> refresh + freshness
-> PDF export + share links
```

### Backend

- `backend/app/api/routes`: FastAPI route layer
- `backend/app/models`: SQLAlchemy persistence models
- `backend/app/schemas`: Pydantic request/response contracts
- `backend/app/services`: business logic, orchestration, analytics rules
- `backend/app/workers`: dashboard refresh worker

Key backend services:

- `ai_service.py`
- `feature_selection_service.py`
- `insight_service.py`
- `insight_ranking_service.py`
- `dashboard_execution_service.py`
- `dashboard_freshness_service.py`
- `dashboard_share_service.py`

### Frontend

- `frontend/src/app`: app bootstrap, auth context, router
- `frontend/src/layouts`: shared page shell
- `frontend/src/api`: API clients and normalization
- `frontend/src/features/ai`: Ask AI, insight views, charts, tables
- `frontend/src/features/dashboards`: dashboards, widgets, share, export, refresh
- `frontend/src/features/demo`: public demo experience
- `frontend/src/components/ui`: design system primitives

### Product Notes

- routes are lazy-loaded
- dashboard PDF export is dynamically imported on demand
- the share dialog is lazy-loaded from the dashboard detail page
- Vite manual chunks split `mui`, `recharts`, `react-grid-layout`, and PDF-export dependencies to reduce initial load pressure

More detail:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/API_OVERVIEW.md](docs/API_OVERVIEW.md)
- [docs/TECHNICAL_DECISIONS.md](docs/TECHNICAL_DECISIONS.md)

## Stack

- Frontend: React 19, TypeScript, Vite, Material UI, React Router, Recharts, react-grid-layout
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic, Pandas
- Database: PostgreSQL 16
- Auth: JWT bearer tokens, hashed passwords
- Infra: Docker Compose
- Frontend tests: Vitest, Testing Library, JSDOM
- Backend tests: pytest

## Run With Docker

From the project root:

```bash
cd insightai-bi
docker compose up --build
```

Services:

- frontend: `http://localhost:5173`
- backend API: `http://localhost:8000`
- postgres: `localhost:5433`

The Compose stack includes:

- `db`
- `backend`
- `frontend`
- `dashboard-refresh-worker`

The refresh worker continuously checks for dashboards due for scheduled refresh.

Notes:

- create `backend/.env` from `backend/.env.example` before starting the stack
- Compose now expects runtime secrets in `backend/.env`, not in the example file
- backend startup applies Alembic migrations before serving traffic
- frontend runs from a production build preview instead of the Vite development server

## Environment Variables

Backend example file:

- [backend/.env.example](backend/.env.example)

Frontend example file:

- [frontend/.env.example](frontend/.env.example)

Important backend variables:

- `APP_ENV`
- `SECRET_KEY`
- `POSTGRES_SERVER`
- `POSTGRES_PORT`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `BACKEND_CORS_ORIGINS`
- `STORAGE_PATH`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_TIMEOUT_SECONDS`
- `OPENAI_MAX_RETRIES`
- `DASHBOARD_REFRESH_LOCK_TIMEOUT_SECONDS`

Important frontend variable:

- `VITE_API_BASE_URL`
- `VITE_CLIENT_ERROR_ENDPOINT`

Notes:

- `OPENAI_API_KEY` is optional for development
- real secrets should never be committed
- public share links store only hashed token values in the database
- `APP_ENV=production` rejects placeholder secrets at startup

## Tests

### Backend

Run the backend suite from the running Docker stack:

```bash
cd insightai-bi
docker compose exec backend python -m pytest -q
```

Backend test notes:

- the suite runs against the real Python dependency set
- PostgreSQL-backed flows are exercised inside Docker
- the smoke suite covers upload, Ask AI, insights, dashboards, refresh, and narrative

Reference:

- [backend/tests/README.md](backend/tests/README.md)

### Frontend

Run all frontend tests:

```bash
cd insightai-bi/frontend
npm test
```

Run the critical dashboard/demo suites:

```bash
cd insightai-bi/frontend
npm test -- --run src/features/dashboards/dashboard-detail-page.test.tsx src/features/dashboards/shared-dashboard-page.test.tsx src/features/demo/demo-page.test.tsx
```

Run the production build:

```bash
cd insightai-bi/frontend
npm run build
```

## Demo Dataset

A representative CSV is included at:

- [demo/wildfire_impact_sample.csv](demo/wildfire_impact_sample.csv)

It is designed to produce:

- meaningful grouped metrics
- chart-friendly outputs
- ranking-worthy insights
- a portfolio-friendly dashboard story

## Portfolio Walkthrough

Recommended live demo order:

1. Open `/demo`
2. Show Ask AI with SQL-backed output
3. Show ranked insights and narrative
4. Show the persistent dashboard and widget layout
5. Mention refresh, PDF export, and public sharing

For a tighter presenter script, use [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).

## Production Readiness

This project is not marketed as a fully deployed enterprise product, but several production-oriented patterns are already in place:

- backend and frontend test coverage for critical workflows
- Docker Compose stack for reproducible local setup
- route-level lazy loading in the frontend
- manual chunk splitting for heavy visualization and export dependencies
- on-demand loading for PDF export and dashboard sharing UI
- dashboard freshness metadata and a worker-driven refresh loop
- hashed public share tokens, expiration support, and revocation support
- public shared dashboards omit owner identity and raw SQL fields

## Security Notes

- authenticated routes require JWT
- dataset and dashboard ownership is enforced server-side
- share links are read-only
- expired or revoked share links return `404`
- share tokens are validated via hash comparison and signed token reconstruction
- CORS is explicit and environment-driven

## Additional Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/API_OVERVIEW.md](docs/API_OVERVIEW.md)
- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)
- [docs/TECHNICAL_DECISIONS.md](docs/TECHNICAL_DECISIONS.md)
