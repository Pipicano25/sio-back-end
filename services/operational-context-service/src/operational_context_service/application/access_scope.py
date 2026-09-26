"""Alcance del usuario por solicitud: plataforma o empresas con membresía (R-01, R-02).

Punto único donde se aplica el aislamiento por empresa (DS-06, FR-040 a FR-045):

- `is_platform_admin`: el token cubre `perm:operational-context:platform:administer`
  (ve y administra todas las empresas sin ser miembro, DS-05);
- `can_lookup`: cubre `perm:operational-context:platform:lookup` (consultas por
  UUID de solo lectura sin membresía, para identidades técnicas);
- `member_company_ids`: empresas con membresía `ACTIVE` del `sub`, leídas en
  cada solicitud (FR-044).

Los permisos de capacidad se evalúan con los grants que ya trae el token
(`TokenClaims.permissions`) y su método público `allows`: no se reinterpreta
ningún permiso (Principio V). Las acciones `administer` y `lookup` no las
conceden los comodines de lectura, creación, modificación ni eliminación; sí
los permisos con acción `all` que cubran el servicio (hoy solo
`perm:all:all:all`).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sio_auth import SioPermission

from operational_context_service.application.exceptions import NotFoundError

SERVICE = "operational-context"
PLATFORM_ADMINISTER = SioPermission(SERVICE, "platform", "administer")
PLATFORM_LOOKUP = SioPermission(SERVICE, "platform", "lookup")


def grants_allow(grants: Iterable[Any], required: SioPermission) -> bool:
    """Indica si algún grant del token cubre el permiso (API pública de los grants)."""
    return any(grant.allows(required) for grant in grants)


@dataclass(frozen=True, slots=True)
class AccessScope:
    """Alcance inmutable de la solicitud actual."""

    subject: str
    is_platform_admin: bool
    can_lookup: bool
    member_company_ids: frozenset[UUID]
    grants: frozenset[Any] = frozenset()

    @classmethod
    def build(
        cls,
        *,
        subject: str,
        grants: Iterable[Any],
        member_company_ids: Iterable[UUID],
    ) -> AccessScope:
        grants = frozenset(grants)

        return cls(
            subject=subject,
            is_platform_admin=grants_allow(grants, PLATFORM_ADMINISTER),
            can_lookup=grants_allow(grants, PLATFORM_LOOKUP),
            member_company_ids=frozenset(member_company_ids),
            grants=grants,
        )

    def has_permission(self, required: SioPermission) -> bool:
        """Permiso del propio token (vía propia del acceso operativo)."""
        return grants_allow(self.grants, required)

    def is_company_visible(self, company_id: UUID, *, lookup_read: bool = False) -> bool:
        """Plataforma, membresía `ACTIVE` o, solo en lecturas por UUID, lookup."""
        if self.is_platform_admin or company_id in self.member_company_ids:
            return True

        return lookup_read and self.can_lookup

    def ensure_company_visible(
        self,
        company_id: UUID,
        *,
        lookup_read: bool = False,
        not_found_message: str = "La empresa solicitada no existe.",
    ) -> None:
        """Lanza la misma `NotFoundError` que un UUID inexistente (DS-06).

        Raises:
            NotFoundError: Si la empresa está fuera del alcance.
        """
        if not self.is_company_visible(company_id, lookup_read=lookup_read):
            raise NotFoundError(not_found_message)

    def company_filter(self) -> frozenset[UUID] | None:
        """`None` (sin filtro) para plataforma; si no, las empresas con membresía `ACTIVE`."""
        return None if self.is_platform_admin else self.member_company_ids
