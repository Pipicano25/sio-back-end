"""Casos de uso de precios de lista (FR-050 a FR-054a, FR-057; R-05, R-06; DS-08, DS-10; H-04).

- "En vigencia" se evalúa con `now()` de la base dentro de la transacción (R-06).
- Un precio en vigencia no se reescribe: solo se cierra, se pospone su fin
  (I2) o se inactiva; para cambiar su valor se usa `change-price`, que cierra el
  vigente y crea el nuevo en una sola transacción (aclaración 1).
- El no solapamiento lo garantiza la restricción de exclusión de la base
  (`PRICE_PERIOD_OVERLAP`, R-05).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from commercial_relationship_service.application.exceptions import (
    InvalidStatusTransitionError,
    VersionConflictError,
    PresentationInactiveError,
    PriceInEffectNotModifiableError,
)
from commercial_relationship_service.application.internal_references import (
    PRESENTATION_FIELD,
    require_active_price_list,
    require_presentation,
    require_product,
)
from commercial_relationship_service.application.mutation import same_value, touch, unchanged
from commercial_relationship_service.domain.currency import validate_amount_scale
from commercial_relationship_service.domain.status import (
    ACTIVE,
    DEACTIVATE,
    REACTIVATE,
    next_status,
)
from commercial_relationship_service.domain.validity import (
    is_in_effect,
    validate_change_effective,
    validate_closing,
    validate_period,
)

EDITABLE_FIELDS = ("unit_price", "valid_from", "valid_to")


def _require_version(current, version: int) -> None:
    """Las reglas de vigencia se validan contra `current`: con otra versión, `409` primero (Principio VII)."""
    if current.version != version:
        raise VersionConflictError


class PriceListItemService:
    """Registro, mantenimiento, cambio de precio y estados de precios de lista."""

    def __init__(self, repository, list_repository, product_repository, presentation_repository) -> None:
        self._repository = repository
        self._lists = list_repository
        self._products = product_repository
        self._presentations = presentation_repository

    # ---------------------------------------------------------------- registro

    def create(self, company_id: UUID, values: dict[str, Any], *, actor: str):
        """FR-050 a FR-053: lista, producto y presentación `ACTIVE`; escala por moneda de la lista."""
        price_list = require_active_price_list(self._lists, values["price_list_id"], company_id)
        product = require_product(self._products, values["company_product_id"], company_id)
        self._check_presentation(company_id, product.id, values[PRESENTATION_FIELD])
        validate_amount_scale(values["unit_price"], price_list.currency_code, field="unit_price")

        if values["valid_from"] is None:
            values = {**values, "valid_from": self._now()}

        validate_period(values["valid_from"], values["valid_to"])

        model = self._repository.build(company_id=company_id, created_by=actor, updated_by=actor, **values)
        return self._repository.add(model, duplicates=self._repository.duplicates)

    # ----------------------------------------------------------- mantenimiento

    def update(self, current, values: dict[str, Any], *, version: int, actor: str):
        """FR-054 (DS-08, I2): precio futuro editable; en vigencia solo `valid_to` futuro.

        Se valida contra `current`; si al bloquear la fila la versión coincide, sus
        datos siguen siendo los validados (Principio VII).
        """
        _require_version(current, version)
        price_list = self._lists.get(current.price_list_id)
        validate_amount_scale(values["unit_price"], price_list.currency_code, field="unit_price")
        now = self._now()

        if is_in_effect(current.valid_from, now):
            if not same_value(current.unit_price, values["unit_price"]) or values["valid_from"] != current.valid_from:
                raise PriceInEffectNotModifiableError(field="unit_price")

            if values["valid_to"] != current.valid_to:
                validate_closing(current.valid_from, values["valid_to"], now)

        else:
            validate_period(values["valid_from"], values["valid_to"])

        model = self._repository.load_for_update(current.id, expected_version=version)

        if unchanged(model, values):
            self._repository.release()
            return model

        for name in EDITABLE_FIELDS:
            setattr(model, name, values[name])

        touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates)

    def change_price(
        self,
        current,
        *,
        unit_price: Decimal,
        effective_from,
        version: int,
        actor: str,
    ):
        """FR-054a: cierra el precio en `effective_from` y crea el nuevo hasta el `valid_to` anterior."""
        _require_version(current, version)

        if current.status != ACTIVE:
            # H-04: cambiar precio sobre un precio inactivo no es una transición válida.
            raise InvalidStatusTransitionError(
                f"La acción change-price no es válida desde el estado {current.status}."
            )

        price_list = require_active_price_list(self._lists, current.price_list_id, current.company_id)
        require_product(self._products, current.company_product_id, current.company_id)
        self._check_presentation_active(current.company_product_presentation_id)
        validate_amount_scale(unit_price, price_list.currency_code, field="unit_price")

        now = self._now()
        effective = effective_from or now
        validate_change_effective(
            effective, now=now, valid_from=current.valid_from, valid_to=current.valid_to
        )

        previous = self._repository.load_for_update(current.id, expected_version=version)
        new = self._repository.build(
            company_id=previous.company_id,
            price_list_id=previous.price_list_id,
            company_product_id=previous.company_product_id,
            company_product_presentation_id=previous.company_product_presentation_id,
            unit_price=unit_price,
            valid_from=effective,
            valid_to=previous.valid_to,
            created_by=actor,
            updated_by=actor,
        )
        previous.valid_to = effective
        touch(previous, actor)
        self._repository.save_change(previous, new)
        return new, previous

    def deactivate(self, current, *, version: int, actor: str):
        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, DEACTIVATE)
        touch(model, actor)
        return self._repository.save(model, duplicates={})

    def reactivate(self, current, *, version: int, actor: str):
        """Revalida lista, producto y presentación `ACTIVE`; el solapamiento lo rechaza la base."""
        next_status(current.status, REACTIVATE)
        require_active_price_list(self._lists, current.price_list_id, current.company_id)
        require_product(self._products, current.company_product_id, current.company_id)
        self._check_presentation_active(current.company_product_presentation_id)

        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, REACTIVATE)
        touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates)

    # -------------------------------------------------------------- internos

    def _check_presentation(self, company_id: UUID, company_product_id: UUID, presentation_id: UUID | None) -> None:
        if presentation_id is not None:
            require_presentation(
                self._presentations,
                presentation_id,
                company_id=company_id,
                company_product_id=company_product_id,
                sellable=True,
            )

    def _check_presentation_active(self, presentation_id: UUID | None) -> None:
        if presentation_id is None:
            return

        presentation = self._presentations.get(presentation_id)

        if presentation is None or presentation.status != ACTIVE:
            raise PresentationInactiveError(field=PRESENTATION_FIELD)

    def _now(self):
        now = self._repository.database_now()
        self._repository.release()
        return now
