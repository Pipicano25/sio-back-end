"""Dobles de Operational Context, Commercial Relationship y Keycloak (Principio IV).

Se inyectan en `create_app(...)`; el código del servicio nunca tiene modos por
entorno. Cada doble registra sus llamadas y puede configurarse para fallar si se
le llama (p. ej. los reintentos idempotentes no deben consultar dependencias).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import jwt

from inventory_service.application.exceptions import (
    COMMERCIAL_RELATIONSHIP,
    OPERATIONAL_CONTEXT,
    DependencyUnavailableError,
    OperationalAccessDeniedError,
)
from inventory_service.application.ports import ApplicationUserInfo, BranchInfo, CompanyProductInfo


def subject_of(authorization: str | None) -> str | None:
    """`sub` del token de la solicitud (sin verificar: lo verificó `sio-auth`)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    claims = jwt.decode(authorization.split(" ", 1)[1], options={"verify_signature": False})
    return claims.get("sub")


@dataclass
class FakeOperationalContext:
    """Sucursales, usuarios operativos y membresías configurables."""

    branches: dict[UUID, BranchInfo] = field(default_factory=dict)
    users: dict[UUID, ApplicationUserInfo] = field(default_factory=dict)
    members: set[tuple[str, UUID]] = field(default_factory=set)
    forbidden_subjects: set[str] = field(default_factory=set)
    unavailable: bool = False
    fail_if_called: bool = False
    technical_calls: list[tuple[str, UUID]] = field(default_factory=list)
    access_calls: list[tuple[str | None, str | None, UUID]] = field(default_factory=list)

    def add_branch(
        self,
        company_id: UUID,
        *,
        branch_id: UUID | None = None,
        status: str = "ACTIVE",
        company_status: str = "ACTIVE",
    ) -> UUID:
        branch_id = branch_id or uuid4()
        self.branches[branch_id] = BranchInfo(branch_id, company_id, status, company_status)
        return branch_id

    def add_user(self, company_id: UUID, *, status: str = "ACTIVE", user_id: UUID | None = None) -> UUID:
        user_id = user_id or uuid4()
        self.users[user_id] = ApplicationUserInfo(user_id, company_id, status, uuid4())
        return user_id

    def add_member(self, sub: str, company_id: UUID) -> None:
        self.members.add((sub, company_id))

    def _guard(self, operation: str, key: UUID) -> None:
        if self.fail_if_called:
            raise AssertionError(f"No debe llamarse a Operational Context ({operation})")
        self.technical_calls.append((operation, key))
        if self.unavailable:
            raise DependencyUnavailableError(OPERATIONAL_CONTEXT, operation=operation, cause="FAKE_UNAVAILABLE")

    # Puerto técnico ----------------------------------------------------------

    def get_branch(self, branch_id: UUID) -> BranchInfo | None:
        self._guard("branch", branch_id)
        return self.branches.get(branch_id)

    def get_application_user(self, application_user_id: UUID) -> ApplicationUserInfo | None:
        self._guard("application_user", application_user_id)
        return self.users.get(application_user_id)

    def directory(self) -> FakeOperationalContext:
        return self

    # Puerto de membresía (token del usuario) --------------------------------

    def access_for(self, request) -> FakeCompanyAccess:
        return FakeCompanyAccess(self, request.headers.get("authorization"))


class FakeCompanyAccess:
    def __init__(self, state: FakeOperationalContext, authorization: str | None) -> None:
        self._state = state
        self._authorization = authorization
        self._sub = subject_of(authorization)

    def is_member(self, company_id: UUID) -> bool:
        if self._state.fail_if_called:
            raise AssertionError("No debe llamarse a operational-access")
        self._state.access_calls.append((self._sub, self._authorization, company_id))
        if self._state.unavailable:
            raise DependencyUnavailableError(OPERATIONAL_CONTEXT, operation="operational_access", cause="FAKE")
        if self._sub in self._state.forbidden_subjects:
            raise OperationalAccessDeniedError()
        return (self._sub, company_id) in self._state.members


@dataclass
class FakeCommercialRelationship:
    """Productos empresariales configurables."""

    products: dict[UUID, CompanyProductInfo] = field(default_factory=dict)
    unavailable: bool = False
    fail_if_called: bool = False
    calls: list[tuple[UUID, ...]] = field(default_factory=list)

    def add_product(
        self,
        company_id: UUID,
        *,
        status: str = "ACTIVE",
        inventory_control_enabled: bool = True,
        product_id: UUID | None = None,
    ) -> UUID:
        product_id = product_id or uuid4()
        self.products[product_id] = CompanyProductInfo(product_id, company_id, status, inventory_control_enabled)
        return product_id

    def lookup(self, product_ids: Iterable[UUID]) -> dict[UUID, CompanyProductInfo]:
        ids = tuple(product_ids)
        if self.fail_if_called:
            raise AssertionError("No debe llamarse a Commercial Relationship")
        self.calls.append(ids)
        if self.unavailable:
            raise DependencyUnavailableError(COMMERCIAL_RELATIONSHIP, operation="batch_lookup", cause="FAKE")
        return {product_id: self.products[product_id] for product_id in ids if product_id in self.products}

    def directory(self) -> FakeCommercialRelationship:
        return self
