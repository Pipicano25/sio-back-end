"""`audit-outbox-worker` contra audit-service y Keycloak reales (T054; SC-008, SC-010; RC-04, RC-05).

Se ejecuta con `pytest -m integration` y exige el entorno integrado:

- audit-service en `AUDIT_INTEGRATION_BASE_URL` (defecto `http://localhost:8110/api/v1`), con su
  contenedor `sio-audit-service` (la prueba lo detiene y lo vuelve a iniciar);
- Keycloak con el cliente `audit-test-emitter` (secreto en `AUDIT_TEST_EMITTER_CLIENT_SECRET` o en
  `infrastructure/.env`) y la contraseña de los usuarios de prueba (`KEYCLOAK_TEST_USER_PASSWORD`);
- Operational Context con alguna membresía `ACTIVE` de `admin.test` (la crean las pruebas de
  integración de los servicios anteriores).

La base del "emisor" es la base de pruebas de la librería (`audit_outbox`). Los datos son ficticios.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from sio_audit.event import AuditEvent, to_canonical_dict
from sio_audit.outbox import record_audit_event
from sio_audit.worker import Worker, WorkerSettings, run_once

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[4]
AUDIT = os.environ.get("AUDIT_INTEGRATION_BASE_URL", "http://localhost:8110/api/v1").rstrip("/")
OPERATIONAL_CONTEXT = os.environ.get(
    "OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL", "http://localhost:8104/api/v1"
).rstrip("/")
KEYCLOAK = os.environ.get("KEYCLOAK_INTEGRATION_BASE_URL", "http://localhost:8081").rstrip("/")
TOKEN_URL = f"{KEYCLOAK}/realms/sio/protocol/openid-connect/token"
AUDIT_CONTAINER = "sio-audit-service"


def _secret(variable: str) -> str | None:
    value = os.environ.get(variable, "").strip()
    env_file = REPO_ROOT / "infrastructure" / ".env"
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, content = line.partition("=")
            if separator and name.strip() == variable:
                value = content.strip()
    return value or None


def _wait_ready(timeout: float = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(AUDIT.removesuffix("/api/v1") + "/health/ready", timeout=3).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise AssertionError("audit-service no volvió a estar listo")


@pytest.fixture(scope="module")
def worker_settings(outbox_database_url: str) -> WorkerSettings:
    secret = _secret("AUDIT_TEST_EMITTER_CLIENT_SECRET")
    if not secret:
        pytest.skip("Defina AUDIT_TEST_EMITTER_CLIENT_SECRET (o infrastructure/.env).")
    try:
        _wait_ready(timeout=5)
    except AssertionError:
        pytest.skip("audit-service no está en ejecución.")
    return WorkerSettings(
        database_url=outbox_database_url,
        audit_base_url=AUDIT,
        keycloak_base_url=KEYCLOAK,
        keycloak_realm="sio",
        client_id="audit-test-emitter",
        client_secret=secret,
        poll_interval_seconds=0.2,
        backoff_initial_seconds=0.2,
        backoff_max_seconds=2.0,
        batch_size=25,
    )


@pytest.fixture(scope="module")
def admin_http():
    password = _secret("KEYCLOAK_TEST_USER_PASSWORD")
    if not password:
        pytest.skip("Defina KEYCLOAK_TEST_USER_PASSWORD (o infrastructure/.env).")
    token = httpx.post(
        TOKEN_URL,
        data={"grant_type": "password", "client_id": "sio-web", "scope": "openid",
              "username": "admin.test", "password": password},
        timeout=15,
    ).raise_for_status().json()["access_token"]
    with httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=15) as client:
        yield client


@pytest.fixture(scope="module")
def company(admin_http) -> UUID:
    """Empresa real donde `admin.test` es miembro `ACTIVE` (Operational Context)."""
    body = admin_http.get(f"{OPERATIONAL_CONTEXT}/me/operational-context").raise_for_status().json()
    for membership in body["memberships"]:
        if membership["status"] == "ACTIVE" and membership["company_status"] == "ACTIVE":
            return UUID(membership["company_id"])
    pytest.skip("admin.test no tiene membresías ACTIVE en Operational Context.")


def _event(company: UUID, **changes) -> AuditEvent:
    values = dict(
        event_id=None,
        company_id=company,
        action="CONFIRM",
        entity_type="Purchase",
        entity_id=uuid4(),
        result="SUCCESS",
        occurred_at=datetime.now(UTC),
        previous_values={"status": "DRAFT"},
        new_values={"status": "CONFIRMED"},
        correlation_id=None,
    )
    values.update(changes)
    return AuditEvent(**values)


def _record(engine, *events: AuditEvent) -> list[UUID]:
    with Session(engine) as session:
        ids = [record_audit_event(session, event) for event in events]
        session.commit()
    return ids


def _status(engine, event_id: UUID) -> str:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT status FROM audit_outbox WHERE event_id = :id"), {"id": event_id}
        ).scalar_one()


def _audit_events(admin_http, company: UUID, **params) -> list[dict]:
    response = admin_http.get(f"{AUDIT}/companies/{company}/audit-events", params={"page_size": 100, **params})
    assert response.status_code == 200, response.text
    return response.json()["items"]


def _drain(engine, settings: WorkerSettings, cycles: int = 10) -> None:
    worker = Worker(settings, engine=engine)
    for _ in range(cycles):
        with engine.begin() as connection:
            connection.execute(text("UPDATE audit_outbox SET next_attempt_at = now() WHERE status = 'PENDING'"))
        run_once(worker.engine, worker.client, settings)


def test_integration_guide_example(clean_outbox, worker_settings, admin_http, company) -> None:
    """Ejemplo de `services/audit-service/docs/integracion-emisores.md` §7 (SC-008)."""
    [event_id] = _record(
        clean_outbox,
        _event(company, new_values={"status": "CONFIRMED", "api_key": "nunca-se-guarda"}),
    )

    worker = Worker(worker_settings, engine=clean_outbox)
    result = run_once(worker.engine, worker.client, worker_settings)

    assert result.sent == [str(event_id)]
    assert _status(clean_outbox, event_id) == "SENT"
    [stored] = _audit_events(admin_http, company, event_id=str(event_id))
    assert stored["source_service"] == "audit-test-emitter"
    assert stored["new_values"] == {"status": "CONFIRMED", "api_key": "***"}
    assert stored["redacted_paths"] == ["new_values.api_key"]
    assert "nunca-se-guarda" not in str(stored)


def test_lost_response_is_idempotent(clean_outbox, worker_settings, admin_http, company) -> None:
    [event_id] = _record(clean_outbox, _event(company))
    _drain(clean_outbox, worker_settings, cycles=1)
    assert _status(clean_outbox, event_id) == "SENT"

    # La confirmación "se perdió": la fila vuelve a PENDING y se reenvía.
    with clean_outbox.begin() as connection:
        connection.execute(
            text("UPDATE audit_outbox SET status = 'PENDING', sent_at = NULL WHERE event_id = :id"),
            {"id": event_id},
        )
    _drain(clean_outbox, worker_settings, cycles=1)

    assert _status(clean_outbox, event_id) == "SENT"
    assert len(_audit_events(admin_http, company, event_id=str(event_id))) == 1


def test_audit_down_then_up_delivers_once(clean_outbox, worker_settings, admin_http, company) -> None:
    """SC-010: con Audit detenido la operación del emisor termina; al volver, se entrega una vez."""
    correlation = uuid4()
    subprocess.run(["docker", "stop", AUDIT_CONTAINER], check=True, capture_output=True)
    try:
        ids = _record(clean_outbox, *[_event(company, correlation_id=correlation) for _ in range(3)])
        worker = Worker(worker_settings, engine=clean_outbox)
        result = run_once(worker.engine, worker.client, worker_settings)
        assert sorted(result.retried) == sorted(str(i) for i in ids)
        assert {_status(clean_outbox, i) for i in ids} == {"PENDING"}
    finally:
        subprocess.run(["docker", "start", AUDIT_CONTAINER], check=True, capture_output=True)
        _wait_ready()

    _drain(clean_outbox, worker_settings, cycles=3)

    assert {_status(clean_outbox, i) for i in ids} == {"SENT"}
    assert len(_audit_events(admin_http, company, correlation_id=str(correlation))) == 3


def test_worker_killed_mid_way_resumes_without_duplicates(
    clean_outbox, worker_settings, admin_http, company, outbox_database_url
) -> None:
    correlation = uuid4()
    ids = _record(clean_outbox, *[_event(company, correlation_id=correlation) for _ in range(120)])

    env = {
        **os.environ,
        "DATABASE_URL": outbox_database_url,
        "AUDIT_SERVICE_BASE_URL": AUDIT,
        "KEYCLOAK_BASE_URL": KEYCLOAK,
        "KEYCLOAK_REALM": "sio",
        "AUDIT_CLIENT_ID": "audit-test-emitter",
        "AUDIT_CLIENT_SECRET": worker_settings.client_secret,
        "AUDIT_OUTBOX_POLL_INTERVAL_SECONDS": "0.1",
        "AUDIT_OUTBOX_BATCH_SIZE": "10",
        "AUDIT_OUTBOX_BACKOFF_INITIAL_SECONDS": "0.2",
        "AUDIT_OUTBOX_BACKOFF_MAX_SECONDS": "2",
    }
    command = [sys.executable, "-m", "sio_audit.worker"]

    first = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    first.kill()  # caída abrupta, sin parada ordenada
    first.wait(timeout=10)

    with clean_outbox.connect() as connection:
        sent_before = connection.execute(text("SELECT count(*) FROM audit_outbox WHERE status = 'SENT'")).scalar_one()
    assert sent_before < len(ids)

    second = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            with clean_outbox.connect() as connection:
                pending = connection.execute(
                    text("SELECT count(*) FROM audit_outbox WHERE status = 'PENDING'")
                ).scalar_one()
            if pending == 0:
                break
            time.sleep(0.5)
    finally:
        second.terminate()
        second.wait(timeout=10)

    assert pending == 0
    delivered = _audit_events(admin_http, company, correlation_id=str(correlation), page=1)
    page2 = _audit_events(admin_http, company, correlation_id=str(correlation), page=2)
    event_ids = [item["event_id"] for item in delivered + page2]
    assert len(event_ids) == len(set(event_ids)) == 120


def test_rejected_event_does_not_block_others(clean_outbox, worker_settings, admin_http, company) -> None:
    correlation = uuid4()
    [existing] = _record(clean_outbox, _event(company, correlation_id=correlation))
    _drain(clean_outbox, worker_settings, cycles=1)

    # Un evento con el mismo event_id y otro contenido (error del emisor) → 409 de Audit.
    clashing = _event(company, event_id=existing, correlation_id=correlation, new_values={"status": "OTRO"})
    with clean_outbox.begin() as connection:
        connection.execute(
            text("UPDATE audit_outbox SET status = 'PENDING', sent_at = NULL, payload = CAST(:p AS jsonb) WHERE event_id = :id"),
            {"p": __import__("json").dumps(to_canonical_dict(clashing)), "id": existing},
        )
    others = _record(clean_outbox, *[_event(company, correlation_id=correlation) for _ in range(2)])

    worker = Worker(worker_settings, engine=clean_outbox)
    result = run_once(worker.engine, worker.client, worker_settings)

    assert result.rejected == [str(existing)]
    assert sorted(result.sent) == sorted(str(i) for i in others)
    assert _status(clean_outbox, existing) == "PENDING"
    assert len(_audit_events(admin_http, company, correlation_id=str(correlation))) == 3
