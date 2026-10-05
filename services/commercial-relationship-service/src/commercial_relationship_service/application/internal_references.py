"""Validación de referencias internas del cuerpo (FR-011 paso 4, FR-021, FR-031, FR-051, FR-061).

Una referencia de otra empresa se responde igual que una inexistente (`422
*_NOT_FOUND`, mismo `code`), sin revelar que existe (FR-061, H-01). Las FK
compuestas de la base (R-02) son la red de seguridad de estas comprobaciones.
"""

from __future__ import annotations

from uuid import UUID

from commercial_relationship_service.application.exceptions import (
    CompanyProductInactiveError,
    CompanyProductNotFoundError,
    CompanySupplierBlockedError,
    CompanySupplierInactiveError,
    CompanySupplierNotFoundError,
    PresentationInactiveError,
    PresentationNotFoundError,
    PresentationNotPurchasableError,
    PresentationNotSellableError,
    PresentationOfOtherProductError,
    PriceListInactiveError,
    PriceListNotFoundError,
)
from commercial_relationship_service.domain.status import ACTIVE, BLOCKED

PRESENTATION_FIELD = "company_product_presentation_id"


def _owned(repository, entity_id: UUID, company_id: UUID):
    model = repository.get(entity_id)
    return model if model is not None and model.company_id == company_id else None


def require_product(repository, company_product_id: UUID, company_id: UUID, *, active: bool = True):
    """Producto empresarial de la empresa y, si se exige, `ACTIVE`."""
    product = _owned(repository, company_product_id, company_id)

    if product is None:
        raise CompanyProductNotFoundError(field="company_product_id")

    if active and product.status != ACTIVE:
        raise CompanyProductInactiveError(field="company_product_id")

    return product


def require_active_supplier(repository, company_supplier_id: UUID, company_id: UUID):
    """Proveedor de la empresa `ACTIVE`: FR-021 y FR-031 sin cambios, con causas separadas (I1)."""
    supplier = _owned(repository, company_supplier_id, company_id)

    if supplier is None:
        raise CompanySupplierNotFoundError(field="company_supplier_id")

    if supplier.status == BLOCKED:
        raise CompanySupplierBlockedError(field="company_supplier_id")

    if supplier.status != ACTIVE:
        raise CompanySupplierInactiveError(field="company_supplier_id")

    return supplier


def require_presentation(
    repository,
    presentation_id: UUID,
    *,
    company_id: UUID,
    company_product_id: UUID,
    purchasable: bool = False,
    sellable: bool = False,
):
    """Presentación empresarial de la empresa, del mismo producto, `ACTIVE` y apta."""
    presentation = _owned(repository, presentation_id, company_id)

    if presentation is None:
        raise PresentationNotFoundError(field=PRESENTATION_FIELD)

    if presentation.company_product_id != company_product_id:
        raise PresentationOfOtherProductError(field=PRESENTATION_FIELD)

    if presentation.status != ACTIVE:
        raise PresentationInactiveError(field=PRESENTATION_FIELD)

    if purchasable and not presentation.is_purchasable:
        raise PresentationNotPurchasableError(field=PRESENTATION_FIELD)

    if sellable and not presentation.is_sellable:
        raise PresentationNotSellableError(field=PRESENTATION_FIELD)

    return presentation


def require_active_price_list(repository, price_list_id: UUID, company_id: UUID):
    """Lista de precios de la empresa y `ACTIVE` (FR-045, FR-051)."""
    price_list = _owned(repository, price_list_id, company_id)

    if price_list is None:
        raise PriceListNotFoundError(field="price_list_id")

    if price_list.status != ACTIVE:
        raise PriceListInactiveError(field="price_list_id")

    return price_list
