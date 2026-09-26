"""Carrera entre inactivar la empresa y crear/reactivar una sucursal (prueba obligatoria 9).

Prueba **determinista**: cada operación corre en su propio hilo con su propia
sesión y conexión, a través de los servicios y repositorios reales. Una de las
dos se retiene justo antes de su `COMMIT` (con los bloqueos ya tomados)
sobrescribiendo `_commit` del repositorio; la otra debe quedar esperando un
bloqueo, lo que se comprueba en `pg_stat_activity` (`wait_event_type = 'Lock'`).
No se usan marcas de tiempo para inferir el orden (RC-09, RN-09, R-09).
"""

from __future__ import annotations

import threading
import time
from uuid import uuid4

import pytest
from sqlalchemy import text

from operational_context_service.application.branch_service import BranchService
from operational_context_service.application.company_service import CompanyService
from operational_context_service.application.exceptions import CompanyInactiveError
from operational_context_service.infrastructure.branch_repository import SQLAlchemyBranchRepository
from operational_context_service.infrastructure.company_repository import SQLAlchemyCompanyRepository
from tests.fakes import FakeGeographyDirectory, FakeOrganizationDirectory

TIMEOUT = 15


class Gate:
    """Retiene una transacción justo antes del `COMMIT` hasta que se libere."""

    def __init__(self) -> None:
        self.reached = threading.Event()
        self.release = threading.Event()

    def hold(self) -> None:
        self.reached.set()
        assert self.release.wait(TIMEOUT), "La transacción retenida no fue liberada"


def _holding_company_repository(session, gate: Gate) -> SQLAlchemyCompanyRepository:
    repository = SQLAlchemyCompanyRepository(session)
    original = repository._commit

    def commit() -> None:
        gate.hold()
        original()

    repository._commit = commit
    return repository


def _holding_branch_repository(session, gate: Gate) -> SQLAlchemyBranchRepository:
    repository = SQLAlchemyBranchRepository(session)
    original = repository._commit

    def commit() -> None:
        gate.hold()
        original()

    repository._commit = commit
    return repository


class Worker(threading.Thread):
    """Ejecuta una operación y guarda su resultado o su excepción."""

    def __init__(self, operation) -> None:
        super().__init__(daemon=True)
        self.operation = operation
        self.result = None
        self.error: BaseException | None = None

    def run(self) -> None:
        try:
            self.result = self.operation()
        except BaseException as exc:  # noqa: BLE001 - se verifica en la prueba
            self.error = exc


def _wait_for_lock_waiter(engine, expected: int = 1) -> None:
    """Espera a que haya `expected` sesiones bloqueadas esperando un lock."""
    deadline = time.monotonic() + TIMEOUT
    with engine.connect() as connection:
        while time.monotonic() < deadline:
            waiting = connection.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                    "AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()"
                )
            ).scalar_one()
            if waiting >= expected:
                return
            time.sleep(0.05)
    raise AssertionError("Ninguna sesión quedó esperando el bloqueo")


@pytest.fixture
def company_id(session_factory):
    with session_factory() as session:
        repository = SQLAlchemyCompanyRepository(session)
        values = {field: None for field in (
            "email", "phone", "address_line", "country_id", "administrative_division_id",
            "city_id", "postal_code", "latitude", "longitude",
        )}
        values.update(organization_identity_id=uuid4(), timezone="America/Bogota", default_currency="COP")
        return repository.create(values, actor_id="setup").id


def _company_service(session, gate: Gate | None = None) -> CompanyService:
    repository = _holding_company_repository(session, gate) if gate else SQLAlchemyCompanyRepository(session)
    return CompanyService(repository, FakeOrganizationDirectory(), FakeGeographyDirectory())


def _branch_service(session, gate: Gate | None = None) -> BranchService:
    repository = _holding_branch_repository(session, gate) if gate else SQLAlchemyBranchRepository(session)
    return BranchService(repository, SQLAlchemyCompanyRepository(session), FakeGeographyDirectory())


def _branch_data(code: str = "RACE-1") -> dict:
    return {"code": code, "name": "Sucursal en carrera"}


def _state(session_factory, company_id, branch_id=None):
    with session_factory() as session:
        company = session.execute(
            text("SELECT status, version FROM companies WHERE id = :id"), {"id": company_id}
        ).one()
        branches = session.execute(
            text("SELECT id, status, version FROM branches WHERE company_id = :id"), {"id": company_id}
        ).all()
    return company, branches


