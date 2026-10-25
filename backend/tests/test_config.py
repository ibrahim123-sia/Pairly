"""Config: APP_* names with FLASK_* fallback, CORS origins, production guard."""
import pytest

import config as cfg


def test_app_env_falls_back_to_flask_env(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("FLASK_ENV", "production")
    assert cfg._env("APP_ENV", "FLASK_ENV", "development") == "production"
    monkeypatch.setenv("APP_ENV", "development")
    assert cfg._env("APP_ENV", "FLASK_ENV", "development") == "development"


def test_origins_include_frontend_url_and_strip_slashes():
    origins = cfg._origins("https://a.example.com/, https://b.example.com ,", "https://pairly.example.com/")
    assert origins == ["https://a.example.com", "https://b.example.com", "https://pairly.example.com"]
    assert cfg._origins("https://x.example.com", "https://x.example.com/") == ["https://x.example.com"]


def test_production_refuses_example_secrets(monkeypatch):
    monkeypatch.setattr(cfg.Config, "APP_ENV", "production")
    monkeypatch.setattr(cfg.Config, "SECRET_KEY", "dev-secret")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        cfg.Config.validate()

    monkeypatch.setattr(cfg.Config, "SECRET_KEY", "a-real-long-secret-value")
    monkeypatch.setattr(cfg.Config, "JWT_SECRET_KEY", "another-real-secret-value")
    monkeypatch.setattr(cfg.Config, "SUPER_ADMIN_PASSWORD", "Admin@12345")
    with pytest.raises(RuntimeError, match="SUPER_ADMIN_PASSWORD"):
        cfg.Config.validate()

    monkeypatch.setattr(cfg.Config, "SUPER_ADMIN_PASSWORD", "a-strong-password-9")
    cfg.Config.validate()


def test_development_allows_example_secrets(monkeypatch):
    monkeypatch.setattr(cfg.Config, "APP_ENV", "development")
    monkeypatch.setattr(cfg.Config, "SECRET_KEY", "dev-secret")
    cfg.Config.validate()


def test_cors_allows_the_frontend(client):
    from config import get_config
    origin = get_config().FRONTEND_URL
    r = client.options("/api/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == origin
    r = client.options("/api/health", headers={"Origin": "https://evil.example.com",
                                               "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers


def test_postgres_urls_pin_the_psycopg2_driver():
    from app.database import normalize_db_url
    assert normalize_db_url("postgres://u:p@h/db") == "postgresql+psycopg2://u:p@h/db"
    assert normalize_db_url("postgresql://u:p@h/db?sslmode=require") == "postgresql+psycopg2://u:p@h/db?sslmode=require"
    assert normalize_db_url("postgresql+psycopg2://u@h/db") == "postgresql+psycopg2://u@h/db"
    assert normalize_db_url("sqlite:///x.sqlite") == "sqlite:///x.sqlite"
