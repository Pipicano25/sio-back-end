"""Repositorios SQLAlchemy de las entidades de Commercial Relationship Service.

Fase A (007): productos empresariales, clientes y proveedores. Fase B (010):
presentaciones, productos de proveedor, condiciones de pago, listas y precios.
Las violaciones de restricciones se traducen por nombre (R-08 de la 007, T022
de la 010); la violación de un índice parcial de predeterminada pese al
bloqueo del ámbito se expone como `409 VERSION_CONFLICT` (DEFAULT_SWAP_CONFLICT).
"""

from __future__ import annotations

from datetime import datetime
from functools import partial
from typing import Any
from uuid import UUID

from sqlalchemy import and_, exists, func, or_, select, tuple_

from commercial_relationship_service.application.exceptions import (
    CompanyProductNotFoundError,
    CompanySupplierNotFoundError,
    DuplicateAdoptionError,
    DuplicateCustomerError,
    DuplicateInternalCodeError,
    DuplicatePresentationAdoptionError,
    DuplicatePriceListCodeError,
    DuplicateSkuError,
    DuplicateSupplierError,
    DuplicateSupplierProductError,
    PresentationOfOtherProductError,
    PriceListNotFoundError,
    PricePeriodOverlapError,
    VersionConflictError,
)
from commercial_relationship_service.domain.rules import code_key
from commercial_relationship_service.infrastructure.models import (
    CompanyCustomerModel,
    CompanyProductModel,
    CompanyProductPresentationModel,
    CompanySupplierModel,
    PriceListItemModel,
    PriceListModel,
    SupplierPaymentConditionModel,
    SupplierProductModel,
)
from commercial_relationship_service.application import audit_events
from commercial_relationship_service.infrastructure.persistence import commit_or_translate, end_read
from commercial_relationship_service.infrastructure.repository_base import (
    ALL_STATUSES,
    SQLAlchemyRepositoryBase,
    like_pattern,
)


def _code_duplicate(table: str) -> dict:
    return {
        f"uq_{table}_company_id_internal_code_ci": partial(DuplicateInternalCodeError, field="internal_code"),
    }


