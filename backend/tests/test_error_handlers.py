import asyncio

from sqlalchemy.exc import IntegrityError

from app.api.error_handlers import _integrity_error_handler


def test_integrity_error_handler_returns_clean_422_without_leaking_sql():
    """DEFERRED-FINAL-015 (parte b): red de seguridad genérica -- cualquier
    IntegrityError que llegue sin pasar por un `assert_*_belongs_to_company`
    específico (p.ej. un dominio nuevo que todavía no valide una FK
    opcional) debe devolver un 422 controlado, nunca un 500 sin capturar
    ni el mensaje real de psycopg (que puede exponer nombres de tabla/
    columna) en el body de la respuesta."""
    fake_exc = IntegrityError(
        "INSERT INTO non_conformances ...",
        params={},
        orig=Exception('insert or update on table "non_conformances" violates foreign key constraint'),
    )

    response = asyncio.run(_integrity_error_handler(None, fake_exc))

    assert response.status_code == 422
    body = response.body.decode()
    assert '"code":"NXR-DATA-001"' in body
    assert "non_conformances" not in body
    assert "foreign key" not in body
