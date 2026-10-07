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
from inventory_service.application.ports import (
    ApplicationUserInfo,
    BranchAccessResult,
    BranchInfo,
    CompanyProductInfo,
)


def subject_of(authorization: str | None) -> str | None:
    """`sub` del token de la solicitud (sin verificar: lo verificó `sio-auth`)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    claims = jwt.decode(authorization.split(" ", 1)[1], options={"verify_signature": False})
    return claims.get("sub")


@dataclass
class FakeOperationalContext:
    """Sucursales, usuarios operativos, membresías, asignaciones y monedas configurables.

    `check_branch` reproduce el orden de evaluación de Operational Context
    (`domain/access.py` de la 005): membresía → empresa → sucursal → asignación.
    """

    branches: dict[UUID, BranchInfo] = field(default_factory=dict)
    users: dict[UUID, ApplicationUserInfo] = field(default_factory=dict)
    members: set[tuple[str, UUID]] = field(default_factory=set)
    member_status: dict[tuple[str, UUID], str] = field(default_factory=dict)
    member_users: dict[tuple[str, UUID], UUID] = field(default_factory=dict)
    assignments: dict[tuple[str, UUID], str] = field(default_factory=dict)
    currencies: dict[UUID, str] = field(default_factory=dict)
    forbidden_subjects: set[str] = field(default_factory=set)
    unavailable: bool = False
    fail_if_called: bool = False
    technical_calls: list[tuple[str, UUID]] = field(default_factory=list)
    access_calls: list[tuple[str | None, str | None, UUID]] = field(default_factory=list)
    branch_access_calls: list[tuple[str | None, str | None, UUID]] = field(default_factory=list)

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
        self.currencies.setdefault(company_id, "COP")
        return branch_id

    def add_user(self, company_id: UUID, *, status: str = "ACTIVE", user_id: UUID | None = None) -> UUID:
        user_id = user_id or uuid4()
        self.users[user_id] = ApplicationUserInfo(user_id, company_id, status, uuid4())
        return user_id

    def add_member(self, sub: str, company_id: UUID, *, status: str = "ACTIVE") -> UUID:
        """Membresía del `sub` en la empresa con su usuario operativo (creado si no existe)."""
        if status == "ACTIVE":
            self.members.add((sub, company_id))
        else:
            self.members.discard((sub, company_id))
        self.member_status[(sub, company_id)] = status
        if (sub, company_id) not in self.member_users:
            self.member_users[(sub, company_id)] = self.add_user(company_id)
        return self.member_users[(sub, company_id)]

    def assign(self, sub: str, branch_id: UUID, *, status: str = "ACTIVE") -> None:
        """Asignación del usuario a la sucursal (`user_branches` de Operational Context)."""
        self.assignments[(sub, branch_id)] = status

    def application_user_of(self, sub: str, company_id: UUID) -> UUID:
        return self.member_users[(sub, company_id)]

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

    def get_company_currency(self, company_id: UUID) -> str | None:
        self._guard("company", company_id)
        return self.currencies.get(company_id)

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

    def _evaluate(self, *, company_id: UUID, branch_id: UUID | None) -> BranchAccessResult:
        state = self._state
        branch = state.branches.get(branch_id) if branch_id is not None else None
        company = branch.company_id if branch is not None else company_id
        membership = state.member_status.get((self._sub, company)) if company is not None else None
        user = state.member_users.get((self._sub, company)) if company is not None else None

        def result(allowed: bool, reason: str | None) -> BranchAccessResult:
            return BranchAccessResult(allowed, reason, company, user)

        if membership is None or (branch_id is not None and branch is None):
            return BranchAccessResult(False, "USER_NOT_MEMBER", None, None)
        if membership != "ACTIVE":
            return result(False, "USER_MEMBERSHIP_INACTIVE")
        company_status = branch.company_status if branch is not None else "ACTIVE"
        if company_status != "ACTIVE":
            return result(False, "COMPANY_INACTIVE")
        if branch is not None:
            if branch.status != "ACTIVE":
                return result(False, "BRANCH_INACTIVE")
            assignment = state.assignments.get((self._sub, branch_id))
            if assignment is None:
                return result(False, "BRANCH_NOT_ASSIGNED")
            if assignment != "ACTIVE":
                return result(False, "USER_BRANCH_INACTIVE")
        return result(True, None)

    def check_branch(self, branch_id: UUID) -> BranchAccessResult:
        """`operational-access?branch_id=` con el token del usuario (resultado sin interpretar)."""
        if self._state.fail_if_called:
            raise AssertionError("No debe llamarse a operational-access")
        self._state.branch_access_calls.append((self._sub, self._authorization, branch_id))
        if self._state.unavailable:
            raise DependencyUnavailableError(OPERATIONAL_CONTEXT, operation="operational_access", cause="FAKE")
        if self._sub in self._state.forbidden_subjects:
            raise OperationalAccessDeniedError()
        return self._evaluate(company_id=None, branch_id=branch_id)

    def check_company(self, company_id: UUID) -> BranchAccessResult:
        """`operational-access?company_id=` con el token del usuario (resultado sin interpretar)."""
        if self._state.fail_if_called:
            raise AssertionError("No debe llamarse a operational-access")
        self._state.access_calls.append((self._sub, self._authorization, company_id))
        if self._state.unavailable:
            raise DependencyUnavailableError(OPERATIONAL_CONTEXT, operation="operational_access", cause="FAKE")
        if self._sub in self._state.forbidden_subjects:
            raise OperationalAccessDeniedError()
        return self._evaluate(company_id=company_id, branch_id=None)


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