class CompanyProductRepository(SQLAlchemyRepositoryBase[CompanyProductModel]):
    """`company_products`."""

    model = CompanyProductModel
    search_columns = ("internal_code", "reference_code", "display_name")

    duplicates = {
        "uq_company_products_company_id_global_product_id": partial(DuplicateAdoptionError, field="global_product_id"),
        **_code_duplicate("company_products"),
    }

    def adoption_exists(self, company_id: UUID, global_product_id: UUID) -> bool:
        return self.exists_where(
            CompanyProductModel.company_id == company_id,
            CompanyProductModel.global_product_id == global_product_id,
        )


    def search_progressive(self, company_id: UUID, criteria: Any) -> tuple[list[CompanyProductModel], bool]:
        """CR-1 (spec 022, FR-022-80): búsqueda de solo lectura con continuación *keyset*.

        Orden `<clave> <dir>, id <dir>`; con `after`, la comparación de filas `(clave, id) > (:k, :id)`
        (`<` si es descendente) la hace PostgreSQL con su intercalación, la misma del `ORDER BY`. Se
        piden `limit + 1` filas para saber si hay más, sin contar.
        """
        product = CompanyProductModel
        presentation = CompanyProductPresentationModel
        statement = select(product).where(product.company_id == company_id)

        if criteria.status != ALL_STATUSES:
            statement = statement.where(product.status == criteria.status)

        for column in ("is_purchasable", "is_sellable", "inventory_control_enabled"):
            value = getattr(criteria, column)
            if value is not None:
                statement = statement.where(getattr(product, column) == value)

        if criteria.search:
            pattern = like_pattern(criteria.search)
            sku_match = exists().where(
                presentation.company_id == company_id,
                presentation.company_product_id == product.id,
                presentation.sku.ilike(pattern, escape="\\"),
            )
            statement = statement.where(
                or_(
                    *(getattr(product, column).ilike(pattern, escape="\\") for column in self.search_columns),
                    sku_match,
                )
            )

        if criteria.internal_code:
            statement = statement.where(func.lower(product.internal_code) == code_key(criteria.internal_code))

        if criteria.sku:
            statement = statement.where(
                exists().where(
                    presentation.company_id == company_id,
                    presentation.company_product_id == product.id,
                    func.lower(presentation.sku) == criteria.sku.strip().lower(),
                )
            )

        if criteria.company_product_ids is not None:
            statement = statement.where(product.id.in_(criteria.company_product_ids))

        if criteria.global_product_ids is not None:
            statement = statement.where(product.global_product_id.in_(criteria.global_product_ids))

        key = getattr(product, criteria.sort_key)
        descending = criteria.descending

        if criteria.after is not None:
            after_value, after_id = criteria.after
            row = tuple_(key, product.id)
            bound = tuple_(after_value, after_id)
            statement = statement.where(row < bound if descending else row > bound)

        order = (key.desc(), product.id.desc()) if descending else (key.asc(), product.id.asc())
        rows = list(self.session.scalars(statement.order_by(*order).limit(criteria.limit + 1)))
        end_read(self.session)
        return rows[: criteria.limit], len(rows) > criteria.limit

    def lock_many(self, ids: list[UUID]) -> dict[UUID, CompanyProductModel]:
        """Bloquea (`FOR UPDATE`) los productos en orden de `id` para una escritura por lote (spec 021)."""
        rows = self.session.scalars(
            select(CompanyProductModel)
            .where(CompanyProductModel.id.in_(ids))
            .order_by(CompanyProductModel.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        models = {row.id: row for row in rows}
        for model in models.values():
            audit_events.remember(self.session, model)
        return models

    def save_all(self, models: list[CompanyProductModel], *, audit: dict[str, Any]) -> list[CompanyProductModel]:
        """Confirma varias modificaciones en una sola transacción, con un evento por producto."""
        for model in models:
            audit_events.track_update(self.session, model, **audit)
        commit_or_translate(self.session, duplicates=self.duplicates)
        for model in models:
            self.session.refresh(model)
        end_read(self.session)
        return models

    def abort(self) -> None:
        self.session.rollback()

class CompanyCustomerRepository(SQLAlchemyRepositoryBase[CompanyCustomerModel]):
    """`company_customers`."""

    model = CompanyCustomerModel
    search_columns = ("internal_code", "display_name")

    duplicates = {
        "uq_company_customers_company_id_person_identity_id": partial(DuplicateCustomerError, field="person_identity_id"),
        "uq_company_customers_company_id_organization_identity_id": partial(DuplicateCustomerError, field="organization_identity_id"),
        **_code_duplicate("company_customers"),
    }

    def identity_exists(
        self,
        company_id: UUID,
        *,
        person_identity_id: UUID | None,
        organization_identity_id: UUID | None,
    ) -> bool:
        if person_identity_id is not None:
            return self.exists_where(
                CompanyCustomerModel.company_id == company_id,
                CompanyCustomerModel.person_identity_id == person_identity_id,
            )

        return self.exists_where(
            CompanyCustomerModel.company_id == company_id,
            CompanyCustomerModel.organization_identity_id == organization_identity_id,
        )


class CompanySupplierRepository(SQLAlchemyRepositoryBase[CompanySupplierModel]):
    """`company_suppliers`."""

    model = CompanySupplierModel
    search_columns = ("internal_code", "display_name")

    duplicates = {
        "uq_company_suppliers_company_id_organization_identity_id": partial(DuplicateSupplierError, field="organization_identity_id"),
        **_code_duplicate("company_suppliers"),
    }

    def organization_exists(self, company_id: UUID, organization_identity_id: UUID) -> bool:
        return self.exists_where(
            CompanySupplierModel.company_id == company_id,
            CompanySupplierModel.organization_identity_id == organization_identity_id,
        )


# --------------------------------------------------------------------------
# Fase B
# --------------------------------------------------------------------------

_PRODUCT_FK = partial(CompanyProductNotFoundError, field="company_product_id")
_SUPPLIER_FK = partial(CompanySupplierNotFoundError, field="company_supplier_id")
_PRESENTATION_FK = partial(PresentationOfOtherProductError, field="company_product_presentation_id")


def _same_presentation(column: Any, presentation_id: UUID | None) -> Any:
    """Igualdad de presentación en la que la ausencia cuenta como un valor (R-03)."""
    return column.is_(None) if presentation_id is None else column == presentation_id


class CompanyProductPresentationRepository(SQLAlchemyRepositoryBase[CompanyProductPresentationModel]):
    """`company_product_presentations` (FR-010 a FR-017)."""

    model = CompanyProductPresentationModel
    search_columns = ("internal_code", "sku", "reference_code")
    order_columns = ("company_product_id", "id")

    duplicates = {
        "uq_company_product_presentations_product_global_presentation": partial(
            DuplicatePresentationAdoptionError, field="global_product_presentation_id"
        ),
        "uq_company_product_presentations_company_id_sku_ci": partial(DuplicateSkuError, field="sku"),
        "uq_company_product_presentations_company_id_internal_code_ci": partial(
            DuplicateInternalCodeError, field="internal_code"
        ),
        "uq_company_product_presentations_default_purchase": VersionConflictError,
        "uq_company_product_presentations_default_sale": VersionConflictError,
        "fk_company_product_presentations_company_product": _PRODUCT_FK,
    }

    def list_by_products(
        self, company_id: UUID, company_product_ids: list[UUID], *, status: str
    ) -> list[CompanyProductPresentationModel]:
        """CR-2 (spec 022, FR-022-81): presentaciones de varios productos de la empresa, en orden estable."""
        model = CompanyProductPresentationModel
        statement = select(model).where(model.company_id == company_id, model.company_product_id.in_(company_product_ids))

        if status != ALL_STATUSES:
            statement = statement.where(model.status == status)

        rows = list(self.session.scalars(statement.order_by(model.company_product_id, model.id)))
        end_read(self.session)
        return rows

    def adoption_exists(self, company_product_id: UUID, global_product_presentation_id: UUID) -> bool:
        return self.exists_where(
            CompanyProductPresentationModel.company_product_id == company_product_id,
            CompanyProductPresentationModel.global_product_presentation_id == global_product_presentation_id,
        )

    def build(self, **fields: Any) -> CompanyProductPresentationModel:
        return CompanyProductPresentationModel(**fields)

    def lock_product(self, company_product_id: UUID) -> None:
        """Bloquea el producto empresarial: ámbito de las predeterminadas (R-04)."""
        self.lock_scope_row(CompanyProductModel, company_product_id)

    def clear_product_marks(
        self, mark: str, company_product_id: UUID, *, exclude_id: UUID | None, actor: str
    ) -> None:
        self.clear_marks(
            mark,
            CompanyProductPresentationModel.company_product_id == company_product_id,
            exclude_id=exclude_id,
            actor=actor,
        )

    def code_in_use(
        self,
        company_id: UUID,
        column: str,
        value: str | None,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        """`sku` o `internal_code` ya usado en la empresa sin distinguir mayúsculas (DS-03)."""
        if value is None:
            return False

        conditions = [
            CompanyProductPresentationModel.company_id == company_id,
            func.lower(getattr(CompanyProductPresentationModel, column)) == code_key(value),
        ]

        if exclude_id is not None:
            conditions.append(CompanyProductPresentationModel.id != exclude_id)

        return self.exists_where(*conditions)


class SupplierProductRepository(SQLAlchemyRepositoryBase[SupplierProductModel]):
    """`supplier_products` (FR-020 a FR-028)."""

    model = SupplierProductModel
    search_columns = ("supplier_product_code",)
    order_columns = ("company_product_id", "company_supplier_id", "id")

    duplicates = {
        "uq_supplier_products_active_relation": DuplicateSupplierProductError,
        "uq_supplier_products_preferred": VersionConflictError,
        "fk_supplier_products_company_supplier": _SUPPLIER_FK,
        "fk_supplier_products_company_product": _PRODUCT_FK,
        "fk_supplier_products_presentation": _PRESENTATION_FK,
    }

    def active_relation_exists(
        self,
        *,
        company_supplier_id: UUID,
        company_product_id: UUID,
        company_product_presentation_id: UUID | None,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Relación `ACTIVE` para proveedor + producto + presentación (aclaración 3)."""
        conditions = [
            SupplierProductModel.company_supplier_id == company_supplier_id,
            SupplierProductModel.company_product_id == company_product_id,
            _same_presentation(
                SupplierProductModel.company_product_presentation_id, company_product_presentation_id
            ),
            SupplierProductModel.status == "ACTIVE",
        ]

        if exclude_id is not None:
            conditions.append(SupplierProductModel.id != exclude_id)

        return self.exists_where(*conditions)

    def build(self, **fields: Any) -> SupplierProductModel:
        return SupplierProductModel(**fields)

    def lock_product(self, company_product_id: UUID) -> None:
        """Bloquea el producto empresarial: ámbito del proveedor preferido (R-04)."""
        self.lock_scope_row(CompanyProductModel, company_product_id)

    def clear_preferred(self, company_product_id: UUID, *, exclude_id: UUID | None, actor: str) -> None:
        self.clear_marks(
            "is_preferred",
            SupplierProductModel.company_product_id == company_product_id,
            exclude_id=exclude_id,
            actor=actor,
        )


class SupplierPaymentConditionRepository(SQLAlchemyRepositoryBase[SupplierPaymentConditionModel]):
    """`supplier_payment_conditions` (FR-030 a FR-038)."""

    model = SupplierPaymentConditionModel
    order_columns = ("company_supplier_id", "currency_code", "valid_from", "id")

    duplicates = {
        "uq_supplier_payment_conditions_default": VersionConflictError,
        "fk_supplier_payment_conditions_company_supplier": _SUPPLIER_FK,
    }

    def build(self, **fields: Any) -> SupplierPaymentConditionModel:
        return SupplierPaymentConditionModel(**fields)

    def lock_supplier(self, company_supplier_id: UUID) -> None:
        """Bloquea el proveedor: ámbito de la condición predeterminada por moneda (R-04)."""
        self.lock_scope_row(CompanySupplierModel, company_supplier_id)

    def clear_default(
        self, company_supplier_id: UUID, currency_code: str, *, exclude_id: UUID | None, actor: str
    ) -> None:
        self.clear_marks(
            "is_default",
            SupplierPaymentConditionModel.company_supplier_id == company_supplier_id,
            SupplierPaymentConditionModel.currency_code == currency_code,
            exclude_id=exclude_id,
            actor=actor,
        )

    def applicable_at(self, at: datetime) -> tuple[Any, ...]:
        """Condiciones aplicables en un instante (filtro `applicable_at`, FR-038)."""
        return (
            SupplierPaymentConditionModel.valid_from <= at,
            or_(
                SupplierPaymentConditionModel.valid_to.is_(None),
                SupplierPaymentConditionModel.valid_to > at,
            ),
        )


class PriceListRepository(SQLAlchemyRepositoryBase[PriceListModel]):
    """`price_lists` (FR-040 a FR-046)."""

    model = PriceListModel
    search_columns = ("code", "name")
    order_columns = ("code", "id")

    duplicates = {
        "uq_price_lists_company_id_code_ci": partial(DuplicatePriceListCodeError, field="code"),
        "uq_price_lists_default": VersionConflictError,
    }

    def list_code_taken(self, company_id: UUID, code: str, *, exclude_id: UUID | None = None) -> bool:
        conditions = [
            PriceListModel.company_id == company_id,
            func.lower(PriceListModel.code) == code_key(code),
        ]

        if exclude_id is not None:
            conditions.append(PriceListModel.id != exclude_id)

        return self.exists_where(*conditions)

    def build(self, **fields: Any) -> PriceListModel:
        return PriceListModel(**fields)

    def lock_default_scope(self, company_id: UUID, currency_code: str) -> None:
        """Bloqueo consultivo del ámbito empresa + moneda, que no tiene fila propia (R-04)."""
        self.lock_advisory(f"price_lists:default:{company_id}:{currency_code}")

    def clear_default(
        self, company_id: UUID, currency_code: str, *, exclude_id: UUID | None, actor: str
    ) -> None:
        self.clear_marks(
            "is_default",
            PriceListModel.company_id == company_id,
            PriceListModel.currency_code == currency_code,
            exclude_id=exclude_id,
            actor=actor,
        )


class PriceListItemRepository(SQLAlchemyRepositoryBase[PriceListItemModel]):
    """`price_list_items` (FR-050 a FR-057) y consultas de resolución (FR-055, R-10)."""

    model = PriceListItemModel
    order_columns = ("price_list_id", "company_product_id", "valid_from", "id")

    duplicates = {
        "ex_price_list_items_no_overlap": PricePeriodOverlapError,
        "fk_price_list_items_price_list": partial(PriceListNotFoundError, field="price_list_id"),
        "fk_price_list_items_company_product": _PRODUCT_FK,
        "fk_price_list_items_presentation": _PRESENTATION_FK,
    }

    def build(self, **fields: Any) -> PriceListItemModel:
        return PriceListItemModel(**fields)

    def applicable_at(self, at: datetime) -> tuple[Any, ...]:
        """Precios vigentes en un instante (filtro `applicable_at`, FR-057)."""
        return (
            PriceListItemModel.valid_from <= at,
            or_(PriceListItemModel.valid_to.is_(None), PriceListItemModel.valid_to > at),
        )

    def save_change(
        self, previous: PriceListItemModel, new: PriceListItemModel, *, audit: dict[str, Any] | None = None,
    ) -> None:
        """Confirma `change-price`: cierre del anterior e inserción del nuevo en una transacción."""
        self.session.flush()
        self.session.add(new)
        if audit is not None:  # feature 016: un evento sobre el ítem nuevo
            audit_events.track_create(self.session, new, **audit)
        self.save(previous, duplicates=self.duplicates)
        self.session.refresh(new)
        end_read(self.session)

    # ------------------------------------------------- resolución de precios

    def resolution_data(
        self,
        company_id: UUID,
        *,
        product_ids: set[UUID],
        presentation_ids: set[UUID],
        list_ids: set[UUID],
        at: datetime,
    ) -> tuple[dict, dict, dict, dict]:
        """Datos de la resolución en a lo sumo 3 consultas (SC-007, R-10).

        Returns:
            Productos y presentaciones de la empresa por UUID; listas implicadas
            (explícitas y predeterminadas por moneda de los productos) por UUID;
            precios `ACTIVE` vigentes en `at` por (lista, producto, presentación).
        """
        rows = self.session.execute(
            select(CompanyProductModel, CompanyProductPresentationModel)
            .outerjoin(
                CompanyProductPresentationModel,
                and_(
                    CompanyProductPresentationModel.company_product_id == CompanyProductModel.id,
                    CompanyProductPresentationModel.id.in_(presentation_ids or [None]),
                ),
            )
            .where(
                CompanyProductModel.company_id == company_id,
                CompanyProductModel.id.in_(product_ids),
            )
        ).all()
        products = {product.id: product for product, _ in rows}
        presentations = {presentation.id: presentation for _, presentation in rows if presentation is not None}

        currencies = {product.currency_code for product in products.values()}
        lists = {
            row.id: row
            for row in self.session.scalars(
                select(PriceListModel).where(
                    PriceListModel.company_id == company_id,
                    or_(
                        PriceListModel.id.in_(list_ids or [None]),
                        and_(
                            PriceListModel.is_default.is_(True),
                            PriceListModel.status == "ACTIVE",
                            PriceListModel.currency_code.in_(currencies or [""]),
                        ),
                    ),
                )
            )
        }

        items: dict[tuple[UUID, UUID, UUID | None], PriceListItemModel] = {}

        if lists and products:
            for item in self.session.scalars(
                select(PriceListItemModel).where(
                    PriceListItemModel.price_list_id.in_(lists),
                    PriceListItemModel.company_product_id.in_(products),
                    PriceListItemModel.status == "ACTIVE",
                    PriceListItemModel.valid_from <= at,
                    or_(PriceListItemModel.valid_to.is_(None), PriceListItemModel.valid_to > at),
                )
            ):
                items[(item.price_list_id, item.company_product_id, item.company_product_presentation_id)] = item

        end_read(self.session)
        return products, presentations, lists, items
