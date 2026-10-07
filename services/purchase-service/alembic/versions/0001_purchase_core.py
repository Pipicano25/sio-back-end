"""Purchase core: compras, líneas, secuencias, contadores por período, operaciones e hitos (014).

`specs/014-purchase-core/data-model.md`. Además de tablas, restricciones e índices:

- `tr_purchases_frozen`: una compra fuera de `DRAFT` solo puede pasar de `CONFIRMED` a
  `CANCELLED` (con sus campos de anulación); número, secuencia e `inventory_operation_id`
  nunca cambian una vez asignados.
- `tr_purchase_details_draft_only`: las líneas solo cambian mientras la compra está en `DRAFT`.
- `tr_purchase_sequence_counters_monotonic`: el contador solo crece y no se elimina.
- `tr_purchase_operations_terminal`: una operación terminal no cambia; la clave, su dueño, el
  usuario operativo que la inició y el motivo nunca cambian; `inventory_operation_id` no se reemplaza.
- Hitos inmutables; sin eliminación física de compras, secuencias, contadores ni operaciones (D7).

Revision ID: 0001
Revises:
Create Date: 2026-10-07

"""
from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa
from sio_audit.outbox import create_audit_outbox_table, drop_audit_outbox_table
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REJECT_FUNCTION = """
CREATE FUNCTION purchase_reject_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'La tabla % no admite % (%).', TG_TABLE_NAME, TG_OP, TG_NAME
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;
"""

PURCHASES_FROZEN = """
CREATE FUNCTION purchase_purchases_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'DRAFT' THEN
        RETURN NEW;
    END IF;
    IF OLD.status = 'CANCELLED' OR NEW.status <> 'CANCELLED' THEN
        RAISE EXCEPTION 'La compra % en estado % no admite cambios.', OLD.id, OLD.status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (NEW.id, NEW.company_id, NEW.branch_id, NEW.company_supplier_id, NEW.supplier_payment_condition_id,
        NEW.payment_condition_code_snapshot, NEW.payment_terms_days_snapshot, NEW.due_date,
        NEW.purchase_sequence_id, NEW.number, NEW.sequence_value, NEW.operation_date,
        NEW.promised_delivery_at, NEW.supplier_document_number, NEW.supplier_name_snapshot,
        NEW.supplier_identification_snapshot, NEW.currency_code, NEW.observations, NEW.subtotal,
        NEW.discount_total, NEW.tax_total, NEW.total, NEW.inventory_operation_id, NEW.created_by_user_id,
        NEW.created_at, NEW.created_by)
       IS DISTINCT FROM
       (OLD.id, OLD.company_id, OLD.branch_id, OLD.company_supplier_id, OLD.supplier_payment_condition_id,
        OLD.payment_condition_code_snapshot, OLD.payment_terms_days_snapshot, OLD.due_date,
        OLD.purchase_sequence_id, OLD.number, OLD.sequence_value, OLD.operation_date,
        OLD.promised_delivery_at, OLD.supplier_document_number, OLD.supplier_name_snapshot,
        OLD.supplier_identification_snapshot, OLD.currency_code, OLD.observations, OLD.subtotal,
        OLD.discount_total, OLD.tax_total, OLD.total, OLD.inventory_operation_id, OLD.created_by_user_id,
        OLD.created_at, OLD.created_by) THEN
        RAISE EXCEPTION 'La compra confirmada % solo admite su anulación.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

DETAILS_DRAFT_ONLY = """
CREATE FUNCTION purchase_details_draft_only() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    parent_status varchar(20);
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.purchase_id IS DISTINCT FROM OLD.purchase_id THEN
        RAISE EXCEPTION 'La línea % no puede cambiar de compra.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    SELECT status INTO parent_status FROM purchases
     WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.purchase_id ELSE NEW.purchase_id END;
    IF parent_status IS DISTINCT FROM 'DRAFT' THEN
        RAISE EXCEPTION 'Las líneas solo cambian mientras la compra está en DRAFT (estado %).', parent_status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;
