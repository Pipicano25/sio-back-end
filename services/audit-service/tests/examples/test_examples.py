"""Prueba de los ejercicios de `docs/ejemplo/` (Principio XXII, puerta de calidad 11; T062).

Verifica, contra la API y la base de pruebas:

- cada ejercicio en una base nueva;
- el estado de cada llamada, incluidos los errores esperados;
- el permiso de cada URL (leído del log de `sio-auth`), que exista en la plantilla del realm, que
  cada usuario sin él reciba `403` y que los usuarios con lectura obtengan la respuesta;
- que la documentación versionada sea exactamente la generada;
- que no haya secretos y que los tokens se pidan con variables de entorno.

Operational Context no se ejecuta (Principio IV): lo sustituye su doble, con todos los usuarios de
prueba como miembros de la empresa de los ejercicios.

Para regenerar la documentación tras cambiar un ejercicio, un contrato o el realm:

    AUDIT_EXAMPLES_WRITE=1 pytest tests/examples
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import UUID

import pytest

from tests.conftest import CREATE, truncate_audit_events
from tests.examples.exercises import COMPANY, EXERCISES
from tests.examples.render import render_exercise, render_general
from tests.examples.runner import EMITTER, NO_PERMISSIONS_HUMAN, NO_PERMISSIONS_SERVICE, run_exercise
from tests.examples.users import USERS

DOCS = Path(__file__).resolve().parents[2] / "docs" / "ejemplo"
HANDWRITTEN = {"README.md"}
WRITE = os.environ.get("AUDIT_EXAMPLES_WRITE") == "1"
RESULTS: dict[int, list[dict]] = {}


class _Client:
    def __init__(self, client, token: str) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"}

    def request(self, method: str, url: str, **kwargs):
        return self._client.request(method, url, headers=self._headers, **kwargs)


@pytest.fixture
def clients(test_client, make_token, service_token, fake_oc):
    result = {}
    for user in USERS:
        name = user["username"]
        fake_oc.add_member(name, UUID(COMPANY))
        result[name] = _Client(test_client, make_token(*user["roles"], sub=name, preferred_username=name))
    result[EMITTER] = _Client(test_client, service_token(CREATE))
    result[NO_PERMISSIONS_SERVICE] = _Client(test_client, service_token(client_id="sin-permisos"))
    result[NO_PERMISSIONS_HUMAN] = _Client(test_client, make_token(sub="nadie", preferred_username="nadie"))
    return result


@pytest.mark.parametrize("exercise", EXERCISES, ids=[e["folder"] for e in EXERCISES])
def test_exercise(exercise, clients, test_engine) -> None:
    truncate_audit_events(test_engine)
    records = run_exercise(exercise, clients)
    RESULTS[exercise["number"]] = records

    files = render_exercise(exercise, records)
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
    assert "$AUDIT_TEST_EMITTER_CLIENT_SECRET" in general
