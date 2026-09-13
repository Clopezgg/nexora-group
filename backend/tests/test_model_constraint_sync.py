import pytest
from sqlalchemy import CheckConstraint

from app.models.accounting import AccountingDocument
from app.models.ap import SupplierInvoice
from app.models.approval_request import ApprovalRequest
from app.models.ar import CustomerInvoice
from app.models.asset import FixedAsset
from app.models.change_order import ChangeOrder
from app.models.contract_payment import (
    ContractPaymentInstallment,
    ContractPaymentSchedule,
)
from app.models.crm import Customer, Lead, Quotation, SalesContract
from app.models.idempotency import IdempotencyRecord
from app.models.inventory import PhysicalCount, PhysicalCountLine
from app.models.project import Project
from app.models.supplier import Supplier, SupplierContract
from app.models.voucher_issuance import VoucherIssuance
from app.models.warehouse import Warehouse
from app.models.wbs import WBSNode
from app.models.workforce import Crew


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


@pytest.mark.parametrize(
    ("model", "constraint_names"),
    [
        (AccountingDocument, {"ck_accounting_documents_status_valid"}),
        (SupplierInvoice, {"ck_supplier_invoices_status_valid"}),
        (ApprovalRequest, {"ck_approval_requests_status_valid"}),
        (CustomerInvoice, {"ck_customer_invoices_status_valid"}),
        (ChangeOrder, {"ck_change_orders_status_valid"}),
        (ContractPaymentSchedule, {"ck_contract_payment_schedules_status_valid"}),
        (ContractPaymentInstallment, {"ck_contract_payment_installments_status_valid"}),
        (Customer, {"ck_customers_status_valid"}),
        (Lead, {"ck_leads_status_valid"}),
        (Quotation, {"ck_quotations_status_valid"}),
        (SalesContract, {"ck_sales_contracts_status_valid"}),
        (IdempotencyRecord, {"ck_idempotency_records_status_valid"}),
        (PhysicalCount, {"ck_physical_counts_status_valid"}),
        (
            PhysicalCountLine,
            {
                "ck_physical_count_lines_expected_quantity_non_negative",
                "ck_physical_count_lines_counted_quantity_non_negative",
            },
        ),
        (Project, {"ck_projects_status_valid"}),
        (SupplierContract, {"ck_supplier_contracts_status_valid"}),
        (VoucherIssuance, {"ck_voucher_issuances_status_valid"}),
        (Warehouse, {"ck_warehouses_status_valid"}),
        (WBSNode, {"ck_wbs_nodes_status_valid"}),
        (Crew, {"ck_crews_status_valid"}),
    ],
)
def test_models_declare_database_status_constraints(model: type, constraint_names: set[str]) -> None:
    assert constraint_names <= _check_names(model)
