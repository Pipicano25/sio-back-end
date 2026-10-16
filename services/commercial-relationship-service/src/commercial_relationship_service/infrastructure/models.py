"""Modelos SQLAlchemy de Commercial Relationship Service (`data-model.md` de la 007 y la 010).

Ocho entidades persistentes de dominio (Principio VI) con auditoría y `version`
(`version_id_col`, Principio VII). Ninguna FK hacia otros servicios: todas sus
referencias son `UUID REF` (Principio II). Las FK internas de la Fase B son
compuestas con `company_id` para garantizar la misma empresa (R-02). Los nombres
de restricciones e índices son los de `data-model.md`; la restricción de
exclusión `ex_price_list_items_no_overlap` solo existe en la migración `0002`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
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
from sqlalchemy.dialects.postgresql import ARRAY, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
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
    # Spec 019: sin precio ni costo; `currency_code` elige la lista de precios predeterminada.
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False)
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
    # Spec 021 (FR-021-07): NULL = sin configurar; 0 es válido. CHECK en la migración 0005.
    purchase_tax_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))

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
        UniqueConstraint("id", "company_id", name="uq_company_products_id_company_id"),
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
        UniqueConstraint("id", "company_id", name="uq_company_suppliers_id_company_id"),
    )


# --------------------------------------------------------------------------
# Fase B (specs/010-commercial-relationship-commercial-product/data-model.md)
# --------------------------------------------------------------------------

NO_PRESENTATION = text(
    "COALESCE(company_product_presentation_id, '00000000-0000-0000-0000-000000000000'::uuid)"
)
"""La ausencia de presentación cuenta como un valor en unicidades y vigencias (R-03)."""


def _same_company_fk(columns: list[str], table: str, name: str) -> ForeignKeyConstraint:
    """FK interna compuesta: la segunda columna liga la empresa o el producto (R-02)."""
    return ForeignKeyConstraint(
        columns, [f"{table}.id", f"{table}.{columns[1]}"], name=name, ondelete="RESTRICT"
    )


class CompanyProductPresentationModel(_Audited, Base):
    """Adopción de una `GlobalProductPresentation` por un producto empresarial (FR-010)."""

    __tablename__ = "company_product_presentations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    company_product_id: Mapped[UUID] = mapped_column(nullable=False)
    global_product_presentation_id: Mapped[UUID] = mapped_column(nullable=False)
    internal_code: Mapped[str | None] = mapped_column(String(80))
    sku: Mapped[str | None] = mapped_column(String(80))
    reference_code: Mapped[str | None] = mapped_column(String(100))
    is_purchasable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_sellable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    is_default_purchase: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_default_sale: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    __mapper_args__ = {"version_id_col": _Audited.version}

    __table_args__ = (
        _same_company_fk(
            ["company_product_id", "company_id"],
            "company_products",
            "fk_company_product_presentations_company_product",
        ),
        UniqueConstraint("id", "company_id", name="uq_company_product_presentations_id_company_id"),
        UniqueConstraint(
            "id", "company_product_id", name="uq_company_product_presentations_id_company_product_id"
        ),
        UniqueConstraint(
            "company_product_id",
            "global_product_presentation_id",
            name="uq_company_product_presentations_product_global_presentation",
        ),
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="status"),
        CheckConstraint(
            "NOT is_default_purchase OR is_purchasable",
            name="default_purchase_purchasable",
        ),
        CheckConstraint(
            "NOT is_default_sale OR is_sellable", name="default_sale_sellable"
        ),
        CheckConstraint(
            "status = 'ACTIVE' OR (NOT is_default_purchase AND NOT is_default_sale)",
            name="default_requires_active",
        ),
        Index(
            "uq_company_product_presentations_company_id_sku_ci",
            "company_id",
            func.lower(text("sku")),
            unique=True,
            postgresql_where=text("sku IS NOT NULL"),
        ),
        Index(
            "uq_company_product_presentations_company_id_internal_code_ci",
            "company_id",
            func.lower(text("internal_code")),
            unique=True,
            postgresql_where=text("internal_code IS NOT NULL"),
        ),
        Index(
            "uq_company_product_presentations_default_purchase",
            "company_product_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND is_default_purchase"),
        ),
        Index(
            "uq_company_product_presentations_default_sale",
            "company_product_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND is_default_sale"),
        ),
        Index("ix_company_product_presentations_company_id_status", "company_id", "status"),
        Index(
            "ix_company_product_presentations_global_product_presentation_id",
            "global_product_presentation_id",
        ),
    )


class SupplierProductModel(_Audited, Base):
    """Producto que un proveedor suministra a la empresa (FR-020)."""

    __tablename__ = "supplier_products"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    company_supplier_id: Mapped[UUID] = mapped_column(nullable=False)
    company_product_id: Mapped[UUID] = mapped_column(nullable=False)
    company_product_presentation_id: Mapped[UUID | None] = mapped_column()
    supplier_product_code: Mapped[str | None] = mapped_column(String(100))
    purchase_unit_id: Mapped[UUID] = mapped_column(nullable=False)
    minimum_order_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, server_default="0"
    )
    pack_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default="1")
    negotiated_unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    expected_supplier_lead_time_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    priority: Mapped[int | None] = mapped_column(SmallInteger)
    is_preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    __mapper_args__ = {"version_id_col": _Audited.version}

    __table_args__ = (
        _same_company_fk(
            ["company_supplier_id", "company_id"],
            "company_suppliers",
            "fk_supplier_products_company_supplier",
        ),
        _same_company_fk(
            ["company_product_id", "company_id"],
            "company_products",
            "fk_supplier_products_company_product",
        ),
        _same_company_fk(
            ["company_product_presentation_id", "company_product_id"],
            "company_product_presentations",
            "fk_supplier_products_presentation",
        ),
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="status"),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency_code_format"),
        CheckConstraint("minimum_order_quantity >= 0 AND pack_quantity > 0", name="quantities"),
        CheckConstraint("status = 'ACTIVE' OR NOT is_preferred", name="preferred_requires_active"),
        Index(
            "uq_supplier_products_active_relation",
            "company_supplier_id",
            "company_product_id",
            NO_PRESENTATION,
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "uq_supplier_products_preferred",
            "company_product_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND is_preferred"),
        ),
        Index("ix_supplier_products_company_id_status", "company_id", "status"),
        Index("ix_supplier_products_company_product_id", "company_product_id"),
        Index("ix_supplier_products_company_supplier_id", "company_supplier_id"),
    )


class SupplierPaymentConditionModel(_Audited, Base):
    """Condición de pago que un proveedor ofrece a la empresa (FR-030)."""

    __tablename__ = "supplier_payment_conditions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    company_supplier_id: Mapped[UUID] = mapped_column(nullable=False)
    payment_condition_type_id: Mapped[UUID] = mapped_column(nullable=False)
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    payment_terms_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    interest_rate_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    cash_discount_percentage: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __mapper_args__ = {"version_id_col": _Audited.version}

    __table_args__ = (
        _same_company_fk(
            ["company_supplier_id", "company_id"],
            "company_suppliers",
            "fk_supplier_payment_conditions_company_supplier",
        ),
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="status"),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency_code_format"),
        CheckConstraint("payment_terms_days BETWEEN 0 AND 3650", name="terms_range"),
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="validity"),
        CheckConstraint("status = 'ACTIVE' OR NOT is_default", name="default_requires_active"),
        Index(
            "uq_supplier_payment_conditions_default",
            "company_supplier_id",
            "currency_code",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND is_default"),
        ),
        Index("ix_supplier_payment_conditions_company_supplier_id", "company_supplier_id"),
        Index(
            "ix_supplier_payment_conditions_payment_condition_type_id", "payment_condition_type_id"
        ),
    )


class PriceListModel(_Audited, Base):
    """Lista de precios de la empresa (FR-040)."""

    __tablename__ = "price_lists"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __mapper_args__ = {"version_id_col": _Audited.version}

    __table_args__ = (
        UniqueConstraint("id", "company_id", name="uq_price_lists_id_company_id"),
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="status"),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency_code_format"),
        CheckConstraint(
            "valid_from IS NULL OR valid_to IS NULL OR valid_to > valid_from", name="validity"
        ),
        CheckConstraint("status = 'ACTIVE' OR NOT is_default", name="default_requires_active"),
        Index(
            "uq_price_lists_company_id_code_ci",
            "company_id",
            func.lower(text("code")),
            unique=True,
        ),
        Index(
            "uq_price_lists_default",
            "company_id",
            "currency_code",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND is_default"),
        ),
        Index("ix_price_lists_company_id_status", "company_id", "status"),
    )


class PriceListItemModel(_Audited, Base):
    """Precio de un producto empresarial (y opcionalmente una presentación) en una lista (FR-050)."""

    __tablename__ = "price_list_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    price_list_id: Mapped[UUID] = mapped_column(nullable=False)
    company_product_id: Mapped[UUID] = mapped_column(nullable=False)
    company_product_presentation_id: Mapped[UUID | None] = mapped_column()
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Spec 021 (FR-021-24): NULL = precio manual; los creados o cerrados por una aplicación lo indican.
    origin: Mapped[str | None] = mapped_column(String(12))
    closure_reason: Mapped[str | None] = mapped_column(String(30))
    automatic_application_id: Mapped[UUID | None] = mapped_column()

    __mapper_args__ = {"version_id_col": _Audited.version}

    __table_args__ = (
        _same_company_fk(
            ["price_list_id", "company_id"], "price_lists", "fk_price_list_items_price_list"
        ),
        _same_company_fk(
            ["company_product_id", "company_id"],
            "company_products",
            "fk_price_list_items_company_product",
        ),
        _same_company_fk(
            ["company_product_presentation_id", "company_product_id"],
            "company_product_presentations",
            "fk_price_list_items_presentation",
        ),
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="status"),
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="validity"),
        CheckConstraint("origin IS NULL OR origin = 'AUTOMATIC'", name="origin"),
        CheckConstraint(
            "closure_reason IS NULL OR closure_reason IN ('AUTOMATIC_SUPERSEDED', 'NO_POLICY')",
            name="closure_reason",
        ),
        ForeignKeyConstraint(
            ["automatic_application_id"],
            ["automatic_price_applications.id"],
            name="fk_price_list_items_automatic_application",
            ondelete="RESTRICT",
        ),
        Index("ix_price_list_items_resolution", "price_list_id", "company_product_id", "valid_from"),
        Index("ix_price_list_items_company_id_status", "company_id", "status"),
    )


# --------------------------------------------------------------------------
# Spec 021: políticas de precios y actualizaciones automáticas por recepción (`data-model.md`).
# Las exclusiones GiST (`ex_price_list_pricing_policy_*_no_overlap`) y los triggers de inmutabilidad
# solo existen en la migración 0005, como `ex_price_list_items_no_overlap`.
# --------------------------------------------------------------------------

AUTOMATIC_FINAL_STATUSES = (
    "APPLIED",
    "UNCHANGED",
    "ENDED_NO_POLICY",
    "NO_PRICE_TO_END",
    "SKIPPED_LIST_NOT_EFFECTIVE",
    "SKIPPED_CURRENCY_MISMATCH",
    "SKIPPED_PRESENTATION_INACTIVE",
    "SKIPPED_ZERO_COST",
    "RESOLVED",
)
AUTOMATIC_STATUSES = ("PENDING", "FAILED", *AUTOMATIC_FINAL_STATUSES)


def _quoted(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


class PricingPolicyModel(_Audited, Base):
    """Política de precios de una lista (FR-021-01); `INACTIVE` es final (FR-021-04)."""

    __tablename__ = "price_list_pricing_policies"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    price_list_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivation_reason: Mapped[str | None] = mapped_column(String(500))

    __mapper_args__ = {"version_id_col": _Audited.version}

    __table_args__ = (
        _same_company_fk(["price_list_id", "company_id"], "price_lists", "fk_price_list_pricing_policies_price_list"),
        UniqueConstraint("id", "price_list_id", name="uq_price_list_pricing_policies_id_price_list_id"),
        CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="status"),
        CheckConstraint("(status = 'INACTIVE') = (deactivated_at IS NOT NULL)", name="deactivation"),
        Index(
            "uq_price_list_pricing_policies_name_ci",
            "price_list_id",
            func.lower(text("name")),
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("ix_price_list_pricing_policies_company_id_status", "company_id", "status"),
    )


class _History:
    """Vigencia `[valid_from, valid_to)` y metadatos D25 de un historial inmutable."""

    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[str | None] = mapped_column(String(255))


def _history_checks() -> tuple[CheckConstraint, ...]:
    return (
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="validity"),
        CheckConstraint(
            "(valid_to IS NULL) = (closed_at IS NULL) AND (closed_at IS NULL) = (closed_by IS NULL)",
            name="closure",
        ),
    )


class PricingPolicyTermModel(_History, Base):
    """Porcentaje de recargo de una política durante una vigencia (FR-021-02); inmutable salvo su cierre."""

    __tablename__ = "price_list_pricing_policy_terms"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    policy_id: Mapped[UUID] = mapped_column(nullable=False)
    markup_percentage: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["policy_id"],
            ["price_list_pricing_policies.id"],
            name="fk_price_list_pricing_policy_terms_policy",
            ondelete="RESTRICT",
        ),
        CheckConstraint("markup_percentage >= 0 AND markup_percentage <= 1000", name="markup_range"),
        *_history_checks(),
    )


class PricingPolicyPresentationModel(_History, Base):
    """Pertenencia de una presentación a una política durante una vigencia (FR-021-03); inmutable salvo su cierre."""

    __tablename__ = "price_list_pricing_policy_presentations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    policy_id: Mapped[UUID] = mapped_column(nullable=False)
    price_list_id: Mapped[UUID] = mapped_column(nullable=False)
    company_product_presentation_id: Mapped[UUID] = mapped_column(nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["policy_id", "price_list_id"],
            ["price_list_pricing_policies.id", "price_list_pricing_policies.price_list_id"],
            name="fk_price_list_pricing_policy_presentations_policy",
            ondelete="RESTRICT",
        ),
        _same_company_fk(
            ["company_product_presentation_id", "company_id"],
            "company_product_presentations",
            "fk_price_list_pricing_policy_presentations_presentation",
        ),
        *_history_checks(),
        Index("ix_price_list_pricing_policy_presentations_policy_id", "policy_id"),
    )


class AutomaticPriceUpdateRequestModel(Base):
    """Inbox idempotente de las solicitudes de Purchase (FR-021-19; D26); inmutable."""

    __tablename__ = "automatic_price_update_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    contract_version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    purchase_id: Mapped[UUID] = mapped_column(nullable=False)
    purchase_detail_id: Mapped[UUID] = mapped_column(nullable=False)
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    company_product_id: Mapped[UUID] = mapped_column(nullable=False)
    company_product_presentation_id: Mapped[UUID] = mapped_column(nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_sequence: Mapped[int | None] = mapped_column(Integer)
    currency_code: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    previous_purchase_detail_id: Mapped[UUID | None] = mapped_column()
    previous_line_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    previous_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_by_user_id: Mapped[UUID] = mapped_column(nullable=False)
    payload_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        _same_company_fk(
            ["company_product_id", "company_id"], "company_products", "fk_automatic_price_update_requests_company_product"
        ),
        _same_company_fk(
            ["company_product_presentation_id", "company_product_id"],
            "company_product_presentations",
            "fk_automatic_price_update_requests_presentation",
        ),
        UniqueConstraint("purchase_detail_id", name="uq_automatic_price_update_requests_purchase_detail_id"),
        UniqueConstraint(
            "company_id", "company_product_presentation_id", "sequence", name="uq_automatic_price_update_requests_sequence"
        ),
        CheckConstraint("sequence > 0", name="sequence_positive"),
        CheckConstraint("previous_sequence IS NULL OR previous_sequence = sequence - 1", name="previous_sequence"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "(previous_line_total IS NULL) = (previous_quantity IS NULL) "
            "AND (previous_quantity IS NULL OR previous_quantity > 0)",
            name="previous_facts",
        ),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="currency_code_format"),
    )


class AutomaticPriceApplicationModel(Base):
    """Aplicación de una solicitud a una lista (FR-021-20..28): la captura es inmutable y un estado final no cambia."""

    __tablename__ = "automatic_price_applications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(nullable=False)
    request_id: Mapped[UUID] = mapped_column(nullable=False)
    price_list_id: Mapped[UUID] = mapped_column(nullable=False)
    company_product_presentation_id: Mapped[UUID] = mapped_column(nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_id: Mapped[UUID | None] = mapped_column()
    term_id: Mapped[UUID | None] = mapped_column()
    markup_percentage: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    current_unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(28, 10))
    previous_unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(28, 10))
    reference_cost: Mapped[Decimal | None] = mapped_column(Numeric(28, 10))
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    new_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    previous_price_item_id: Mapped[UUID | None] = mapped_column()
    new_price_item_id: Mapped[UUID | None] = mapped_column()
    cancelled_future_item_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)), nullable=False, server_default=text("'{}'::uuid[]")
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    first_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(60))
    last_error_detail: Mapped[str | None] = mapped_column(String(500))
    resolved_by: Mapped[str | None] = mapped_column(String(255))
    resolution_reason: Mapped[str | None] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)

    __mapper_args__ = {"version_id_col": version}

    __table_args__ = (
        ForeignKeyConstraint(
            ["request_id"],
            ["automatic_price_update_requests.id"],
            name="fk_automatic_price_applications_request",
            ondelete="RESTRICT",
        ),
        _same_company_fk(["price_list_id", "company_id"], "price_lists", "fk_automatic_price_applications_price_list"),
        ForeignKeyConstraint(
            ["policy_id"],
            ["price_list_pricing_policies.id"],
            name="fk_automatic_price_applications_policy",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["term_id"],
            ["price_list_pricing_policy_terms.id"],
            name="fk_automatic_price_applications_term",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("request_id", "price_list_id", name="uq_automatic_price_applications_request_list"),
        CheckConstraint(f"status IN ({_quoted(AUTOMATIC_STATUSES)})", name="status"),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        CheckConstraint(
            "(policy_id IS NULL) = (term_id IS NULL) AND (policy_id IS NULL) = (markup_percentage IS NULL)",
            name="capture",
        ),
        CheckConstraint(
            f"(status IN ({_quoted(AUTOMATIC_FINAL_STATUSES)})) = (completed_at IS NOT NULL)", name="completion"
        ),
        CheckConstraint(
            "(status = 'RESOLVED') = (resolved_by IS NOT NULL AND resolution_reason IS NOT NULL)", name="resolution"
        ),
        Index("ix_automatic_price_applications_queue", "price_list_id", "company_product_presentation_id", "sequence"),
        Index(
            "ix_automatic_price_applications_pending",
            "next_attempt_at",
            postgresql_where=text("status IN ('PENDING', 'FAILED')"),
        ),
        Index("ix_automatic_price_applications_company_id_status", "company_id", "status"),
    )

# Outbox de auditoría (feature 016, D26): estructura de `libs/sio-audit`, registrada en el
# `metadata` para que `alembic check` coincida con la migración.
from sio_audit.outbox import audit_outbox_table  # noqa: E402

audit_outbox = audit_outbox_table(Base.metadata)
