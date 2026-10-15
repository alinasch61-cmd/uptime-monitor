Run integration tests against the existing PostgreSQL test database:

```sh
TEST_DATABASE_URL='postgresql+psycopg://user:password@127.0.0.1:5432/test_api_monitor' uv run pytest app/tests/integration
```

If `TEST_DATABASE_URL` is unset, tests use the configured `DATABASE_URL`.
The database role must be able to create schemas. Each test creates a unique
schema inside a transaction and applies all Alembic migrations through `head`,
including database functions and triggers. Tests use real database constraints
and password hashing, then roll back the schema and test data afterward.
Existing tables are untouched. The fixtures do not create the database itself.

Resume tests verify that the trigger sets `next_check_at` to PostgreSQL `NOW()`.
PostgreSQL `NOW()` is the outer transaction's start time, which stays constant
throughout a test.
