"""Tasa de impuesto de compra del producto de la empresa (spec 021: FR-021-07, FR-021-08; M-3, M-5).

- Se configura con un permiso propio (`company_product_purchase_taxes:update`), separado del `PUT` del producto.
- `None` es "sin configurar"; 0 es una tasa válida; una tasa configurada no vuelve a "sin configurar".
- No afecta el producto global ni a otras empresas, y no cambia compras ya confirmadas: Purchase congela la tasa en
  cada línea al confirmar.
- El lote (hasta 100) es todo o nada: valida todo, bloquea en orden de `id` y confirma en una transacción.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from commercial_relationship_service.application import audit_events
from commercial_relationship_service.application.exceptions import (
    BatchLimitExceededError,
    CompanyProductNotFoundError,
    VersionConflictError,
)
from commercial_relationship_service.application.mutation import touch
from commercial_relationship_service.domain.purchase_tax import validate_purchase_tax

MAX_ITEMS = 100
ENTITY = "CompanyProduct"


class CompanyProductTaxService:
    """Configura la tasa de impuesto de compra predeterminada de los productos de la empresa."""

    def __init__(self, repository) -> None:
        self._repository = repository

    def set_one(self, current, *, value: Any, version: int, actor: str):
        tax = validate_purchase_tax(value)
        model = self._repository.load_for_update(current.id, expected_version=version)

        if model.purchase_tax_percentage is not None and model.purchase_tax_percentage == tax:
            self._repository.release()
            return model

        model.purchase_tax_percentage = tax
        touch(model, actor)
        return self._repository.save(
            model,
            duplicates={},
            audit=audit_events.spec(audit_events.UPDATE_COMPANY_PRODUCT_PURCHASE_TAX, ENTITY, model.company_id),
        )

    def set_batch(self, company_id: UUID, items: list[dict[str, Any]], *, actor: str):
        if len(items) > MAX_ITEMS:
            raise BatchLimitExceededError(f"El lote admite como máximo {MAX_ITEMS} productos.", field="items")

        taxes = [
            validate_purchase_tax(item["purchase_tax_percentage"], field=f"items[{index}].purchase_tax_percentage")
            for index, item in enumerate(items)
        ]
        ids = [item["company_product_id"] for item in items]
        models = self._repository.lock_many(ids)

        for index, item in enumerate(items):
            model = models.get(item["company_product_id"])
            if model is None or model.company_id != company_id:
                self._repository.abort()
                raise CompanyProductNotFoundError(field=f"items[{index}].company_product_id")
            if model.version != item["version"]:
                self._repository.abort()
                raise VersionConflictError

        changed = []
        for item, tax in zip(items, taxes, strict=True):
            model = models[item["company_product_id"]]
            if model.purchase_tax_percentage is not None and model.purchase_tax_percentage == tax:
                continue
            model.purchase_tax_percentage = tax
            touch(model, actor)
            changed.append(model)

        self._repository.save_all(
            changed,
            audit=audit_events.spec(audit_events.UPDATE_COMPANY_PRODUCT_PURCHASE_TAX, ENTITY, company_id),
        )
        return [models[item["company_product_id"]] for item in items]
