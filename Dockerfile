FROM python:3.14.4-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home monitor_user \
    && mkdir -p /app \
    && chown monitor_user:monitor_user /app
WORKDIR /app

USER monitor_user

COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /uvx /bin/

# Install dependencies first for better Docker layer caching
COPY --chown=monitor_user:monitor_user pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Copy the project into the image
COPY --chown=monitor_user:monitor_user . .
RUN uv sync --locked --no-dev
