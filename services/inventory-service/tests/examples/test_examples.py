"""Prueba de los ejercicios de `docs/ejemplo/` (Principio XXII, puerta de calidad 11; T056).

Verifica, contra la API y la base de pruebas:

- cada ejercicio en una base nueva;
- el estado de cada llamada, incluidos los errores esperados;
- el permiso de cada URL (leído del log de `sio-auth`), que exista en la plantilla del realm, que
  cada usuario sin él reciba `403` y que los usuarios con lectura obtengan la respuesta;
- que la documentación versionada sea exactamente la generada;
- que no haya secretos y que los tokens se pidan con variables de entorno.

Operational Context y Commercial Relationship no se ejecutan (Principio IV): los sustituyen sus
dobles, con los datos ficticios de los ejercicios y todos los usuarios de prueba como miembros.

Para regenerar la documentación tras cambiar un ejercicio, un contrato o el realm:

    INVENTORY_EXAMPLES_WRITE=1 pytest tests/examples
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import UUID

import pytest

from tests.conftest import truncate_all
from tests.examples.exercises import ACEITE, ARROZ, BRANCH, BRANCH_B, COMPANY, EXERCISES, SERVICIO, USER
from tests.examples.render import render_exercise, render_general
from tests.examples.runner import NO_PERMISSIONS_HUMAN, NO_PERMISSIONS_SERVICE, OPERATOR, WILDCARD_SERVICE, run_exercise
from tests.examples.users import OPERATOR as OPERATOR_CLIENT
from tests.examples.users import OPERATOR_ROLES, OPERATOR_SUB, USERS

DOCS = Path(__file__).resolve().parents[2] / "docs" / "ejemplo"
HANDWRITTEN = {"README.md"}
WRITE = os.environ.get("INVENTORY_EXAMPLES_WRITE") == "1"
RESULTS: dict[int, list[dict]] = {}


class _Client:
    def __init__(self, client, token: str) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"}

    def request(self, method: str, url: str, **kwargs):
        return self._client.request(method, url, headers=self._headers, **kwargs)


@pytest.fixture
def clients(test_client, make_token, fake_oc, fake_cr):
    company = UUID(COMPANY)
    fake_oc.add_branch(company, branch_id=UUID(BRANCH))
    fake_oc.add_branch(company, branch_id=UUID(BRANCH_B))  # 013: sin usuarios asignados
    fake_oc.add_user(company, user_id=UUID(USER))
    fake_cr.add_product(company, product_id=UUID(ARROZ))
    fake_cr.add_product(company, product_id=UUID(ACEITE))
    fake_cr.add_product(company, product_id=UUID(SERVICIO), inventory_control_enabled=False)

    result = {}
    for index, user in enumerate(USERS, start=1):
        name = user["username"]
        fake_oc.add_member(name, company)
        # 013: usuario operativo fijo de cada usuario de prueba (documentación estable) y asignación
        # a la sucursal principal (ajustes y conteos la exigen).
        operator_user = UUID(f"d44c0000-0000-4000-8000-{100 + index:012d}")
        fake_oc.member_users[(name, company)] = operator_user
        fake_oc.add_user(company, user_id=operator_user)
        fake_oc.assign(name, UUID(BRANCH))
        result[name] = _Client(test_client, make_token(*user["roles"], sub=name, preferred_username=name))
    result[OPERATOR] = _Client(
        test_client,
        make_token(*OPERATOR_ROLES, sub=OPERATOR_SUB, preferred_username=f"service-account-{OPERATOR_CLIENT}", client_id=OPERATOR_CLIENT),
    )
    result[NO_PERMISSIONS_SERVICE] = _Client(
        test_client, make_token(sub="sin-permisos", preferred_username="service-account-sin-permisos", client_id="sin-permisos")
    )
    result[NO_PERMISSIONS_HUMAN] = _Client(test_client, make_token(sub="nadie", preferred_username="nadie"))
    result[WILDCARD_SERVICE] = _Client(
        test_client,
        make_token("perm:all:all:all", sub="comodin", preferred_username="service-account-comodin", client_id="comodin"),
    )
    return result


@pytest.mark.parametrize("exercise", EXERCISES, ids=[e["folder"] for e in EXERCISES])
def test_exercise(exercise, clients, test_engine) -> None:
    truncate_all(test_engine)
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
    assert "$INVENTORY_TEST_OPERATOR_CLIENT_SECRET" in general
