"""Doble de Operational Context para las pruebas (Principio IV: sin servicios reales).

Se inyecta en `create_app(access_directory_factory=...)`; nunca hay modos por
entorno en el código del servicio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import jwt

from audit_service.application.exceptions import (
    DependencyUnavailableError,
    OperationalAccessDeniedError,
)
from audit_service.application.ports import CompanyAccess


def subject_of(authorization: str | None) -> str | None:
    """`sub` del token de la solicitud (sin verificar: lo verificó `sio-auth`)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    claims = jwt.decode(authorization.split(" ", 1)[1], options={"verify_signature": False})
    return claims.get("sub")


@dataclass
class FakeOperationalContext:
    """Membresías por `sub` y empresa, y fallas configurables.

    - `forbidden_subjects`: usuarios a los que Operational Context responde `403`
      (p. ej. sin `perm:operational-context:application_users:read`, FR-037).
    - `unavailable`: simula red caída / `5xx` / tiempo agotado.
    - `fail_if_called`: las rutas de plataforma nunca deben consultarlo.
    """

    members: set[tuple[str, UUID]] = field(default_factory=set)
    forbidden_subjects: set[str] = field(default_factory=set)
    unavailable: bool = False
    fail_if_called: bool = False
    calls: list[tuple[str | None, str | None, UUID]] = field(default_factory=list)

    def add_member(self, sub: str, company_id: UUID) -> None:
        self.members.add((sub, company_id))

    def access_for(self, request) -> FakeCompanyAccessDirectory:
        return FakeCompanyAccessDirectory(self, request.headers.get("authorization"))


class FakeCompanyAccessDirectory:
    def __init__(self, state: FakeOperationalContext, authorization: str | None) -> None:
        self._state = state
        self._authorization = authorization
        self._sub = subject_of(authorization)

    def check_company_access(self, company_id: UUID) -> CompanyAccess:
        if self._state.fail_if_called:
            raise AssertionError("La consulta de plataforma no debe llamar a Operational Context")

        self._state.calls.append((self._sub, self._authorization, company_id))

        if self._state.unavailable:
            raise DependencyUnavailableError(
                "operational-context", operation="operational_access", cause="FAKE_UNAVAILABLE"
            )

        if self._sub in self._state.forbidden_subjects:
            raise OperationalAccessDeniedError("Acceso operativo denegado.")

        return CompanyAccess(member_active=(self._sub, company_id) in self._state.members)
