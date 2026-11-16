"""Party Identity leído de su vista de contrato (spec 025, T053; D27).

Mismo puerto que `HTTPPartyDirectory`: `v1_organization_identities` reemplaza a `GET /organization-identities/{id}`.
Sin fila → `None` (el `404`); identificación vacía → campos `None`, igual que hoy.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Engine

from purchase_service.application.exceptions import PARTY_IDENTITY
from purchase_service.application.ports import OrganizationInfo
from purchase_service.infrastructure.contract_support import ContractReader

_ORGANIZATION = (
    "SELECT identification_type, identification_number FROM contract.v1_organization_identities WHERE id = :id"
)


def _text(value: Any) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return str(value)


class ContractPartyDirectory:
    def __init__(self, *, engine: Engine) -> None:
        self._reader = ContractReader(engine, PARTY_IDENTITY)

    def get_organization(self, organization_id: UUID) -> OrganizationInfo | None:
        row = self._reader.one("organization_identity", _ORGANIZATION, {"id": organization_id})
        if row is None:
            return None
        return OrganizationInfo(
            id=organization_id,
            identification_type=_text(row.get("identification_type")),
            identification_number=_text(row.get("identification_number")),
        )
