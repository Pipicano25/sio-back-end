"""Reglas puras del acceso operativo efectivo (DS-07, DS-08, C-14, R-10).

El acceso se calcula en cada consulta y nunca se persiste. La causa de una
denegación es la **primera** condición que falla en un orden fijo; las
siguientes no se evalúan (en particular el permiso, que en la vía técnica exige
consultar Keycloak). Contrato: `contracts/operational-access-provider.md`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

ACTIVE = "ACTIVE"


class AccessDenialReason(StrEnum):
    """Catálogo cerrado de causas de denegación (añadir una exige el Principio XVI)."""

    USER_NOT_MEMBER = "USER_NOT_MEMBER"
    USER_MEMBERSHIP_INACTIVE = "USER_MEMBERSHIP_INACTIVE"
    COMPANY_INACTIVE = "COMPANY_INACTIVE"
    BRANCH_INACTIVE = "BRANCH_INACTIVE"
    BRANCH_NOT_ASSIGNED = "BRANCH_NOT_ASSIGNED"
    USER_BRANCH_INACTIVE = "USER_BRANCH_INACTIVE"
    PERMISSION_DENIED = "PERMISSION_DENIED"


@dataclass(frozen=True, slots=True)
class AccessFacts:
    """Hechos ya cargados para evaluar el acceso de un usuario.

    Attributes:
        company_status: Estado de la empresa, o `None` si no existe.
        branch_requested: Si la consulta es sobre una sucursal.
        branch_status: Estado de la sucursal, o `None` si no existe o no aplica.
        membership_status: Estado de la membresía del usuario en la empresa
            (la `ACTIVE`, o la inactiva más reciente), o `None` si no tiene.
        user_branch_status: Estado de la asignación a la sucursal, o `None`.
        permission_granted: Evaluación diferida del permiso; `None` si el
            consumidor no indicó permiso. Solo se invoca si todo lo anterior se
            cumple.
    """

    company_status: str | None
    branch_requested: bool
    branch_status: str | None
    membership_status: str | None
    user_branch_status: str | None
    permission_granted: Callable[[], bool] | None = None


def _membership(facts: AccessFacts) -> AccessDenialReason | None:
    if facts.membership_status is None:
        return AccessDenialReason.USER_NOT_MEMBER

    if facts.membership_status != ACTIVE:
        return AccessDenialReason.USER_MEMBERSHIP_INACTIVE

    return None


def _company(facts: AccessFacts) -> AccessDenialReason | None:
    if facts.company_status != ACTIVE:
        return AccessDenialReason.COMPANY_INACTIVE

    return None


def _branch(facts: AccessFacts) -> AccessDenialReason | None:
    if facts.branch_requested and facts.branch_status != ACTIVE:
        return AccessDenialReason.BRANCH_INACTIVE

    return None


def _assignment_and_permission(facts: AccessFacts) -> AccessDenialReason | None:
    if facts.branch_requested:
        if facts.user_branch_status is None:
            return AccessDenialReason.BRANCH_NOT_ASSIGNED

        if facts.user_branch_status != ACTIVE:
            return AccessDenialReason.USER_BRANCH_INACTIVE

    if facts.permission_granted is not None and not facts.permission_granted():
        return AccessDenialReason.PERMISSION_DENIED

    return None


def evaluate_own_access(facts: AccessFacts) -> AccessDenialReason | None:
    """Vía propia (token del usuario evaluado), C-14.

    Orden: membresía existente → membresía `ACTIVE` → empresa → sucursal →
    asignación → asignación `ACTIVE` → permiso. Una empresa o sucursal
    inexistente llega sin membresía y produce `USER_NOT_MEMBER`, igual que una
    ajena: esta vía no distingue ambos casos ni revela su estado.

    Returns:
        `None` si el acceso está permitido; si no, la primera causa que falla.
    """
    if facts.company_status is None or (facts.branch_requested and facts.branch_status is None):
        return AccessDenialReason.USER_NOT_MEMBER

    for rule in (_membership, _company, _branch, _assignment_and_permission):
        reason = rule(facts)

        if reason is not None:
            return reason

    return None


def evaluate_technical_access(facts: AccessFacts) -> AccessDenialReason | None:
    """Vía técnica (`platform:lookup` + `sub`).

    Orden: empresa → sucursal → membresía existente → membresía `ACTIVE` →
    asignación → asignación `ACTIVE` → permiso. La inexistencia de la empresa o
    sucursal se resuelve antes como `404` (no llega aquí).

    Returns:
        `None` si el acceso está permitido; si no, la primera causa que falla.
    """
    for rule in (_company, _branch, _membership, _assignment_and_permission):
        reason = rule(facts)

        if reason is not None:
            return reason

    return None
