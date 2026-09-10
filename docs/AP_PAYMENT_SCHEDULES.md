# AP payment calendars

`SupplierInvoiceCashForecastItem` is a forecast-only calendar for a
non-contract supplier invoice. It distributes the invoice's remaining amount
across expected due dates for cash forecasting and voucher context; it does
not create executable installments, does not allocate payments, and does not
grant permission to pay a future date.

Contractual obligations use the separate chain
`SupplierContract -> ContractPaymentSchedule -> ContractPaymentInstallment ->
ContractPaymentAllocation`. Its business-month eligibility is enforced by the
backend using `business_today()` in `America/Tegucigalpa`.

The legacy Python import name `SupplierInvoicePaymentPlanItem` remains an
alias for compatibility, but new code must use `SupplierInvoiceCashForecastItem`.
