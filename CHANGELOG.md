# Changelog

All notable changes to Pairly. Dates are YYYY-MM-DD.

## [3.1.0] - 2026-10-24

The product is now called **Pairly** (formerly "Assortment Dashboard").

### Added
- **AI Insights card** on the dashboard: three to five plain-English insights, each with a suggested action. Every number is checked against the analytics results; on failure Pairly retries once, then falls back to a template summary. Cached per store, dataset and thresholds, with a Regenerate button.
- **Ask Pairly** assistant: tool calling over seven read-only analytics tools, streamed answers (SSE), and the tools used shown under each answer. Tools are always scoped to the signed-in user's store.
- One OpenAI-compatible LLM gateway for Groq and Gemini (`LLM_PROVIDER`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `LLM_MODEL`), with timeouts and one retry.
- AI controls: platform switch and per-store block (super admin), store switch (Settings), daily request limit per store, and usage with token counts on the super-admin dashboard.
- New tables `platform_settings`, `store_ai_settings`, `ai_usage_logs` and `ai_insight_cache` (Alembic migration `3678ef73e299`).
- Demo seed `scripts/seed_demo.py` with `--file` and `--reload`, loading a 4.6 MB sample of Online Retail II from `backend/app/demo/sample_transactions.csv`.
- A 315-row test fixture with planted product pairs (`backend/tests/fixtures/`) and tests that check exact rules, bundles and recommendations from it.
- Docker images for the API and the web app, and `docker-compose.yml` (PostgreSQL + API + web).
- Cloudflare deployment (`cloudflare/`): one Worker serves the web app and forwards `/api` to the API container (Cloudflare Containers), with a managed PostgreSQL (Neon, or PlanetScale billed through Cloudflare), R2 for uploaded datasets, a Cron Trigger for scheduled jobs, and a manual "Deploy to Cloudflare" GitHub workflow.
- Gemini as an automatic fallback when Groq fails.
- `STORAGE_BACKEND=r2` (datasets kept in Cloudflare R2) and `SCHEDULER_MODE=external` (scheduled jobs triggered via `POST /api/internal/scheduled-jobs/run`).
- GitHub Actions CI: ruff + pytest, migrations and seed on PostgreSQL, ESLint + build, and a docker compose end-to-end check.
- pytest suite (121 tests, run on both SQLite and PostgreSQL in CI) with a mock LLM and no network access, including store-isolation tests for the AI tools.
- LICENSE, SECURITY.md, `.editorconfig` and `.gitattributes`.

### Changed
- Settings `APP_ENV` / `APP_DEBUG` replace `FLASK_ENV` / `FLASK_DEBUG`; the old names still work as fallbacks.
- With `APP_ENV=production` the API refuses to start with the example secrets.
- `FRONTEND_URL` is always an allowed CORS origin; `ALLOWED_ORIGIN_REGEX` was added for preview deploys.
- Migrations use plain Alembic (the old setup depended on Flask). The initial migration now also runs on PostgreSQL, and PostgreSQL URLs always use the psycopg2 driver (SQLAlchemy 2.1 changed the default).
- Analytics pages use the shared API client, so `VITE_API_BASE_URL` works in production. The default API base is `/api`.
- The recommendations CSV export is about 15 times faster, with identical output.
- The frontend build is split into vendor chunks (largest chunk 1.0 MB → 494 kB).
- The repo is restructured: `backend/tests/`, `backend/scripts/`, and one root `.gitignore` that ignores `*.csv`, `*.xlsx` and `*.ipynb` apart from the two sample files.
- All backend code lives in the `app` package: `config.py` is now `app/config.py` and the email templates are in `app/templates/`. The frontend analytics pages are in `pages/analytics/`.
- README screenshots moved to `.github/assets/screenshots/`. `docs/` is no longer committed.

### Fixed
- `httpx` is now a runtime dependency. It was only in `requirements-dev.txt`, so the production image crashed on startup.

### Removed
- CONTRIBUTING.md and the issue and PR templates (Pairly is proprietary).
- The root `data/` folder and its two large CSVs (164 MB) are no longer tracked, and neither is `notebook/Phase-1.ipynb` (kept locally). Git history is unchanged.
- Unused code: the old Flask blueprints and decorators, `backend/legacy/`, an unused sidebar component, and unused images.

## [3.0.0] - 2026-05

- Backend moved from Flask to FastAPI, with PostgreSQL support.
