#!/bin/sh
# Start-up for the Pairly API container: migrate, optionally seed the demo, serve.
set -e

alembic upgrade head

# SEED_DEMO: true = load the demo before serving (docker compose, CI);
# background = serve at once and load it alongside (Cloudflare, where the
# port must open quickly). Safe to repeat; restores the demo after a disk wipe.
case "${SEED_DEMO:-false}" in
  true) python scripts/seed_demo.py ;;
  background) python scripts/seed_demo.py & ;;
esac

# One process: the APScheduler jobs run in-process and must not be duplicated.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-5000}" --proxy-headers --forwarded-allow-ips="*"
