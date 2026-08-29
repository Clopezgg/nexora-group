import uuid

from app.schemas.base import CamelModel


class RoleAccessResponse(CamelModel):
    id: uuid.UUID
    name: str
    assigned: bool


class CompanyAccessResponse(CamelModel):
    id: uuid.UUID
    name: str
    assigned: bool


class ProjectAccessResponse(CamelModel):
    id: uuid.UUID
    company_id: uuid.UUID
    code: str | None
    name: str
    assigned: bool


class UserAccessSummaryResponse(CamelModel):
    user_id: uuid.UUID
    roles: list[RoleAccessResponse]
    companies: list[CompanyAccessResponse]
    projects: list[ProjectAccessResponse]
