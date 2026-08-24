from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.routes import accounting, auth, context, dashboard, health, master_data, projects
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

    register_error_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(context.router, prefix="/api")
    app.include_router(master_data.router, prefix="/api")
    app.include_router(accounting.router, prefix="/api")
    app.include_router(projects.router, prefix="/api")

    return app


app = create_app()
