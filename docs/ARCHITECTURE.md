# Architecture

## Overview

InsightAI BI is structured as a two-tier application:

- React frontend for interactive analytics UX
- FastAPI backend for data processing, persistence, orchestration, and secure API access

The product is built around a dataset-to-insight-to-dashboard pipeline.

## Backend Layers

### API routes

Located in `backend/app/api/routes`.

Responsibilities:

- request validation
- auth wiring
- response serialization
- mapping HTTP contracts to service calls

### Services

Located in `backend/app/services`.

Key services:

- `schema_profile_service.py`
- `column_semantic_service.py`
- `feature_selection_service.py`
- `insight_service.py`
- `insight_ranking_service.py`
- `insight_narrative_service.py`
- `dashboard_service.py`
- `dashboard_execution_service.py`
- `dashboard_freshness_service.py`
- `dashboard_narrative_service.py`
- `dashboard_share_service.py`

Responsibilities:

- business rules
- orchestration across models
- deterministic analytics logic
- guarded fallback behavior when AI is unavailable

### Models

Located in `backend/app/models`.

Important entities:

- `User`
- `Dataset`
- `DatasetColumn`
- `DatasetInsightRun`
- `QueryHistory`
- `QueryResult`
- `Dashboard`
- `DashboardWidget`
- `DashboardShareLink`

### Schemas

Located in `backend/app/schemas`.

Responsibilities:

- public API contracts
- request validation
- additive compatibility for frontend evolution

### Worker

Located in `backend/app/workers/dashboard_refresh_worker.py`.

Current scope:

- polls dashboards due for refresh
- applies dashboard refresh safely
- avoids double execution with `refresh_in_progress`

## Frontend Layers

### API clients

Located in `frontend/src/api`.

Responsibilities:

- call backend endpoints
- normalize payloads
- hide API response quirks from feature components

### Feature modules

Located in `frontend/src/features`.

Main feature areas:

- `ai`
- `dashboards`
- `datasets`

### Pages and routing

Located in `frontend/src/pages` and `frontend/src/app/router.tsx`.

Routes are lazy-loaded to reduce initial bundle size for the unauthenticated shell and lighter screens.

## Data Flow

### 1. Dataset upload

```text
CSV upload
-> Pandas ingestion
-> schema profile
-> dataset + column metadata persisted
```

### 2. Insights generation

```text
schema profile
-> semantic typing
-> feature scoring
-> raw insights
-> ranking + deduplication
-> top insights
-> narrative
```

### 3. Dashboard lifecycle

```text
Ask AI result / insight
-> save as widget
-> manual refresh or scheduled refresh
-> freshness computation
-> dashboard narrative
-> PDF export / public share
```

## Security Model

- authenticated routes require JWT
- dataset and dashboard ownership is enforced server-side
- public share links are read-only
- plain share tokens are never stored
- public shared payloads omit sensitive owner and SQL data

## Refresh Model

Dashboard freshness fields:

- `auto_refresh_enabled`
- `refresh_interval_minutes`
- `last_successful_refresh_at`
- `next_refresh_at`
- `freshness_status`
- `refresh_in_progress`

Freshness states:

- `never_refreshed`
- `fresh`
- `stale`
- `failed`

## AI Strategy

The product is built so that core value does not depend on live LLM availability.

Deterministic first:

- schema profiling
- semantic typing
- feature selection
- insight generation
- narrative generation

Optional LLM usage:

- Ask AI SQL generation
- narrative summary polishing when configured

If OpenAI fails or is unavailable, the platform still returns structured outputs.
