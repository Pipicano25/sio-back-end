"""Prueba de los ejercicios de `docs/ejemplo/` (Principio XXII, puerta de calidad 11; T074).

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

    SALES_EXAMPLES_WRITE=1 pytest tests/examples
"""

from __future__ import annotations

import os
import re
from decimal import Decimal
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
WRITE = os.environ.get("SALES_EXAMPLES_WRITE") == "1"
RESULTS: dict[int, list[dict]] = {}


def fixed_world() -> World:
    return World(
        company=UUID(data.COMPANY),
        other_company=UUID(data.OTHER_COMPANY),
        branch=UUID(data.BRANCH),
        branch_b=UUID(data.BRANCH_B),
        customer=UUID(data.CUSTOMER),
        customer_org=UUID(data.CUSTOMER_ORG),
        person=UUID(data.PERSON),
        organization=UUID(data.ORGANIZATION),
        product=UUID(data.ARROZ),
        product_2=UUID(data.ACEITE),
        product_no_inventory=UUID(data.SERVICIO),
        global_product=UUID(data.GLOBAL_ARROZ),
        global_product_2=UUID(data.GLOBAL_ACEITE),
        presentation=UUID(data.CAJA),
        global_presentation=UUID(data.GLOBAL_CAJA),
        unit=UUID(data.UNIT),
        price_list=UUID(data.LISTA),
        price_list_2=UUID(data.LISTA_2),
        item_box=UUID(data.ITEM_CAJA),
        item_product_2=UUID(data.ITEM_ACEITE),
        unit_presentation=UUID(data.UNIDAD_ARROZ),
        unit_presentation_2=UUID(data.UNIDAD_ACEITE),
        unit_presentation_ni=UUID(data.UNIDAD_SERVICIO),
        global_unit=UUID(data.GLOBAL_UNIDAD_ARROZ),
        global_unit_2=UUID(data.GLOBAL_UNIDAD_ACEITE),
        default_list=UUID(data.LISTA_GENERAL),
        item_unit=UUID(data.ITEM_UNIDAD_ARROZ),
        item_unit_2=UUID(data.ITEM_UNIDAD_ACEITE),
        item_unit_ni=UUID(data.ITEM_UNIDAD_SERVICIO),
        item_box_default=UUID(data.ITEM_CAJA_GENERAL),
    )


@pytest.fixture
def fakes():
    """Sustituye el doble general por uno con identificadores fijos (documentación estable)."""
    built = build_fakes(fixed_world())
    for index, user in enumerate(USERS, start=1):
        built.oc.add_member(
            user["username"], built.world.company, branches=(built.world.branch,), user_id=UUID(f"d15f1000-0000-4000-8000-{index:012d}")
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
        elif change.startswith("price:"):
            world = fakes.world  # spec 019: precio de la unidad de arroz en la predeterminada, con id fijo
            fakes.cr.set_price(world.default_list, world.product, world.unit_presentation, change.split(":", 1)[1],
                               item=UUID(data.ITEM_UNIDAD_ARROZ_NUEVO))
        elif change.startswith("stock:"):
            fakes.inventory.layers.pop((str(fakes.world.branch), str(fakes.world.product)), None)
            fakes.inventory.stock(fakes.world.branch, fakes.world.product, change.split(":", 1)[1], "1000")
        elif change.startswith("unknown_cost:"):
            fakes.inventory.layers.pop((str(fakes.world.branch), str(fakes.world.product)), None)
            fakes.inventory.stock(fakes.world.branch, fakes.world.product, change.split(":", 1)[1], "0", known=False)
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
