import uuid

from fastapi import Header


def get_correlation_id(x_correlation_id: str | None = Header(default=None)) -> str:
    return x_correlation_id or str(uuid.uuid4())
