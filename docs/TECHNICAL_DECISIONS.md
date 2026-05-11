# Technical Decisions

## Overview

InsightAI BI was designed as a product system, not just a collection of screens or isolated AI demos.

The main product decision is to combine:

- fast AI-assisted exploration
- deterministic analytics logic
- persistent dashboard artifacts
- operational refresh and sharing behavior

This document explains the main technical choices behind that architecture.

## 1. LLM to SQL Pipeline

### Problem

A pure LLM answer is fast, but weak on auditability and hard to operationalize. For a BI product, the answer needs to be tied to actual dataset results.

### Decision

Ask AI uses an LLM-assisted SQL workflow instead of returning free-form answers only.

The path is:

```text
question
-> dataset schema context
-> SQL generation
-> SQL validation and normalization
-> SQL execution against the dataset table
-> SQL analysis
-> result-grounded answer
-> visualization suggestion
-> query history persistence
```

Relevant files:

- `backend/app/services/ai_service.py`
- `backend/app/services/sql_generator.py`
- `backend/app/services/sql_validator.py`
- `backend/app/services/sql_analysis_service.py`
- `backend/app/services/query_history_service.py`

### Why this approach

- it makes AI answers auditable
- the same query result can later be persisted as a dashboard widget
- visualization can be derived from result shape, not only from prompt text
- the system can store execution metadata and query history cleanly

### Tradeoff

This is more complex than a chat-only design because it requires SQL generation, validation, execution, and response shaping. The benefit is that the product behaves more like BI software than a generic assistant.

## 2. Insight Engine

### Problem

Uploaded datasets need useful insights even before a user writes good prompts. Relying only on chat would make discovery quality uneven.

### Decision

The product includes a deterministic Insight Engine that generates structured findings directly from dataset semantics and statistics.

Current insight families include:

- top performer
- distribution
- correlation
- outlier

Relevant files:

- `backend/app/services/insight_service.py`
- `backend/app/services/insight_narrative_service.py`
- `backend/app/services/column_semantic_service.py`
- `backend/app/services/schema_profile_service.py`

### Why this approach

- it provides immediate value after upload
- it avoids making users depend on prompt quality
- it keeps a meaningful experience even when live LLM access is unavailable
- it creates reusable dashboard-ready outputs

### Tradeoff

Deterministic insights are narrower than unconstrained AI reasoning. The benefit is stability, explainability, and repeatability.

## 3. Feature Selection

### Problem

Not all columns are equally useful for analysis. High-cardinality IDs, constants, and low-signal fields can pollute insight generation.

### Decision

Before prioritizing insights, the backend computes feature scores for columns based on several signals:

- variance
- correlation strength
- entropy
- cardinality
- non-null ratio
- outlier ratio

Relevant file:

- `backend/app/services/feature_selection_service.py`

### Why this approach

- it pushes analytically useful columns upward
- it reduces noise from identifiers and weak columns
- it improves ranking quality without requiring model calls
- it scales better for larger datasets because sampling is applied above `100,000` rows

### Tradeoff

Heuristics are imperfect and dataset-dependent, but they are cheap, deterministic, and easy to reason about.

## 4. Ranking and Deduplication

### Problem

Raw generated insights can be repetitive or overly concentrated around the same columns or insight type.

### Decision

Insight candidates are deduplicated and ranked before selection. The ranking combines:

- quality score
- confidence
- impact
- feature importance

The top insight set is then filtered again for diversity so the final list is not dominated by one pattern or one column pair.

Relevant files:

- `backend/app/services/insight_ranking_service.py`
- `backend/app/services/insight_service.py`

### Why this approach

- it keeps the output concise
- it improves perceived intelligence of the product
- it avoids showing five variants of the same story
- it makes dashboard saving more useful because surfaced insights are already curated

### Tradeoff

Any ranking system encodes opinionated heuristics. Here the bias is intentional: prefer strong, varied findings over exhaustive raw output.

## 5. Dashboard Refresh and Freshness

### Problem

Saved dashboards are only valuable if users can trust whether they are current.

### Decision

Dashboards store refresh metadata and support both manual and scheduled refresh. Freshness is treated as first-class product state.

Key fields:

