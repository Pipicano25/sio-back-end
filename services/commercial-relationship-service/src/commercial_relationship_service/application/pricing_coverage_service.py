"""Cobertura de políticas de precios por presentación (spec 021, FR-021-35; `contracts/commercial-relationship.md` §3b).

Purchase la consulta al confirmar una compra (y al guardar líneas, como advertencia) para no confirmar presentaciones
sin política de ganancia. Solo informa si hay cobertura y en qué listas: **nunca** porcentajes, costos ni políticas
(FR-021-32a). Una presentación de otra empresa responde `found: false` (aislamiento). La identidad técnica con
`platform:lookup` no necesita membresía; un usuario sí (si no es miembro, `404` como cualquier recurso ajeno).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select

from commercial_relationship_service.application.company_scope import CompanyScopeService, RequestIdentity
from commercial_relationship_service.application.exceptions import BatchLimitExceededError

BATCH_LIMIT = 100


@dataclass(frozen=True, slots=True)
class CoverageItem:
    company_product_presentation_id: UUID
    found: bool
    covered: bool
    price_list_ids: list[UUID]


class PricingCoverageService:
    def __init__(self, policy_repository, presentation_repository) -> None:
        self._policies = policy_repository
        self._presentations = presentation_repository

    def coverage(
        self,
        company_id: UUID,
        currency_code: str,
        presentation_ids: list[UUID],
        *,
        identity: RequestIdentity,
        scope: CompanyScopeService,
    ) -> list[CoverageItem]:
        unique = list(dict.fromkeys(presentation_ids))
        if len(unique) > BATCH_LIMIT:
            raise BatchLimitExceededError(field="company_product_presentation_ids")
        if not identity.technical_lookup:
            scope.require_member(company_id, write=False)

        mine = {row.id for row in self._presentations.get_many(unique) if row.company_id == company_id}
        at = self._policies.session.scalar(select(func.now()))
        covering = self._policies.coverage(company_id, currency_code, [value for value in unique if value in mine], at)
        return [
            CoverageItem(
                company_product_presentation_id=value,
                found=value in mine,
                covered=bool(covering.get(value)),
                price_list_ids=covering.get(value, []),
            )
            for value in unique
        ]