def _create_inactive_branch(session_factory, company_id):
    with session_factory() as session:
        service = _branch_service(session)
        branch = service.create(company_id, _branch_data("RE-1"), actor_id="setup")
        return service.deactivate(branch.id, expected_version=1, actor_id="setup")


def _run(first_gate: Gate, first: Worker, second: Worker, engine) -> None:
    first.start()
    assert first_gate.reached.wait(TIMEOUT), "La primera transacción no llegó al COMMIT"
    second.start()
    try:
        _wait_for_lock_waiter(engine)
        assert second.is_alive(), "La segunda operación no quedó esperando"
    finally:
        first_gate.release.set()
    first.join(TIMEOUT)
    second.join(TIMEOUT)
    assert not first.is_alive() and not second.is_alive(), "Posible interbloqueo"


def test_case_a_deactivate_first_then_create_branch_waits_and_fails(session_factory, test_engine, company_id):
    gate = Gate()
    session_a, session_b = session_factory(), session_factory()
    try:
        deactivate = Worker(lambda: _company_service(session_a, gate).deactivate(
            company_id, expected_version=1, actor_id="a"))
        create = Worker(lambda: _branch_service(session_b).create(company_id, _branch_data(), actor_id="b"))

        _run(gate, deactivate, create, test_engine)
    finally:
        session_a.close()
        session_b.close()

    assert deactivate.error is None
    assert isinstance(create.error, CompanyInactiveError)
    company, branches = _state(session_factory, company_id)
    assert company.status == "INACTIVE"
    assert branches == []


def test_case_b_create_branch_first_then_deactivate_waits(session_factory, test_engine, company_id):
    gate = Gate()
    session_a, session_b = session_factory(), session_factory()
    try:
        create = Worker(lambda: _branch_service(session_b, gate).create(company_id, _branch_data(), actor_id="b"))
        deactivate = Worker(lambda: _company_service(session_a).deactivate(
            company_id, expected_version=1, actor_id="a"))

        _run(gate, create, deactivate, test_engine)
    finally:
        session_a.close()
        session_b.close()

    assert create.error is None and deactivate.error is None
    company, branches = _state(session_factory, company_id)
    assert (company.status, company.version) == ("INACTIVE", 2)
    assert [(b.status, b.version) for b in branches] == [("ACTIVE", 1)]  # DS-07: sin cambio automático
    with session_factory() as session:
        branch = SQLAlchemyBranchRepository(session).get_by_id(branches[0].id)
    assert branch.company_status == "INACTIVE"


def test_case_c_deactivate_first_then_reactivate_branch_waits_and_fails(session_factory, test_engine, company_id):
    branch = _create_inactive_branch(session_factory, company_id)
    gate = Gate()
    session_a, session_b = session_factory(), session_factory()
    try:
        deactivate = Worker(lambda: _company_service(session_a, gate).deactivate(
            company_id, expected_version=1, actor_id="a"))
        reactivate = Worker(lambda: _branch_service(session_b).reactivate(
            branch.id, expected_version=branch.version, actor_id="b"))

        _run(gate, deactivate, reactivate, test_engine)
    finally:
        session_a.close()
        session_b.close()

    assert deactivate.error is None
    assert isinstance(reactivate.error, CompanyInactiveError)
    company, branches = _state(session_factory, company_id)
    assert company.status == "INACTIVE"
    assert [(b.status, b.version) for b in branches] == [("INACTIVE", branch.version)]


def test_case_d_reactivate_branch_first_then_deactivate_waits(session_factory, test_engine, company_id):
    branch = _create_inactive_branch(session_factory, company_id)
    gate = Gate()
    session_a, session_b = session_factory(), session_factory()
    try:
        reactivate = Worker(lambda: _branch_service(session_b, gate).reactivate(
            branch.id, expected_version=branch.version, actor_id="b"))
        deactivate = Worker(lambda: _company_service(session_a).deactivate(
            company_id, expected_version=1, actor_id="a"))

        _run(gate, reactivate, deactivate, test_engine)
    finally:
        session_a.close()
        session_b.close()

    assert reactivate.error is None and deactivate.error is None
    company, branches = _state(session_factory, company_id)
    assert company.status == "INACTIVE"
    assert [(b.status, b.version) for b in branches] == [("ACTIVE", branch.version + 1)]
