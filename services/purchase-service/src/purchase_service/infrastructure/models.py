"""Modelos SQLAlchemy de Purchase Service (`specs/014-purchase-core/data-model.md`).

Toda columna REF es un UUID validado contra su dueño (research.md R-06), sin FK
física hacia otros servicios. Las restricciones llevan nombre explícito por la
convención de `Base` (Principio VIII). Las reglas de ciclo de vida e inmutabilidad
también viven en triggers de la migración `0001`.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sio_audit.outbox import audit_outbox_table
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from purchase_service.infrastructure.database import Base

NIL_UUID = "00000000-0000-0000-0000-000000000000"

PURCHASE_LIFECYCLE = (
    "(status = 'DRAFT' AND number IS NULL AND sequence_value IS NULL AND purchase_sequence_id IS NULL "
    "AND inventory_operation_id IS NULL AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL "
    "AND cancellation_reason IS NULL) "
    "OR (status = 'CONFIRMED' AND number IS NOT NULL AND sequence_value IS NOT NULL "
    "AND purchase_sequence_id IS NOT NULL AND inventory_operation_id IS NOT NULL "
    "AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancellation_reason IS NULL) "
    "OR (status = 'CANCELLED' AND cancelled_by_user_id IS NOT NULL AND cancelled_at IS NOT NULL "
    "AND cancellation_reason IS NOT NULL AND ("
    "(number IS NULL AND sequence_value IS NULL AND purchase_sequence_id IS NULL AND inventory_operation_id IS NULL) "
    "OR (number IS NOT NULL AND sequence_value IS NOT NULL AND purchase_sequence_id IS NOT NULL "
    "AND inventory_operation_id IS NOT NULL)))"
)


class AuditColumns:
    """Auditoría D1 (Principio VI): `sub` de la identidad autenticada o del proceso."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


class Purchase(AuditColumns, Base):
    """Cabecera de la compra (§7.1; BR-14: `inventory_operation_id` y D1)."""

    __tablename__ = "purchases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    company_supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    supplier_payment_condition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payment_condition_code_snapshot: Mapped[str] = mapped_column(String(30), nullable=False)
    payment_terms_days_snapshot: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_sequence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_sequences.id"), nullable=True
    )
    number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sequence_value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    operation_date: Mapped[date] = mapped_column(Date, nullable=False)
    promised_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supplier_document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supplier_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    supplier_identification_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    tax_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    inventory_operation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    __mapper_args__ = {"version_id_col": version}

    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','CONFIRMED','CANCELLED')", name="status"),
        CheckConstraint(PURCHASE_LIFECYCLE, name="lifecycle"),
        CheckConstraint("payment_condition_code_snapshot IN ('CASH','CREDIT','FINANCING')", name="payment_code"),
        CheckConstraint(
            "payment_terms_days_snapshot >= 0 AND "
            "(payment_condition_code_snapshot <> 'CASH' OR payment_terms_days_snapshot = 0)",
            name="payment_terms",
        ),
        CheckConstraint("due_date >= operation_date", name="due_date"),
        CheckConstraint("sequence_value IS NULL OR sequence_value > 0", name="sequence_value"),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency_code"),
        CheckConstraint(
            "subtotal >= 0 AND discount_total >= 0 AND tax_total >= 0 AND total >= 0", name="amounts_non_negative"
        ),
        CheckConstraint("total = subtotal - discount_total + tax_total", name="totals"),
        CheckConstraint("version >= 1", name="version"),
        Index(
            "uq_purchases_company_number",
            "company_id",
            "number",
            unique=True,
            postgresql_where=text("number IS NOT NULL"),
        ),
        Index("ix_purchases_company_date", "company_id", "operation_date", "created_at", "id"),
        Index("ix_purchases_company_status", "company_id", "status"),
        Index("ix_purchases_company_branch", "company_id", "branch_id"),
        Index("ix_purchases_company_supplier", "company_id", "company_supplier_id"),
    )


class PurchaseDetail(AuditColumns, Base):
    """Línea de la compra (§7.2; BR-14: D1)."""

    __tablename__ = "purchase_details"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    purchase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchases.id"), nullable=False)
    line_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    company_product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    company_product_presentation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    supplier_product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    supplier_lead_time_snapshot_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    product_code_snapshot: Mapped[str] = mapped_column(String(80), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    presentation_code_snapshot: Mapped[str | None] = mapped_column(String(80), nullable=True)
    presentation_name_snapshot: Mapped[str | None] = mapped_column(String(160), nullable=True)
    base_quantity_factor_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(18, 8), nullable=False, server_default=text("1")
    )
    unit_code_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("purchase_id", "line_number", name="uq_purchase_details_line_number"),
        CheckConstraint("line_number BETWEEN 1 AND 100", name="line_number"),
        CheckConstraint("quantity > 0", name="quantity"),
        CheckConstraint("unit_cost >= 0", name="unit_cost"),
        CheckConstraint("tax_amount >= 0", name="tax_amount"),
        CheckConstraint("subtotal >= 0", name="subtotal"),
        CheckConstraint("discount_amount >= 0 AND discount_amount <= subtotal", name="discount_amount"),
        CheckConstraint("total = subtotal - discount_amount + tax_amount", name="total"),
        CheckConstraint("base_quantity_factor_snapshot > 0", name="factor"),
        CheckConstraint(
            "(company_product_presentation_id IS NULL AND base_quantity_factor_snapshot = 1 "
            "AND presentation_code_snapshot IS NULL AND presentation_name_snapshot IS NULL) "
            "OR (company_product_presentation_id IS NOT NULL AND presentation_code_snapshot IS NOT NULL "
            "AND presentation_name_snapshot IS NOT NULL)",
            name="presentation",
        ),
        CheckConstraint(
            "supplier_lead_time_snapshot_hours IS NULL OR supplier_lead_time_snapshot_hours >= 0", name="lead_time"
        ),
    )