"""

COUNTERS_MONOTONIC = """
CREATE FUNCTION purchase_sequence_counters_monotonic() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.purchase_sequence_id IS DISTINCT FROM OLD.purchase_sequence_id
       OR NEW.period_key IS DISTINCT FROM OLD.period_key
       OR NEW.current_number <= OLD.current_number
       OR NEW.created_at IS DISTINCT FROM OLD.created_at
       OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION 'El contador % / % solo puede crecer.', OLD.purchase_sequence_id, OLD.period_key
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

OPERATIONS_TERMINAL = """
CREATE FUNCTION purchase_operations_terminal() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status <> 'PENDING' THEN
        RAISE EXCEPTION 'La operación % ya terminó (%).', OLD.id, OLD.status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (NEW.id, NEW.company_id, NEW.purchase_id, NEW.operation_type, NEW.idempotency_key, NEW.correlation_id,
        NEW.application_user_id, NEW.reason, NEW.started_at, NEW.created_at, NEW.created_by)
       IS DISTINCT FROM
       (OLD.id, OLD.company_id, OLD.purchase_id, OLD.operation_type, OLD.idempotency_key, OLD.correlation_id,
        OLD.application_user_id, OLD.reason, OLD.started_at, OLD.created_at, OLD.created_by) THEN
        RAISE EXCEPTION 'La identidad de la operación % no cambia.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF OLD.inventory_operation_id IS NOT NULL AND NEW.inventory_operation_id IS DISTINCT FROM OLD.inventory_operation_id THEN
        RAISE EXCEPTION 'inventory_operation_id de la operación % no se reemplaza.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

TRIGGER_STATEMENTS = (
    "CREATE TRIGGER tr_purchases_frozen BEFORE UPDATE ON purchases "
    "FOR EACH ROW EXECUTE FUNCTION purchase_purchases_frozen()",
    "CREATE TRIGGER tr_purchases_no_delete BEFORE DELETE ON purchases "
    "FOR EACH ROW EXECUTE FUNCTION purchase_reject_change()",
    "CREATE TRIGGER tr_purchases_no_truncate BEFORE TRUNCATE ON purchases "
    "FOR EACH STATEMENT EXECUTE FUNCTION purchase_reject_change()",
    "CREATE TRIGGER tr_purchase_details_draft_only BEFORE INSERT OR UPDATE OR DELETE ON purchase_details "
    "FOR EACH ROW EXECUTE FUNCTION purchase_details_draft_only()",
    "CREATE TRIGGER tr_purchase_sequences_no_delete BEFORE DELETE ON purchase_sequences "
    "FOR EACH ROW EXECUTE FUNCTION purchase_reject_change()",
    "CREATE TRIGGER tr_purchase_sequence_counters_monotonic BEFORE UPDATE ON purchase_sequence_counters "
    "FOR EACH ROW EXECUTE FUNCTION purchase_sequence_counters_monotonic()",
    "CREATE TRIGGER tr_purchase_sequence_counters_no_delete BEFORE DELETE ON purchase_sequence_counters "
    "FOR EACH ROW EXECUTE FUNCTION purchase_reject_change()",
    "CREATE TRIGGER tr_purchase_operations_terminal BEFORE UPDATE ON purchase_operations "
    "FOR EACH ROW EXECUTE FUNCTION purchase_operations_terminal()",
    "CREATE TRIGGER tr_purchase_operations_no_delete BEFORE DELETE ON purchase_operations "
    "FOR EACH ROW EXECUTE FUNCTION purchase_reject_change()",
    "CREATE TRIGGER tr_purchase_lifecycle_events_no_update BEFORE UPDATE ON purchase_lifecycle_events "
    "FOR EACH ROW EXECUTE FUNCTION purchase_reject_change()",
    "CREATE TRIGGER tr_purchase_lifecycle_events_no_delete BEFORE DELETE ON purchase_lifecycle_events "
    "FOR EACH ROW EXECUTE FUNCTION purchase_reject_change()",
    "CREATE TRIGGER tr_purchase_lifecycle_events_no_truncate BEFORE TRUNCATE ON purchase_lifecycle_events "
    "FOR EACH STATEMENT EXECUTE FUNCTION purchase_reject_change()",
)

TRIGGERS = (
    ("purchases", "tr_purchases_frozen"),
    ("purchases", "tr_purchases_no_delete"),
    ("purchases", "tr_purchases_no_truncate"),
    ("purchase_details", "tr_purchase_details_draft_only"),
    ("purchase_sequences", "tr_purchase_sequences_no_delete"),
    ("purchase_sequence_counters", "tr_purchase_sequence_counters_monotonic"),
    ("purchase_sequence_counters", "tr_purchase_sequence_counters_no_delete"),
    ("purchase_operations", "tr_purchase_operations_terminal"),
    ("purchase_operations", "tr_purchase_operations_no_delete"),
    ("purchase_lifecycle_events", "tr_purchase_lifecycle_events_no_update"),
    ("purchase_lifecycle_events", "tr_purchase_lifecycle_events_no_delete"),
    ("purchase_lifecycle_events", "tr_purchase_lifecycle_events_no_truncate"),
)

FUNCTIONS = (
    "purchase_reject_change()",
    "purchase_purchases_frozen()",
    "purchase_details_draft_only()",
    "purchase_sequence_counters_monotonic()",
    "purchase_operations_terminal()",
)


def create_triggers() -> None:
    for statement in (REJECT_FUNCTION, PURCHASES_FROZEN, DETAILS_DRAFT_ONLY, COUNTERS_MONOTONIC, OPERATIONS_TERMINAL):
        op.execute(statement)
    for statement in TRIGGER_STATEMENTS:
        op.execute(statement)


def drop_triggers() -> None:
    for table, trigger in TRIGGERS:
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
    for function in FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {function}")


def upgrade() -> None:
    """Upgrade schema."""
    create_audit_outbox_table(op)
    op.create_table('purchase_sequences',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('branch_id', sa.UUID(), nullable=True),
    sa.Column('document_kind', sa.String(length=40), nullable=False),
    sa.Column('series_code', sa.String(length=40), nullable=False),
    sa.Column('prefix', sa.String(length=20), nullable=False),
    sa.Column('separator', sa.String(length=5), nullable=False),
    sa.Column('initial_number', sa.BigInteger(), nullable=False),
    sa.Column('maximum_number', sa.BigInteger(), nullable=True),
    sa.Column('number_length', sa.SmallInteger(), nullable=False),
    sa.Column('reset_policy', sa.String(length=20), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.CheckConstraint("document_kind = 'PURCHASE'", name=op.f('ck_purchase_sequences_document_kind')),
    sa.CheckConstraint("prefix ~ '^[A-Z0-9]{1,20}$'", name=op.f('ck_purchase_sequences_prefix')),
    sa.CheckConstraint("reset_policy IN ('NEVER','YEARLY','MONTHLY')", name=op.f('ck_purchase_sequences_reset_policy')),
    sa.CheckConstraint("separator IN ('-','/','.','_','')", name=op.f('ck_purchase_sequences_separator')),
    sa.CheckConstraint("series_code ~ '^[A-Z0-9_-]{1,40}$'", name=op.f('ck_purchase_sequences_series_code')),
    sa.CheckConstraint('char_length(prefix) + 2 * char_length(separator) + 6 + number_length <= 80', name=op.f('ck_purchase_sequences_number_text_length')),
    sa.CheckConstraint('initial_number >= 1', name=op.f('ck_purchase_sequences_initial_number')),
    sa.CheckConstraint('maximum_number IS NULL OR maximum_number >= initial_number', name=op.f('ck_purchase_sequences_maximum_number')),
    sa.CheckConstraint('number_length BETWEEN 1 AND 18', name=op.f('ck_purchase_sequences_number_length')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_purchase_sequences_version')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_purchase_sequences'))
    )
    op.create_index('uq_purchase_sequences_active', 'purchase_sequences', ['company_id', sa.literal_column("COALESCE(branch_id, '00000000-0000-0000-0000-000000000000'::uuid)"), 'document_kind'], unique=True, postgresql_where=sa.text('is_active'))
    op.create_index('uq_purchase_sequences_series', 'purchase_sequences', ['company_id', sa.literal_column("COALESCE(branch_id, '00000000-0000-0000-0000-000000000000'::uuid)"), 'document_kind', 'series_code'], unique=True)
    op.create_table('purchase_sequence_counters',
    sa.Column('purchase_sequence_id', sa.UUID(), nullable=False),
    sa.Column('period_key', sa.String(length=6), nullable=False),
    sa.Column('current_number', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.CheckConstraint("period_key ~ '^([0-9]{4}|[0-9]{6})?$'", name=op.f('ck_purchase_sequence_counters_period_key')),
    sa.CheckConstraint('current_number >= 1', name=op.f('ck_purchase_sequence_counters_current_number')),
    sa.ForeignKeyConstraint(['purchase_sequence_id'], ['purchase_sequences.id'], name=op.f('fk_purchase_sequence_counters_purchase_sequence_id_purchase_sequences')),
    sa.PrimaryKeyConstraint('purchase_sequence_id', 'period_key', name=op.f('pk_purchase_sequence_counters'))
    )
    op.create_table('purchases',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('branch_id', sa.UUID(), nullable=False),
    sa.Column('company_supplier_id', sa.UUID(), nullable=False),
    sa.Column('supplier_payment_condition_id', sa.UUID(), nullable=True),
    sa.Column('payment_condition_code_snapshot', sa.String(length=30), nullable=False),
    sa.Column('payment_terms_days_snapshot', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('purchase_sequence_id', sa.UUID(), nullable=True),
    sa.Column('number', sa.String(length=80), nullable=True),
    sa.Column('sequence_value', sa.BigInteger(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('operation_date', sa.Date(), nullable=False),
    sa.Column('promised_delivery_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('supplier_document_number', sa.String(length=100), nullable=True),
    sa.Column('supplier_name_snapshot', sa.String(length=200), nullable=False),
    sa.Column('supplier_identification_snapshot', sa.String(length=100), nullable=False),
    sa.Column('currency_code', sa.CHAR(length=3), nullable=False),
    sa.Column('observations', sa.Text(), nullable=True),
    sa.Column('subtotal', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('discount_total', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('tax_total', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('total', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('inventory_operation_id', sa.UUID(), nullable=True),
    sa.Column('created_by_user_id', sa.UUID(), nullable=False),
    sa.Column('cancelled_by_user_id', sa.UUID(), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cancellation_reason', sa.Text(), nullable=True),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.CheckConstraint("(status = 'DRAFT' AND number IS NULL AND sequence_value IS NULL AND purchase_sequence_id IS NULL AND inventory_operation_id IS NULL AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancellation_reason IS NULL) OR (status = 'CONFIRMED' AND number IS NOT NULL AND sequence_value IS NOT NULL AND purchase_sequence_id IS NOT NULL AND inventory_operation_id IS NOT NULL AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancellation_reason IS NULL) OR (status = 'CANCELLED' AND cancelled_by_user_id IS NOT NULL AND cancelled_at IS NOT NULL AND cancellation_reason IS NOT NULL AND ((number IS NULL AND sequence_value IS NULL AND purchase_sequence_id IS NULL AND inventory_operation_id IS NULL) OR (number IS NOT NULL AND sequence_value IS NOT NULL AND purchase_sequence_id IS NOT NULL AND inventory_operation_id IS NOT NULL)))", name=op.f('ck_purchases_lifecycle')),
    sa.CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name=op.f('ck_purchases_currency_code')),
    sa.CheckConstraint("payment_condition_code_snapshot IN ('CASH','CREDIT','FINANCING')", name=op.f('ck_purchases_payment_code')),
    sa.CheckConstraint("payment_terms_days_snapshot >= 0 AND (payment_condition_code_snapshot <> 'CASH' OR payment_terms_days_snapshot = 0)", name=op.f('ck_purchases_payment_terms')),
    sa.CheckConstraint("status IN ('DRAFT','CONFIRMED','CANCELLED')", name=op.f('ck_purchases_status')),
    sa.CheckConstraint('due_date >= operation_date', name=op.f('ck_purchases_due_date')),
    sa.CheckConstraint('sequence_value IS NULL OR sequence_value > 0', name=op.f('ck_purchases_sequence_value')),
    sa.CheckConstraint('subtotal >= 0 AND discount_total >= 0 AND tax_total >= 0 AND total >= 0', name=op.f('ck_purchases_amounts_non_negative')),
    sa.CheckConstraint('total = subtotal - discount_total + tax_total', name=op.f('ck_purchases_totals')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_purchases_version')),
    sa.ForeignKeyConstraint(['purchase_sequence_id'], ['purchase_sequences.id'], name=op.f('fk_purchases_purchase_sequence_id_purchase_sequences')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_purchases'))
    )
    op.create_index('ix_purchases_company_branch', 'purchases', ['company_id', 'branch_id'], unique=False)
    op.create_index('ix_purchases_company_date', 'purchases', ['company_id', 'operation_date', 'created_at', 'id'], unique=False)
    op.create_index('ix_purchases_company_status', 'purchases', ['company_id', 'status'], unique=False)
    op.create_index('ix_purchases_company_supplier', 'purchases', ['company_id', 'company_supplier_id'], unique=False)
    op.create_index('uq_purchases_company_number', 'purchases', ['company_id', 'number'], unique=True, postgresql_where=sa.text('number IS NOT NULL'))
    op.create_table('purchase_details',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('purchase_id', sa.UUID(), nullable=False),
    sa.Column('line_number', sa.SmallInteger(), nullable=False),
    sa.Column('company_product_id', sa.UUID(), nullable=False),
    sa.Column('company_product_presentation_id', sa.UUID(), nullable=True),
    sa.Column('supplier_product_id', sa.UUID(), nullable=True),
    sa.Column('supplier_lead_time_snapshot_hours', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('product_code_snapshot', sa.String(length=80), nullable=False),
    sa.Column('product_name_snapshot', sa.String(length=200), nullable=False),
    sa.Column('presentation_code_snapshot', sa.String(length=80), nullable=True),
    sa.Column('presentation_name_snapshot', sa.String(length=160), nullable=True),
    sa.Column('base_quantity_factor_snapshot', sa.Numeric(precision=18, scale=8), server_default=sa.text('1'), nullable=False),
    sa.Column('unit_code_snapshot', sa.String(length=20), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('unit_cost', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('discount_amount', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('tax_amount', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('subtotal', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('total', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.CheckConstraint('(company_product_presentation_id IS NULL AND base_quantity_factor_snapshot = 1 AND presentation_code_snapshot IS NULL AND presentation_name_snapshot IS NULL) OR (company_product_presentation_id IS NOT NULL AND presentation_code_snapshot IS NOT NULL AND presentation_name_snapshot IS NOT NULL)', name=op.f('ck_purchase_details_presentation')),
    sa.CheckConstraint('base_quantity_factor_snapshot > 0', name=op.f('ck_purchase_details_factor')),
    sa.CheckConstraint('discount_amount >= 0 AND discount_amount <= subtotal', name=op.f('ck_purchase_details_discount_amount')),
    sa.CheckConstraint('line_number BETWEEN 1 AND 100', name=op.f('ck_purchase_details_line_number')),
    sa.CheckConstraint('quantity > 0', name=op.f('ck_purchase_details_quantity')),
    sa.CheckConstraint('subtotal >= 0', name=op.f('ck_purchase_details_subtotal')),
    sa.CheckConstraint('supplier_lead_time_snapshot_hours IS NULL OR supplier_lead_time_snapshot_hours >= 0', name=op.f('ck_purchase_details_lead_time')),
    sa.CheckConstraint('tax_amount >= 0', name=op.f('ck_purchase_details_tax_amount')),
    sa.CheckConstraint('total = subtotal - discount_amount + tax_amount', name=op.f('ck_purchase_details_total')),
    sa.CheckConstraint('unit_cost >= 0', name=op.f('ck_purchase_details_unit_cost')),
    sa.ForeignKeyConstraint(['purchase_id'], ['purchases.id'], name=op.f('fk_purchase_details_purchase_id_purchases')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_purchase_details')),
    sa.UniqueConstraint('purchase_id', 'line_number', name='uq_purchase_details_line_number')
    )
    op.create_table('purchase_lifecycle_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('purchase_id', sa.UUID(), nullable=False),
    sa.Column('event_type', sa.String(length=40), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('recorded_by_user_id', sa.UUID(), nullable=False),
    sa.Column('source', sa.String(length=30), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.CheckConstraint("event_type IN ('ORDERED','SUPPLIER_DISPATCHED','ARRIVED','RECEIVED','AVAILABLE_FOR_SALE')", name=op.f('ck_purchase_lifecycle_events_event_type')),
    sa.CheckConstraint("source IN ('USER','SUPPLIER','INTEGRATION','SYSTEM')", name=op.f('ck_purchase_lifecycle_events_source')),
    sa.ForeignKeyConstraint(['purchase_id'], ['purchases.id'], name=op.f('fk_purchase_lifecycle_events_purchase_id_purchases')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_purchase_lifecycle_events'))
    )
    op.create_index('ix_purchase_lifecycle_events_purchase', 'purchase_lifecycle_events', ['purchase_id', 'event_type', 'created_at', 'id'], unique=False)
    op.create_table('purchase_operations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('purchase_id', sa.UUID(), nullable=False),
    sa.Column('operation_type', sa.String(length=20), nullable=False),
    sa.Column('idempotency_key', sa.String(length=150), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('correlation_id', sa.UUID(), nullable=False),
    sa.Column('application_user_id', sa.UUID(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('error_code', sa.String(length=100), nullable=True),
    sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('inventory_operation_id', sa.UUID(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.CheckConstraint("(status = 'PENDING') = (completed_at IS NULL)", name=op.f('ck_purchase_operations_completed_at')),
    sa.CheckConstraint("operation_type IN ('CONFIRM','CANCEL')", name=op.f('ck_purchase_operations_operation_type')),
    sa.CheckConstraint("status <> 'FAILED' OR error_code IS NOT NULL", name=op.f('ck_purchase_operations_failed_code')),
    sa.CheckConstraint("status <> 'SUCCEEDED' OR operation_type = 'CANCEL' OR inventory_operation_id IS NOT NULL", name=op.f('ck_purchase_operations_inventory_operation')),
    sa.CheckConstraint("status IN ('PENDING','SUCCEEDED','FAILED')", name=op.f('ck_purchase_operations_status')),
    sa.CheckConstraint('char_length(idempotency_key) BETWEEN 1 AND 150', name=op.f('ck_purchase_operations_idempotency_key')),
    sa.CheckConstraint("operation_type <> 'CANCEL' OR reason IS NOT NULL", name=op.f('ck_purchase_operations_cancel_reason')),
    sa.ForeignKeyConstraint(['purchase_id'], ['purchases.id'], name=op.f('fk_purchase_operations_purchase_id_purchases')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_purchase_operations')),
    sa.UniqueConstraint('idempotency_key', name='uq_purchase_operations_idempotency_key')
    )
    op.create_index('ix_purchase_operations_pending_age', 'purchase_operations', ['updated_at'], unique=False, postgresql_where=sa.text("status = 'PENDING'"))
    op.create_index('ix_purchase_operations_purchase', 'purchase_operations', ['purchase_id', 'started_at'], unique=False)
    op.create_index('uq_purchase_operations_pending', 'purchase_operations', ['purchase_id'], unique=True, postgresql_where=sa.text("status = 'PENDING'"))
    create_triggers()


def downgrade() -> None:
    """Downgrade schema."""
    drop_triggers()
    op.drop_index('uq_purchase_operations_pending', table_name='purchase_operations', postgresql_where=sa.text("status = 'PENDING'"))
    op.drop_index('ix_purchase_operations_purchase', table_name='purchase_operations')
    op.drop_index('ix_purchase_operations_pending_age', table_name='purchase_operations', postgresql_where=sa.text("status = 'PENDING'"))
    op.drop_table('purchase_operations')
    op.drop_index('ix_purchase_lifecycle_events_purchase', table_name='purchase_lifecycle_events')
    op.drop_table('purchase_lifecycle_events')
    op.drop_table('purchase_details')
    op.drop_index('uq_purchases_company_number', table_name='purchases', postgresql_where=sa.text('number IS NOT NULL'))
    op.drop_index('ix_purchases_company_supplier', table_name='purchases')
    op.drop_index('ix_purchases_company_status', table_name='purchases')
    op.drop_index('ix_purchases_company_date', table_name='purchases')
    op.drop_index('ix_purchases_company_branch', table_name='purchases')
    op.drop_table('purchases')
    op.drop_table('purchase_sequence_counters')
    op.drop_index('uq_purchase_sequences_series', table_name='purchase_sequences')
    op.drop_index('uq_purchase_sequences_active', table_name='purchase_sequences', postgresql_where=sa.text('is_active'))
    op.drop_table('purchase_sequences')
    drop_audit_outbox_table(op)
