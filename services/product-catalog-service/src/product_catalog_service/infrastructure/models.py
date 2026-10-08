"""Modelos SQLAlchemy del catálogo global (`data-model.md`).

Bloques comunes:

- A: auditoría y concurrencia (`id`, `created_*`, `updated_*`, `version`).
- S: estado `ACTIVE`/`INACTIVE`.
- C: código normalizado en mayúsculas.
- U: marca irreversible de primer uso.

Las restricciones `CHECK` usan la convención `ck_<tabla>_<nombre>`; los índices
y restricciones únicas se nombran explícitamente.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from product_catalog_service.infrastructure.database import Base

STATUS_VALUES = ("ACTIVE", "INACTIVE")


# --------------------------------------------------------------------------
# Bloques comunes
# --------------------------------------------------------------------------


class AuditVersionMixin:
    """Bloque A: identificador, auditoría y control de concurrencia optimista."""

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    @declared_attr.directive
    def __mapper_args__(cls) -> dict:
        return {"version_id_col": cls.__table__.c.version}


class StatusMixin:
    """Bloque S: estado del registro."""

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default=text("'ACTIVE'"),
    )


class FirstUseMixin:
    """Bloque U: marca irreversible de primer uso (FR-076 a FR-079)."""

    first_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_used_by: Mapped[str | None] = mapped_column(String(255))
    first_use_source: Mapped[str | None] = mapped_column(String(20))


def status_check() -> CheckConstraint:
    return CheckConstraint("status IN ('ACTIVE','INACTIVE')", name="status")


def code_check() -> CheckConstraint:
    return CheckConstraint("code = upper(btrim(code)) AND code <> ''", name="code_normalized")


def first_use_checks() -> tuple[CheckConstraint, CheckConstraint]:
    return (
        CheckConstraint(
            "first_use_source IS NULL OR first_use_source IN ('ADOPTION','MANUAL')",
            name="first_use_source",
        ),
        CheckConstraint(
            "(first_used_at IS NULL AND first_used_by IS NULL AND first_use_source IS NULL)"
            " OR (first_used_at IS NOT NULL AND first_used_by IS NOT NULL"
            " AND first_use_source IS NOT NULL)",
            name="first_use_consistent",
        ),
    )


def display_order_check() -> CheckConstraint:
    return CheckConstraint("display_order >= 0", name="display_order")


# --------------------------------------------------------------------------
# 1–4. Catálogos base y taxonomía
# --------------------------------------------------------------------------


class GlobalUnitOfMeasureModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "global_units_of_measure"
    __table_args__ = (
        UniqueConstraint("code", name="uq_global_units_of_measure_code"),
        code_check(),
        status_check(),
        CheckConstraint(
            "measurement_type IN ('UNIT','MASS','VOLUME','LENGTH','AREA')",
            name="measurement_type",
        ),
    )

    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    measurement_type: Mapped[str] = mapped_column(String(30), nullable=False)
    allows_decimals: Mapped[bool] = mapped_column(Boolean, nullable=False)


class GlobalPackagingTypeModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "global_packaging_types"
    __table_args__ = (
        UniqueConstraint("code", name="uq_global_packaging_types_code"),
        code_check(),
        status_check(),
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class GlobalBrandModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "global_brands"
    __table_args__ = (
        UniqueConstraint("code", name="uq_global_brands_code"),
        code_check(),
        status_check(),
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class GlobalCategoryModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "global_categories"
    __table_args__ = (
        UniqueConstraint("code", name="uq_global_categories_code"),
        code_check(),
        status_check(),
        CheckConstraint(
            "parent_category_id IS NULL OR parent_category_id <> id",
            name="not_self_parent",
        ),
        Index("ix_global_categories_parent_category_id", "parent_category_id"),
    )

    parent_category_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("global_categories.id", ondelete="RESTRICT"),
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------------
# 5–6. Producto y clasificación
# --------------------------------------------------------------------------


class GlobalProductModel(AuditVersionMixin, StatusMixin, FirstUseMixin, Base):
    __tablename__ = "global_products"
    __table_args__ = (
        status_check(),
        CheckConstraint("product_type IN ('GOOD')", name="product_type"),
        *first_use_checks(),
        Index(
            "ix_global_products_canonical_name_key_trgm",
            "canonical_name_key",
            postgresql_using="gin",
            postgresql_ops={"canonical_name_key": "gin_trgm_ops"},
        ),
        Index("ix_global_products_duplicate_key", "canonical_name_key", "global_brand_id"),
        Index("ix_global_products_global_brand_id", "global_brand_id"),
        Index("ix_global_products_manufacturer_organization_id", "manufacturer_organization_id"),
        Index("ix_global_products_base_unit_id", "base_unit_id"),
        Index("ix_global_products_status", "status"),
    )

    product_type: Mapped[str] = mapped_column(String(20), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    canonical_name_key: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    global_brand_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("global_brands.id", ondelete="RESTRICT"),
    )
    # REF → Party Identity Service (OrganizationIdentity); sin FK física.
    manufacturer_organization_id: Mapped[UUID | None] = mapped_column(Uuid)
    base_unit_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("global_units_of_measure.id", ondelete="RESTRICT"),
        nullable=False,
    )


class GlobalProductCategoryModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "global_product_categories"
    __table_args__ = (
        UniqueConstraint(
            "global_product_id",
            "global_category_id",
            name="uq_global_product_categories_product_category",
        ),
        Index(
            "uq_global_product_categories_primary",
            "global_product_id",
            unique=True,
            postgresql_where=text("is_primary AND status = 'ACTIVE'"),
        ),
        status_check(),
        CheckConstraint("NOT is_primary OR status = 'ACTIVE'", name="primary_active"),
        Index("ix_global_product_categories_global_category_id", "global_category_id"),
    )

    global_product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("global_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    global_category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("global_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )


# --------------------------------------------------------------------------
# 7–10. Atributos
# --------------------------------------------------------------------------


class ProductAttributeDefinitionModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "product_attribute_definitions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_product_attribute_definitions_code"),
        code_check(),
        status_check(),
        CheckConstraint(
            "data_type IN ('TEXT','INTEGER','DECIMAL','BOOLEAN','DATE','OPTION')",
            name="data_type",
        ),
        CheckConstraint(
            "unit_of_measure_id IS NULL OR data_type IN ('INTEGER','DECIMAL')",
            name="unit_numeric",
        ),
        CheckConstraint("btrim(description) <> ''", name="description_not_blank"),
    )

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    data_type: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_of_measure_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("global_units_of_measure.id", ondelete="RESTRICT"),
    )


class ProductAttributeOptionModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "product_attribute_options"
    __table_args__ = (
        UniqueConstraint(
            "attribute_definition_id",
            "code",
            name="uq_product_attribute_options_definition_code",
        ),
        UniqueConstraint(
            "id",
            "attribute_definition_id",
            name="uq_product_attribute_options_id_definition",
        ),
        code_check(),
        status_check(),
        display_order_check(),
    )

    attribute_definition_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("product_attribute_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )


class GlobalCategoryAttributeModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "global_category_attributes"
    __table_args__ = (
        UniqueConstraint(
            "global_category_id",
            "attribute_definition_id",
            name="uq_global_category_attributes_category_definition",
        ),
        status_check(),
        display_order_check(),
        Index("ix_global_category_attributes_attribute_definition_id", "attribute_definition_id"),
    )

    global_category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("global_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attribute_definition_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("product_attribute_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_filterable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    display_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )


class GlobalProductAttributeValueModel(AuditVersionMixin, Base):
    __tablename__ = "global_product_attribute_values"
    __table_args__ = (
        UniqueConstraint(
            "global_product_id",
            "attribute_definition_id",
            name="uq_global_product_attribute_values_product_definition",
        ),
        ForeignKeyConstraint(
            ["option_id", "attribute_definition_id"],
            ["product_attribute_options.id", "product_attribute_options.attribute_definition_id"],
            name="fk_global_product_attribute_values_option_definition",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "num_nonnulls(option_id, text_value, integer_value, decimal_value,"
            " boolean_value, date_value) = 1",
            name="exactly_one",
        ),
        CheckConstraint("text_value IS NULL OR btrim(text_value) <> ''", name="text_not_blank"),
        Index("ix_global_product_attribute_values_attribute_definition_id", "attribute_definition_id"),
    )

    global_product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("global_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attribute_definition_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("product_attribute_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    option_id: Mapped[UUID | None] = mapped_column(Uuid)
    text_value: Mapped[str | None] = mapped_column(Text)
    integer_value: Mapped[int | None] = mapped_column(BigInteger)
    decimal_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    boolean_value: Mapped[bool | None] = mapped_column(Boolean)
    date_value: Mapped[date | None] = mapped_column(Date)


# --------------------------------------------------------------------------
# 11–12. Presentaciones e identificadores
# --------------------------------------------------------------------------


class GlobalProductPresentationModel(AuditVersionMixin, StatusMixin, FirstUseMixin, Base):
    __tablename__ = "global_product_presentations"
    __table_args__ = (
        UniqueConstraint(
            "global_product_id",
            "code",
            name="uq_global_product_presentations_product_code",
        ),
        UniqueConstraint(
            "id",
            "global_product_id",
            name="uq_global_product_presentations_id_product",
        ),
        Index(
            "uq_global_product_presentations_base",
            "global_product_id",
            unique=True,
            postgresql_where=text("is_base AND status = 'ACTIVE'"),
        ),
        code_check(),
        status_check(),
        *first_use_checks(),
        CheckConstraint("base_quantity > 0", name="base_quantity_positive"),
        CheckConstraint(
            "(content_quantity IS NULL) = (content_unit_id IS NULL)",
            name="content_pair",
        ),
        CheckConstraint(
            "content_quantity IS NULL OR content_quantity > 0",
            name="content_positive",
        ),
        CheckConstraint("NOT is_base OR base_quantity = 1", name="base_factor"),
        CheckConstraint("NOT is_base OR status = 'ACTIVE'", name="base_active"),
        display_order_check(),
    )

    global_product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("global_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    packaging_type_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("global_packaging_types.id", ondelete="RESTRICT"),
    )
    base_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 8), nullable=False, default=Decimal("1"), server_default=text("1")
    )
    content_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    content_unit_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("global_units_of_measure.id", ondelete="RESTRICT"),
    )
    display_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )
    is_base: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


class GlobalProductIdentifierModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "global_product_identifiers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["global_product_presentation_id", "global_product_id"],
            ["global_product_presentations.id", "global_product_presentations.global_product_id"],
            name="fk_global_product_identifiers_presentation_product",
            ondelete="RESTRICT",
        ),
        status_check(),
        CheckConstraint(
            "identifier_type IN ('GTIN','EAN','UPC','BARCODE','OTHER')",
            name="type",
        ),
        CheckConstraint(
            "identifier_type NOT IN ('GTIN','EAN','UPC') OR (value ~ '^[0-9]+$'"
            " AND length(value) IN (8, 12, 13, 14) AND canonical_value = lpad(value, 14, '0'))",
            name="gtin_format",
        ),
        CheckConstraint(
            "value !~ '[[:space:]-]' AND value <> ''",
            name="value_normalized",
        ),
        CheckConstraint("NOT is_primary OR status = 'ACTIVE'", name="primary_active"),
        Index(
            "uq_global_product_identifiers_gtin_family",
            "canonical_value",
            unique=True,
            postgresql_where=text("identifier_type IN ('GTIN','EAN','UPC')"),
        ),
        Index(
            "uq_global_product_identifiers_barcode",
            "value",
            unique=True,
            postgresql_where=text("identifier_type = 'BARCODE'"),
        ),
        Index(
            "uq_global_product_identifiers_other",
            "global_product_id",
            "value",
            unique=True,
            postgresql_where=text("identifier_type = 'OTHER'"),
        ),
        Index(
            "uq_global_product_identifiers_primary",
            "global_product_id",
            "global_product_presentation_id",
            "identifier_type",
            unique=True,
            postgresql_nulls_not_distinct=True,
            postgresql_where=text("is_primary AND status = 'ACTIVE'"),
        ),
        Index("ix_global_product_identifiers_canonical_value", "canonical_value"),
        Index("ix_global_product_identifiers_global_product_id", "global_product_id"),
    )

    global_product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("global_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    global_product_presentation_id: Mapped[UUID | None] = mapped_column(Uuid)
    identifier_type: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    canonical_value: Mapped[str] = mapped_column(String(100), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


# --------------------------------------------------------------------------
# 13–16. Grupos y activos
# --------------------------------------------------------------------------


class GlobalProductGroupTypeModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "global_product_group_types"
    __table_args__ = (
        UniqueConstraint("code", name="uq_global_product_group_types_code"),
        code_check(),
        status_check(),
        display_order_check(),
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    allows_multiple: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    display_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )


class GlobalProductGroupModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "global_product_groups"
    __table_args__ = (
        UniqueConstraint("group_type_id", "code", name="uq_global_product_groups_type_code"),
        UniqueConstraint("id", "group_type_id", name="uq_global_product_groups_id_type"),
        ForeignKeyConstraint(
            ["parent_group_id", "group_type_id"],
            ["global_product_groups.id", "global_product_groups.group_type_id"],
            name="fk_global_product_groups_parent_same_type",
            ondelete="RESTRICT",
        ),
        code_check(),
        status_check(),
        CheckConstraint(
            "parent_group_id IS NULL OR parent_group_id <> id",
            name="not_self_parent",
        ),
        Index("ix_global_product_groups_parent_group_id", "parent_group_id"),
    )

    group_type_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("global_product_group_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_group_id: Mapped[UUID | None] = mapped_column(Uuid)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class GlobalProductGroupAssignmentModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "global_product_group_assignments"
    __table_args__ = (
        UniqueConstraint(
            "global_product_id",
            "global_product_group_id",
            name="uq_global_product_group_assignments_product_group",
        ),
        ForeignKeyConstraint(
            ["global_product_group_id", "group_type_id"],
            ["global_product_groups.id", "global_product_groups.group_type_id"],
            name="fk_global_product_group_assignments_group_type",
            ondelete="RESTRICT",
        ),
        status_check(),
        Index(
            "ix_global_product_group_assignments_product_type",
            "global_product_id",
            "group_type_id",
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("ix_global_product_group_assignments_group_id", "global_product_group_id"),
        Index("ix_global_product_group_assignments_global_product_id", "global_product_id"),
    )

    global_product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("global_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    global_product_group_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    group_type_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)


class ProductAssetModel(AuditVersionMixin, StatusMixin, Base):
    __tablename__ = "product_assets"
    __table_args__ = (
        status_check(),
        CheckConstraint(
            "asset_type IN ('IMAGE','TECHNICAL_SHEET','MANUAL','CERTIFICATE','OTHER')",
            name="asset_type",
        ),
        CheckConstraint("NOT is_primary OR status = 'ACTIVE'", name="primary_active"),
        Index(
            "uq_product_assets_primary",
            "global_product_id",
            "asset_type",
            unique=True,
            postgresql_where=text("is_primary AND status = 'ACTIVE'"),
        ),
        Index("ix_product_assets_global_product_id", "global_product_id"),
    )

    global_product_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("global_products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120))
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


# Outbox de auditoría (feature 016, D26): estructura de `libs/sio-audit`, registrada en el
# `metadata` para que `alembic check` coincida con la migración.
from sio_audit.outbox import audit_outbox_table  # noqa: E402

audit_outbox = audit_outbox_table(Base.metadata)
