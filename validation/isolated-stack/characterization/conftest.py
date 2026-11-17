"""Caracterización extremo a extremo de la spec 025 en la pila aislada (T011).

Uso, desde la raíz y con la pila levantada (``stack.sh levantar``):

    eval "$(bash validation/isolated-stack/stack.sh entorno)"
    # 1. grabar con las lecturas de hoy (http)
    SIO_CHARACTERIZATION_RECORD=1 services/product-catalog-service/.venv/bin/pytest \\
        validation/isolated-stack/characterization -p no:cacheprovider -q
    # 2. reproducir con las lecturas por contrato
    bash validation/isolated-stack/stack.sh lecturas contract
    services/product-catalog-service/.venv/bin/pytest validation/isolated-stack/characterization -p no:cacheprovider -q

Antes de la primera solicitud exige ``SIO_TEST_TARGET=isolated`` y pasa todas las URL por
``validation/isolation_guard.py``. Los tokens se piden a Keycloak de la pila con las contraseñas de su ``.env``
y nunca se imprimen.
"""

from __future__ import annotations

import importlib.util
import secrets
import sys
import time
from pathlib import Path

import httpx
import pytest

HERE = Path(__file__).resolve().parent
STACK = HERE.parent
REPO = STACK.parents[1]
sys.path.insert(0, str(HERE))

from support import OUTAGES, CaseBook, read_source  # noqa: E402

URLS = {
    "keycloak": "http://127.0.0.1:18081/realms/sio/protocol/openid-connect/token",
    "geography": "http://127.0.0.1:18102",
    "party_identity": "http://127.0.0.1:18101/api/v1",
    "operational_context": "http://127.0.0.1:18104/api/v1",
    "product_catalog": "http://127.0.0.1:18103/api/v1",
    "commercial_relationship": "http://127.0.0.1:18106/api/v1",
    "payment_reference": "http://127.0.0.1:18105",
    "inventory": "http://127.0.0.1:18109/api/v1",
    "purchase": "http://127.0.0.1:18107/api/v1",
    "sales": "http://127.0.0.1:18108/api/v1",
    "audit": "http://127.0.0.1:18110/api/v1",
    "product_inventory_query": "http://127.0.0.1:18112/api/v1",
    "business_reporting": "http://127.0.0.1:18113/api/v1",
}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def guard():
    module = _load("sio_isolation_guard", REPO / "validation" / "isolation_guard.py")
    module.check_targets(URLS)  # falla antes de escribir si algún destino no es sio-it-*
    return module


@pytest.fixture(scope="session")
def seed(guard):
    """Ayudas de ``seed.py`` (empresas y miembros ficticios); se usan con su propio sufijo de ejecución."""
    return _load("sio_it_seed", STACK / "seed.py")


@pytest.fixture(scope="session")
def stack_env(seed):
    return seed.isolated_env()


@pytest.fixture(scope="session")
def run_id() -> str:
    return secrets.token_hex(3).upper()


@pytest.fixture(scope="session")
def users(stack_env, guard):
    """Clientes HTTP por usuario de prueba, con renovación del token."""
    clients: dict[str, httpx.Client] = {}

    def get(username: str) -> httpx.Client:
        if username not in clients:
            clients[username] = _user_client(stack_env, username)
        return clients[username]

    yield get
    for client in clients.values():
        client.close()


class _Token(httpx.Auth):
    def __init__(self, data: dict) -> None:
        self._data, self._token, self._expires = data, None, 0.0

    def auth_flow(self, request):
        if self._token is None or time.monotonic() > self._expires - 30:
            response = httpx.post(URLS["keycloak"], data=self._data, timeout=20)
            if response.status_code != 200:
                raise RuntimeError(f"Keycloak de la pila respondió {response.status_code} al pedir el token.")
            body = response.json()
            self._token, self._expires = body["access_token"], time.monotonic() + float(body.get("expires_in", 300))
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


def _user_client(env: dict, username: str) -> httpx.Client:
    return httpx.Client(
        auth=_Token(
            {
                "grant_type": "password",
                "client_id": "sio-web",
                "scope": "openid",
                "username": username,
                "password": env["KEYCLOAK_TEST_USER_PASSWORD"],
            }
        ),
        timeout=60,
    )


@pytest.fixture(scope="session")
def reads():
    """Fuente de lectura vigente en la pila (http o contract), tomada del contenedor de Sales."""
    return read_source("sio-it-sales-service", "OPERATIONAL_CONTEXT_READ_SOURCE")


@pytest.fixture(scope="module")
def book(request, reads):
    module = Path(request.module.__file__).stem
    case_book = CaseBook(module)
    if case_book.record and reads != "http":
        pytest.fail("La caracterización se graba con las lecturas de hoy: stack.sh lecturas http")
    yield case_book
    case_book.save(source=reads)


outages_only = pytest.mark.skipif(
    not OUTAGES, reason="Caídas opcionales (T079): definir SIO_CHARACTERIZATION_OUTAGES=1; cortan las bases de la pila.")


@pytest.fixture(scope="module")
def outage_book(request, reads):
    """Casos de caída del módulo, en ``cases/<módulo>_caidas.json`` (se graban con http y se comparan con contract)."""
    case_book = CaseBook(Path(request.module.__file__).stem + "_caidas")
    if case_book.record and reads != "http":
        pytest.fail("La caracterización se graba con las lecturas de hoy: stack.sh lecturas http")
    yield case_book
    case_book.save(source=reads)


def expect(response: httpx.Response, *statuses: int) -> dict:
    """Respuesta esperada al preparar datos; si no, detiene la prueba sin mostrar cabeceras."""
    if response.status_code not in (statuses or (200, 201)):
        raise AssertionError(
            f"{response.request.method} {response.request.url.path} → {response.status_code}: {response.text[:300]}"
        )
    return response.json() if response.content else {}
