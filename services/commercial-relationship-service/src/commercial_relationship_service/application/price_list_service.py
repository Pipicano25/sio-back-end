"""Casos de uso de listas de precios (FR-040 a FR-046; R-04; DS-09).

La moneda de la lista es inmutable (la capa API la rechaza en el `PUT`). La
lista predeterminada es única por empresa y moneda entre las `ACTIVE`; como ese
ámbito no tiene fila propia, se serializa con un bloqueo consultivo (R-04).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from commercial_relationship_service.application import audit_events
from commercial_relationship_service.application.exceptions import DuplicatePriceListCodeError
from commercial_relationship_service.application.mutation import touch, unchanged
from commercial_relationship_service.domain.currency import validate_currency
from commercial_relationship_service.domain.rules import code_key, require_active_for_mark
from commercial_relationship_service.domain.status import DEACTIVATE, REACTIVATE, next_status
from commercial_relationship_service.domain.validity import validate_period

EDITABLE_FIELDS = ("code", "name", "description", "valid_from", "valid_to", "is_default")


class PriceListService:
    """Creación, mantenimiento y estados de listas de precios."""

    def __init__(self, repository) -> None:
        self._repository = repository

    def create(self, company_id: UUID, values: dict[str, Any], *, actor: str):
        values = {**values, "currency_code": validate_currency(values["currency_code"])}
        validate_period(values["valid_from"], values["valid_to"])

        if self._repository.list_code_taken(company_id, values["code"]):
            raise DuplicatePriceListCodeError(field="code")

        model = self._repository.build(company_id=company_id, created_by=actor, updated_by=actor, **values)

        if values["is_default"]:
            self._repository.lock_default_scope(company_id, values["currency_code"])
            self._repository.clear_default(company_id, values["currency_code"], exclude_id=None, actor=actor)

        return self._repository.add(model, duplicates=self._repository.duplicates, audit=audit_events.spec(audit_events.CREATE_PRICE_LIST, "PriceList", model.company_id))

    def update(self, current, values: dict[str, Any], *, version: int, actor: str):
        """`PUT` en cualquier estado sin cambiar `status` ni la moneda (FR-044, DS-09)."""
        validate_period(values["valid_from"], values["valid_to"])
        require_active_for_mark(current.status, marked=values["is_default"], field="is_default")

        if code_key(values["code"]) != code_key(current.code) and self._repository.list_code_taken(
            current.company_id, values["code"], exclude_id=current.id
        ):
            raise DuplicatePriceListCodeError(field="code")

        self._repository.lock_default_scope(current.company_id, current.currency_code)
        model = self._repository.load_for_update(current.id, expected_version=version)

        if unchanged(model, values):
            self._repository.release()
            return model

        if values["is_default"] and not model.is_default:
            self._repository.clear_default(
                model.company_id, model.currency_code, exclude_id=model.id, actor=actor
            )

        for name in EDITABLE_FIELDS:
            setattr(model, name, values[name])

        touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates, audit=audit_events.spec(audit_events.UPDATE_PRICE_LIST, "PriceList", model.company_id))

    def deactivate(self, current, *, version: int, actor: str):
        """Inactivar retira `is_default` y no modifica sus precios (FR-045)."""
        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, DEACTIVATE)
        model.is_default = False
        touch(model, actor)
        return self._repository.save(model, duplicates={}, audit=audit_events.spec(audit_events.DEACTIVATE_PRICE_LIST, "PriceList", model.company_id))

    def reactivate(self, current, *, version: int, actor: str):
        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, REACTIVATE)
        touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates, audit=audit_events.spec(audit_events.REACTIVATE_PRICE_LIST, "PriceList", model.company_id))
