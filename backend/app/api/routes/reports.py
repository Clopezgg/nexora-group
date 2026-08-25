import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories import project_repository
from app.schemas.reporting import (
    BudgetVsActualReportResponse,
    TrialBalanceReportResponse,
    TrialBalanceRowResponse,
)
from app.services import reporting_service
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/trial-balance", response_model=TrialBalanceReportResponse)
def get_trial_balance(
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reports.trial_balance", "read")),
) -> TrialBalanceReportResponse:
    assert_company_access(
        db, user_id=user.id, resource="reports.trial_balance", action="read", company_id=company_id
    )
    report = reporting_service.trial_balance(db, company_id=company_id)
    return TrialBalanceReportResponse(
        rows=[
            TrialBalanceRowResponse(
                account_code=row.account_code,
                account_name=row.account_name,
                debit_balance=row.debit_balance,
                credit_balance=row.credit_balance,
            )
            for row in report.rows
        ],
        total_debit=report.total_debit,
        total_credit=report.total_credit,
    )


@router.get("/budget-vs-actual", response_model=BudgetVsActualReportResponse)
def get_budget_vs_actual(
    project_id: uuid.UUID = Query(alias="projectId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("reports.budget_vs_actual", "read")),
) -> BudgetVsActualReportResponse:
    project = project_repository.get_by_id(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    assert_company_access(
        db,
        user_id=user.id,
        resource="reports.budget_vs_actual",
        action="read",
        company_id=project.company_id,
    )
    report = reporting_service.budget_vs_actual(db, project_id=project_id)
    return BudgetVsActualReportResponse(
        authorized=report.authorized,
        committed=report.committed,
        accrued=report.accrued,
        paid=report.paid,
        available=report.available,
    )
