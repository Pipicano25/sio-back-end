"""Sales core: ventas, líneas, secuencias, contadores por período y operaciones (015).

`specs/015-sales-core/data-model.md`. Además de tablas, restricciones e índices:

- `tr_sales_frozen`: una venta fuera de `DRAFT` solo puede pasar de `CONFIRMED` a
  `CANCELLED` (con sus campos de anulación); número, secuencia e `inventory_operation_id`
  nunca cambian una vez asignados.
- `tr_sale_details_draft_only`: las líneas solo cambian mientras la venta está en `DRAFT`.
- `tr_sale_sequence_counters_monotonic`: el contador solo crece y no se elimina.
- `tr_sale_operations_terminal`: una operación terminal no cambia; la clave, su dueño, el
  usuario operativo que la inició y el motivo nunca cambian; `inventory_operation_id` no se reemplaza.
- Sin eliminación física de ventas, secuencias, contadores ni operaciones (D7).
- Costo y margen de las líneas se escriben en la transacción que confirma, mientras la venta
  sigue en `DRAFT` (antes de cambiar su estado); después no cambian (RN-04).

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
CREATE FUNCTION sale_reject_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'La tabla % no admite % (%).', TG_TABLE_NAME, TG_OP, TG_NAME
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;
"""

SALES_FROZEN = """
CREATE FUNCTION sale_sales_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'DRAFT' THEN
        RETURN NEW;
    END IF;
    IF OLD.status = 'CANCELLED' OR NEW.status <> 'CANCELLED' THEN
        RAISE EXCEPTION 'La venta % en estado % no admite cambios.', OLD.id, OLD.status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (NEW.id, NEW.company_id, NEW.branch_id, NEW.company_customer_id, NEW.customer_payment_condition_id,
        NEW.payment_condition_code_snapshot, NEW.payment_terms_days_snapshot, NEW.due_date,
        NEW.sale_sequence_id, NEW.number, NEW.sequence_value, NEW.operation_date,
        NEW.customer_name_snapshot, NEW.customer_identification_snapshot, NEW.currency_code,
        NEW.observations, NEW.subtotal, NEW.discount_total, NEW.tax_total, NEW.total, NEW.has_unknown_cost,
        NEW.inventory_operation_id, NEW.created_by_user_id, NEW.created_at, NEW.created_by)
       IS DISTINCT FROM
       (OLD.id, OLD.company_id, OLD.branch_id, OLD.company_customer_id, OLD.customer_payment_condition_id,
        OLD.payment_condition_code_snapshot, OLD.payment_terms_days_snapshot, OLD.due_date,
        OLD.sale_sequence_id, OLD.number, OLD.sequence_value, OLD.operation_date,
        OLD.customer_name_snapshot, OLD.customer_identification_snapshot, OLD.currency_code,
        OLD.observations, OLD.subtotal, OLD.discount_total, OLD.tax_total, OLD.total, OLD.has_unknown_cost,
        OLD.inventory_operation_id, OLD.created_by_user_id, OLD.created_at, OLD.created_by) THEN
        RAISE EXCEPTION 'La venta confirmada % solo admite su anulación.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

DETAILS_DRAFT_ONLY = """
CREATE FUNCTION sale_details_draft_only() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    parent_status varchar(20);
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.sale_id IS DISTINCT FROM OLD.sale_id THEN
        RAISE EXCEPTION 'La línea % no puede cambiar de venta.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    SELECT status INTO parent_status FROM sales
     WHERE id = CASE WHEN TG_OP = 'DELETE' THEN OLD.sale_id ELSE NEW.sale_id END;
    IF parent_status IS DISTINCT FROM 'DRAFT' THEN
        RAISE EXCEPTION 'Las líneas solo cambian mientras la venta está en DRAFT (estado %).', parent_status
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
CREATE FUNCTION sale_sequence_counters_monotonic() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.sale_sequence_id IS DISTINCT FROM OLD.sale_sequence_id
       OR NEW.period_key IS DISTINCT FROM OLD.period_key
       OR NEW.current_number <= OLD.current_number
       OR NEW.created_at IS DISTINCT FROM OLD.created_at
       OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION 'El contador % / % solo puede crecer.', OLD.sale_sequence_id, OLD.period_key
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

