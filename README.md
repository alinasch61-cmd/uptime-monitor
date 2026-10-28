# API Health Check

## 1. Overview

API Health Check is a backend service that monitors registered HTTP endpoints and records their availability over time.
It replaces repeated manual checks with scheduled requests, status classification, and a queryable history of results.
Users can manage their own endpoints through an authenticated REST API and pause or resume monitoring as needed.

## 2. Project Motivation

This is a learning project focused on backend development, background processing, relational databases, and testing.
I created it to practice building a complete service: designing an API, managing database migrations,
moving work into background jobs, and verifying behavior with unit and integration tests.

## 3. Features

- **JWT authentication:** register an account and sign in to access your endpoints.
- **Endpoint registration:** configure an HTTP or HTTPS URL, expected status code, and check frequency.
- **Scheduled checks:** dispatch background HTTP checks for active endpoints, with a minimum interval of 120 seconds.
- **Status classification:** green for an exact status-code match, orange for the same HTTP status class,
  and red for a different class or a request failure.
- **Historical results:** retrieve the latest result or paginated history, optionally filtered by status,
  including HTTP status codes, latency, timestamps, and normalized transport errors.
- **Pause/resume:** suspend future scheduling and resume monitoring through the endpoint update API.

## 4. Tech Stack

| Purpose | Technologies |
| --- | --- |
| API | Python 3.14, FastAPI, Pydantic |
| Database | PostgreSQL, SQLAlchemy, Alembic, psycopg |
| Background processing | Redis, RQ, APScheduler, Requests |
| Authentication | PyJWT, pwdlib with Argon2 |
| Infrastructure | Docker, Docker Compose |
| Testing and development | pytest, uv, Ruff, mypy, pre-commit |

## 5. Architecture

FastAPI handles authentication and endpoint management, while PostgreSQL stores users, endpoint configurations,
and check results. A separate APScheduler process polls for due, unpaused endpoints every 120 seconds,
advances their next scheduled check time, and enqueues one RQ job per endpoint in Redis.
An RQ worker performs each HTTP GET request and saves its classified result to PostgreSQL.

```mermaid
flowchart LR
    Client <-->|API requests and responses| API[FastAPI]
    API <--> DB[(PostgreSQL)]
    Scheduler[APScheduler] <-->|Read due endpoints and update schedule| DB
    Scheduler -->|Enqueue RQ jobs| Redis[(Redis)]
    Redis <-->|Consume jobs and update job state| Worker[RQ worker]
    Worker <-->|HTTP GET and response| Target[Registered endpoint]
    Worker <-->|Read endpoint configuration and store results| DB
```

Checks disable redirects and use an 8-second Requests timeout.
The scheduler's polling interval and queue wait time affect when a due check actually runs.

## 6. Getting Started

### Prerequisites

- Docker with Docker Compose v2.
- Available local ports `8000` for the API and `5432` for PostgreSQL.
- Python 3.14 and uv if you want to run tests on the host.

Run the following commands from the repository root.

### Environment configuration

Create a `.env` file with these values, replacing the example password and signing key:

```dotenv
POSTGRES_DB=api_monitor
POSTGRES_USER=monitor
POSTGRES_PASSWORD=change-me-local-password
DATABASE_URL=postgresql+psycopg://monitor:change-me-local-password@postgres:5432/api_monitor
SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRES_MINUTES=30
REDIS_URL=redis://redis:6379/0
RQ_REDIS_URL=redis://redis:6379/0
```

Generate a signing key, for example, with `openssl rand -hex 32`.
Keep `.env` private; it is excluded from Git and the Docker build context.
If your database credentials contain URL-special characters, percent-encode them in `DATABASE_URL`.
The `postgres` and `redis` hostnames refer to services inside the Compose network.
`REDIS_URL` configures the application's queue connection; `RQ_REDIS_URL` configures the RQ worker CLI.

### Start the services and apply migrations

