from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.accounting import AccountingDocument
from app.models.company import Company
from app.models.currency import Currency
from app.models.document_type import DocumentType
from app.models.project import Project


def _seed_minimal_catalog(db_session) -> Company:
    """No depende del bootstrap del lifespan (que solo corre vía el fixture
    `client`): siembra directamente lo mínimo indispensable para poder
    insertar un AccountingDocument y así aislar el CHECK constraint bajo
    prueba de cualquier otra FK."""
    db_session.add(Currency(code="HNL", name="Lempira hondureño", symbol="L"))
    db_session.add(DocumentType(code="JRN", name="Asiento contable manual", number_prefix="JRN"))
    company = Company(name="Constructora Constraint Test")
    db_session.add(company)
    db_session.flush()
    return company


def test_check_constraint_rejects_central_scope_with_project(db_session):
    """INV-OPS-001, a nivel de constraint REAL de PostgreSQL, sin pasar por
    el service layer. Se usa un project_id que sí existe (FK válida) para
    aislar que lo que falla es el CHECK, no una FK."""
    company = _seed_minimal_catalog(db_session)
    project = Project(company_id=company.id, name="Torre Nexora I", status="ACTIVE")
    db_session.add(project)
    db_session.flush()

    bad_document = AccountingDocument(
        company_id=company.id,
        document_type_code="JRN",
        document_number="JRN-TEST-000001",
        scope="CENTRAL",
        project_id=project.id,
        currency_code="HNL",
        fx_rate=Decimal("1"),
        status="DRAFT",
    )
    db_session.add(bad_document)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_check_constraint_rejects_project_scope_without_project(db_session):
    """INV-OPS-003 a nivel de constraint real."""
    company = _seed_minimal_catalog(db_session)

    bad_document = AccountingDocument(
        company_id=company.id,
        document_type_code="JRN",
        document_number="JRN-TEST-000002",
        scope="PROJECT",
        project_id=None,
        currency_code="HNL",
        fx_rate=Decimal("1"),
        status="DRAFT",
    )
    db_session.add(bad_document)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_check_constraint_accepts_valid_general_scope(db_session):
    """Control positivo: la misma combinación pero válida (GENERAL sin
    project) debe insertarse sin error, probando que el CHECK no es
    sobre-restrictivo."""
    company = _seed_minimal_catalog(db_session)

    good_document = AccountingDocument(
        company_id=company.id,
        document_type_code="JRN",
        document_number="JRN-TEST-000003",
        scope="GENERAL",
        project_id=None,
        currency_code="HNL",
        fx_rate=Decimal("1"),
        status="DRAFT",
    )
    db_session.add(good_document)
    db_session.flush()
    db_session.rollback()
