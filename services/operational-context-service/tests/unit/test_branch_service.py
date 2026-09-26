"""Servicio de sucursales: dependencias antes de la transacción (R-09, C4).

Las llamadas a Geography ocurren sin transacción de base de datos abierta y
sin bloqueo `FOR SHARE` sobre la empresa mientras se espera la respuesta.
"""

import threading
from uuid import uuid4

import pytest
from sqlalchemy import text

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.branch_service import BranchService
from operational_context_service.application.exceptions import (
    CityNotFoundError,
    DependencyUnavailableError,
)
from operational_context_service.infrastructure.branch_repository import SQLAlchemyBranchRepository
from operational_context_service.infrastructure.company_repository import SQLAlchemyCompanyRepository

# Alcance de plataforma (Fase B): estas pruebas llaman a los servicios directamente.
PLATFORM = AccessScope(
    subject="test", is_platform_admin=True, can_lookup=True, member_company_ids=frozenset()
)


@pytest.fixture
def company(db_session):
    repository = SQLAlchemyCompanyRepository(db_session)
    values = {field: None for field in (
        "email", "phone", "address_line", "country_id", "administrative_division_id",
        "city_id", "postal_code", "latitude", "longitude",
    )}
    values.update(organization_identity_id=uuid4(), timezone="America/Bogota", default_currency="COP")
    created = repository.create(values, actor_id="sub")
    repository.end_read()
    return created


@pytest.fixture
def service(db_session, fake_geography, fake_organizations):
    fake_geography.watched_sessions.append(db_session)
    return BranchService(
        SQLAlchemyBranchRepository(db_session),
        SQLAlchemyCompanyRepository(db_session),
        fake_geography,
    )


def _data(**overrides):
    data = {"code": "B-01", "name": "Sucursal"}
    data.update(overrides)
    return data


def test_create_calls_geography_without_open_transaction(service, company, fake_geography, geo):
    service.create(
        PLATFORM,
        company.id,
        _data(country_id=geo.colombia, administrative_division_id=geo.antioquia, city_id=geo.medellin),
        actor_id="sub",
    )

    assert fake_geography.count() == 3
    assert fake_geography.in_transaction_at_call == [False, False, False]


def test_update_with_location_change_calls_geography_without_open_transaction(service, company, fake_geography, geo):
    branch = service.create(PLATFORM, company.id, _data(), actor_id="sub")
    fake_geography.reset()

    service.update(PLATFORM, branch.id, _data(country_id=geo.colombia), expected_version=branch.version, actor_id="sub")

    assert fake_geography.in_transaction_at_call == [False]


def test_rejections_write_nothing(service, company, db_session, fake_geography, geo):
    with pytest.raises(CityNotFoundError):
        service.create(PLATFORM, company.id, _data(country_id=geo.colombia, city_id=uuid4()), actor_id="sub")

    fake_geography.mode = "unavailable"
    with pytest.raises(DependencyUnavailableError):
        service.create(PLATFORM, company.id, _data(country_id=geo.colombia), actor_id="sub")

    assert db_session.execute(text("SELECT count(*) FROM branches")).scalar_one() == 0


def test_branches_never_call_party_identity(service, company, fake_organizations, geo):
    branch = service.create(PLATFORM, company.id, _data(country_id=geo.colombia), actor_id="sub")
    service.update(PLATFORM, branch.id, _data(name="Otro", country_id=geo.colombia), expected_version=1, actor_id="sub")

    assert fake_organizations.count() == 0


def test_no_lock_on_company_while_waiting_for_geography(
    session_factory, company, fake_geography, geo, test_engine
):
    """Con Geography retenido, no hay transacción abierta ni bloqueo sobre la empresa."""
    fake_geography.hold = threading.Event()
    errors = []

    def create():
        with session_factory() as session:
            fake_geography.watched_sessions.append(session)
            service = BranchService(
                SQLAlchemyBranchRepository(session),
                SQLAlchemyCompanyRepository(session),
                fake_geography,
            )
            try:
                service.create(PLATFORM, company.id, _data(country_id=geo.colombia), actor_id="sub")
            except Exception as exc:  # pragma: no cover - se reporta abajo
                errors.append(exc)

    worker = threading.Thread(target=create)
    worker.start()
    try:
        assert fake_geography.called.wait(timeout=10), "Geography no fue consultado"

        with test_engine.connect() as connection:
            locks = connection.execute(
                text(
                    "SELECT count(*) FROM pg_locks l JOIN pg_class c ON c.oid = l.relation "
                    "WHERE c.relname = 'companies' AND l.mode IN ('RowShareLock', 'RowExclusiveLock') "
                    "AND l.pid <> pg_backend_pid()"
                )
            ).scalar_one()
            idle_in_transaction = connection.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
                    "AND state LIKE 'idle in transaction%' AND pid <> pg_backend_pid()"
                )
            ).scalar_one()

        assert locks == 0
        assert idle_in_transaction == 0
        assert fake_geography.in_transaction_at_call == [False]
    finally:
        fake_geography.hold.set()
        worker.join(timeout=10)

    assert not errors
