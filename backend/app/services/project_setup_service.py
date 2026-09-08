from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import InvalidFinancialReferenceError
from app.models.evidence import Evidence
from app.models.project_setup import ProjectSetupRun
from app.models.supplier import Supplier
from app.repositories import project_control_repository, project_repository, supplier_repository
from app.services import audit_service, budget_service, contract_payment_service, document_service
from app.services.permission_service import grant_project_access

STAGED_DOCUMENT_ENTITY = "PROJECT_SETUP_STAGED"


def get_run(db: Session, run_id: uuid.UUID) -> ProjectSetupRun | None:
    return db.get(ProjectSetupRun, run_id)


def get_by_key(db: Session, *, company_id: uuid.UUID, key: str) -> ProjectSetupRun | None:
    return db.execute(select(ProjectSetupRun).where(ProjectSetupRun.company_id == company_id, ProjectSetupRun.idempotency_key == key)).scalar_one_or_none()


def staged_evidence(db: Session, run_id: uuid.UUID) -> list[Evidence]:
    return list(db.execute(select(Evidence).where(Evidence.entity_type == STAGED_DOCUMENT_ENTITY, Evidence.entity_id == run_id).order_by(Evidence.created_at)).scalars())


def create_run(db: Session, *, company_id: uuid.UUID, requested_by: uuid.UUID, key: str, payload: dict, activate: bool) -> ProjectSetupRun:
    run = ProjectSetupRun(company_id=company_id, requested_by=requested_by, idempotency_key=key, payload=payload, activate=activate)
    db.add(run)
    db.flush()
    return run


def execute(db: Session, *, run: ProjectSetupRun, correlation_id: str) -> ProjectSetupRun:
    """Execute every PostgreSQL side effect in one transaction.

    Callers must catch exceptions, roll back, then persist ``FAILED`` in a
    fresh transaction.  That separation preserves a useful checkpoint without
    allowing any partially-created financial/configuration object to escape.
    """
    if run.status == "COMPLETED":
        return run
    p = run.payload
    project_input = {key: value for key, value in p["project"].items() if key != "company_id"}
    project = project_repository.create_project(db, company_id=run.company_id, **project_input)
    grant_project_access(db, user_id=run.requested_by, project_id=project.id)
    audit_service.record(db, actor_user_id=run.requested_by, action="project.create", entity_type="project", entity_id=project.id, company_id=run.company_id, project_id=project.id, before=None, after={"name": project.name, "code": project.code, "setupRunId": str(run.id)}, correlation_id=correlation_id)

    wbs = p.get("wbs") or {}
    wbs_id = None
    if wbs.get("code"):
        node = project_control_repository.create_wbs_node(db, project_id=project.id, code=wbs["code"], name=wbs["name"], planned_start=project.planned_start, planned_finish=project.planned_end)
        wbs_id = node.id
        audit_service.record(db, actor_user_id=run.requested_by, action="project.wbs.create", entity_type="project.wbs", entity_id=node.id, company_id=run.company_id, project_id=project.id, before=None, after={"code": node.code, "name": node.name, "setupRunId": str(run.id)}, correlation_id=correlation_id)

    if p.get("baseline_amount") is not None:
        budget_service.create_baseline(db, project_id=project.id, currency_code=project.currency_code or "", lines=[budget_service.BudgetLineInput(authorized_amount=Decimal(str(p["baseline_amount"])), wbs_node_id=wbs_id, cost_center_id=project.cost_center_id)], notes="Presupuesto BASELINE creado por configuración inicial reanudable.", commit=False)

    contract_input = p.get("contract")
    if contract_input:
        supplier = db.get(Supplier, uuid.UUID(contract_input["supplier_id"]))
        if supplier is None or supplier.company_id != run.company_id or supplier.status != "ACTIVE":
            raise InvalidFinancialReferenceError("El proveedor/contratista debe existir, pertenecer a la compañía y estar ACTIVE")
        contract = supplier_repository.create_contract(
            db, company_id=run.company_id, supplier_id=supplier.id, project_id=project.id,
            contract_number=contract_input["contract_number"], contract_category=contract_input["contract_category"],
            scope_description=None, value=Decimal(str(contract_input["value"])), currency_code=project.currency_code or "",
            start_date=date.fromisoformat(contract_input["start_date"]),
            end_date=date.fromisoformat(contract_input["end_date"]) if contract_input.get("end_date") else None,
            advance_percentage=Decimal(0),
            advance_amount=Decimal(str(contract_input["advance_amount"])) if contract_input.get("advance_amount") is not None else None,
            advance_due_date=date.fromisoformat(contract_input["advance_due_date"]) if contract_input.get("advance_due_date") else None,
            retention_percentage=Decimal(str(contract_input["retention_percentage"])), payment_terms=None,
            payment_terms_type=contract_input["payment_terms_type"],
        )
        audit_service.record(db, actor_user_id=run.requested_by, action="procurement.contract.create", entity_type="procurement.contract", entity_id=contract.id, company_id=run.company_id, project_id=project.id, before=None, after={"contractNumber": contract.contract_number, "setupRunId": str(run.id)}, correlation_id=correlation_id)
        if contract.payment_terms_type != "LUMP_SUM":
            first_period = project.planned_start or contract.start_date
            rows = contract_payment_service.build_contract_plan(contract_value=contract.value, advance_amount=contract.advance_amount or Decimal(0), advance_due_date=contract.advance_due_date, retention_percentage=contract.retention_percentage, regular_months=int(contract_input["regular_months"]), due_day=int(contract_input["due_day"]), first_period=first_period.replace(day=1))
            schedule = contract_payment_service.create_schedule(db, supplier_contract_id=contract.id, schedule_type="MONTHLY" if contract.payment_terms_type == "MONTHLY" else "CUSTOM", installments=rows, due_day=int(contract_input["due_day"]), commit=False)
            audit_service.record(db, actor_user_id=run.requested_by, action="contract.payment_schedule.create", entity_type="contract.payment_schedule", entity_id=schedule.id, company_id=run.company_id, project_id=project.id, before=None, after={"contractNumber": contract.contract_number, "setupRunId": str(run.id)}, correlation_id=correlation_id)

    for evidence in staged_evidence(db, run.id):
        document = document_service.create_document(db, company_id=run.company_id, scope="PROJECT", project_id=project.id, category="OTHER", title=evidence.original_filename, description="Documento inicial cargado en la configuración reanudable del proyecto.", evidence_id=evidence.id, uploaded_by=run.requested_by, commit=False)
        evidence.entity_type = "PROJECT"
        evidence.entity_id = project.id
        audit_service.record(db, actor_user_id=run.requested_by, action="document.document.create", entity_type="document.document", entity_id=document.id, company_id=run.company_id, project_id=project.id, before=None, after={"title": document.title, "setupRunId": str(run.id)}, correlation_id=correlation_id)

    if run.activate:
        project.status = "ACTIVE"
        audit_service.record(db, actor_user_id=run.requested_by, action="project.status.transition", entity_type="project", entity_id=project.id, company_id=run.company_id, project_id=project.id, before={"status": "PLANNING"}, after={"status": "ACTIVE", "setupRunId": str(run.id)}, correlation_id=correlation_id)
    run.project_id = project.id
    run.status = "COMPLETED"
    run.failure_step = None
    run.failure_message = None
    db.flush()
    return run