class PurchaseSequence(AuditColumns, Base):
    """Configuración de numeración (§7.3; BR-14: sin `current_number`/`last_reset_at`, D1)."""

    __tablename__ = "purchase_sequences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    document_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    series_code: Mapped[str] = mapped_column(String(40), nullable=False)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    separator: Mapped[str] = mapped_column(String(5), nullable=False)
    initial_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    maximum_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    number_length: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reset_policy: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    __mapper_args__ = {"version_id_col": version}

    __table_args__ = (
        CheckConstraint("document_kind = 'PURCHASE'", name="document_kind"),
        CheckConstraint("series_code ~ '^[A-Z0-9_-]{1,40}$'", name="series_code"),
        CheckConstraint("prefix ~ '^[A-Z0-9]{1,20}$'", name="prefix"),
        CheckConstraint("separator IN ('-','/','.','_','')", name="separator"),
        CheckConstraint("initial_number >= 1", name="initial_number"),
        CheckConstraint("maximum_number IS NULL OR maximum_number >= initial_number", name="maximum_number"),
        CheckConstraint("number_length BETWEEN 1 AND 18", name="number_length"),
        CheckConstraint("reset_policy IN ('NEVER','YEARLY','MONTHLY')", name="reset_policy"),
        CheckConstraint(
            "char_length(prefix) + 2 * char_length(separator) + 6 + number_length <= 80", name="number_text_length"
        ),
        CheckConstraint("version >= 1", name="version"),
        Index(
            "uq_purchase_sequences_active",
            "company_id",
            text(f"COALESCE(branch_id, '{NIL_UUID}'::uuid)"),
            "document_kind",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        Index(
            "uq_purchase_sequences_series",
            "company_id",
            text(f"COALESCE(branch_id, '{NIL_UUID}'::uuid)"),
            "document_kind",
            "series_code",
            unique=True,
        ),
    )


class PurchaseSequenceCounter(AuditColumns, Base):
    """Contador por secuencia y período (nueva; BR-14, P-04)."""

    __tablename__ = "purchase_sequence_counters"

    purchase_sequence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_sequences.id"), primary_key=True
    )
    period_key: Mapped[str] = mapped_column(String(6), primary_key=True)
    current_number: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("period_key ~ '^([0-9]{4}|[0-9]{6})?$'", name="period_key"),
        CheckConstraint("current_number >= 1", name="current_number"),
    )


class PurchaseOperation(Base):
    """Seguimiento de confirmación o anulación distribuida (§7.4; BR-14, P-05)."""

    __tablename__ = "purchase_operations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    purchase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchases.id"), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    application_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    inventory_operation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_purchase_operations_idempotency_key"),
        CheckConstraint("operation_type IN ('CONFIRM','CANCEL')", name="operation_type"),
        CheckConstraint("status IN ('PENDING','SUCCEEDED','FAILED')", name="status"),
        CheckConstraint("status <> 'FAILED' OR error_code IS NOT NULL", name="failed_code"),
        CheckConstraint("(status = 'PENDING') = (completed_at IS NULL)", name="completed_at"),
        CheckConstraint(
            "status <> 'SUCCEEDED' OR operation_type = 'CANCEL' OR inventory_operation_id IS NOT NULL",
            name="inventory_operation",
        ),
        CheckConstraint("char_length(idempotency_key) BETWEEN 1 AND 150", name="idempotency_key"),
        CheckConstraint("operation_type <> 'CANCEL' OR reason IS NOT NULL", name="cancel_reason"),
        Index(
            "uq_purchase_operations_pending",
            "purchase_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index("ix_purchase_operations_pending_age", "updated_at", postgresql_where=text("status = 'PENDING'")),
        Index("ix_purchase_operations_purchase", "purchase_id", "started_at"),
    )


class PurchaseLifecycleEvent(Base):
    """Hito logístico inmutable (§7.5; BR-14: `created_by`)."""

    __tablename__ = "purchase_lifecycle_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    purchase_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchases.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('ORDERED','SUPPLIER_DISPATCHED','ARRIVED','RECEIVED','AVAILABLE_FOR_SALE')",
            name="event_type",
        ),
        CheckConstraint("source IN ('USER','SUPPLIER','INTEGRATION','SYSTEM')", name="source"),
        Index("ix_purchase_lifecycle_events_purchase", "purchase_id", "event_type", "created_at", "id"),
    )


audit_outbox = audit_outbox_table(Base.metadata)
