"""Casos de uso de las políticas de precios de lista (spec 021: FR-021-01..06; RC-021-1, RC-021-2).

- El porcentaje y la pertenencia de presentaciones son historiales inmutables: cambiar el porcentaje cierra el
  término vigente y abre otro; asignar abre una vigencia y retirar la cierra. Así cada recepción puede capturar las
  condiciones vigentes en su `received_at` (RC-021-5).
- Ninguna operación de esta clase modifica precios (RC-021-2): los cambios rigen desde la siguiente recepción.
- Una presentación pertenece a lo sumo a una política de la misma lista en cada instante; lo garantiza la exclusión
  GiST de la base, también ante operaciones concurrentes (RC-021-1).
- `INACTIVE` es final (FR-021-04): inactivar cierra el término y las asignaciones; la política no se reactiva.
- Los instantes se toman de `now()` de la base dentro de la transacción (como los precios, R-06 de la 010).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from commercial_relationship_service.application import audit_events
from commercial_relationship_service.application.exceptions import (
    BatchLimitExceededError,
    NotFoundError,
    PolicyInactiveError,
    PresentationInactiveError,
    PresentationNotFoundError,
    PresentationNotInPolicyError,
    PresentationNotSellableError,
    PriceListInactiveError,
)
from commercial_relationship_service.application.mutation import touch
from commercial_relationship_service.domain.pricing_policy import (
    MAX_PRESENTATIONS_PER_REQUEST,
    unique_in_order,
    validate_markup,
)
from commercial_relationship_service.domain.status import ACTIVE
from commercial_relationship_service.infrastructure.models import (
    PricingPolicyModel,
    PricingPolicyPresentationModel,
    PricingPolicyTermModel,
)

ENTITY = "PricingPolicy"
PRESENTATIONS_FIELD = "company_product_presentation_ids"
INACTIVE = "INACTIVE"
QUANTUM = Decimal("0.0001")


def markup_text(value: Decimal) -> str:
    """Porcentaje con 4 decimales, como lo presentan la API y la auditoría."""
    return format(Decimal(value).quantize(QUANTUM), "f")


class PricingPolicyService:
    """Creación, mantenimiento e inactivación de políticas de precios."""

    def __init__(self, repository, list_repository, presentation_repository) -> None:
        self._repository = repository
        self._lists = list_repository
        self._presentations = presentation_repository

    # ---------------------------------------------------------------- altas

    def create(self, company_id: UUID, price_list_id: UUID, values: dict[str, Any], *, actor: str):
        markup = validate_markup(values["markup_percentage"])
        presentation_ids = self._checked_presentations(company_id, values[PRESENTATIONS_FIELD])
        price_list = self._lists.get(price_list_id)

        if price_list is None or price_list.company_id != company_id:
            raise NotFoundError

        if price_list.status != ACTIVE:
            raise PriceListInactiveError(field="price_list_id")

        now = self._repository.database_now()
        policy = PricingPolicyModel(
            id=uuid4(),
            company_id=company_id,
            price_list_id=price_list_id,
            name=values["name"],
            created_by=actor,
            updated_by=actor,
        )
        rows: list[Any] = [
            PricingPolicyTermModel(id=uuid4(), policy_id=policy.id, markup_percentage=markup, valid_from=now, created_by=actor)
        ]
        rows += [self._assignment(policy, presentation_id, now, actor) for presentation_id in presentation_ids]
        return self._repository.insert(
            policy,
            rows,
            audit=audit_events.spec(
                audit_events.CREATE_PRICING_POLICY,
                ENTITY,
                company_id,
                extra_new={"markup_percentage": markup_text(markup), PRESENTATIONS_FIELD: presentation_ids},
            ),
        )

    # -------------------------------------------------------- modificaciones

    def rename(self, current, *, name: str, version: int, actor: str):
        policy = self._locked(current, version)

        if policy.name == name:
            self._repository.release()
            return policy

        policy.name = name
        touch(policy, actor)
        return self._repository.save_with(
            policy, [], audit=audit_events.spec(audit_events.UPDATE_PRICING_POLICY, ENTITY, policy.company_id)
        )

    def change_percentage(self, current, *, markup_percentage: Any, version: int, actor: str):
        """Cierra el término vigente y abre otro; el nuevo rige desde la siguiente recepción (CP-15)."""
        markup = validate_markup(markup_percentage)
        policy = self._locked(current, version)
        term = self._repository.open_term(policy.id)

        if term.markup_percentage == markup:
            self._repository.release()
            return policy

        now = self._repository.database_now()
        self._repository.close(term, now, actor)
        new_term = PricingPolicyTermModel(
            id=uuid4(), policy_id=policy.id, markup_percentage=markup, valid_from=now, created_by=actor
        )
        touch(policy, actor)
        return self._repository.save_with(
            policy,
            [new_term],
            audit=audit_events.spec(
                audit_events.CHANGE_PRICING_POLICY_PERCENTAGE,
                ENTITY,
                policy.company_id,
                extra_previous={"markup_percentage": markup_text(term.markup_percentage)},
                extra_new={"markup_percentage": markup_text(markup)},
            ),
        )

    def assign(self, current, *, presentation_ids: list[UUID], version: int, actor: str):
        """Incorpora presentaciones; las que ya pertenecen a la política no cambian."""
        presentation_ids = self._checked_presentations(current.company_id, presentation_ids)
        policy = self._locked(current, version)
        assigned = self._repository.open_assignments(policy.id)
        new_ids = [presentation_id for presentation_id in presentation_ids if presentation_id not in assigned]

        if not new_ids:
            self._repository.release()
            return policy

        now = self._repository.database_now()
        rows = [self._assignment(policy, presentation_id, now, actor) for presentation_id in new_ids]
        touch(policy, actor)
        return self._repository.save_with(
            policy,
            rows,
            audit=audit_events.spec(
                audit_events.ASSIGN_PRICING_POLICY_PRESENTATION,
                ENTITY,
                policy.company_id,
                extra_new={"assigned_presentation_ids": new_ids},
            ),
        )

    def remove(self, current, *, presentation_ids: list[UUID], version: int, actor: str):
        """Retira presentaciones; no toca precios: desde la siguiente recepción quedan `SKIPPED_NO_POLICY` (CP-16)."""
        presentation_ids = unique_in_order(presentation_ids)
        _require_batch(presentation_ids)
        policy = self._locked(current, version)
        assigned = self._repository.open_assignments(policy.id)

        if not presentation_ids or any(presentation_id not in assigned for presentation_id in presentation_ids):
            self._repository.abort()
            raise PresentationNotInPolicyError(field=PRESENTATIONS_FIELD)

        now = self._repository.database_now()
        for presentation_id in presentation_ids:
            self._repository.close(assigned[presentation_id], now, actor)
        touch(policy, actor)
        return self._repository.save_with(
            policy,
            [],
            audit=audit_events.spec(
                audit_events.UNASSIGN_PRICING_POLICY_PRESENTATION,
                ENTITY,
                policy.company_id,
                extra_new={"removed_presentation_ids": presentation_ids},
            ),
        )

    def deactivate(self, current, *, reason: str, version: int, actor: str):
        """Estado final: cierra el término y las asignaciones abiertas (FR-021-04)."""
        policy = self._locked(current, version)
        now = self._repository.database_now()
        self._repository.close(self._repository.open_term(policy.id), now, actor)
        removed = []
        for presentation_id, assignment in self._repository.open_assignments(policy.id).items():
            self._repository.close(assignment, now, actor)
            removed.append(presentation_id)
        policy.status = INACTIVE
        policy.deactivated_at = now
        policy.deactivation_reason = reason
        touch(policy, actor)
        return self._repository.save_with(
            policy,
            [],
            audit=audit_events.spec(
                audit_events.DEACTIVATE_PRICING_POLICY,
                ENTITY,
                policy.company_id,
                extra_new={"removed_presentation_ids": removed} if removed else None,
                reason=reason,
            ),
        )

    # -------------------------------------------------------------- internos

    def _locked(self, current, version: int) -> PricingPolicyModel:
        policy = self._repository.load_for_update(current.id, expected_version=version)

        if policy.status != ACTIVE:
            self._repository.abort()
            raise PolicyInactiveError

        return policy

    def _checked_presentations(self, company_id: UUID, presentation_ids: list[UUID]) -> list[UUID]:
        """Presentaciones de la empresa, `ACTIVE` y vendibles: sus precios los fijará la política."""
        presentation_ids = unique_in_order(presentation_ids)
        _require_batch(presentation_ids)
        found = {row.id: row for row in self._presentations.get_many(presentation_ids)} if presentation_ids else {}

        for presentation_id in presentation_ids:
            presentation = found.get(presentation_id)
            if presentation is None or presentation.company_id != company_id:
                raise PresentationNotFoundError(field=PRESENTATIONS_FIELD)
            if presentation.status != ACTIVE:
                raise PresentationInactiveError(field=PRESENTATIONS_FIELD)
            if not presentation.is_sellable:
                raise PresentationNotSellableError(field=PRESENTATIONS_FIELD)

        return presentation_ids

    @staticmethod
    def _assignment(policy: PricingPolicyModel, presentation_id: UUID, now, actor: str) -> PricingPolicyPresentationModel:
        return PricingPolicyPresentationModel(
            id=uuid4(),
            company_id=policy.company_id,
            policy_id=policy.id,
            price_list_id=policy.price_list_id,
            company_product_presentation_id=presentation_id,
            valid_from=now,
            created_by=actor,
        )


def _require_batch(presentation_ids: list[UUID]) -> None:
    if len(presentation_ids) > MAX_PRESENTATIONS_PER_REQUEST:
        raise BatchLimitExceededError(
            f"Se admiten como máximo {MAX_PRESENTATIONS_PER_REQUEST} presentaciones por solicitud.",
            field=PRESENTATIONS_FIELD,
        )
