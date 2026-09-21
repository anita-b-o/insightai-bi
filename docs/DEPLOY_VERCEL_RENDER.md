# Deploy en Vercel + Render con Neon PostgreSQL

Este repo queda preparado para desplegar `frontend/` en Vercel y `backend/` en
Render, con PostgreSQL administrado en Neon. No despliegues frontend y backend
juntos en Vercel.

## Orden recomendado

1. Crear el proyecto PostgreSQL en Neon.
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
  - `VITE_AUTH_RESTORE_TIMEOUT_MS=12000` limita la validación inicial de `/users/me`; no configura reintentos automáticos.
  - `VITE_CLIENT_ERROR_ENDPOINT=` si no se usa reporte externo.
  - `VITE_SENTRY_DSN=`, `VITE_SENTRY_ENVIRONMENT=production`, `VITE_SENTRY_TRACES_SAMPLE_RATE=0` si aplica.

`frontend/vercel.json` solo contiene el rewrite SPA hacia `index.html`, suficiente para rutas directas como `/demo`, `/login`, `/register`, `/datasets`, `/upload`, `/dashboards`, `/dashboards/:id` y `/share/:token`.

## Neon PostgreSQL

- Crear el proyecto Neon con la misma version mayor de PostgreSQL usada en
  produccion.
- Elegir la region de Neon mas cercana a la region del backend de Render.
- Usar la URL pooled de Neon como `DATABASE_URL`.
- Usar la URL directa de Neon como `DATABASE_DIRECT_URL`.
- Conservar `sslmode=require&channel_binding=require` en ambas URLs.
- `DATABASE_URL` tiene prioridad sobre `POSTGRES_SERVER`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB`.
- Alembic tiene prioridad por `DATABASE_DIRECT_URL` y solo usa
  `DATABASE_URL` como fallback.

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
DATABASE_URL=<Neon pooled URL>
DATABASE_DIRECT_URL=<Neon direct URL>
MAX_UPLOAD_BYTES=10485760
MAX_DATASET_ROWS=50000
MAX_DATASET_COLUMNS=100
MAX_CELL_LENGTH=16384
FEATURE_SELECTION_SAMPLE_ROWS=10000
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

## CSV transitorio y límites de upload

El CSV sólo existe durante la ingestión; no se escribe en el filesystem. PostgreSQL
guarda `datasets`, `dataset_columns` y cada tabla dinámica `dataset_<id>`, por lo
que Render Free puede reiniciar o reemplazar el contenedor sin perder datasets
correctamente importados. Los defaults están pensados para demo/Render Free y
Neon Free: 10 MiB por upload, 50.000 filas, 100 columnas, celdas de 16.384
caracteres y una muestra de insights de 10.000 filas. Se pueden ajustar por
variables de entorno según el presupuesto de RAM y base de datos.

## Refresh programado de dashboards en Render Free

Render Free no ofrece Background Workers ni Cron Jobs gratuitos. El refresh
programado se dispara desde GitHub Actions cada diez minutos hacia el endpoint
interno autenticado del backend. Consultar
[SCHEDULED_REFRESH.md](./SCHEDULED_REFRESH.md) antes de desplegar: requiere
configurar el mismo `SCHEDULER_SECRET` en Render y como GitHub Actions Secret.

No ejecutar un loop de worker dentro de `uvicorn`: Render puede suspender un
Web Service Free inactivo y perdería el scheduler embebido.

## Base Render anterior

Durante una migracion, conservar PostgreSQL de Render sin trafico durante la
ventana de rollback. No eliminarlo ni quitarlo del Blueprint hasta validar
integridad, login, datasets, dashboards, uploads, IA y worker sobre Neon.

## Smoke test

- `GET https://BACKEND.onrender.com/health`
- Abrir el frontend de Vercel en `/demo`, `/login`, `/register`, `/datasets`, `/upload`, `/dashboards` y `/share/<token-valido>`.
- Verificar login y requests con header `Authorization: Bearer ...`.
