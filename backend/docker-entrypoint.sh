#!/bin/sh
# Start-up for the Pairly API container: migrate, optionally seed the demo, serve.
set -e

alembic upgrade head

if [ "${SEED_DEMO:-false}" = "true" ]; then
  # Safe to repeat. Reloads the sample if the container disk was wiped.
  python scripts/seed_demo.py
fi

# One process: the APScheduler jobs run in-process and must not be duplicated.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-5000}" --proxy-headers --forwarded-allow-ips="*"
