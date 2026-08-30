import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.domain.errors import NotFoundError
from app.models.approval_request import ApprovalRequest
from app.models.role import Role
from app.models.user_role import UserRole


def create(db: Session, **kwargs) -> ApprovalRequest:
    row = ApprovalRequest(**kwargs)
    db.add(row)
    db.flush()
    return row


def get_for_update(db: Session, *, request_id: uuid.UUID) -> ApprovalRequest:
    row = db.execute(
        select(ApprovalRequest).where(ApprovalRequest.id == request_id).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Solicitud de aprobación no encontrada")
    return row


def user_matches_assignment(
    db: Session, *, request: ApprovalRequest, user_id: uuid.UUID
) -> bool:
    """Return whether a user is allowed by the request's explicit assignment.

    A direct user assignment is authoritative. If no user was selected, an
    assigned role is resolved against the user's real roles. Fully unassigned
    requests remain available to any otherwise-authorized approver so generic
    workflows keep their existing behavior.
    """
    if request.assigned_to is not None:
        return request.assigned_to == user_id
    if request.assigned_role is None:
        return True
    stmt = (
        select(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id, Role.name == request.assigned_role)
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def list_assigned_to(
    db: Session, *, user_id: uuid.UUID, company_id: uuid.UUID, module: str | None = None
) -> list[ApprovalRequest]:
    user_role_names = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    assignment = or_(
        ApprovalRequest.assigned_to == user_id,
        and_(
            ApprovalRequest.assigned_to.is_(None),
            ApprovalRequest.assigned_role.in_(user_role_names),
        ),
        and_(
            ApprovalRequest.assigned_to.is_(None),
            ApprovalRequest.assigned_role.is_(None),
        ),
    )
    stmt = select(ApprovalRequest).where(
        assignment,
        ApprovalRequest.company_id == company_id,
        ApprovalRequest.status == "PENDING",
    )
    if module is not None:
        stmt = stmt.where(ApprovalRequest.module == module)
    return list(db.execute(stmt.order_by(ApprovalRequest.created_at.desc())).scalars())
