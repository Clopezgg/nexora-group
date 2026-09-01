"""ORDEN MAESTRA DEFINITIVA DE INTEGRACIÓN §26.

`voucher_service` leía `supplier.address_line_1` / `city` / `country`, campos
que no existían en el modelo `Supplier` — el bloque de dirección del
beneficiario salía siempre vacío. Ahora el modelo tiene dirección
estructurada canónica y `format_supplier_address` recurre al texto libre
`address` cuando la estructurada está vacía.
"""
from types import SimpleNamespace

from app.models.supplier import Supplier
from app.services.voucher_service import format_supplier_address


def test_supplier_model_has_the_structured_address_fields():
    columns = set(Supplier.__table__.columns.keys())
    assert {
        "address",
        "address_line_1",
        "address_line_2",
        "city",
        "state_department",
        "country",
    } <= columns


def test_structured_address_is_preferred_and_joined():
    supplier = SimpleNamespace(
        address_line_1="Col. Palmira, 3a calle",
        address_line_2="Edificio Nexora, piso 4",
        city="Tegucigalpa",
        state_department="Francisco Morazán",
        country="HN",
        address="texto viejo que no debe usarse",
    )
    assert format_supplier_address(supplier) == (
        "Col. Palmira, 3a calle · Edificio Nexora, piso 4 · "
        "Tegucigalpa · Francisco Morazán · HN"
    )


def test_falls_back_to_legacy_free_text_address():
    supplier = SimpleNamespace(
        address_line_1=None,
        address_line_2=None,
        city=None,
        state_department=None,
        country=None,
        address="  Barrio Guadalupe, Comayagüela  ",
    )
    assert format_supplier_address(supplier) == "Barrio Guadalupe, Comayagüela"


def test_returns_none_when_no_address_at_all():
    supplier = SimpleNamespace(
        address_line_1=None, city=None, state_department=None, country=None, address=None
    )
    assert format_supplier_address(supplier) is None
