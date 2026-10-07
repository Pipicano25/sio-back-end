"""Puertos de Inventory Service (Principio XV).

Las pruebas sustituyen los adaptadores HTTP por dobles inyectados en
`create_app` (sin modos por entorno).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BranchInfo:
    """Sucursal según Operational Context (contrato 004)."""

    id: UUID
    company_id: UUID
    status: str
    company_status: str


@dataclass(frozen=True, slots=True)
class ApplicationUserInfo:
    """Usuario operativo según Operational Context (contrato 005)."""

    id: UUID
    company_id: UUID
    status: str
    keycloak_user_id: UUID | None


@dataclass(frozen=True, slots=True)
class CompanyProductInfo:
    """Producto empresarial según Commercial Relationship (contrato 007)."""

    id: UUID
    company_id: UUID
    status: str
    inventory_control_enabled: bool


@dataclass(frozen=True, slots=True)
class BranchAccessResult:
    """Resultado sin interpretar de `operational-access` (contrato 005; `dependencies-delta.md`).

    La traducción de `reason` a respuestas de Inventory vive en
    `application/branch_access.py` (un solo lugar para adaptador y dobles).
    """

    allowed: bool
    reason: str | None
    company_id: UUID | None
    application_user_id: UUID | None


class OperationalContextDirectory(Protocol):
    """Operational Context con la identidad técnica de Inventory (`platform:lookup`)."""

    def get_branch(self, branch_id: UUID) -> BranchInfo | None:
        """`None` si no existe. Raises `DependencyUnavailableError`."""
        ...

    def get_application_user(self, application_user_id: UUID) -> ApplicationUserInfo | None:
        """`None` si no existe. Raises `DependencyUnavailableError`."""
        ...

    def get_company_currency(self, company_id: UUID) -> str | None:
        """`default_currency` de la empresa (R-03b); `None` si no existe. Raises `DependencyUnavailableError`."""
        ...


class CompanyProductDirectory(Protocol):
    """Commercial Relationship con la identidad técnica de Inventory (`platform:lookup`)."""

    def lookup(self, product_ids: Iterable[UUID]) -> dict[UUID, CompanyProductInfo]:
        """Productos encontrados por `id` (los ausentes no existen). Raises `DependencyUnavailableError`."""
        ...


class CompanyAccessDirectory(Protocol):
    """Membresía del usuario consultante (`operational-access` con su token)."""

    def is_member(self, company_id: UUID) -> bool:
        """Raises `OperationalAccessDeniedError` o `DependencyUnavailableError`."""
        ...

    def check_branch(self, branch_id: UUID) -> BranchAccessResult:
        """`operational-access?branch_id=` (R-09). Raises `OperationalAccessDeniedError` o `DependencyUnavailableError`."""
        ...

    def check_company(self, company_id: UUID) -> BranchAccessResult:
        """`operational-access?company_id=` con `application_user_id` (políticas). Mismos errores."""
        ...


class TokenProvider(Protocol):
    """Token técnico `client_credentials` de Inventory."""

    def get_token(self) -> str: ...

    def invalidate(self) -> None: ...
