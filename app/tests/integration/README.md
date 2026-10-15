Run registration integration tests against PostgreSQL:

```sh
TEST_DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/test_db uv run pytest app/tests/integration
```

If `TEST_DATABASE_URL` is unset, tests use the configured `DATABASE_URL`.
The database role must be able to create schemas. Each test creates a unique
schema inside a transaction, uses real database constraints and password hashing,
and rolls back the schema and test data afterward. Existing tables are untouched.
