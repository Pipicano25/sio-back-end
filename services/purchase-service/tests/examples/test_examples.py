"""Prueba de los ejercicios de `docs/ejemplo/` (Principio XXII, puerta de calidad 11; T068).

Verifica, contra la API y la base de pruebas:

- cada ejercicio en una base nueva, con reloj e identificadores fijos;
- el estado de cada llamada, incluidos los errores esperados;
- el permiso de cada URL (leído del log de `sio-auth`), que exista en la plantilla del realm, que
  cada usuario sin él reciba `403`, que una cuenta de servicio con comodín reciba `403` en las
  escrituras y que los usuarios con lectura obtengan la respuesta;
- que la documentación versionada sea exactamente la generada;
- que no haya secretos y que los tokens se pidan con variables de entorno.

Las dependencias no se ejecutan (Principio IV): las sustituyen sus dobles con los datos ficticios
de los ejercicios y todos los usuarios de prueba como miembros asignados a la sucursal principal.

Para regenerar la documentación tras cambiar un ejercicio, un contrato o el realm:

    PURCHASE_EXAMPLES_WRITE=1 pytest tests/examples
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import UUID

import pytest

from tests.conftest import truncate_all
from tests.examples import exercises as data
from tests.examples.exercises import EXERCISES, NOW
from tests.examples.render import render_exercise, render_general
from tests.examples.runner import NO_PERMISSIONS_HUMAN, WILDCARD_SERVICE, run_exercise
from tests.examples.users import USERS
from tests.fakes import World, build_fakes

DOCS = Path(__file__).resolve().parents[2] / "docs" / "ejemplo"
HANDWRITTEN = {"README.md"}
WRITE = os.environ.get("PURCHASE_EXAMPLES_WRITE") == "1"
RESULTS: dict[int, list[dict]] = {}


def fixed_world() -> World:
    return World(
        company=UUID(data.COMPANY),
        other_company=UUID(data.OTHER_COMPANY),
        branch=UUID(data.BRANCH),
        branch_b=UUID(data.BRANCH_B),
        supplier=UUID(data.SUPPLIER),
        organization=UUID(data.ORGANIZATION),
        condition=UUID(data.CONDITION),
        credit_type=UUID(data.CREDIT_TYPE),
        product=UUID(data.ARROZ),
        product_2=UUID(data.ACEITE),
        product_no_inventory=UUID(data.SERVICIO),
        global_product=UUID(data.GLOBAL_ARROZ),
        global_product_2=UUID(data.GLOBAL_ACEITE),
        presentation=UUID(data.CAJA),
        global_presentation=UUID(data.GLOBAL_CAJA),
        supplier_product=UUID(data.SUPPLIER_PRODUCT),
        unit=UUID(data.UNIT),
    )


@pytest.fixture
def fakes():
    """Sustituye el doble general por uno con identificadores fijos (documentación estable)."""
    built = build_fakes(fixed_world())
    for index, user in enumerate(USERS, start=1):
        built.oc.add_member(
            user["username"], built.world.company, branches=(built.world.branch,), user_id=UUID(f"d14f1000-0000-4000-8000-{index:012d}")
        )
    return built


class _Client:
    def __init__(self, client, token: str) -> None:
        self._client = client
        self._headers = {"Authorization": f"Bearer {token}"}

    def request(self, method: str, url: str, **kwargs):
        headers = {**self._headers, **kwargs.pop("headers", {})}
        return self._client.request(method, url, headers=headers, **kwargs)


@pytest.fixture
def clients(test_client, make_token, clock):
    clock.fixed = NOW
    clock.ticking = True  # como en producción, cada modificación registra un momento distinto
    result = {
        user["username"]: _Client(test_client, make_token(*user["roles"], sub=user["username"], preferred_username=user["username"]))
        for user in USERS
    }
    result[NO_PERMISSIONS_HUMAN] = _Client(test_client, make_token(sub="nadie", preferred_username="nadie"))
    result[WILDCARD_SERVICE] = _Client(
        test_client,
        make_token("perm:all:all:all", sub="comodin", preferred_username="service-account-comodin", client_id="comodin"),
    )
    return result


def before_hook(fakes):
    def apply(change: str, ctx: dict) -> None:
        if change == "inventory_down":
            fakes.inventory.availability.down = True
        elif change == "inventory_up":
            fakes.inventory.availability.down = False
        elif change.startswith("consume:"):
            fakes.inventory.consumed.add(UUID(str(ctx[change.split(":", 1)[1]])))
        else:
            raise AssertionError(f"Cambio desconocido: {change}")

    return apply


@pytest.mark.parametrize("exercise", EXERCISES, ids=[e["folder"] for e in EXERCISES])
def test_exercise(exercise, clients, fakes, test_engine) -> None:
    truncate_all(test_engine)
    records = run_exercise(exercise, clients, before_hook(fakes))
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
    assert "$KEYCLOAK_TEST_USER_PASSWORD" in (DOCS / "usuarios-y-permisos.md").read_text(encoding="utf-8")
