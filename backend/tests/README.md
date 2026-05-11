# Backend Tests

The backend suite is designed to run inside Docker with the real Python dependencies and the real PostgreSQL service.

## Standard command

```bash
docker compose exec backend python -m pytest -q
```

## Smoke / integration coverage

`tests/test_bi_smoke_integration.py` validates the main BI backend flow end-to-end:

- Alembic migrations apply against PostgreSQL
- user register + login
- dataset CSV upload
- Ask AI query route with OpenAI mocked
- insight generation
- dashboard creation
- widget creation from query + insight
- dashboard refresh
- individual widget refresh
- dashboard narrative

The smoke suite does not call the real OpenAI API. It disables `OPENAI_API_KEY` during the test and mocks the Ask AI query execution at the route boundary so the flow stays reproducible.

## Notes

- Run the tests from the running Compose stack shown in `docker-compose.yml`.
- The smoke suite truncates application tables between tests to keep runs isolated.
- If this suite fails, treat it as a backend contract or platform regression, not just a unit test failure.
