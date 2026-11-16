"""Mundo de acceso operativo para probar los adaptadores de contrato de los consumidores (spec 025, Historia 3).

Inserta, en una base con el esquema real de Operational Context (``create_owner_schema``), empresas, sucursales,
membresías y asignaciones que cubren todas las causas de la vía propia, y devuelve para cada caso el resultado
esperado de ``GET /operational-access``. Ese resultado está comprobado contra el servicio real por la prueba de
paridad de Operational Context (``tests/contract_views/test_operational_access_parity.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Engine, text

from sio_contract_read.operational_access import OperationalAccess


@dataclass(frozen=True, slots=True)
class AccessCase:
    name: str
    subject: str
    company_id: UUID | None
    branch_id: UUID | None
    expected: OperationalAccess

    def oc_body(self) -> dict:
        """Cuerpo que devolvería ``GET /operational-access`` (para el doble HTTP)."""
        return {
            "allowed": self.expected.allowed,
            "reason": self.expected.reason,
            "keycloak_user_id": self.subject,
            "company_id": None if self.expected.company_id is None else str(self.expected.company_id),
            "branch_id": None if self.branch_id is None else str(self.branch_id),
            "application_user_id": (
                None if self.expected.application_user_id is None else str(self.expected.application_user_id)
            ),
            "permission": None,
        }


_AUDIT = "'contract-test', 'contract-test'"


def _company(connection, status: str = "ACTIVE") -> UUID:
    company_id = uuid4()
    connection.execute(
        text(f"INSERT INTO companies (id, organization_identity_id, status, version, created_by, updated_by) "
             f"VALUES (:id, :org, :status, 1, {_AUDIT})"),
        {"id": company_id, "org": uuid4(), "status": status},
    )
    return company_id


def _branch(connection, company_id: UUID, code: str, status: str = "ACTIVE") -> UUID:
    branch_id = uuid4()
    connection.execute(
        text(f"INSERT INTO branches (id, company_id, code, name, status, version, created_by, updated_by) "
             f"VALUES (:id, :company, :code, :name, :status, 1, {_AUDIT})"),
        {"id": branch_id, "company": company_id, "code": code, "name": f"Sucursal {code}", "status": status},
    )
    return branch_id


def _member(connection, company_id: UUID, subject: str, status: str = "ACTIVE", age_days: int = 0) -> UUID:
    member_id = uuid4()
    connection.execute(
        text(f"INSERT INTO application_users (id, company_id, keycloak_user_id, person_identity_id, display_name, "
             f"status, updated_at, created_by, updated_by) VALUES (:id, :company, :sub, :person, 'Ficticio', :status, "
             f"now() - make_interval(days => :age), {_AUDIT})"),
        {"id": member_id, "company": company_id, "sub": subject, "person": uuid4(), "status": status, "age": age_days},
    )
    return member_id


def _assign(connection, member_id: UUID, branch_id: UUID, company_id: UUID, status: str = "ACTIVE") -> None:
    connection.execute(
        text("INSERT INTO user_branches (id, application_user_id, branch_id, company_id, status, assigned_by, "
             "deactivated_at, created_by, updated_by) VALUES (:id, :member, :branch, :company, :status, "
             "'contract-test', :deactivated, 'contract-test', 'contract-test')"),
        {"id": uuid4(), "member": member_id, "branch": branch_id, "company": company_id, "status": status,
         "deactivated": None if status == "ACTIVE" else datetime.now(UTC)},
    )


def seed_access_world(engine: Engine) -> list[AccessCase]:
    """Crea los datos y devuelve los casos con su resultado esperado."""
    ok, foreign, inactive_member, two_inactive = (f"sub-{name}-{uuid4()}" for name in ("ok", "ajeno", "inactivo", "dos"))
    with engine.begin() as connection:
        c = _company(connection)
        d = _company(connection, "INACTIVE")
        s1, s2 = _branch(connection, c, "S1"), _branch(connection, c, "S2")
        s3, s4 = _branch(connection, c, "S3"), _branch(connection, c, "S4", "INACTIVE")
        d1 = _branch(connection, d, "D1")
        m_ok = _member(connection, c, ok)
        _assign(connection, m_ok, s1, c)
        _assign(connection, m_ok, s3, c, "INACTIVE")
        _assign(connection, m_ok, s4, c)
        m_ok_d = _member(connection, d, ok)
        _assign(connection, m_ok_d, d1, d)
        m_inactive = _member(connection, c, inactive_member, "INACTIVE")
        _assign(connection, m_inactive, s1, c)
        _member(connection, c, two_inactive, "INACTIVE", age_days=3)
        m_recent = _member(connection, c, two_inactive, "INACTIVE", age_days=1)
        _member(connection, d, foreign, "ACTIVE")  # miembro de D, no de C

    unknown = uuid4()
    allowed = lambda company, member: OperationalAccess(True, None, company, member)  # noqa: E731
    denied = lambda reason, company, member: OperationalAccess(False, reason, company, member)  # noqa: E731
    return [
        AccessCase("permitido_empresa", ok, c, None, allowed(c, m_ok)),
        AccessCase("permitido_sucursal", ok, None, s1, allowed(c, m_ok)),
        AccessCase("empresa_inexistente", ok, unknown, None, denied("USER_NOT_MEMBER", unknown, None)),
        AccessCase("sucursal_inexistente", ok, None, unknown, denied("USER_NOT_MEMBER", None, None)),
        AccessCase("empresa_ajena", foreign, c, None, denied("USER_NOT_MEMBER", c, None)),
        AccessCase("sucursal_ajena", foreign, None, s1, denied("USER_NOT_MEMBER", None, None)),
        AccessCase("membresia_inactiva", inactive_member, None, s1,
                   denied("USER_MEMBERSHIP_INACTIVE", c, m_inactive)),
        AccessCase("membresia_inactiva_mas_reciente", two_inactive, c, None,
                   denied("USER_MEMBERSHIP_INACTIVE", c, m_recent)),
        AccessCase("empresa_inactiva", ok, d, None, denied("COMPANY_INACTIVE", d, m_ok_d)),
        AccessCase("empresa_inactiva_sucursal", ok, None, d1, denied("COMPANY_INACTIVE", d, m_ok_d)),
        AccessCase("sucursal_inactiva", ok, None, s4, denied("BRANCH_INACTIVE", c, m_ok)),
        AccessCase("sucursal_no_asignada", ok, None, s2, denied("BRANCH_NOT_ASSIGNED", c, m_ok)),
        AccessCase("asignacion_inactiva", ok, None, s3, denied("USER_BRANCH_INACTIVE", c, m_ok)),
    ]


def lock_access_tables(engine: Engine):
    """Contexto que bloquea ``application_users`` para provocar ``statement_timeout`` en el lector."""
    from contextlib import contextmanager

    @contextmanager
    def _lock():
        connection = engine.connect()
        transaction = connection.begin()
        try:
            connection.execute(text("LOCK TABLE application_users IN ACCESS EXCLUSIVE MODE"))
            yield
        finally:
            transaction.rollback()
            connection.close()

    return _lock()
