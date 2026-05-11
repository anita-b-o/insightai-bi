# Frontend Route Contract

## Public Frontend Routes
- `/login`
- `/register`
- `/demo`
- `/share/:token`

## Protected Frontend Routes
- `/datasets`
- `/datasets/:id`
- `/upload`
- `/dashboards`
- `/dashboards/:id`

## Integration Notes
- Public dashboard data is resolved through `GET /api/public/dashboards/:token`
- `/public/dashboards/:token` remains a legacy compatibility route and should redirect to `/share/:token`
- Demo mode is frontend-only and does not depend on a backend demo endpoint
- PDF export remains client-side because no backend export endpoint exists

## Known Backend Limitations
- No dataset edit endpoint
- No dataset delete endpoint
- No forgot/reset password flow
- No backend-side PDF export
- No dashboard duplication endpoint
