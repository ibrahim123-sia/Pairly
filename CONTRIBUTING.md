# Contributing

Pairly is proprietary (see [LICENSE](LICENSE)). Contributions are by invitation.
If you have been invited, this is how to work on it.

## Setup

Follow **Quick start** in the [README](README.md). For backend work also install the dev tools:

```bash
cd backend
pip install -r requirements-dev.txt
```

## Before you open a pull request

```bash
# backend (from backend/)
ruff check .
pytest

# frontend (from frontend/)
npm run lint
npm run build
```

CI runs the same checks on every pull request.

## Guidelines

- Keep pull requests small and focused on one change.
- Write commit messages in the imperative, e.g. `fix: handle empty basket`.
- Add or update tests for behaviour changes. Tests must never call a real LLM API; use the mock in `backend/tests`.
- Numbers shown to users come from the analytics code. The AI layer only explains them.
- Never commit secrets, real customer data or personal contact details.
- Change the database through an Alembic migration (`alembic revision --autogenerate -m "..."`).
