"""Prueba de los ejercicios de `docs/ejemplo/` (Principio XXII, puerta de calidad 11).

Ejecuta los ejercicios contra la API con las dependencias simuladas, verifica estados y permisos por usuario y que
la documentación versionada sea exactamente la generada. Para regenerarla:

    BUSINESS_REPORTING_EXAMPLES_WRITE=1 pytest tests/examples
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from business_reporting_service.main import create_app
from tests.conftest import NOW
from tests.examples.exercises import COMMON_DATA, EXERCISES, seed
from tests.examples.render import render_exercise, render_general
from tests.examples.runner import NO_PERMISSIONS, run_exercise
from tests.examples.users import USERS
from tests.fakes import build_fakes

DOCS = Path(__file__).resolve().parents[2] / "docs" / "ejemplo"
HANDWRITTEN = {"README.md"}
WRITE = os.environ.get("BUSINESS_REPORTING_EXAMPLES_WRITE") == "1"
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
    app = create_app(test_settings, auth=test_auth, jwks_probe=lambda: True, ports_factory=fakes.ports_for,
                     clock=lambda: NOW)
    with TestClient(app, raise_server_exceptions=False) as client:
        result = {user["username"]: _Client(client, make_token(*user["roles"], sub=f"sub-{user['username']}",
                                                               preferred_username=user["username"])) for user in USERS}
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


def test_reportes_never_receives_costs() -> None:
    assert len(RESULTS) == len(EXERCISES), "Ejecute la prueba completa de tests/examples"
    text = str(RESULTS).lower()
    for word in ("unit_cost", "movement_value", "cost_of_goods", "gross_margin", "inventory_value"):
        assert word not in text


SECRET_PATTERNS = (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\."), re.compile(r"password=(?!\"\$)", re.IGNORECASE))


def test_no_secrets_in_documentation() -> None:
    for path in DOCS.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            assert not pattern.search(text), f"{path}: posible secreto"
