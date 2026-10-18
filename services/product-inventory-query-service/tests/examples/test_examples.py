"""Prueba de los ejercicios de `docs/ejemplo/` (Principio XXII, puerta de calidad 11; T128).

Verifica, contra la API con OC, CR, PC e Inventory simulados (Principio IV):

- el estado de cada llamada, incluidos los errores esperados;
- el permiso de cada URL (leído del log de `sio-auth`), que exista en la plantilla del realm, que `compras`,
  `reportes` y `consulta` reciban `403` y que los usuarios con permiso obtengan su respuesta;
- que la documentación versionada sea exactamente la generada;
- que no haya secretos y que los tokens se pidan con variables de entorno.

Para regenerar la documentación tras cambiar un ejercicio, un contrato o el realm:

    PRODUCT_INVENTORY_QUERY_EXAMPLES_WRITE=1 pytest tests/examples
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from product_inventory_query_service.application.listing import Ports
from product_inventory_query_service.main import create_app
from tests.examples.exercises import COMMON_DATA, EXERCISES, seed
from tests.examples.render import render_exercise, render_general
from tests.examples.runner import NO_PERMISSIONS, run_exercise
from tests.examples.users import USERS
from tests.fakes import build_fakes

DOCS = Path(__file__).resolve().parents[2] / "docs" / "ejemplo"
HANDWRITTEN = {"README.md"}
WRITE = os.environ.get("PRODUCT_INVENTORY_QUERY_EXAMPLES_WRITE") == "1"
RESULTS: dict[int, list[dict]] = {}


class _Client:
    def __init__(self, client: TestClient, token: str) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"}

    def get(self, url: str):
        return self._client.get(url, headers=self._headers)


@pytest.fixture
def clients(test_settings, test_auth, make_token):
    fakes = build_fakes()
    seed(fakes)
    app = create_app(test_settings, auth=test_auth, jwks_probe=lambda: True,
                     ports_factory=lambda authorization: Ports(fakes.oc, fakes.cr, fakes.pc, fakes.inventory))
    with TestClient(app, raise_server_exceptions=False) as client:
        result = {
            user["username"]: _Client(client, make_token(*user["roles"], sub=user["username"],
                                                         preferred_username=user["username"]))
            for user in USERS
        }
        result[NO_PERMISSIONS] = _Client(client, make_token(sub="nadie", preferred_username="nadie"))
        yield result


@pytest.mark.parametrize("exercise", EXERCISES, ids=[e["folder"] for e in EXERCISES])
def test_exercise(exercise, clients) -> None:
    records = run_exercise(exercise, clients)
    RESULTS[exercise["number"]] = records
    files = render_exercise(exercise, records, COMMON_DATA)
    folder = DOCS / exercise["folder"]

    if WRITE:
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("*.md"):
            old.unlink()
        for name, content in files.items():
            (folder / name).write_text(content, encoding="utf-8", newline="\n")
        return

    assert sorted(path.name for path in folder.glob("*.md")) == sorted(files), "Archivos distintos"
    for name, content in files.items():
        assert (folder / name).read_text(encoding="utf-8") == content, f"{exercise['folder']}/{name} desactualizado"


def test_general_document() -> None:
    assert len(RESULTS) == len(EXERCISES), "Ejecute la prueba completa de tests/examples"
    content = render_general(RESULTS)
    path = DOCS / "usuarios-y-permisos.md"

    if WRITE:
        path.write_text(content, encoding="utf-8", newline="\n")
        return

    assert path.read_text(encoding="utf-8") == content, "usuarios-y-permisos.md desactualizado"


def test_no_unexpected_files() -> None:
    expected = HANDWRITTEN | {"usuarios-y-permisos.md"} | {exercise["folder"] for exercise in EXERCISES}
    assert {path.name for path in DOCS.iterdir()} == expected


def test_each_exercise_has_order_and_users() -> None:
    for exercise in EXERCISES:
        folder = DOCS / exercise["folder"]
        assert (folder / "ORDEN.md").is_file() and (folder / "USUARIOS.md").is_file()


def test_users_without_any_query_permission_get_403_in_every_step() -> None:
    """T128: `compras`, `reportes` y `consulta` reciben `403` en todos los pasos."""
    assert len(RESULTS) == len(EXERCISES), "Ejecute la prueba completa de tests/examples"
    for records in RESULTS.values():
        for record in records:
            for name in ("compras.test", "reportes.test", "consulta.test"):
                assert record["access"][name]["status"] == 403


SECRET_PATTERNS = (
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\."),  # JWT
    re.compile(r"password=(?!\"\$)", re.IGNORECASE),
    re.compile(r"client_secret=(?!\"\$)", re.IGNORECASE),
)


def test_no_secrets_in_documentation() -> None:
    for path in DOCS.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            assert not pattern.search(text), f"{path}: posible secreto"
    general = (DOCS / "usuarios-y-permisos.md").read_text(encoding="utf-8")
    assert "$KEYCLOAK_TEST_USER_PASSWORD" in general
