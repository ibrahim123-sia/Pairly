# Pairly

**Find which products sell together, and turn it into bundles and revenue.**

[![CI](https://github.com/ibrahim123-sia/Pairly/actions/workflows/ci.yml/badge.svg)](https://github.com/ibrahim123-sia/Pairly/actions/workflows/ci.yml)

Pairly is a web app for shop owners. You upload your sales data (CSV or Excel) and Pairly shows:

- which products customers buy together,
- which bundles to offer,
- how revenue moves over the year,
- which customers are loyal and which are slipping away.

An AI layer then explains the results in plain English. It suggests next steps and answers questions such as *"What should I bundle with coffee?"*. The AI never invents numbers: every number comes from Pairly's analytics and is checked before you see it.

Pairly is multi-tenant. A super admin creates stores, and each store manager only ever sees their own store's data.

![Pairly dashboard with AI Insights](docs/screenshots/dashboard.png)

| Bundles | Product network |
|---|---|
| ![Product bundles](docs/screenshots/bundles.png) | ![Product network graph](docs/screenshots/network.png) |
| **Customer segments (RFM)** | **Super admin: AI usage per store** |
| ![RFM customer segments](docs/screenshots/customers-rfm.png) | ![Super-admin dashboard](docs/screenshots/admin.png) |

## Features

**Analytics**
- **Association rules (Apriori).** "Customers who buy X also buy Y", with support, confidence and lift you can tune.
- **Bundles.** Ready-made product pairs to sell together, plus a discount simulator.
- **Product network.** An interactive graph of which products appear in the same baskets.
- **Recommendations.** The best cross-sell products for any product.
- **Revenue and seasonality.** Revenue by country and year, top products, and peak months, weekdays and hours.
- **Customers.** RFM segments (Champions, At Risk, ...), cohort retention and period-over-period trends.
- **Exports.** PDF reports and CSV files.

**AI features**
- **AI Insights card.** Three to five short insights on the dashboard, each with a suggested action. Every number in the text is checked against the analytics results. If the check fails, Pairly retries once, then shows a template summary instead. Results are cached per store, dataset and thresholds, and a **Regenerate** button makes a fresh set.
- **Ask Pairly.** A chat assistant that answers questions by calling read-only tools: association rules, bundles, product recommendations, revenue breakdown, seasonal trend, RFM segments and top products. Answers stream in, show which tools were used, and say plainly when the data can't answer.
- **Safe by design.**
  - Tools always run on the signed-in user's store. A store id from the model is ignored.
  - Only aggregated results go to the LLM, never customer rows, names or emails.
- **Controls.**
  - AI on/off switch for each store (in Settings) and for the whole platform (super admin).
  - A daily request limit per store.
  - Usage and token counts per store on the super-admin dashboard.
- **Providers.** Groq or Gemini through one OpenAI-compatible gateway, chosen with env vars. Without a key, Pairly still works and shows template summaries.

**Platform**
- Stores, store managers and a super admin, with JWT sign-in, password reset and an audit log.
- Each store's data is isolated. Every endpoint resolves the store on the server.
- Scheduled re-analysis with email summaries.

## Tech stack

| Part | Tools |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (or SQLite) |
| Analytics | pandas, NumPy, mlxtend (Apriori), ReportLab (PDF) |
| AI | Groq or Gemini via an OpenAI-compatible API (httpx), tool calling, Server-Sent Events |
| Frontend | React 19, Vite 7, Tailwind CSS 3, Recharts, react-force-graph |
| Quality | pytest (with a mock LLM), Ruff, ESLint, GitHub Actions |
| Deploy | Docker, docker compose, Render (API + database), Vercel or Cloudflare Pages (web app) |

How the parts connect: [docs/architecture.md](docs/architecture.md).

## Quick start

### Option 1: Docker (everything in one command)

You need Docker Desktop (or Docker Engine with compose).

```bash
git clone https://github.com/ibrahim123-sia/Pairly.git
cd Pairly
docker compose up --build
```

Open <http://localhost:8080>. This starts PostgreSQL, the API and the web app, and loads the demo data. API docs are at <http://localhost:5000/docs>.

To turn on the AI features, create a file named `.env` next to `docker-compose.yml` with `GROQ_API_KEY=your-key` (or `GEMINI_API_KEY=...`), then run `docker compose up` again.

### Option 2: Run it yourself

You need Python 3.10+ and Node.js 20.19+ (or 22). The backend uses SQLite unless you set `DATABASE_URL`.

**1. Backend** (from the repo root)

macOS / Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python scripts/seed_demo.py
python run.py
```

Windows (PowerShell):

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python scripts/seed_demo.py
python run.py
```

If PowerShell blocks `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use Command Prompt with `.venv\Scripts\activate.bat`.

The API runs on <http://localhost:5000> (docs at `/docs`).

**2. Frontend** (in a second terminal, same commands on every OS)

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite forwards `/api` to the backend.

**3. AI (optional).** Put `GROQ_API_KEY=...` or `GEMINI_API_KEY=...` in `backend/.env` and restart the backend.

### Configuration

All settings are environment variables. The full list with comments is in [`backend/.env.example`](backend/.env.example) and [`frontend/.env.example`](frontend/.env.example). The main ones:

| Variable | What it does |
|---|---|
| `APP_ENV` | `development` or `production`. Production refuses to start with the example secrets. |
| `APP_DEBUG` | Auto-reload in development (default `true`). `FLASK_ENV` / `FLASK_DEBUG` still work as fallbacks. |
| `SECRET_KEY`, `JWT_SECRET_KEY` | Signing secrets; use long random strings |
| `DATABASE_URL` | PostgreSQL URL; empty means a local SQLite file |
| `DATA_DIR` | Where uploaded datasets and exports are stored |
| `FRONTEND_URL` | Web app address, used in emails and always allowed by CORS |
| `ALLOWED_ORIGINS`, `ALLOWED_ORIGIN_REGEX` | Extra CORS origins, and a regex for preview deploys |
| `SUPER_ADMIN_EMAIL`, `SUPER_ADMIN_PASSWORD` | The super admin created on startup |
| `LLM_PROVIDER`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `LLM_MODEL` | AI provider and model (all optional) |
| `AI_ENABLED`, `AI_DAILY_REQUEST_LIMIT` | Default platform AI switch and requests per store per day |
| `MAIL_*` | SMTP settings; `MAIL_SUPPRESS_SEND=true` logs emails instead of sending them |
| `VITE_API_BASE_URL` (frontend) | Full API URL when the API is on another domain, e.g. `https://pairly-api.onrender.com/api` |

## Demo logins

After `python scripts/seed_demo.py` or `docker compose up`:

| Role | Email | Password |
|---|---|---|
| Store manager (Demo Store) | `demo@example.com` | `Demo@12345` |
| Super admin | `admin@example.com` | `Admin@12345` |

These are local demo accounts. On a public deployment, set your own `SUPER_ADMIN_PASSWORD` (production refuses the example one) and share only the store manager login.

The seed loads `backend/app/demo/sample_transactions.csv` (see [Demo data](#demo-data)). To load another file: `python scripts/seed_demo.py --file path/to/file.csv`.

## Project structure

```
Pairly/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app, CORS, routers
│   │   ├── demo/               # sample_transactions.csv (4.6 MB demo data)
│   │   ├── dependencies.py     # auth and store scoping
│   │   ├── models/             # SQLAlchemy models (incl. AI tables)
│   │   ├── routers/            # auth, admin, store, analytics, ai
│   │   ├── services/           # analytics, datasets, email, exports, ...
│   │   │   └── ai/             # LLM gateway, number check, tools, insights, assistant
│   │   └── utils/
│   ├── migrations/             # Alembic
│   ├── scripts/                # seed_demo.py, make_sample.py
│   ├── templates/email/
│   ├── tests/                  # pytest (mock LLM, no network) + fixtures/
│   ├── config.py · run.py · alembic.ini · pyproject.toml
│   ├── requirements.txt · requirements-dev.txt
│   ├── Dockerfile · .dockerignore · docker-entrypoint.sh
│   └── .env.example
├── frontend/
│   ├── src/                    # pages, components, layouts, api, context
│   ├── public/
│   ├── nginx/                  # nginx config for the Docker image
│   ├── Dockerfile · vercel.json · vite.config.js
│   └── .env.example
├── docs/
│   ├── architecture.md
│   └── screenshots/
├── .github/                    # CI workflow, issue and PR templates
├── docker-compose.yml · render.yaml
└── LICENSE · SECURITY.md · CONTRIBUTING.md · CHANGELOG.md
```

## Tests

```bash
# backend (from backend/)
pip install -r requirements-dev.txt
ruff check .
pytest

# frontend (from frontend/)
npm run lint
npm run build
```

Backend tests use a temporary database and a mock LLM, and block all network access, so they never call a real API. They cover:

- the API and the market basket math,
- exact rules and bundles from a small fixture with planted product pairs,
- the number check,
- tool store scoping (store A can never read store B),
- the template fallback,
- the chat stream,
- the AI switches and limits.

GitHub Actions runs everything on each push and pull request, including migrations against PostgreSQL and a full `docker compose` start.

## Deployment

The API and database go on **Render**, and the web app on **Vercel** or **Cloudflare Pages**.

1. **API on Render.** In Render, choose *New → Blueprint* and pick this repo. [`render.yaml`](render.yaml) creates the Docker web service and a PostgreSQL database. It generates `SECRET_KEY` and `JWT_SECRET_KEY` and asks you for:
   - `SUPER_ADMIN_EMAIL` and `SUPER_ADMIN_PASSWORD`
   - `FRONTEND_URL`. Use your web app's URL; you can fill it in after step 2.
   - `GROQ_API_KEY` (optional)
   - `ALLOWED_ORIGIN_REGEX` (optional, for preview URLs)

   On each start the container runs migrations and loads the demo data.
2. **Web app on Vercel.** Import the repo and set **Root Directory** to `frontend`. Add the variable `VITE_API_BASE_URL=https://<your-render-service>.onrender.com/api`, then deploy.
   **Or Cloudflare Pages:** set the root directory to `frontend`, the build command to `npm run build` and the output to `dist`, with the same variable.
3. Set `FRONTEND_URL` on Render to the web app's URL (no trailing slash) so CORS allows it.

Notes for the free plans:
- The Render web service sleeps when idle, so the first request takes about a minute.
- Uploaded files live on the container disk and are lost on redeploy. The demo data reloads automatically.

## Demo data

Pairly works on each store's own sales data, uploaded as CSV or Excel on the **My Datasets** page. The repo has two small files for the demo and the tests; no other data is tracked.

| File | What it is |
|---|---|
| `backend/app/demo/sample_transactions.csv` | About 57,000 rows (2,668 whole invoices, 4.6 MB), loaded into the demo store by `scripts/seed_demo.py` |
| `backend/tests/fixtures/transactions_small.csv` | 315 hand-designed rows with planted product pairs, so tests can check exact rules and bundles (`tests/fixtures/make_fixture.py`) |

**Attribution.** The demo sample comes from the **Online Retail II** dataset by Daqing Chen, UCI Machine Learning Repository, <https://archive.ics.uci.edu/dataset/502/online+retail+ii>, [doi:10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It covers transactions from a UK online gift shop between December 2009 and December 2011.

**Changes made.** Cancelled invoices and rows with no price, quantity or customer ID were removed. Then 8% of invoices were picked at random (seed 42), keeping every line of each chosen invoice, and columns Pairly computes itself were dropped. To rebuild it from a full cleaned export: `python scripts/make_sample.py --source path/to/Online_Retail_II_Cleaned.csv`.

## License

Proprietary. Copyright 2026 Syed Ibrahim Ali, all rights reserved. See [LICENSE](LICENSE). The dataset keeps its own CC BY 4.0 licence.