OPERATIONS_TERMINAL = """
CREATE FUNCTION sale_operations_terminal() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status <> 'PENDING' THEN
        RAISE EXCEPTION 'La operación % ya terminó (%).', OLD.id, OLD.status
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (NEW.id, NEW.company_id, NEW.sale_id, NEW.operation_type, NEW.idempotency_key, NEW.correlation_id,
        NEW.application_user_id, NEW.reason, NEW.started_at, NEW.created_at, NEW.created_by)
       IS DISTINCT FROM
       (OLD.id, OLD.company_id, OLD.sale_id, OLD.operation_type, OLD.idempotency_key, OLD.correlation_id,
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
    "CREATE TRIGGER tr_sales_frozen BEFORE UPDATE ON sales "
    "FOR EACH ROW EXECUTE FUNCTION sale_sales_frozen()",
    "CREATE TRIGGER tr_sales_no_delete BEFORE DELETE ON sales "
    "FOR EACH ROW EXECUTE FUNCTION sale_reject_change()",
    "CREATE TRIGGER tr_sales_no_truncate BEFORE TRUNCATE ON sales "
    "FOR EACH STATEMENT EXECUTE FUNCTION sale_reject_change()",
    "CREATE TRIGGER tr_sale_details_draft_only BEFORE INSERT OR UPDATE OR DELETE ON sale_details "
    "FOR EACH ROW EXECUTE FUNCTION sale_details_draft_only()",
    "CREATE TRIGGER tr_sale_sequences_no_delete BEFORE DELETE ON sale_sequences "
    "FOR EACH ROW EXECUTE FUNCTION sale_reject_change()",
    "CREATE TRIGGER tr_sale_sequence_counters_monotonic BEFORE UPDATE ON sale_sequence_counters "
    "FOR EACH ROW EXECUTE FUNCTION sale_sequence_counters_monotonic()",
    "CREATE TRIGGER tr_sale_sequence_counters_no_delete BEFORE DELETE ON sale_sequence_counters "
    "FOR EACH ROW EXECUTE FUNCTION sale_reject_change()",
    "CREATE TRIGGER tr_sale_operations_terminal BEFORE UPDATE ON sale_operations "
    "FOR EACH ROW EXECUTE FUNCTION sale_operations_terminal()",
    "CREATE TRIGGER tr_sale_operations_no_delete BEFORE DELETE ON sale_operations "
    "FOR EACH ROW EXECUTE FUNCTION sale_reject_change()",
)

TRIGGERS = (
    ("sales", "tr_sales_frozen"),
    ("sales", "tr_sales_no_delete"),
    ("sales", "tr_sales_no_truncate"),
    ("sale_details", "tr_sale_details_draft_only"),
    ("sale_sequences", "tr_sale_sequences_no_delete"),
    ("sale_sequence_counters", "tr_sale_sequence_counters_monotonic"),
    ("sale_sequence_counters", "tr_sale_sequence_counters_no_delete"),
    ("sale_operations", "tr_sale_operations_terminal"),
    ("sale_operations", "tr_sale_operations_no_delete"),
)

FUNCTIONS = (
    "sale_reject_change()",
    "sale_sales_frozen()",
    "sale_details_draft_only()",
    "sale_sequence_counters_monotonic()",
    "sale_operations_terminal()",
)


def create_triggers() -> None:
    for statement in (REJECT_FUNCTION, SALES_FROZEN, DETAILS_DRAFT_ONLY, COUNTERS_MONOTONIC, OPERATIONS_TERMINAL):
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
    op.create_table('sale_sequences',
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
    sa.CheckConstraint("document_kind = 'SALE'", name=op.f('ck_sale_sequences_document_kind')),
    sa.CheckConstraint("prefix ~ '^[A-Z0-9]{1,20}$'", name=op.f('ck_sale_sequences_prefix')),
    sa.CheckConstraint("reset_policy IN ('NEVER','YEARLY','MONTHLY')", name=op.f('ck_sale_sequences_reset_policy')),
    sa.CheckConstraint("separator IN ('-','/','.','_','')", name=op.f('ck_sale_sequences_separator')),
    sa.CheckConstraint("series_code ~ '^[A-Z0-9_-]{1,40}$'", name=op.f('ck_sale_sequences_series_code')),
    sa.CheckConstraint('char_length(prefix) + 2 * char_length(separator) + 6 + number_length <= 80', name=op.f('ck_sale_sequences_number_text_length')),
    sa.CheckConstraint('initial_number >= 1', name=op.f('ck_sale_sequences_initial_number')),
    sa.CheckConstraint('maximum_number IS NULL OR maximum_number >= initial_number', name=op.f('ck_sale_sequences_maximum_number')),
    sa.CheckConstraint('number_length BETWEEN 1 AND 18', name=op.f('ck_sale_sequences_number_length')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_sale_sequences_version')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sale_sequences'))
    )
    op.create_index('uq_sale_sequences_active', 'sale_sequences', ['company_id', sa.literal_column("COALESCE(branch_id, '00000000-0000-0000-0000-000000000000'::uuid)"), 'document_kind'], unique=True, postgresql_where=sa.text('is_active'))
    op.create_index('uq_sale_sequences_series', 'sale_sequences', ['company_id', sa.literal_column("COALESCE(branch_id, '00000000-0000-0000-0000-000000000000'::uuid)"), 'document_kind', 'series_code'], unique=True)
    op.create_table('sale_sequence_counters',
    sa.Column('sale_sequence_id', sa.UUID(), nullable=False),
    sa.Column('period_key', sa.String(length=6), nullable=False),
    sa.Column('current_number', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.CheckConstraint("period_key ~ '^([0-9]{4}|[0-9]{6})?$'", name=op.f('ck_sale_sequence_counters_period_key')),
    sa.CheckConstraint('current_number >= 1', name=op.f('ck_sale_sequence_counters_current_number')),
    sa.ForeignKeyConstraint(['sale_sequence_id'], ['sale_sequences.id'], name=op.f('fk_sale_sequence_counters_sale_sequence_id_sale_sequences')),
    sa.PrimaryKeyConstraint('sale_sequence_id', 'period_key', name=op.f('pk_sale_sequence_counters'))
    )
    op.create_table('sales',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('branch_id', sa.UUID(), nullable=False),
    sa.Column('company_customer_id', sa.UUID(), nullable=False),
    sa.Column('customer_payment_condition_id', sa.UUID(), nullable=True),
    sa.Column('payment_condition_code_snapshot', sa.String(length=30), nullable=False),
    sa.Column('payment_terms_days_snapshot', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('due_date', sa.Date(), nullable=False),
    sa.Column('sale_sequence_id', sa.UUID(), nullable=True),
    sa.Column('number', sa.String(length=80), nullable=True),
    sa.Column('sequence_value', sa.BigInteger(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('operation_date', sa.Date(), nullable=False),
    sa.Column('customer_name_snapshot', sa.String(length=200), nullable=False),
    sa.Column('customer_identification_snapshot', sa.String(length=100), nullable=False),
    sa.Column('currency_code', sa.CHAR(length=3), nullable=False),
    sa.Column('observations', sa.Text(), nullable=True),
    sa.Column('subtotal', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('discount_total', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('tax_total', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('total', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('has_unknown_cost', sa.Boolean(), server_default=sa.text('false'), nullable=False),
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
    sa.CheckConstraint("(status = 'DRAFT' AND number IS NULL AND sequence_value IS NULL AND sale_sequence_id IS NULL AND inventory_operation_id IS NULL AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancellation_reason IS NULL) OR (status = 'CONFIRMED' AND number IS NOT NULL AND sequence_value IS NOT NULL AND sale_sequence_id IS NOT NULL AND inventory_operation_id IS NOT NULL AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancellation_reason IS NULL) OR (status = 'CANCELLED' AND cancelled_by_user_id IS NOT NULL AND cancelled_at IS NOT NULL AND cancellation_reason IS NOT NULL AND ((number IS NULL AND sequence_value IS NULL AND sale_sequence_id IS NULL AND inventory_operation_id IS NULL) OR (number IS NOT NULL AND sequence_value IS NOT NULL AND sale_sequence_id IS NOT NULL AND inventory_operation_id IS NOT NULL)))", name=op.f('ck_sales_lifecycle')),
    sa.CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name=op.f('ck_sales_currency_code')),
    sa.CheckConstraint("payment_condition_code_snapshot IN ('CASH','CREDIT','FINANCING')", name=op.f('ck_sales_payment_code')),
    sa.CheckConstraint("payment_terms_days_snapshot >= 0 AND (payment_condition_code_snapshot <> 'CASH' OR payment_terms_days_snapshot = 0)", name=op.f('ck_sales_payment_terms')),
    sa.CheckConstraint("status IN ('DRAFT','CONFIRMED','CANCELLED')", name=op.f('ck_sales_status')),
    sa.CheckConstraint("customer_payment_condition_id IS NULL AND payment_condition_code_snapshot = 'CASH' AND payment_terms_days_snapshot = 0 AND due_date = operation_date", name=op.f('ck_sales_cash_only')),
    sa.CheckConstraint("status <> 'DRAFT' OR has_unknown_cost IS FALSE", name=op.f('ck_sales_draft_unknown_cost')),
    sa.CheckConstraint('sequence_value IS NULL OR sequence_value > 0', name=op.f('ck_sales_sequence_value')),
    sa.CheckConstraint('subtotal >= 0 AND discount_total >= 0 AND tax_total >= 0 AND total >= 0', name=op.f('ck_sales_amounts_non_negative')),
    sa.CheckConstraint('total = subtotal - discount_total + tax_total', name=op.f('ck_sales_totals')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_sales_version')),
    sa.ForeignKeyConstraint(['sale_sequence_id'], ['sale_sequences.id'], name=op.f('fk_sales_sale_sequence_id_sale_sequences')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sales'))
    )
    op.create_index('ix_sales_company_branch', 'sales', ['company_id', 'branch_id'], unique=False)
    op.create_index('ix_sales_company_date', 'sales', ['company_id', 'operation_date', 'created_at', 'id'], unique=False)
    op.create_index('ix_sales_company_status', 'sales', ['company_id', 'status'], unique=False)
    op.create_index('ix_sales_company_customer', 'sales', ['company_id', 'company_customer_id'], unique=False)
    op.create_index('uq_sales_company_number', 'sales', ['company_id', 'number'], unique=True, postgresql_where=sa.text('number IS NOT NULL'))
    op.create_table('sale_details',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('sale_id', sa.UUID(), nullable=False),
    sa.Column('line_number', sa.SmallInteger(), nullable=False),
    sa.Column('company_product_id', sa.UUID(), nullable=False),
    sa.Column('company_product_presentation_id', sa.UUID(), nullable=True),
    sa.Column('price_list_id', sa.UUID(), nullable=True),
    sa.Column('price_list_item_id', sa.UUID(), nullable=True),
    sa.Column('price_list_requested', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('product_code_snapshot', sa.String(length=80), nullable=False),
    sa.Column('product_name_snapshot', sa.String(length=200), nullable=False),
    sa.Column('presentation_code_snapshot', sa.String(length=80), nullable=True),
    sa.Column('presentation_name_snapshot', sa.String(length=160), nullable=True),
    sa.Column('base_quantity_factor_snapshot', sa.Numeric(precision=18, scale=8), server_default=sa.text('1'), nullable=False),
    sa.Column('unit_code_snapshot', sa.String(length=20), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
    sa.Column('unit_cost_snapshot', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('cost_total', sa.Numeric(precision=18, scale=2), nullable=True),
    sa.Column('cost_known', sa.Boolean(), nullable=True),
    sa.Column('gross_margin_amount', sa.Numeric(precision=18, scale=2), nullable=True),
    sa.Column('gross_margin_percentage', sa.Numeric(precision=7, scale=4), nullable=True),
    sa.Column('discount_amount', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('tax_amount', sa.Numeric(precision=18, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('subtotal', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('total', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=255), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by', sa.String(length=255), nullable=False),
    sa.CheckConstraint('(company_product_presentation_id IS NULL AND base_quantity_factor_snapshot = 1 AND presentation_code_snapshot IS NULL AND presentation_name_snapshot IS NULL) OR (company_product_presentation_id IS NOT NULL AND presentation_code_snapshot IS NOT NULL AND presentation_name_snapshot IS NOT NULL)', name=op.f('ck_sale_details_presentation')),
    sa.CheckConstraint('base_quantity_factor_snapshot > 0', name=op.f('ck_sale_details_factor')),
    sa.CheckConstraint('discount_amount >= 0 AND discount_amount <= subtotal', name=op.f('ck_sale_details_discount_amount')),
    sa.CheckConstraint('line_number BETWEEN 1 AND 100', name=op.f('ck_sale_details_line_number')),
    sa.CheckConstraint('quantity > 0', name=op.f('ck_sale_details_quantity')),
    sa.CheckConstraint('subtotal >= 0', name=op.f('ck_sale_details_subtotal')),
    sa.CheckConstraint('tax_amount >= 0', name=op.f('ck_sale_details_tax_amount')),
    sa.CheckConstraint('total = subtotal - discount_amount + tax_amount', name=op.f('ck_sale_details_total')),
    sa.CheckConstraint('unit_price >= 0', name=op.f('ck_sale_details_unit_price')),
    sa.CheckConstraint('unit_cost_snapshot IS NULL OR unit_cost_snapshot >= 0', name=op.f('ck_sale_details_unit_cost_snapshot')),
    sa.CheckConstraint('cost_total IS NULL OR cost_total >= 0', name=op.f('ck_sale_details_cost_total')),
    sa.CheckConstraint('(unit_cost_snapshot IS NULL AND cost_total IS NULL AND cost_known IS NULL) OR (unit_cost_snapshot IS NOT NULL AND cost_total IS NOT NULL AND cost_known IS NOT NULL)', name=op.f('ck_sale_details_cost_block')),
    sa.CheckConstraint('(cost_known IS TRUE AND gross_margin_amount IS NOT NULL) OR (cost_known IS NOT TRUE AND gross_margin_amount IS NULL AND gross_margin_percentage IS NULL)', name=op.f('ck_sale_details_margin_amount')),
    sa.CheckConstraint('gross_margin_percentage IS NULL OR gross_margin_percentage <= 100', name=op.f('ck_sale_details_margin_percentage')),
    sa.CheckConstraint('price_list_item_id IS NULL OR price_list_id IS NOT NULL', name=op.f('ck_sale_details_price_list_item')),
    sa.CheckConstraint('price_list_requested IS FALSE OR price_list_id IS NOT NULL', name=op.f('ck_sale_details_price_list_requested')),
    sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], name=op.f('fk_sale_details_sale_id_sales')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sale_details')),
    sa.UniqueConstraint('sale_id', 'line_number', name='uq_sale_details_line_number')
    )
    op.create_table('sale_operations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('sale_id', sa.UUID(), nullable=False),
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
    sa.CheckConstraint("(status = 'PENDING') = (completed_at IS NULL)", name=op.f('ck_sale_operations_completed_at')),
    sa.CheckConstraint("operation_type IN ('CONFIRM','CANCEL')", name=op.f('ck_sale_operations_operation_type')),
    sa.CheckConstraint("status <> 'FAILED' OR error_code IS NOT NULL", name=op.f('ck_sale_operations_failed_code')),
    sa.CheckConstraint("status <> 'SUCCEEDED' OR operation_type = 'CANCEL' OR inventory_operation_id IS NOT NULL", name=op.f('ck_sale_operations_inventory_operation')),
    sa.CheckConstraint("status IN ('PENDING','SUCCEEDED','FAILED')", name=op.f('ck_sale_operations_status')),
    sa.CheckConstraint('char_length(idempotency_key) BETWEEN 1 AND 150', name=op.f('ck_sale_operations_idempotency_key')),
    sa.CheckConstraint("operation_type <> 'CANCEL' OR reason IS NOT NULL", name=op.f('ck_sale_operations_cancel_reason')),
    sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], name=op.f('fk_sale_operations_sale_id_sales')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sale_operations')),
    sa.UniqueConstraint('idempotency_key', name='uq_sale_operations_idempotency_key')
    )
    op.create_index('ix_sale_operations_pending_age', 'sale_operations', ['updated_at'], unique=False, postgresql_where=sa.text("status = 'PENDING'"))
    op.create_index('ix_sale_operations_sale', 'sale_operations', ['sale_id', 'started_at'], unique=False)
    op.create_index('uq_sale_operations_pending', 'sale_operations', ['sale_id'], unique=True, postgresql_where=sa.text("status = 'PENDING'"))
    create_triggers()


def downgrade() -> None:
    """Downgrade schema."""
    drop_triggers()
    op.drop_index('uq_sale_operations_pending', table_name='sale_operations', postgresql_where=sa.text("status = 'PENDING'"))
    op.drop_index('ix_sale_operations_sale', table_name='sale_operations')
    op.drop_index('ix_sale_operations_pending_age', table_name='sale_operations', postgresql_where=sa.text("status = 'PENDING'"))
    op.drop_table('sale_operations')
    op.drop_table('sale_details')
    op.drop_index('uq_sales_company_number', table_name='sales', postgresql_where=sa.text('number IS NOT NULL'))
    op.drop_index('ix_sales_company_customer', table_name='sales')
    op.drop_index('ix_sales_company_status', table_name='sales')
    op.drop_index('ix_sales_company_date', table_name='sales')
    op.drop_index('ix_sales_company_branch', table_name='sales')
    op.drop_table('sales')
    op.drop_table('sale_sequence_counters')
    op.drop_index('uq_sale_sequences_series', table_name='sale_sequences')
    op.drop_index('uq_sale_sequences_active', table_name='sale_sequences', postgresql_where=sa.text('is_active'))
    op.drop_table('sale_sequences')
    drop_audit_outbox_table(op)
