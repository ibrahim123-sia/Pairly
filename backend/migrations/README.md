# Migrations

Plain Alembic. Run every command from `backend/`.

```bash
alembic upgrade head                          # apply all migrations
alembic revision --autogenerate -m "message"  # new migration after a model change
alembic current                               # show the applied revision
```

The app also calls `Base.metadata.create_all()` on startup, so a fresh local
SQLite database works without running Alembic. Each migration skips tables
that already exist, so `alembic upgrade head` is safe on such a database too.
