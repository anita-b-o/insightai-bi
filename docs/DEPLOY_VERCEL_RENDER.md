# Deploy en Vercel + Render

Este repo queda preparado para desplegar `frontend/` en Vercel y `backend/` en Render, con PostgreSQL administrado en Render. No despliegues frontend y backend juntos en Vercel.

## Orden recomendado

1. Crear PostgreSQL en Render.
2. Crear el backend en Render.
3. Configurar variables del backend.
4. Ejecutar migraciones.
5. Obtener la URL publica del backend.
6. Crear el frontend en Vercel.
7. Configurar `VITE_API_BASE_URL`.
8. Agregar la URL final de Vercel a CORS.
9. Redeploy del backend.
10. Ejecutar smoke test.

## Vercel

- Importar el mismo repositorio.
- Root Directory: `frontend`
- Framework Preset: `Vite`
- Build Command: `npm run build`
- Output Directory: `dist`
- Variables:
  - `VITE_API_BASE_URL=https://BACKEND.onrender.com/api`
  - `VITE_CLIENT_ERROR_ENDPOINT=` si no se usa reporte externo.
  - `VITE_SENTRY_DSN=`, `VITE_SENTRY_ENVIRONMENT=production`, `VITE_SENTRY_TRACES_SAMPLE_RATE=0` si aplica.

`frontend/vercel.json` solo contiene el rewrite SPA hacia `index.html`, suficiente para rutas directas como `/demo`, `/login`, `/register`, `/datasets`, `/upload`, `/dashboards`, `/dashboards/:id` y `/share/:token`.

## Render Postgres

- Crear una base PostgreSQL en Render o usar el `render.yaml`.
- Mantener la base y el backend en la misma region.
- Conectar `DATABASE_URL` al Web Service con la Internal Database URL o con `fromDatabase.connectionString`.
- `DATABASE_URL` tiene prioridad sobre `POSTGRES_SERVER`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB`.

## Render Backend

- Crear desde el mismo repositorio.
- Root Directory: `backend`
- Runtime: Docker.
- Dockerfile: `backend/Dockerfile`
- Health Check Path: `/health`
- Start command:

```sh
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Variables necesarias:

```sh
APP_ENV=production
API_V1_PREFIX=/api
DATABASE_URL=<Render Internal Database URL>
STORAGE_PATH=/var/data/datasets
BACKEND_CORS_ORIGINS=["https://mi-proyecto.vercel.app"]
SECRET_KEY=<generado por Render o valor seguro>
OPENAI_API_KEY=<configurar si se usa IA>
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TIMEOUT_SECONDS=45
OPENAI_MAX_RETRIES=1
DASHBOARD_REFRESH_LOCK_TIMEOUT_SECONDS=300
WORKER_HEARTBEAT_TIMEOUT_SECONDS=180
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0
```

## Migraciones

Ejecutar desde `backend/`:

```sh
alembic upgrade head
```

El Blueprint usa `preDeployCommand: alembic upgrade head`. Si se configura el servicio manualmente y no se usa pre-deploy, ejecutarlo como comando manual antes del primer smoke test y despues de cambios de schema.

## CORS

Agregar la URL final de Vercel:

```sh
BACKEND_CORS_ORIGINS=["https://mi-proyecto.vercel.app"]
```

Para previews de Vercel, agregar explicitamente cada dominio preview que se quiera permitir. No usar `*` porque el backend tiene `allow_credentials=True`.

El frontend usa tokens Bearer en `Authorization` desde `localStorage`; no depende de cookies cross-site.

## CSV y disco persistente

Local:

```sh
STORAGE_PATH=storage/datasets
```

Render con persistencia:

```sh
STORAGE_PATH=/var/data/datasets
```

Montar un Persistent Disk en:

```sh
/var/data
```

El `render.yaml` declara un disco de 1 GB en `/var/data`. Los discos persistentes requieren instancia paga. Si se usa un plan gratuito sin disco, el filesystem de Render es efimero y los CSV pueden perderse en reinicios o redeploys.

## Worker de dashboards

El worker no debe ejecutarse dentro del proceso `uvicorn`. Es opcional para refrescos programados de dashboards; las funciones basicas de API y demo no requieren correrlo junto al web service.

Comando para un Background Worker separado en Render:

```sh
while true; do python -m app.workers.dashboard_refresh_worker; sleep 60; done
```

Debe usar las mismas variables que el backend, incluyendo `DATABASE_URL` y `STORAGE_PATH`.

## Smoke test

- `GET https://BACKEND.onrender.com/health`
- Abrir el frontend de Vercel en `/demo`, `/login`, `/register`, `/datasets`, `/upload`, `/dashboards` y `/share/<token-valido>`.
- Verificar login y requests con header `Authorization: Bearer ...`.
