from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, context, dashboard, health
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.bootstrap_service import bootstrap_admin_if_needed


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db = SessionLocal()
    try:
        bootstrap_admin_if_needed(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    if settings.applicationinsights_connection_string:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(connection_string=settings.applicationinsights_connection_string)

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(context.router, prefix="/api")

    return app


app = create_app()
