"""Alcance por empresa e identidad técnica (R-02, R-11; FR-040 a FR-045, FR-061).

Punto único donde se decide:

- si la solicitud puede usar la **exención técnica** de lectura: el token cubre
  `perm:commercial-relationship:platform:lookup` (evaluado con `sio-auth`) **y**
  es una identidad técnica reconocida por la correlación de claims
  `client_id` + `preferred_username == "service-account-" + client_id`
  (no basta el prefijo; `sid` no interviene; ser técnica no concede nada sin la
  capacidad);
- si un usuario puede operar sobre una empresa: membresía `ACTIVE` según
  Operational Context, en cada solicitud y sin caché (DS-02). Fuera del alcance
  → `404` igual que un UUID inexistente; empresa `INACTIVE` → solo lecturas e
  inactivación (FR-042).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sio_auth import SioPermission

from commercial_relationship_service.application.exceptions import (
    CompanyInactiveError,
    NotFoundError,
)
from commercial_relationship_service.application.ports import CompanyAccessDirectory

SERVICE = "commercial-relationship"
PLATFORM_LOOKUP = SioPermission(SERVICE, "platform", "lookup")
SERVICE_ACCOUNT_PREFIX = "service-account-"


def grants_allow(grants: Iterable[Any], required: SioPermission) -> bool:
    """Indica si algún grant del token cubre el permiso (API pública de `sio-auth`)."""
    return any(grant.allows(required) for grant in grants)


def is_technical_identity(raw_claims: Mapping[str, Any]) -> bool:
    """Correlación exacta de claims de una cuenta de servicio (R-11).

    Exige `client_id` y `preferred_username` presentes, y que este sea exactamente
    `service-account-{client_id}`. `sid` y `azp` no intervienen.
    """
    client_id = raw_claims.get("client_id")
    username = raw_claims.get("preferred_username")

    if not isinstance(client_id, str) or not client_id:
        return False

    if not isinstance(username, str) or not username:
        return False

    return username == f"{SERVICE_ACCOUNT_PREFIX}{client_id}"


@dataclass(frozen=True, slots=True)
class RequestIdentity:
    """Identidad de la solicitud en curso.

    Attributes:
        subject: `sub` del token (auditoría `created_by`/`updated_by`).
        technical_lookup: Puede leer sin membresía (capacidad + identidad técnica).
    """

    subject: str
    technical_lookup: bool
    technical: bool = False
    """Spec 021 (DS-05): cuenta de servicio (`client_id` + `service-account-{client_id}`), con o sin `lookup`."""

    @classmethod
    def build(
        cls,
        *,
        subject: str,
        grants: Iterable[Any],
        raw_claims: Mapping[str, Any],
    ) -> RequestIdentity:
        return cls(
            subject=subject,
            technical_lookup=grants_allow(grants, PLATFORM_LOOKUP)
            and is_technical_identity(raw_claims),
            technical=is_technical_identity(raw_claims),
        )


class CompanyScopeService:
    """Comprueba la membresía del usuario en una empresa (una llamada por invocación)."""

    def __init__(self, access_directory: CompanyAccessDirectory) -> None:
        self._access = access_directory

    def require_member(
        self,
        company_id: UUID,
        *,
        write: bool,
        allow_inactive_company: bool = False,
    ) -> None:
        """Exige membresía `ACTIVE`; en escrituras, además empresa `ACTIVE` salvo excepción.

        Raises:
            NotFoundError: Sin membresía activa (no se revela la empresa).
            CompanyInactiveError: Escritura no permitida con la empresa inactiva.
            OperationalAccessDeniedError, DependencyUnavailableError: Del adaptador.
        """
        access = self._access.check_company_access(company_id)

        if not access.member_active:
            raise NotFoundError

        if write and not allow_inactive_company and access.company_active is False:
            raise CompanyInactiveError

    def is_member(self, company_id: UUID) -> bool:
        """Membresía `ACTIVE` sin exigir empresa activa (lecturas por lotes, R-12)."""
        return self._access.check_company_access(company_id).member_active
