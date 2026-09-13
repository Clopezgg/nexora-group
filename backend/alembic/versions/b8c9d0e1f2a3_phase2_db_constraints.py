"""Phase 2 DB last defense: CHECK constraints for procurement, budget, planning

Revision ID: b8c9d0e1f2a3
Revises: a7b3c4d5e6f7
Create Date: 2026-09-08
"""


from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "a7b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Procurement status CHECK constraints
    op.create_check_constraint(
        "ck_purchase_requisitions_status_valid",
        "purchase_requisitions",
        "status IN ('DRAFT','SUBMITTED','APPROVED','REJECTED','CONVERTED','CANCELLED')",
    )
    op.create_check_constraint(
        "ck_purchase_requisitions_priority_valid",
        "purchase_requisitions",
        "priority IN ('LOW','NORMAL','HIGH','URGENT')",
    )
    op.create_check_constraint(
        "ck_rfq_status_valid",
        "requests_for_quotation",
        "status IN ('DRAFT','SENT','CLOSED','CANCELLED')",
    )
    op.create_check_constraint(
        "ck_supplier_quotations_status_valid",
        "supplier_quotations",
        "status IN ('RECEIVED','SELECTED','REJECTED')",
    )
    op.create_check_constraint(
        "ck_supplier_quotations_delivery_non_negative",
        "supplier_quotations",
        "delivery_days >= 0",
    )
    op.create_check_constraint(
        "ck_purchase_orders_status_valid",
        "purchase_orders",
        "status IN ('DRAFT','APPROVAL_PENDING','APPROVED','SENT','PARTIALLY_RECEIVED','RECEIVED','CLOSED','CANCELLED')",
    )
    op.create_check_constraint(
        "ck_three_way_match_results_status_valid",
        "three_way_match_results",
        "status IN ('MATCHED','EXCEPTION')",
    )

    # Procurement amount/quantity non-negative constraints
    op.create_check_constraint("ck_pr_lines_quantity_positive", "purchase_requisition_lines", "quantity > 0")
    op.create_check_constraint("ck_pr_lines_cost_non_negative", "purchase_requisition_lines", "estimated_unit_cost >= 0")
    op.create_check_constraint("ck_quotation_lines_quantity_positive", "supplier_quotation_lines", "quantity > 0")
    op.create_check_constraint("ck_quotation_lines_price_non_negative", "supplier_quotation_lines", "unit_price >= 0")
    op.create_check_constraint("ck_quotation_lines_tax_non_negative", "supplier_quotation_lines", "tax_amount >= 0")
    op.create_check_constraint("ck_po_lines_quantity_positive", "purchase_order_lines", "quantity > 0")
    op.create_check_constraint("ck_po_lines_price_non_negative", "purchase_order_lines", "unit_price >= 0")
    op.create_check_constraint("ck_po_lines_tax_non_negative", "purchase_order_lines", "tax_amount >= 0")
    op.create_check_constraint("ck_po_lines_received_non_negative", "purchase_order_lines", "quantity_received >= 0")
    op.create_check_constraint("ck_gr_lines_quantity_positive", "goods_receipt_lines", "quantity_received > 0")
    op.create_check_constraint(
        "ck_service_entries_progress_valid", "service_entries",
        "progress_percentage >= 0 AND progress_percentage <= 100",
    )
    op.create_check_constraint("ck_service_entries_value_non_negative", "service_entries", "accepted_value >= 0")
    op.create_check_constraint("ck_twm_invoice_amount_non_negative", "three_way_match_results", "supplier_invoice_amount >= 0")
    op.create_check_constraint("ck_twm_invoice_quantity_non_negative", "three_way_match_results", "supplier_invoice_quantity >= 0")
    op.create_check_constraint("ck_twm_received_quantity_non_negative", "three_way_match_results", "received_quantity >= 0")
    op.create_check_constraint("ck_twm_ordered_amount_non_negative", "three_way_match_results", "ordered_amount >= 0")
    op.create_check_constraint(
        "ck_twm_quantity_tolerance_valid", "three_way_match_results",
        "quantity_tolerance_pct >= 0 AND quantity_tolerance_pct <= 100",
    )
    op.create_check_constraint(
        "ck_twm_amount_tolerance_valid", "three_way_match_results",
        "amount_tolerance_pct >= 0 AND amount_tolerance_pct <= 100",
    )

    # Budget CHECK constraints
    op.create_check_constraint("ck_budgets_version_valid", "budgets", "version IN ('BASELINE','REVISED')")
    op.create_check_constraint("ck_budgets_status_valid", "budgets", "status IN ('ACTIVE','SUPERSEDED')")
    op.create_check_constraint("ck_budget_lines_amount_positive", "budget_lines", "authorized_amount > 0")

    # Planning CHECK constraints
    op.create_check_constraint(
        "ck_tasks_status_valid", "tasks",
        "status IN ('PLANNED','IN_PROGRESS','DONE','BLOCKED','CANCELLED')",
    )
    op.create_check_constraint(
        "ck_tasks_planned_dates_valid", "tasks",
        "planned_end IS NULL OR planned_start IS NULL OR planned_end >= planned_start",
    )
    op.create_check_constraint(
        "ck_milestones_status_valid", "milestones",
        "status IN ('PLANNED','ACHIEVED','MISSED','CANCELLED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_milestones_status_valid", "milestones")
    op.drop_constraint("ck_tasks_planned_dates_valid", "tasks")
    op.drop_constraint("ck_tasks_status_valid", "tasks")
    op.drop_constraint("ck_budget_lines_amount_positive", "budget_lines")
    op.drop_constraint("ck_budgets_status_valid", "budgets")
    op.drop_constraint("ck_budgets_version_valid", "budgets")
    op.drop_constraint("ck_service_entries_value_non_negative", "service_entries")
    op.drop_constraint("ck_service_entries_progress_valid", "service_entries")
    op.drop_constraint("ck_gr_lines_quantity_positive", "goods_receipt_lines")
    op.drop_constraint("ck_po_lines_received_non_negative", "purchase_order_lines")
    op.drop_constraint("ck_po_lines_tax_non_negative", "purchase_order_lines")
    op.drop_constraint("ck_po_lines_price_non_negative", "purchase_order_lines")
    op.drop_constraint("ck_po_lines_quantity_positive", "purchase_order_lines")
    op.drop_constraint("ck_quotation_lines_tax_non_negative", "supplier_quotation_lines")
    op.drop_constraint("ck_quotation_lines_price_non_negative", "supplier_quotation_lines")
    op.drop_constraint("ck_quotation_lines_quantity_positive", "supplier_quotation_lines")
    op.drop_constraint("ck_pr_lines_cost_non_negative", "purchase_requisition_lines")
    op.drop_constraint("ck_pr_lines_quantity_positive", "purchase_requisition_lines")
    op.drop_constraint("ck_twm_amount_tolerance_valid", "three_way_match_results")
    op.drop_constraint("ck_twm_quantity_tolerance_valid", "three_way_match_results")
    op.drop_constraint("ck_twm_ordered_amount_non_negative", "three_way_match_results")
    op.drop_constraint("ck_twm_received_quantity_non_negative", "three_way_match_results")
    op.drop_constraint("ck_twm_invoice_quantity_non_negative", "three_way_match_results")
    op.drop_constraint("ck_twm_invoice_amount_non_negative", "three_way_match_results")
    op.drop_constraint("ck_three_way_match_results_status_valid", "three_way_match_results")
    op.drop_constraint("ck_purchase_orders_status_valid", "purchase_orders")
    op.drop_constraint("ck_supplier_quotations_delivery_non_negative", "supplier_quotations")
    op.drop_constraint("ck_supplier_quotations_status_valid", "supplier_quotations")
    op.drop_constraint("ck_rfq_status_valid", "requests_for_quotation")
    op.drop_constraint("ck_purchase_requisitions_priority_valid", "purchase_requisitions")
    op.drop_constraint("ck_purchase_requisitions_status_valid", "purchase_requisitions")
