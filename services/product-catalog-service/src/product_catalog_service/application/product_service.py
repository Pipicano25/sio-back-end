"""Servicio de productos globales (FR-025 a FR-031, FR-027a, DS-03, DS-04, DS-06)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.application import audit_events as audit
from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    BaseUnitLockedByFirstUseError,
    DependencyUnavailableError,
    ManufacturerAccessDeniedError,
    ManufacturerDirectoryAccessDeniedError,
    ManufacturerDirectoryUnavailableError,
    ManufacturerNotFoundError,
    NotFoundError,
    ProductInactiveError,
    ReferenceInactiveError,
    ReferenceNotFoundError,
)
from product_catalog_service.application.normalization import (
    canonical_name_key,
    normalize_name,
    normalize_optional_text,
)
from product_catalog_service.application.pagination import PageResult, paginate
from product_catalog_service.application.ports import ManufacturerDirectory
from product_catalog_service.infrastructure.locks import lock_product
from product_catalog_service.infrastructure.models import (
    GlobalBrandModel,
    GlobalProductModel,
    GlobalUnitOfMeasureModel,
)
from product_catalog_service.infrastructure.query_helpers import apply_common_filters

ACTIVE = lifecycle.ACTIVE


@dataclass(frozen=True, slots=True)
class DuplicateWarning:
    """Advertencia no bloqueante de posible duplicado (FR-029)."""

    matching_product_ids: tuple[UUID, ...]
    code: str = "POSSIBLE_DUPLICATE"
    message: str = "Existe otro producto con el mismo nombre normalizado y la misma marca."


@dataclass(frozen=True, slots=True)
class ProductWriteResult:
    product: GlobalProductModel
    warnings: tuple[DuplicateWarning, ...]


def ensure_product_active_for_dependents(product: GlobalProductModel) -> None:
    """Sobre un producto `INACTIVE` solo se consultan e inactivan dependientes (FR-031)."""
    if product.status != ACTIVE:
        raise ProductInactiveError(
            "El producto está inactivo: sus elementos solo pueden consultarse o inactivarse."
        )


class ProductService:
    """Casos de uso del producto global."""

    def __init__(self, session: Session, manufacturers: ManufacturerDirectory | None = None) -> None:
        self.session = session
        self.manufacturers = manufacturers

    # ------------------------------------------------------------------ lectura

    def get(self, product_id: UUID) -> GlobalProductModel:
        product = self.session.get(GlobalProductModel, product_id)
        if product is None:
            raise NotFoundError(f"El producto {product_id} no existe.")
        return product

    def list(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        search: str | None = None,
        extra_filters=None,
    ) -> PageResult:
        statement = apply_common_filters(
            select(GlobalProductModel),
            GlobalProductModel,
            status=status,
            search=search,
            search_column=GlobalProductModel.canonical_name_key,
        )
        if extra_filters is not None:
            statement = extra_filters(statement)
        statement = statement.order_by(GlobalProductModel.canonical_name_key, GlobalProductModel.id)
        return paginate(self.session, statement, page=page, page_size=page_size)

    # ---------------------------------------------------------------- escritura

    def create(
        self,
        *,
        product_type: str,
        canonical_name: str,
        description: str | None,
        global_brand_id: UUID | None,
        manufacturer_organization_id: UUID | None,
        base_unit_id: UUID,
        actor: str,
    ) -> ProductWriteResult:
        name = normalize_name(canonical_name, max_length=200, field="canonical_name")
        self._require_active(GlobalBrandModel, global_brand_id, "La marca")
        self._require_active(GlobalUnitOfMeasureModel, base_unit_id, "La unidad base")
        if manufacturer_organization_id is not None:
            self._validate_manufacturer(manufacturer_organization_id)

        product = GlobalProductModel(
            product_type=product_type,
            canonical_name=name,
            canonical_name_key=canonical_name_key(name),
            description=normalize_optional_text(description),
            global_brand_id=global_brand_id,
            manufacturer_organization_id=manufacturer_organization_id,
            base_unit_id=base_unit_id,
            status=ACTIVE,
        )
        lifecycle.stamp_create(product, actor)
        self.session.add(product)
        self.session.flush()

        audit.track_create(self.session, product, action=audit.CREATE_PRODUCT, entity_type="Product")
        warnings = self._duplicate_warnings(product)
        self.session.commit()
        return ProductWriteResult(product, warnings)

    def update(
        self,
        product_id: UUID,
        *,
        version: int,
        canonical_name: str,
        description: str | None,
        global_brand_id: UUID | None,
        manufacturer_organization_id: UUID | None,
        base_unit_id: UUID,
        actor: str,
    ) -> ProductWriteResult:
        product = lock_product(self.session, product_id)
        lifecycle.check_version(product, version)

        name = normalize_name(canonical_name, max_length=200, field="canonical_name")

        if global_brand_id != product.global_brand_id:
            self._require_active(GlobalBrandModel, global_brand_id, "La marca")

        if base_unit_id != product.base_unit_id:
            if product.first_used_at is not None:
                raise BaseUnitLockedByFirstUseError(
                    "El producto tiene uso histórico: su unidad base no puede cambiarse "
                    "mediante una actualización ordinaria."
                )
            self._require_active(GlobalUnitOfMeasureModel, base_unit_id, "La unidad base")

        if (
            manufacturer_organization_id is not None
            and manufacturer_organization_id != product.manufacturer_organization_id
        ):
            self._validate_manufacturer(manufacturer_organization_id)

        name_or_brand_changed = (
            canonical_name_key(name) != product.canonical_name_key
            or global_brand_id != product.global_brand_id
        )

        product.canonical_name = name
        product.canonical_name_key = canonical_name_key(name)
        product.description = normalize_optional_text(description)
        product.global_brand_id = global_brand_id
        product.manufacturer_organization_id = manufacturer_organization_id
        product.base_unit_id = base_unit_id
        lifecycle.stamp_update(product, actor)
        audit.track_update(self.session, product, action=audit.UPDATE_PRODUCT, entity_type="Product")
        self.session.flush()

        warnings = self._duplicate_warnings(product) if name_or_brand_changed else ()
        self.session.commit()
        return ProductWriteResult(product, warnings)

    def deactivate(self, product_id: UUID, *, version: int, actor: str) -> GlobalProductModel:
        """Sin cascada sobre relaciones, presentaciones, identificadores ni activos (FR-030)."""
        product = lock_product(self.session, product_id)
        lifecycle.deactivate(product, version, actor)
        audit.track_update(self.session, product, action=audit.DEACTIVATE_PRODUCT, entity_type="Product")
        self.session.commit()
        return product

    def reactivate(self, product_id: UUID, *, version: int, actor: str) -> GlobalProductModel:
        """No revalida marca ni unidad base ya asignadas (FR-006, respuesta 5A)."""
        product = lock_product(self.session, product_id)
        lifecycle.reactivate(product, version, actor)
        audit.track_update(self.session, product, action=audit.REACTIVATE_PRODUCT, entity_type="Product")
        self.session.commit()
        return product

    # ---------------------------------------------------------------- utilidades

    def _require_active(self, model, entity_id: UUID | None, label: str) -> None:
        if entity_id is None:
            return

        status = self.session.execute(
            select(model.status).where(model.id == entity_id)
        ).scalar_one_or_none()

        if status is None:
            raise ReferenceNotFoundError(f"{label} {entity_id} no existe.")
        if status != ACTIVE:
            raise ReferenceInactiveError(f"{label} está inactiva y no puede asignarse.")

    def _validate_manufacturer(self, organization_id: UUID) -> None:
        if self.manufacturers is None:
            raise DependencyUnavailableError("No hay un directorio de fabricantes configurado.")

        try:
            exists = self.manufacturers.exists(organization_id)
        except ManufacturerDirectoryAccessDeniedError:
            raise ManufacturerAccessDeniedError(
                "No tiene permiso para consultar organizaciones en Party Identity Service."
            ) from None
        except ManufacturerDirectoryUnavailableError:
            raise DependencyUnavailableError(
                "Party Identity Service no está disponible; intente asignar el fabricante más tarde."
            ) from None

        if not exists:
            raise ManufacturerNotFoundError(
                f"La organización fabricante {organization_id} no existe en Party Identity Service."
            )

    def _duplicate_warnings(self, product: GlobalProductModel) -> tuple[DuplicateWarning, ...]:
        brand_condition = (
            GlobalProductModel.global_brand_id.is_(None)
            if product.global_brand_id is None
            else GlobalProductModel.global_brand_id == product.global_brand_id
        )
        matches = tuple(
            self.session.execute(
                select(GlobalProductModel.id)
                .where(
                    GlobalProductModel.canonical_name_key == product.canonical_name_key,
                    brand_condition,
                    GlobalProductModel.id != product.id,
                )
                .order_by(GlobalProductModel.created_at)
                .limit(20)
            ).scalars()
        )
        return (DuplicateWarning(matching_product_ids=matches),) if matches else ()
