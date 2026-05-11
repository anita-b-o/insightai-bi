# Frontend Rebuild Audit

Date: 2026-05-03

## Baseline
- Frontend path: `frontend/`
- Build system: Vite + TypeScript
- UI stack already present: React 19, Material UI, React Query, React Router, Recharts, `react-grid-layout`, Axios
- Current frontend tests: 57 passing
- Current production build: passing

## Existing Routes
- `/login`
- `/register`
- `/demo`
- `/share/:token`
- `/public/dashboards/:token`
- `/datasets`
- `/datasets/:datasetId`
- `/upload`
- `/dashboards`
- `/dashboards/:dashboardId`
- `*`

## Existing Capabilities
- JWT auth with persisted token
- Dataset upload, list, detail
- Ask AI query flow with persisted history
- Automatic insights with narrative
- Dashboard CRUD and widget CRUD
- Dashboard refresh and freshness metadata
- Public share links
- PDF export
- Demo mode

## Main Frontend Risks
- `dashboard-detail-page` concentrates too much page state and mutation logic
- DTO normalization is spread across long API files
- Legacy visual system is inconsistent across cards, spacing, radius, and chart/table shells
- Debug logging is present in user-facing paths
- Recharts test warnings indicate the chart container layer needs to be rebuilt

## Rebuild Strategy
- Keep backend contract unchanged
- Introduce `src_next/` as the new frontend architecture
- Migrate route-by-route while preserving a working app
- Reuse live backend contracts; document missing endpoints instead of inventing them
