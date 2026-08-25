from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.routes import (
    accounting,
    ap,
    approvals,
    ar,
    assets,
    audit,
    auth,
    context,
    crm,
    dashboard,
    documents,
    equipment,
    evidence,
    health,
    inventory,
    master_data,
    notifications,
    procurement,
    projects,
    quality,
    reports,
    rfi,
    safety,
    site_reports,
    submittals,
    suppliers,
    treasury,
    workforce,
)
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

    from app.services import ap_service, approval_service, submittal_service

    approval_service.register_decision_adapter(
        "ap.supplier_invoice",
        lambda db, entity_id, decision, decided_by: ap_service.apply_approval_decision(
            db, invoice_id=entity_id, decision=decision
        ),
    )
    approval_service.register_decision_adapter(
        "construction.submittal",
        lambda db, entity_id, decision, decided_by: submittal_service.apply_approval_decision(
            db, submittal_id=entity_id, decision=decision, decided_by=decided_by
        ),
    )

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(context.router, prefix="/api")
    app.include_router(master_data.router, prefix="/api")
    app.include_router(accounting.router, prefix="/api")
    app.include_router(suppliers.router, prefix="/api")
    app.include_router(procurement.router, prefix="/api")
    app.include_router(inventory.router, prefix="/api")
    app.include_router(projects.router, prefix="/api")
    # Track A - Financial Core.
    app.include_router(treasury.router, prefix="/api")
    app.include_router(ap.router, prefix="/api")
    app.include_router(ar.router, prefix="/api")
    # Track D - Enterprise Resources.
    app.include_router(assets.router, prefix="/api")
    app.include_router(equipment.router, prefix="/api")
    app.include_router(workforce.router, prefix="/api")
    # Track E - Commercial (CRM).
    app.include_router(crm.router, prefix="/api")
    # Track D - Construction Control (Documents/Evidence, RFI/Submittals).
    app.include_router(documents.router, prefix="/api")
    app.include_router(evidence.router, prefix="/api")
    app.include_router(rfi.router, prefix="/api")
    app.include_router(submittals.router, prefix="/api")
    # Track D - Construction Control (Daily Site Reports/Quality/Safety).
    app.include_router(site_reports.router, prefix="/api")
    app.include_router(quality.router, prefix="/api")
    app.include_router(safety.router, prefix="/api")
    # Track G - Platform (Audit trail, NXR-REQ-0090; Approval Inbox / SoD,
    # NXR-REQ-0087/0088/0089).
    app.include_router(audit.router, prefix="/api")
    app.include_router(approvals.router, prefix="/api")
    app.include_router(notifications.router, prefix="/api")
    # Track H - Reports/Search/Analytics (NXR-REQ-0093/0094): Trial
    # Balance + Budget vs Actual + CSV export only -- see
    # docs/superpowers/specs/2026-08-25-reports-search-analytics-design.md
    # for what is deliberately out of scope in this phase.
    app.include_router(reports.router, prefix="/api")

    return app


app = create_app()
