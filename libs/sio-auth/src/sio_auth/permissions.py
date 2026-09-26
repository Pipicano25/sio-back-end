"""Interpretación dinámica y evaluación de wildcards para permisos provenientes de Keycloak."""

from __future__ import annotations

from collections.abc import Iterable

from .models import SioGrant, SioPermission

PERMISSION_PREFIX = "perm:"


def parse_permission_grant(role: str) -> SioGrant | None:
    """Interpreta un client role de Keycloak cuando cumple el formato de SIO.

    Los roles que no utilizan el espacio de nombres ``perm:`` permanecen como
    roles normales de Keycloak y se ignoran al evaluar permisos. Los permisos
    mal formados también se ignoran para evitar que concedan acceso por error.
    """

    if not isinstance(role, str) or not role.startswith(PERMISSION_PREFIX):
        return None

    parts = role.split(":")
    if len(parts) != 4 or parts[0] != "perm":
        return None

    try:
        return SioGrant(
            service=parts[1],
            resource=parts[2],
            action=parts[3],
        )
    except ValueError:
        return None


def extract_permission_grants(roles: Iterable[str]) -> frozenset[SioGrant]:
    """Extrae dinámicamente los grants de permisos desde los client roles de Keycloak."""

    return frozenset(
        grant
        for role in roles
        if (grant := parse_permission_grant(role)) is not None
    )


def has_permission(
    grants: Iterable[SioGrant],
    required: SioPermission,
) -> bool:
    """Indica si algún grant de Keycloak cubre el permiso exigido por el endpoint."""

    return any(grant.allows(required) for grant in grants)


def evaluate_permission(
    roles: Iterable[str],
    required: SioPermission,
) -> bool:
    """Evalúa si un conjunto de client roles de Keycloak concede un permiso.

    Función pura de la API pública (versión 0.3.0). Aplica exactamente el mismo
    algoritmo que ``auth.permission``: interpreta los roles ``perm:...`` (los
    roles sin ese prefijo o mal formados se ignoran) y compara los grants,
    incluidos los wildcards ``all``, con el permiso concreto exigido.

    Está pensada para evaluar roles efectivos obtenidos por otra vía (por
    ejemplo, leídos de Keycloak para un usuario distinto del que hace la
    solicitud). No consulta Keycloak ni produce efectos.
    """

    return has_permission(extract_permission_grants(roles), required)
