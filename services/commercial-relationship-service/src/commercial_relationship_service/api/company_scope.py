"""Dependencias de alcance por empresa (R-02, R-03, R-11).

Se declaran como parámetros `Depends` de cada ruta, después de la dependencia de
permiso (`dependencies=[...]`). FastAPI las resuelve antes de validar el cuerpo,
así un usuario sin membresía recibe `404` aunque el cuerpo sea inválido
(FR-011 paso 2, FR-041).

Reglas:

- `company_scope(...)`: empresa de la ruta; colecciones y altas.
- `scoped_resource(...)`: recurso por UUID; si no existe → `404` sin llamar a
  Operational Context; si existe, alcance por su `company_id`.
- `lookup=True` (lecturas por UUID): la exención técnica (identidad técnica +
  `platform:lookup`) omite Operational Context. Nunca se aplica a escrituras.
- `write=True` exige empresa `ACTIVE` salvo `allow_inactive_company=True`
  (inactivar, FR-042).
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends

from commercial_relationship_service.api.dependencies import get_identity, get_scope_service
from commercial_relationship_service.application.company_scope import (
    CompanyScopeService,
    RequestIdentity,
)
from commercial_relationship_service.application.exceptions import NotFoundError


def check_company(
    company_id: UUID,
    *,
    identity: RequestIdentity,
    scope: CompanyScopeService,
    write: bool,
    allow_inactive_company: bool = False,
    lookup: bool = False,
) -> None:
    """Aplica el alcance a una empresa ya conocida."""
    if lookup and not write and identity.technical_lookup:
        return

    scope.require_member(company_id, write=write, allow_inactive_company=allow_inactive_company)


def company_dependency(*, write: bool, lookup: bool = False):
    """Dependencia `company_id` de la ruta con el alcance aplicado (rutas de la Fase B)."""

    def dependency(
        company_id: UUID,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
    ) -> UUID:
        check_company(company_id, identity=identity, scope=scope, write=write, lookup=lookup)
        return company_id

    return dependency


def load_scoped(
    loader: Callable[[UUID], object | None],
    entity_id: UUID,
    *,
    identity: RequestIdentity,
    scope: CompanyScopeService,
    write: bool,
    allow_inactive_company: bool = False,
    lookup: bool = False,
):
    """Carga el recurso y aplica el alcance de su empresa; `404` si no existe o es ajeno."""
    model = loader(entity_id)

    if model is None:
        raise NotFoundError

    check_company(
        model.company_id,
        identity=identity,
        scope=scope,
        write=write,
        allow_inactive_company=allow_inactive_company,
        lookup=lookup,
    )
    return model
