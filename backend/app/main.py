from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.correlation import CorrelationIdMiddleware
from app.api.csrf import register_csrf_guard
from app.api.edit_access_guard import register_edit_access_guard
from app.api.error_handlers import register_error_handlers
from app.api.routes import (
    access_management,
    accounting,
    ap,
    approvals,
    ar,
    assets,
    audit,
    auth,
    closing,
    company_management,
    context,
    contract_payments,
    crm,
    dashboard,
    documents,
    edit_access,
    equipment,
    evidence,
    financial_control,
    financial_reversals,
    fiscal,
    health,
    inventory,
    master_data,
    master_dimensions,
    notifications,
    preferences,
    procurement,
    project_budget_management,
    project_extended_control,
    project_management,
    projects,
    quality,
    reports,
    rfi,
    safety,
    search,
    site_reports,
    submittals,
    suppliers,
    treasury,
    treasury_advanced,
    voucher_verification,
    workforce,
)
from app.api.security_headers import register_security_headers
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
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
    configure_logging()

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
    app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
    register_csrf_guard(app)
    register_edit_access_guard(app)
    app.add_middleware(CorrelationIdMiddleware)
    register_security_headers(app)

    register_error_handlers(app)

    from app.services import (
        ap_service,
        approval_service,
        submittal_service,
    )
    from app.services.reversal_hooks import register_default_reversal_hooks

    register_default_reversal_hooks()

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
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(edit_access.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(financial_control.router, prefix="/api")
    app.include_router(closing.router, prefix="/api")
    app.include_router(context.router, prefix="/api")
    app.include_router(contract_payments.router, prefix="/api")
    app.include_router(master_data.router, prefix="/api")
    app.include_router(access_management.router, prefix="/api")
    app.include_router(master_dimensions.router, prefix="/api")
    app.include_router(company_management.router, prefix="/api")
    app.include_router(fiscal.router, prefix="/api")
    app.include_router(accounting.router, prefix="/api")
    app.include_router(suppliers.router, prefix="/api")
    app.include_router(procurement.router, prefix="/api")
    app.include_router(inventory.router, prefix="/api")
    app.include_router(projects.router, prefix="/api")
    app.include_router(project_management.router, prefix="/api")
    app.include_router(project_budget_management.router, prefix="/api")
    app.include_router(project_extended_control.router, prefix="/api")
    app.include_router(treasury.router, prefix="/api")
    app.include_router(treasury_advanced.router, prefix="/api")
    app.include_router(ap.router, prefix="/api")
    app.include_router(ar.router, prefix="/api")
    app.include_router(financial_reversals.router, prefix="/api")
    app.include_router(assets.router, prefix="/api")
    app.include_router(equipment.router, prefix="/api")
    app.include_router(workforce.router, prefix="/api")
    app.include_router(crm.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(evidence.router, prefix="/api")
    app.include_router(rfi.router, prefix="/api")
    app.include_router(submittals.router, prefix="/api")
    app.include_router(site_reports.router, prefix="/api")
    app.include_router(quality.router, prefix="/api")
    app.include_router(safety.router, prefix="/api")
    app.include_router(audit.router, prefix="/api")
    app.include_router(approvals.router, prefix="/api")
    app.include_router(notifications.router, prefix="/api")
    app.include_router(preferences.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(voucher_verification.router, prefix="/api")

    return app


app = create_app()
