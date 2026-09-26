"""Prueba de los ejercicios de uso de docs/ejemplo/ (Principio XXII, puerta de calidad 11).

Verifica, contra la API y la base de pruebas:

- cada ejercicio en una base nueva y los cinco seguidos en la misma base (en ambos órdenes);
- el código de estado de cada llamada, incluidos los errores esperados;
- el permiso que exige cada URL, que ese permiso exista en la plantilla del realm, que cada usuario
  de prueba sin él reciba `403` y que los usuarios con lectura obtengan la respuesta en las consultas;
- que la documentación versionada sea exactamente la que generan esas ejecuciones;
- que no haya secretos y que los tokens se pidan con `KEYCLOAK_TEST_USER_PASSWORD`.

Para regenerar la documentación después de cambiar un ejercicio, un contrato o el realm:

    PRODUCT_CATALOG_EXAMPLES_WRITE=1 pytest tests/examples
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from product_catalog_service.seed.loader import load_seed
from tests.conftest import ApiClient, truncate_all
from tests.examples.exercises import EXERCISES
from tests.examples.render import render_exercise, render_general_document
from tests.examples.runner import NO_PERMISSIONS, run_exercise
from tests.examples.users import REALM_ROLES, REPO_ROOT, USERS

SERVICE_ROOT = Path(__file__).resolve().parents[2]
DOCS = SERVICE_ROOT / "docs" / "ejemplo"
EXAMPLES = Path(__file__).resolve().parent
HANDWRITTEN = {"README.md", "mapeo-campos-excel.md"}
PASSWORD_VARIABLE = "KEYCLOAK_TEST_USER_PASSWORD"
WRITE = os.environ.get("PRODUCT_CATALOG_EXAMPLES_WRITE") == "1"

# Resultados de las ejecuciones aisladas, para generar el documento general sin repetirlas.
_RESULTS: dict[int, tuple[dict, list]] = {}


# --------------------------------------------------------------------------- utilidades

def _clients(test_client, make_token):
    clients = {
        user["username"]: ApiClient(test_client, make_token(*user["roles"], sub=user["username"]))
        for user in USERS
    }
    clients[NO_PERMISSIONS] = ApiClient(test_client, make_token("sin-permisos", sub="sin-permisos"))
    return clients


def _seed(engine):
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        load_seed(session)


def _check_documents(documents):
    """Compara (o escribe, en modo regeneración) los documentos generados con los versionados."""
    stale = []
    for relative, content in documents.items():
        path = DOCS / relative
        if WRITE:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            continue
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current != content:
            stale.append(relative)
    assert not stale, (
        "docs/ejemplo/ no corresponde con lo que valida la prueba. Regenere con "
        f"PRODUCT_CATALOG_EXAMPLES_WRITE=1 pytest tests/examples. Archivos: {stale}"
    )


def _scanned_files():
    files = [path for path in DOCS.rglob("*.md")]
    files += [path for path in EXAMPLES.glob("*.py") if path.name != Path(__file__).name]
    return files


def _configured_password():
    value = os.environ.get(PASSWORD_VARIABLE, "").strip()
    env_file = REPO_ROOT / "infrastructure" / ".env"
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, content = line.partition("=")
            if separator and name.strip() == PASSWORD_VARIABLE:
                value = content.strip().strip('"').strip("'")
    return value or None


# --------------------------------------------------------------------------- ejecución

@pytest.mark.parametrize("index", range(len(EXERCISES)), ids=[ex["folder"] for ex in EXERCISES])
def test_exercise_runs_and_matches_documentation(
    api, test_engine, test_client, make_token, fake_manufacturer_directory, index
):
    """Ejercicio en una base nueva: respuestas, permisos por usuario y documentación."""
    _seed(test_engine)
    exercise = EXERCISES[index]
    ctx, records = run_exercise(api, fake_manufacturer_directory, exercise, _clients(test_client, make_token))
    _RESULTS[index] = (ctx, records)

    permissions = {record["permission"] for record in records if "permission" in record}
    assert permissions, "El ejercicio no registró permisos."
    missing = sorted(permissions - REALM_ROLES)
    assert not missing, f"Permisos que no existen en la plantilla del realm: {missing}"

    for record in records:
        if "access" in record:
            assert record["access"]["admin.test"], "admin.test debe poder ejecutar todo el ejercicio."

    _check_documents(render_exercise(exercise, ctx, records))


@pytest.mark.parametrize("order", ["forward", "reverse"])
def test_exercises_share_one_database(api, test_engine, fake_manufacturer_directory, order):
    """Los cinco ejercicios en la misma base: los registros compartidos se reutilizan, no chocan."""
    _seed(test_engine)
    exercises = EXERCISES if order == "forward" else list(reversed(EXERCISES))
    for exercise in exercises:
        run_exercise(api, fake_manufacturer_directory, exercise)


def test_general_permissions_document(api, test_engine, test_client, make_token, fake_manufacturer_directory):
    """`usuarios-y-permisos.md` corresponde con los permisos observados en los cinco ejercicios."""
    for index, exercise in enumerate(EXERCISES):
        if index not in _RESULTS:
            truncate_all(test_engine)
            _seed(test_engine)
            _RESULTS[index] = run_exercise(
                api, fake_manufacturer_directory, exercise, _clients(test_client, make_token)
            )

    _check_documents({"usuarios-y-permisos.md": render_general_document(
        [_RESULTS[index][1] for index in range(len(EXERCISES))]
    )})

    generated = {DOCS / exercise["folder"] for exercise in EXERCISES}
    folders = {path for path in DOCS.iterdir() if path.is_dir()}
    assert folders == generated, f"Carpetas de ejercicios sin prueba: {sorted(map(str, folders - generated))}"


# --------------------------------------------------------------------------- documentación

def test_documentation_has_no_secrets():
    jwt = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
    password_assignment = re.compile(r"password\s*[=:]\s*['\"]?([^\s'\"&|}]+)", re.IGNORECASE)
    password = _configured_password()

    problems = []
    for path in _scanned_files():
        text = path.read_text(encoding="utf-8")
        if jwt.search(text):
            problems.append(f"{path.name}: contiene un token JWT")
        if password and password in text:
            problems.append(f"{path.name}: contiene el valor de {PASSWORD_VARIABLE}")
        for match in password_assignment.finditer(text):
            if PASSWORD_VARIABLE not in match.group(1):
                problems.append(f"{path.name}: contraseña literal ({match.group(0)!r})")
    assert not problems, problems


def test_documentation_requests_tokens_with_password_variable():
    general = (DOCS / "usuarios-y-permisos.md").read_text(encoding="utf-8")
    readme = (DOCS / "README.md").read_text(encoding="utf-8")
    assert PASSWORD_VARIABLE in general and PASSWORD_VARIABLE in readme

    for exercise in EXERCISES:
        users = (DOCS / exercise["folder"] / "USUARIOS.md").read_text(encoding="utf-8")
        token_requests = users.count("openid-connect/token")
        assert token_requests > 0
        assert users.count(f"password=${PASSWORD_VARIABLE}") == token_requests, exercise["folder"]


def test_documentation_links_exist():
    link = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
    broken = []
    for path in DOCS.rglob("*.md"):
        for match in link.finditer(path.read_text(encoding="utf-8")):
            target = match.group(1)
            if not target.startswith("http") and not (path.parent / target).resolve().exists():
                broken.append(f"{path.relative_to(DOCS)} → {target}")
    assert not broken, broken


def test_handwritten_documents_exist():
    for name in HANDWRITTEN:
        assert (DOCS / name).is_file(), name