```sh
docker compose up --build -d
docker compose ps -a
docker compose logs -f api scheduler worker
```

Application logs write `INFO` messages to stdout and `ERROR` messages to stderr.
Each entry includes the timestamp, level, and service name (endpoint handler, scheduler, or job).
Docker collects these streams; no log files or log volume mounts are needed.

Compose starts PostgreSQL and Redis, runs `alembic upgrade head` in the one-off `migrate` service,
then starts the API, scheduler, and worker after migrations succeed.
A successful `migrate` container exits with code `0`; it does not stay running.
The API is available at [http://localhost:8000/docs](http://localhost:8000/docs).

To inspect migration output or explicitly apply migrations to an existing environment:

```sh
docker compose logs migrate
docker compose run --rm migrate
```

After changing application code or dependencies, rebuild with `docker compose up --build -d`.
Stop the stack with `docker compose down`; the named PostgreSQL volume preserves database data.

## 7. API Documentation

Explore and execute requests through [Swagger UI at `/docs`](http://localhost:8000/docs).
The generated OpenAPI schema is available at [`/openapi.json`](http://localhost:8000/openapi.json).

1. Create a user in Swagger UI: expand `POST /auth/register`, select **Try it out**, enter a username
   and password in the JSON request body, and select **Execute**. A successful request returns `201 Created`.
2. Select **Authorize**, enter the username and password of the user you just created, and authorize access.
   Login uses form data and returns a JWT bearer token.
3. Register an endpoint through `POST /endpoints/` using Swagger UI or the following request
   with your access token:

```sh
curl -X POST http://localhost:8000/endpoints/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","expected_status_code":200,"check_frequency_seconds":120}'
```

Use `PATCH /endpoints/{endpoint_id}` with `{"is_paused":true}` to pause or `{"is_paused":false}` to resume.
The status route returns `404` until the endpoint has a recorded result.

## 8. Testing

Install the locked dependencies and run the unit tests locally:

```sh
uv sync --locked
uv run pytest app/tests/unit
```

The application settings in `.env` must be present even for unit tests.
Unit tests mock HTTP requests and DNS resolution to verify status classification, error handling,
URL validation, and scheduling calculations without external services.

Integration tests require a reachable PostgreSQL database and a role allowed to create schemas.
With the Compose stack running and the example credentials above, create a dedicated test database once:

```sh
docker compose exec postgres createdb -U monitor test_api_monitor
```

Run integration tests or the complete suite against that database using its host-accessible address:

```sh
TEST_DATABASE_URL='postgresql+psycopg://monitor:change-me-local-password@localhost:5432/test_api_monitor' \
  uv run pytest app/tests/integration

TEST_DATABASE_URL='postgresql+psycopg://monitor:change-me-local-password@localhost:5432/test_api_monitor' \
  uv run pytest app/tests
```

Integration tests exercise API behavior and worker persistence with real PostgreSQL constraints,
password hashing, migrations, and triggers. Each test uses a unique schema inside a transaction,
then rolls back its schema and data. HTTP calls and queue dispatch are mocked where appropriate.
If `TEST_DATABASE_URL` is omitted, tests fall back to `DATABASE_URL`.

## 9. Limitations / Out of Scope

- **No frontend:** interaction is through the REST API and generated documentation.
- **No distributed scheduling:** run a single scheduler process; coordination between scheduler replicas is not implemented.
- **No retry mechanism:** failed checks and failed jobs do not have an application-level retry policy.
- **Incomplete SSRF protection:** registration rejects non-HTTP(S) URLs and blocked resolved IP addresses,
  and checks do not follow redirects. Workers resolve hostnames again when requesting a URL,
  so DNS changes or rebinding can bypass the registration-time validation.
- **Limited check configuration:** checks use GET without custom headers, request bodies, or response-body assertions.
- **Pause affects scheduling:** jobs already queued or running may still finish and record results.
