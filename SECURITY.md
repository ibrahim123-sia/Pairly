# Security

## Reporting a problem

Please do not open a public issue for security problems.
Use GitHub's private reporting instead: **Security → Report a vulnerability** on this repository.

Include what you found, how to reproduce it, and what an attacker could do with it.
You should get a reply within a few days.

## How Pairly protects data

- **Store isolation.** Every analytics, dataset, export and AI endpoint resolves the store from the signed-in user on the server. A store manager can only reach their own store.
- **AI tools are read-only and server-scoped.** The assistant's tools never take a store id from the model. They only read aggregated results (rules, bundles, segment totals), never raw customer rows, names or emails.
- **Passwords** are hashed with bcrypt. Logins lock after repeated failures.
- **Tokens** are short-lived JWT access tokens plus refresh tokens.
- **Production checks.** With `APP_ENV=production` the API refuses to start if `SECRET_KEY`, `JWT_SECRET_KEY` or `SUPER_ADMIN_PASSWORD` still use example values.
- **Internal endpoint.** `POST /api/internal/scheduled-jobs/run` (used by the Cloudflare Cron Trigger) requires the `X-Cron-Secret` header to match `CRON_SECRET`, compared in constant time. Without `CRON_SECRET` it returns 404.
- **Secrets** live only in environment variables. `.env` files are git-ignored; only `.env.example` files with placeholders are committed.

## Supported versions

Only the latest version on `main` gets fixes.
