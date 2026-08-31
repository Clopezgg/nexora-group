import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_correlation import get_correlation_id
from app.schemas.closing import (
    ClosingCheckResponse,
    ClosingManifestResponse,
    HardCloseRequest,
    PreCloseChecklistResponse,
)
from app.services import audit_service, closing_service
from app.services.closing_service import ClosingBlockedError
from app.services.permission_service import assert_company_access, require_permission

router = APIRouter(prefix="/accounting/closing", tags=["accounting-closing"])


@router.get("/checklist", response_model=PreCloseChecklistResponse)
def get_checklist(
    company_id: uuid.UUID = Query(alias="companyId"),
    period_id: uuid.UUID = Query(alias="periodId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.closing", "read")),
) -> PreCloseChecklistResponse:
    assert_company_access(
        db, user_id=user.id, resource="accounting.closing", action="read", company_id=company_id
    )
    try:
        checklist = closing_service.build_checklist(
            db, company_id=company_id, period_id=period_id
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return PreCloseChecklistResponse(
        period_id=uuid.UUID(checklist.period_id),
        period_label=checklist.period_label,
        period_status=checklist.period_status,
        can_hard_close=checklist.can_hard_close,
        checks=[
            ClosingCheckResponse(
                key=c.key, label=c.label, passed=c.passed, blocking=c.blocking, detail=c.detail
            )
            for c in checklist.checks
        ],
    )


@router.post("/{period_id}/hard-close", response_model=ClosingManifestResponse)
def hard_close(
    period_id: uuid.UUID,
    payload: HardCloseRequest,
    company_id: uuid.UUID = Query(alias="companyId"),
    db: Session = Depends(get_db),
    user=Depends(require_permission("accounting.closing", "execute")),
    correlation_id: str = Depends(get_correlation_id),
) -> ClosingManifestResponse:
    assert_company_access(
        db, user_id=user.id, resource="accounting.closing", action="execute", company_id=company_id
    )
    try:
        manifest = closing_service.hard_close(
            db,
            company_id=company_id,
            period_id=period_id,
            force=payload.force,
            reason=payload.reason,
        )
        audit_service.record(
            db,
            actor_user_id=user.id,
            action="accounting.closing.hard_close",
            entity_type="fiscal.period",
            entity_id=period_id,
            company_id=company_id,
            project_id=None,
            before={"status": "OPEN_OR_SOFT_CLOSED"},
            after={"status": "CLOSED", "forced": manifest["forced"], "reason": manifest["forceReason"]},
            correlation_id=correlation_id,
        )
        db.commit()
    except ClosingBlockedError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    except Exception:
        db.rollback()
        raise
    return ClosingManifestResponse(
        period_id=uuid.UUID(manifest["periodId"]),
        period_label=manifest["periodLabel"],
        company_id=uuid.UUID(manifest["companyId"]),
        closed_at=manifest["closedAt"],
        forced=manifest["forced"],
        force_reason=manifest["forceReason"],
        checks=[
            ClosingCheckResponse(
                key=c["key"],
                label=c["label"],
                passed=c["passed"],
                blocking=c["blocking"],
                detail=c["detail"],
            )
            for c in manifest["checks"]
        ],
    )