- `auto_refresh_enabled`
- `refresh_interval_minutes`
- `last_successful_refresh_at`
- `next_refresh_at`
- `freshness_status`
- `refresh_in_progress`

Relevant files:

- `backend/app/services/dashboard_execution_service.py`
- `backend/app/services/dashboard_freshness_service.py`
- `backend/app/workers/dashboard_refresh_worker.py`

### Why this approach

- it gives users a visible signal of data recency
- it supports operational dashboards, not only static snapshots
- the worker loop avoids making the frontend responsible for refresh orchestration
- widget-level execution state can degrade gracefully if only some refreshes fail

### Tradeoff

Refresh introduces scheduling and failure-state complexity, but it is required if dashboards are meant to feel durable rather than disposable.

## 6. Share Links

### Problem

Portfolio-grade BI products need a way to expose dashboards externally without exposing edit access or forcing viewer authentication.

### Decision

Dashboards can be shared through read-only public links. The plain token is returned only on creation. The database stores only a hash, and public payloads exclude sensitive owner and SQL fields.

Relevant files:

- `backend/app/services/dashboard_share_service.py`
- `backend/app/models/dashboard_share_link.py`

### Why this approach

- it keeps sharing simple for viewers
- it limits exposure compared to exposing authenticated dashboards directly
- expiration and revocation are supported
- token verification uses hash comparison and signed token reconstruction

### Tradeoff

Public links are still bearer-style access tokens, so they must be treated carefully. Hashing, expiration, revocation, and read-only payload shaping reduce the risk.

## 7. Frontend Design System

### Problem

As the product surface expanded across dashboard, Ask AI, dataset, demo, and shared views, consistency risk increased.

### Decision

The frontend uses shared UI primitives and a stricter surface hierarchy instead of letting each view define its own ad hoc containers.

Examples:

- `SurfaceCard`
- `SectionBlock`
- `SectionHeader`
- `DataTableShell`
- `StatusChip`

Relevant files:

- `frontend/src/components/ui/surfaces.tsx`
- `frontend/src/theme/app-theme.ts`

### Why this approach

- it reduces duplicated styling logic
- it keeps views visually consistent
- it lowers the cost of future refinement
- it makes the frontend more defendable in interviews because the system is intentional, not accidental

## 8. Frontend Performance Strategy

### Problem

The dashboard view brings together several heavy dependencies:

- Material UI
- Recharts
- react-grid-layout
- html2canvas
- jsPDF

Without intervention, this pushes the main route chunk too high.

### Decision

The frontend uses:

- route-level lazy loading
- on-demand loading for PDF export
- lazy loading for the dashboard share dialog
- Vite manual chunk splitting for heavy dependency groups

Relevant files:

- `frontend/src/app/router.tsx`
- `frontend/src/features/dashboards/dashboard-detail-page.tsx`
- `frontend/vite.config.ts`

Chunking strategy currently separates:

- `mui`
- `recharts`
- `dashboard-grid`
- `pdf-export`
- `pdf-html2canvas`
- `pdf-jspdf`
- `react-vendor`
- `network`
- `vendor`

### Why this approach

- it reduces pressure on initial route load
- it keeps heavy export dependencies out of the critical path
- it makes the dashboard route more production-like without redesigning the UI

## 9. Production Readiness

The project is still a portfolio project, but several production-oriented choices are already present.

### Testing

- backend pytest suite covers auth, upload, insights, dashboards, refresh, sharing, and smoke integration
- frontend Vitest coverage includes dashboard detail, shared dashboard, and demo flows

### Docker

- Docker Compose provides reproducible local startup for database, backend, frontend, and refresh worker

### Performance

- route lazy loading is enabled
- PDF export is dynamically imported
- heavy libraries are split into manual chunks

### Security Basics

- JWT authentication for private flows
- ownership checks for datasets and dashboards
- read-only shared dashboards
- hashed share tokens
- expiration and revocation support
- public responses omit sensitive owner and SQL fields

## Summary

The core architectural choice in InsightAI BI is deliberate:

- use AI where it improves speed and usability
- use deterministic logic where stability and explainability matter
- persist useful outputs so the product behaves like BI software, not temporary chat

That combination is what makes the project stronger for both product storytelling and technical interviews.
