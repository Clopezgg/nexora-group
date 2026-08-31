from app.schemas.base import CamelModel


class ExceptionResponse(CamelModel):
    code: str
    severity: str
    title: str
    detail: str
    count: int
    suggested_action: str
    route: str | None = None


class ExceptionCenterResponse(CamelModel):
    exception_zero: bool
    total: int
    critical_count: int
    exceptions: list[ExceptionResponse]
