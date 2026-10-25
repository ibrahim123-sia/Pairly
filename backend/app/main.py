import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, SessionLocal, engine
from app.routers.admin import router as admin_router
from app.routers.ai import admin_router as ai_admin_router
from app.routers.ai import router as ai_router
from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.internal import router as internal_router
from app.routers.store import router as store_router
from app.services import auth_service, scheduler_service
from config import get_config

config = get_config()
config.validate()
logger = logging.getLogger("pairly")

APP_NAME = "Pairly"
APP_TAGLINE = "Find which products sell together, and turn it into bundles and revenue."
APP_VERSION = "3.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure data directories exist
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.STORES_DIR, exist_ok=True)

    # Automatically create database tables if they do not exist
    # This acts as an initial bootstrap on PostgreSQL / SQLite
    Base.metadata.create_all(bind=engine)

    # Ensure super admin is created
    db = SessionLocal()
    try:
        auth_service.ensure_super_admin(db)
    except Exception as exc:
        logger.warning("Pairly could not bootstrap the super admin on startup: %s", exc)
    finally:
        db.close()

    # Initialize the background scheduler
    scheduler_service.init_scheduler()

    yield

    # Shutdown scheduler on app exit
    scheduler = scheduler_service.get_scheduler()
    if scheduler:
        try:
            scheduler.shutdown()
        except Exception:
            pass


app = FastAPI(
    title=f"{APP_NAME} API",
    description=APP_TAGLINE,
    version=APP_VERSION,
    lifespan=lifespan,
)

# CORS: FRONTEND_URL + ALLOWED_ORIGINS (+ optional ALLOWED_ORIGIN_REGEX for preview deploys).
# Auth uses bearer headers, not cookies; credentials stay on unless "*" is configured.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_origin_regex=config.ALLOWED_ORIGIN_REGEX,
    allow_credentials="*" not in config.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(store_router, prefix="/api/store", tags=["Store"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI"])
app.include_router(ai_admin_router, prefix="/api/admin/ai", tags=["Admin", "AI"])
app.include_router(internal_router, prefix="/api/internal", tags=["Internal"], include_in_schema=False)


@app.get("/")
def index():
    return {
        "name": f"{APP_NAME} API",
        "tagline": APP_TAGLINE,
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
    }
