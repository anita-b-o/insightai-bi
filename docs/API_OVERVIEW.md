# API Overview

Base prefix:

- `/api`

## Auth

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/users/me`

## Datasets

- `POST /api/datasets/upload`
- `GET /api/datasets`
- `GET /api/datasets/{id}`

## Ask AI

- `POST /api/ai/query`

Purpose:

- generate SQL-backed answers over a selected dataset

## Insights

- `POST /api/datasets/{dataset_id}/insights/generate`
- `GET /api/datasets/{dataset_id}/insights/latest`

Primary output:

- ranked structured insights
- narrative summary

## Dashboards

- `POST /api/dashboards`
- `GET /api/dashboards`
- `GET /api/dashboards/{id}`
- `PATCH /api/dashboards/{id}`
- `DELETE /api/dashboards/{id}`

## Dashboard Widgets

- `POST /api/dashboards/{id}/widgets`
- `PATCH /api/dashboards/{id}/widgets/{widget_id}`
- `DELETE /api/dashboards/{id}/widgets/{widget_id}`
- `POST /api/dashboards/{id}/refresh`
- `POST /api/dashboards/{dashboard_id}/widgets/{widget_id}/refresh`

## Dashboard Freshness and Scheduling

- `PATCH /api/dashboards/{id}/refresh-settings`

Fields exposed:

- `auto_refresh_enabled`
- `refresh_interval_minutes`
- `last_successful_refresh_at`
- `next_refresh_at`
- `freshness_status`

## Dashboard Narrative

- `GET /api/dashboards/{id}/narrative`

## Dashboard Share Links

Authenticated management:

- `POST /api/dashboards/{id}/share-links`
- `GET /api/dashboards/{id}/share-links`
- `DELETE /api/dashboards/{id}/share-links/{share_id}`

Public read-only access:

- `GET /api/public/dashboards/{token}`

## Public Share Security

- the plain token is returned only when the share link is created
- the database stores only `token_hash`
- revoked links return `404`
- expired links return `404`
- public responses omit owner identity and query SQL

## Contract Philosophy

The API is kept additive where possible:

- new fields are added as optional metadata
- frontend-safe normalization happens in the client layer
- refresh, narrative, and sharing are layered on top of stable dashboard primitives
