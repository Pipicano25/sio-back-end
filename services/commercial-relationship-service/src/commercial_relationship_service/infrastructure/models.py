"""Modelos SQLAlchemy de Commercial Relationship Service (`data-model.md`).

Tres entidades persistentes de dominio (Principio VI) con auditoría y `version`
(`version_id_col`, Principio VII). Ninguna FK física: todas las referencias a
otros servicios son `UUID REF` (Principio II). Los nombres de restricciones e
índices son los de `data-model.md`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR
from sqlalchemy.orm import Mapped, mapped_column

from commercial_relationship_service.infrastructure.database import Base


class _Audited:
    """Columnas comunes de auditoría y concurrencia."""

    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="ACTIVE")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


class CompanyProductModel(_Audited, Base):
    """Adopción privada de un `GlobalProduct` por una empresa (§`company_products`)."""

    __tablename__ = "company_products"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    global_product_id: Mapped[UUID] = mapped_column(nullable=False)
    internal_code: Mapped[str] = mapped_column(String(60), nullable=False)
    reference_code: Mapped[str | None] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(160))
    sale_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    reference_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, server_default="0"
    )
    inventory_control_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    lot_tracking_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    expiration_tracking_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_purchasable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_sellable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __mapper_args__ = {"version_id_col": _Audited.version}

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "global_product_id",
            name="uq_company_products_company_id_global_product_id",
        ),
        Index(
            "uq_company_products_company_id_internal_code_ci",
            "company_id",
            func.lower(text("internal_code")),
            unique=True,
        ),
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="status"),
        CheckConstraint("sale_price >= 0", name="sale_price_non_negative"),
        CheckConstraint(
            "reference_cost >= 0", name="reference_cost_non_negative"
        ),
        CheckConstraint(
            "currency_code ~ '^[A-Z]{3}$'", name="currency_code_format"
        ),
        CheckConstraint(
            "NOT lot_tracking_enabled OR inventory_control_enabled",
            name="lot_requires_inventory",
        ),
        CheckConstraint(
            "NOT expiration_tracking_enabled OR lot_tracking_enabled",
            name="expiration_requires_lot",
        ),
        CheckConstraint(
            "internal_code = btrim(internal_code) AND internal_code <> ''",
            name="internal_code_not_blank",
        ),
        CheckConstraint(
            "btrim(display_name) <> ''", name="display_name_not_blank"
        ),
        Index("ix_company_products_company_id_status", "company_id", "status"),
        Index("ix_company_products_global_product_id", "global_product_id"),
    )


class CompanyCustomerModel(_Audited, Base):
    """Relación privada empresa–cliente persona u organización (§`company_customers`)."""

    __tablename__ = "company_customers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    customer_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    person_identity_id: Mapped[UUID | None] = mapped_column()
    organization_identity_id: Mapped[UUID | None] = mapped_column()
    internal_code: Mapped[str] = mapped_column(String(60), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    preferred_contact_person_id: Mapped[UUID | None] = mapped_column()

    __mapper_args__ = {"version_id_col": _Audited.version}

    __table_args__ = (
        CheckConstraint(
            "customer_kind IN ('PERSON','ORGANIZATION')", name="kind"
        ),
        CheckConstraint(
            "(customer_kind = 'PERSON' AND person_identity_id IS NOT NULL "
            "AND organization_identity_id IS NULL) OR "
            "(customer_kind = 'ORGANIZATION' AND organization_identity_id IS NOT NULL "
            "AND person_identity_id IS NULL)",
            name="identity_by_kind",
        ),
        CheckConstraint(
            "preferred_contact_person_id IS NULL OR customer_kind = 'ORGANIZATION'",
            name="contact_only_organization",
        ),
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="status"),
        CheckConstraint(
            "internal_code = btrim(internal_code) AND internal_code <> ''",
            name="internal_code_not_blank",
        ),
        CheckConstraint(
            "btrim(display_name) <> ''", name="display_name_not_blank"
        ),
        Index(
            "uq_company_customers_company_id_person_identity_id",
            "company_id",
            "person_identity_id",
            unique=True,
            postgresql_where=text("person_identity_id IS NOT NULL"),
        ),
        Index(
            "uq_company_customers_company_id_organization_identity_id",
            "company_id",
            "organization_identity_id",
            unique=True,
            postgresql_where=text("organization_identity_id IS NOT NULL"),
        ),
        Index(
            "uq_company_customers_company_id_internal_code_ci",
            "company_id",
            func.lower(text("internal_code")),
            unique=True,
        ),
        Index("ix_company_customers_company_id_status", "company_id", "status"),
        Index("ix_company_customers_person_identity_id", "person_identity_id"),
        Index("ix_company_customers_organization_identity_id", "organization_identity_id"),
    )


class CompanySupplierModel(_Audited, Base):
    """Relación privada empresa–proveedor organización (§`company_suppliers`)."""

    __tablename__ = "company_suppliers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    organization_identity_id: Mapped[UUID] = mapped_column(nullable=False)
    internal_code: Mapped[str] = mapped_column(String(60), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    preferred_contact_person_id: Mapped[UUID | None] = mapped_column()
    block_reason: Mapped[str | None] = mapped_column(String(500))

    __mapper_args__ = {"version_id_col": _Audited.version}

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "organization_identity_id",
            name="uq_company_suppliers_company_id_organization_identity_id",
        ),
        Index(
            "uq_company_suppliers_company_id_internal_code_ci",
            "company_id",
            func.lower(text("internal_code")),
            unique=True,
        ),
        CheckConstraint(
            "status IN ('ACTIVE','INACTIVE','BLOCKED')", name="status"
        ),
        CheckConstraint(
            "(status = 'BLOCKED' AND block_reason IS NOT NULL AND btrim(block_reason) <> '') "
            "OR (status <> 'BLOCKED' AND block_reason IS NULL)",
            name="block_reason_consistency",
        ),
        CheckConstraint(
            "internal_code = btrim(internal_code) AND internal_code <> ''",
            name="internal_code_not_blank",
        ),
        CheckConstraint(
            "btrim(display_name) <> ''", name="display_name_not_blank"
        ),
        Index("ix_company_suppliers_company_id_status", "company_id", "status"),
        Index("ix_company_suppliers_organization_identity_id", "organization_identity_id"),
    )
