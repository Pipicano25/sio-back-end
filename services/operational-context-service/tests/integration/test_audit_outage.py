"""Entrega confiable con Audit detenido (feature 016; H1, H2; RC-02, RC-03, RC-04; SC-003; T068).

Dos escenarios separados (H1):

- caída corta (< 30 s): la operación responde igual; el evento queda `PENDING`; al levantar Audit se
  entrega una sola vez en menos de 1 minuto;
- caída prolongada (varios minutos, para que el backoff por evento llegue al tope): entrega única a
  más tardar `AUDIT_OUTBOX_BACKOFF_MAX_SECONDS` + 60 s después de levantar Audit. El valor se lee de la
  configuración del worker; la política de `libs/sio-audit` no cambia.

En ambos se reinicia el worker con pendientes (retoma) y la historia se reconstruye por `occurred_at`:
nunca se exige el orden de llegada (H2). Detiene `sio-audit-service` y lo vuelve a iniciar.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest

from tests.integration.test_audit_delivery import AUDIT, _history, member  # noqa: F401
from tests.integration.test_real_dependencies import (  # noqa: F401 (fixtures)
    OPERATIONAL_CONTEXT,
    RUN_ID,
    client,
    company_id,
    geography,
    organization_id,
    person_id,
)

BRANCH_FIELDS = ("code", "email", "phone", "address_line", "country_id", "administrative_division_id", "city_id",
                 "postal_code", "latitude", "longitude", "timezone", "version")


@pytest.fixture(scope="module")
def writer(client, company_id, member):
    sequence = iter(range(1000))

    def _write(count: int):
        created = client.post(f"{OPERATIONAL_CONTEXT}/api/v1/companies/{company_id}/branches", json={
            "code": f"OUT-{RUN_ID}-{next(sequence)}", "name": "Sucursal de caída (dato ficticio)"})
        assert created.status_code == 201, created.text
        current = created.json()
        for index in range(count - 1):
            body = {key: current[key] for key in BRANCH_FIELDS}
            updated = client.put(f"{OPERATIONAL_CONTEXT}/api/v1/branches/{current['id']}",
                                 json={**body, "name": f"Sucursal de caída {index} (dato ficticio)"})
            assert updated.status_code == 200, updated.text
            current = updated.json()
        return "Branch", current["id"], lambda: _history(client, company_id, "Branch", current["id"])

    return _write

pytestmark = pytest.mark.integration

AUDIT_CONTAINER = "sio-audit-service"
WORKER = "sio-operational-context-audit-outbox-worker"
DB_CONTAINER = "sio-operational-context-db"


def _docker(*args: str) -> str:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=True).stdout.strip()


TOKEN_URL = "http://127.0.0.1:8081/realms/sio/protocol/openid-connect/token"
ENV_FILE = Path(__file__).resolve().parents[4] / "infrastructure" / ".env"


def _renew_token(client) -> None:
    """La prueba dura más que el token del usuario: se renueva mientras se espera la entrega."""
    password = os.environ.get("KEYCLOAK_TEST_USER_PASSWORD", "").strip()
    if not password and ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "KEYCLOAK_TEST_USER_PASSWORD":
                password = value.strip()
    token = httpx.post(TOKEN_URL, data={"grant_type": "password", "client_id": "sio-web", "scope": "openid",
                                        "username": "admin.test", "password": password}, timeout=15).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"


def _backoff_max() -> float:
    env = _docker("inspect", "-f", "{{range .Config.Env}}{{println .}}{{end}}", WORKER)
    for line in env.splitlines():
        if line.startswith("AUDIT_OUTBOX_BACKOFF_MAX_SECONDS="):
            return float(line.split("=", 1)[1])
    return 300.0


def _pending(entity_id: str) -> int:
    sql = f"SELECT count(*) FROM audit_outbox WHERE status = 'PENDING' AND payload->>'entity_id' = '{entity_id}'"
    out = _docker("exec", DB_CONTAINER, "sh", "-c", f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "{sql}"')
    return int(out or 0)


def _audit_up() -> bool:
    try:
        return httpx.get(f"{AUDIT.removesuffix('/api/v1')}/health/ready", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def _outage(writer, seconds: float, writes: int = 2):
    _docker("stop", AUDIT_CONTAINER)
    try:
        started = time.monotonic()
        entity_type, entity_id, history = writer(writes)
        time.sleep(3)
        assert _pending(entity_id) >= writes  # la operación respondió y el evento quedó pendiente
        _docker("restart", WORKER)  # reinicio con pendientes: retoma (RC-03)
        remaining = seconds - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)
    finally:
        _docker("start", AUDIT_CONTAINER)
    deadline = time.monotonic() + 120
    while not _audit_up():
        assert time.monotonic() < deadline, "Audit no volvió"
        time.sleep(2)
    return entity_type, entity_id, history, time.monotonic()


def _delivered(client, history, entity_id: str, writes: int, back_at: float, limit: float) -> float:
    renewed = 0.0
    while True:
        if time.monotonic() - renewed > 120:
            _renew_token(client)
            renewed = time.monotonic()
        items = history()
        if len(items) >= writes and _pending(entity_id) == 0:
            elapsed = time.monotonic() - back_at
            break
        assert time.monotonic() - back_at < limit, f"Sin entrega completa en {limit:.0f} s"
        time.sleep(2)
    time.sleep(5)
    _renew_token(client)
    items = history()
    assert len(items) == writes and len({e["event_id"] for e in items}) == writes  # una sola vez
    occurred = [e["occurred_at"] for e in items]
    assert occurred == sorted(occurred)  # reconstrucción por occurred_at (H2)
    return elapsed


@pytest.fixture(scope="module", autouse=True)
def audit_running():
    if not _audit_up():
        pytest.skip("audit-service no disponible.")


def test_short_outage_delivers_once_in_less_than_a_minute(client, writer) -> None:
    _, entity_id, history, back_at = _outage(writer, seconds=20)
    elapsed = _delivered(client, history, entity_id, 2, back_at, limit=60)
    print(f"\ncaída corta: entrega completa {elapsed:.1f} s después de levantar Audit")


def test_long_outage_delivers_once_within_backoff_max_plus_60(client, writer) -> None:
    limit = _backoff_max() + 60
    _, entity_id, history, back_at = _outage(writer, seconds=420)
    elapsed = _delivered(client, history, entity_id, 2, back_at, limit=limit)
    print(f"\ncaída prolongada: entrega completa {elapsed:.1f} s después de levantar Audit (límite {limit:.0f} s)")
