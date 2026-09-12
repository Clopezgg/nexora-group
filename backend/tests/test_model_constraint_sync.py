from sqlalchemy import CheckConstraint

from app.models.asset import FixedAsset
from app.models.supplier import Supplier


def _check_names(model: type) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, CheckConstraint) and constraint.name is not None
    }


def test_supplier_model_declares_database_check_constraints() -> None:
    assert {"ck_suppliers_status", "ck_suppliers_party_role"} <= _check_names(Supplier)


def test_fixed_asset_model_declares_disposal_check_constraints() -> None:
    assert {
        "ck_fixed_assets_accumulated_depreciation_non_negative",
        "ck_fixed_assets_disposal_date",
        "ck_fixed_assets_disposal_proceeds_non_negative",
    } <= _check_names(FixedAsset)
