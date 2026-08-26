import uuid

from pydantic import EmailStr

from app.schemas.base import CamelModel


class LoginRequest(CamelModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class CurrentUserResponse(CamelModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    roles: list[str]
