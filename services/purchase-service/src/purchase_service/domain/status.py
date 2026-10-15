"""Estados de la compra y de las operaciones distribuidas (§7.1, §7.4)."""

DRAFT = "DRAFT"
CONFIRMED = "CONFIRMED"
CANCELLED = "CANCELLED"
PURCHASE_STATUSES = (DRAFT, CONFIRMED, CANCELLED)

CONFIRM = "CONFIRM"
CANCEL = "CANCEL"
RECEIVE = "RECEIVE"
"""Spec 020: la recepción física completa aplica la entrada en Inventory (la confirmación ya no)."""
OPERATION_TYPES = (CONFIRM, CANCEL, RECEIVE)

RECEIPT_PENDING = "PENDING"
RECEIPT_RECEIVED = "RECEIVED"
"""`receipt_status` derivado (spec 020, FR-020-05): confirmada sin recibir / recibida."""

PENDING = "PENDING"
SUCCEEDED = "SUCCEEDED"
FAILED = "FAILED"
OPERATION_STATUSES = (PENDING, SUCCEEDED, FAILED)

CASH = "CASH"
CREDIT = "CREDIT"
FINANCING = "FINANCING"
PAYMENT_CODES = (CASH, CREDIT, FINANCING)

DOCUMENT_KIND = "PURCHASE"
MAX_LINES = 100

RECONCILER_ACTOR = "system:purchase-reconciler"
"""Identidad técnica del conciliador para `created_by`/`updated_by` (D1, D22)."""

