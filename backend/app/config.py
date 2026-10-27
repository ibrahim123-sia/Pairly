import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _env(name, legacy=None, default=None):
    """Read an env var, falling back to an older name (e.g. FLASK_ENV)."""
    value = os.environ.get(name)
    if value is None and legacy:
        value = os.environ.get(legacy)
    return default if value is None else value


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _origins(raw, *extra):
    origins = []
    for o in [*(raw or "").split(","), *extra]:
        o = (o or "").strip().rstrip("/")
        if o and o not in origins:
            origins.append(o)
    return origins


# Values that must never reach production.
INSECURE_DEFAULTS = {
    "dev-secret",
    "change-me-to-a-long-random-string",
    "change-me-to-another-long-random-string",
    "Admin@12345",
    "ChangeMeOnFirstLogin!",
}


class Config:
    APP_ENV = _env("APP_ENV", "FLASK_ENV", "development").strip().lower()

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=_int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES"), 900))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=_int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES"), 604800))
    JWT_TOKEN_LOCATION = ["headers"]

    # backend/ (this file lives in backend/app/)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.abspath(os.environ.get("DATA_DIR") or os.path.join(BASE_DIR, "data"))
    STORES_DIR = os.path.join(DATA_DIR, "stores")
    DEMO_DATASET_PATH = os.environ.get("DEMO_DATASET_PATH") or os.path.join(
        BASE_DIR, "app", "demo", "sample_transactions.csv"
    )

    _db_url = os.environ.get("DATABASE_URL") or "sqlite:///data/app.sqlite"
    if _db_url.startswith("sqlite:///") and not _db_url.startswith("sqlite:////"):
        rel = _db_url.replace("sqlite:///", "", 1)
        if not os.path.isabs(rel):
            _db_url = "sqlite:///" + os.path.join(BASE_DIR, rel).replace("\\", "/")
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = _int(os.environ.get("MAIL_PORT"), 587)
    MAIL_USE_TLS = _bool(os.environ.get("MAIL_USE_TLS"), True)
    MAIL_USE_SSL = _bool(os.environ.get("MAIL_USE_SSL"), False)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME") or None
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD") or None
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "Pairly <no-reply@example.com>")
    MAIL_SUPPRESS_SEND = _bool(os.environ.get("MAIL_SUPPRESS_SEND"), False)

    SUPER_ADMIN_EMAIL = os.environ.get("SUPER_ADMIN_EMAIL", "admin@example.com")
    SUPER_ADMIN_PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", "Admin@12345")
    SUPER_ADMIN_NAME = os.environ.get("SUPER_ADMIN_NAME", "Super Admin")

    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173").strip().rstrip("/")
    # FRONTEND_URL is always allowed, so a single-frontend deploy only needs FRONTEND_URL.
    ALLOWED_ORIGINS = _origins(os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173"), FRONTEND_URL)
    # Optional regex for preview deploys, e.g. ^https://.*\.pairly\.pages\.dev$
    ALLOWED_ORIGIN_REGEX = os.environ.get("ALLOWED_ORIGIN_REGEX") or None

    MAX_UPLOAD_MB = _int(os.environ.get("MAX_UPLOAD_MB"), 50)
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    MAX_ROWS_PER_DATASET = _int(os.environ.get("MAX_ROWS_PER_DATASET"), 1_000_000)

    PASSWORD_RESET_TTL_MINUTES = _int(os.environ.get("PASSWORD_RESET_TTL_MINUTES"), 60)
    LOGIN_LOCKOUT_THRESHOLD = _int(os.environ.get("LOGIN_LOCKOUT_THRESHOLD"), 5)
    LOGIN_LOCKOUT_MINUTES = _int(os.environ.get("LOGIN_LOCKOUT_MINUTES"), 15)

    # --- AI layer ---
    # LLM_PROVIDER: groq | gemini | none. Empty picks the first provider with a key.
    LLM_PROVIDER = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or None
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or None
    LLM_MODEL = os.environ.get("LLM_MODEL") or None
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL") or None
    LLM_TIMEOUT_SECONDS = _float(os.environ.get("LLM_TIMEOUT_SECONDS"), 30.0)
    AI_ENABLED = _bool(os.environ.get("AI_ENABLED"), True)
    AI_DAILY_REQUEST_LIMIT = _int(os.environ.get("AI_DAILY_REQUEST_LIMIT"), 50)

    # --- File storage (see app/services/storage.py) ---
    R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID") or None
    R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID") or None
    R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY") or None
    R2_BUCKET = os.environ.get("R2_BUCKET") or None
    STORAGE_BACKEND = (os.environ.get("STORAGE_BACKEND") or ("r2" if R2_BUCKET else "local")).strip().lower()

    # --- Scheduled jobs ---
    # internal: APScheduler inside the API process (development, docker compose).
    # external: an outside timer (Cloudflare Cron Trigger) calls
    #           POST /api/internal/scheduled-jobs/run with header X-Cron-Secret.
    SCHEDULER_MODE = (os.environ.get("SCHEDULER_MODE") or "internal").strip().lower()
    CRON_SECRET = os.environ.get("CRON_SECRET") or None

    DEBUG = _bool(_env("APP_DEBUG", "FLASK_DEBUG"), True)

    @classmethod
    def validate(cls):
        """Refuse to run in production with the example secrets."""
        if cls.APP_ENV != "production":
            return
        bad = [
            name for name in ("SECRET_KEY", "JWT_SECRET_KEY", "SUPER_ADMIN_PASSWORD")
            if getattr(cls, name) in INSECURE_DEFAULTS
        ]
        if bad:
            raise RuntimeError(
                "APP_ENV=production but these settings still use example values: "
                + ", ".join(bad)
                + ". Set real values in the environment."
            )


class DevelopmentConfig(Config):
    pass


class ProductionConfig(Config):
    DEBUG = False


def get_config():
    if Config.APP_ENV == "production":
        return ProductionConfig
    return DevelopmentConfig
