"""Prueba de los ejercicios de docs/ejemplo/ (Principio XXII, puerta de calidad 11).

Verifica, contra la API y la base de pruebas:

- cada ejercicio en una base nueva y todos seguidos en la misma base (en ambos órdenes);
- el código de estado de cada llamada, incluidos los errores esperados;
- el permiso que exige cada URL, que ese permiso exista en la plantilla del realm, que cada
  usuario de prueba sin él reciba `403` y que los usuarios con lectura obtengan la respuesta;
- que la documentación versionada sea exactamente la que generan esas ejecuciones;
- que no haya secretos y que los tokens se pidan con `KEYCLOAK_TEST_USER_PASSWORD`.

Operational Context, Product Catalog, Party Identity y Payment Reference no se ejecutan (Principio IV): los
sustituyen los dobles de sus puertos, cargados con los identificadores de `spec_common.py`.
Todos los usuarios de prueba son miembros de las empresas de los ejercicios.

Para regenerar la documentación después de cambiar un ejercicio, un contrato o el realm:

    COMMERCIAL_RELATIONSHIP_EXAMPLES_WRITE=1 pytest tests/examples
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from commercial_relationship_service.application.automatic_price_application_service import (
    AutomaticPriceApplicationService,
)
from commercial_relationship_service.application.ports import PaymentConditionTypeRef
from commercial_relationship_service.audit_context import AuditActor, reset_actor, set_actor
from commercial_relationship_service.infrastructure.pricing_repositories import AutomaticPricingRepository
from commercial_relationship_service.price_worker import WORKER_ACTOR, WORKER_USERNAME, run_cycle
from tests.conftest import ApiClient, truncate_all
from tests.examples import spec_common
from tests.examples.exercises import EXERCISES
from tests.examples.render import data_file, render_exercise, render_general_document
from tests.examples.runner import NO_PERMISSIONS, run_exercise
from tests.examples.users import REALM_ROLES, REPO_ROOT, USERS

SERVICE_ROOT = Path(__file__).resolve().parents[2]
DOCS = SERVICE_ROOT / "docs" / "ejemplo"
EXAMPLES = Path(__file__).resolve().parent
HANDWRITTEN = {"README.md", "mapeo-campos-excel.md"}
PASSWORD_VARIABLE = "KEYCLOAK_TEST_USER_PASSWORD"
WRITE = os.environ.get("COMMERCIAL_RELATIONSHIP_EXAMPLES_WRITE") == "1"

_RESULTS: dict[int, tuple[dict, list]] = {}


# --------------------------------------------------------------------------- utilidades

@pytest.fixture(autouse=True)
def external_data(fake_oc, fake_catalog, fake_party, fake_payment):
    """Carga en los dobles los identificadores de los ejercicios (llamadas externas simuladas)."""
    for company_id, organization_id in spec_common.COMPANIES.items():
        fake_oc.organizations[UUID(company_id)] = UUID(organization_id)
        for user in USERS:
            fake_oc.add_member(user["username"], UUID(company_id))
    for product_id, (status, eligible) in spec_common.GLOBAL_PRODUCTS.items():
        fake_catalog.add(UUID(product_id), status=status, eligible=eligible)
    for person_id, status in spec_common.PERSONS.items():
        fake_party.persons[UUID(person_id)] = status
    for organization_id, status in spec_common.ORGANIZATIONS.items():
        fake_party.organizations[UUID(organization_id)] = status
    for contact_id, (organization_id, active) in spec_common.CONTACTS.items():
        fake_party.add_contact(UUID(contact_id), UUID(organization_id), is_active=active)
    for organization_id, name in spec_common.COMPANY_NAMES.items():
        fake_party.names[UUID(organization_id)] = name
    # Fase B: presentaciones globales, unidades base y tipos de condición de pago.
    for presentation_id, (product_id, status, eligible) in spec_common.GLOBAL_PRESENTATIONS.items():
        fake_catalog.add_presentation(UUID(presentation_id), UUID(product_id), status=status, eligible=eligible)
    for product_id, unit_id in spec_common.BASE_UNITS.items():
        fake_catalog.base_units[UUID(product_id)] = UUID(unit_id)
    for type_id, (code, status) in spec_common.CONDITION_TYPES.items():
        fake_payment.types[UUID(type_id)] = PaymentConditionTypeRef(id=UUID(type_id), code=code, status=status)


@pytest.fixture
def processes(test_client, service_token, test_engine):
    """Procesos automáticos de los ejercicios (spec 021): la entrega de Purchase y el worker de precios."""
    purchase = ApiClient(test_client, service_token(
        "perm:commercial-relationship:automatic_price_update_requests:submit", client_id="purchase-service"))

    def recepcion(company, product, presentation, purchase_id, purchase_detail_id, sequence, line_total, quantity,
                  previous=None, fail=False):
        body = {
            "contract_version": 1, "purchase_detail_id": purchase_detail_id, "purchase_id": purchase_id,
            "branch_id": spec_common.SEDE_EJ9, "company_product_id": product,
            "company_product_presentation_id": presentation, "sequence": sequence,
            "previous_sequence": sequence - 1 if sequence > 1 else None, "currency_code": "COP",
            "line_total": line_total, "quantity": quantity,
            "previous_purchase_detail_id": spec_common.DETALLE_EJ9_1 if previous else None,
            "previous_line_total": previous[0] if previous else None,
            "previous_quantity": previous[1] if previous else None,
            "received_at": datetime.now(UTC).isoformat(), "received_by_user_id": spec_common.RECIBIO_EJ9,
        }
        response = purchase.post(f"/api/v1/companies/{company}/automatic-price-update-requests", json=body)
        assert response.status_code == 202, response.text
        [application] = response.json()["applications"]
        if fail:  # falla simulada con una espera larga: no se reintenta durante el ejercicio
            token = set_actor(AuditActor(WORKER_ACTOR, WORKER_USERNAME))
            try:
                with Session(test_engine, expire_on_commit=False) as session:
                    AutomaticPriceApplicationService(
                        AutomaticPricingRepository(session), interval_seconds=3600, max_backoff_seconds=3600
                    ).fail(UUID(application["id"]), RuntimeError("Falla simulada en el ejercicio"))
            finally:
                reset_actor(token)
        else:
            while run_cycle(test_engine, batch_size=50, max_backoff_seconds=300, interval_seconds=0.01).processed:
                pass
        with test_engine.connect() as connection:
            row = connection.execute(
                text("SELECT status, new_price, last_error_code FROM automatic_price_applications WHERE id = :id"),
                {"id": application["id"]},
            ).mappings().one()
        price = None if row["new_price"] is None else format(Decimal(row["new_price"]).quantize(Decimal("0.01")), "f")
        return {"status": row["status"], "new_price": price, "last_error_code": row["last_error_code"]}

    return {"recepcion": recepcion}


def _token(make_token, user):
    return make_token(*user["roles"], sub=user["username"], preferred_username=user["username"])


@pytest.fixture
def api(test_client, make_token):
    admin = next(user for user in USERS if user["username"] == "admin.test")
    return ApiClient(test_client, _token(make_token, admin))


def _clients(test_client, make_token):
    clients = {user["username"]: ApiClient(test_client, _token(make_token, user)) for user in USERS}
    clients[NO_PERMISSIONS] = ApiClient(test_client, make_token("sin-permisos", sub="sin-permisos"))
    return clients


def _check_documents(documents):
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
        f"COMMERCIAL_RELATIONSHIP_EXAMPLES_WRITE=1 pytest tests/examples. Archivos: {stale}"
    )


def _scanned_files():
    files = list(DOCS.rglob("*.md"))
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
def test_exercise_runs_and_matches_documentation(api, test_client, make_token, processes, index):
    """Ejercicio en una base nueva: respuestas, permisos por usuario y documentación."""
    exercise = EXERCISES[index]
    ctx, records = run_exercise(api, exercise, _clients(test_client, make_token), processes)
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
def test_exercises_share_one_database(api, processes, order):
    """Todos los ejercicios en la misma base no chocan entre sí."""
    exercises = EXERCISES if order == "forward" else list(reversed(EXERCISES))
    for exercise in exercises:
        run_exercise(api, exercise, processes=processes)


def test_general_permissions_document(api, test_engine, test_client, make_token, processes):
    """`usuarios-y-permisos.md` corresponde con los permisos observados en todos los ejercicios."""
    for index, exercise in enumerate(EXERCISES):
        if index not in _RESULTS:
            truncate_all(test_engine)
            _RESULTS[index] = run_exercise(api, exercise, _clients(test_client, make_token), processes)

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
        content = path.read_text(encoding="utf-8")
        if jwt.search(content):
            problems.append(f"{path.name}: contiene un token JWT")
        if password and password in content:
            problems.append(f"{path.name}: contiene el valor de {PASSWORD_VARIABLE}")
        for match in password_assignment.finditer(content):
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


def test_data_source_is_declared():
    """Principio XXII: datos reales citan su fila; los inventados se declaran ficticios."""
    for exercise in EXERCISES:
        data = (DOCS / exercise["folder"] / data_file(exercise)).read_text(encoding="utf-8")
        assert "ficticio" in data.lower() or "ficticia" in data.lower(), exercise["folder"]
        if exercise.get("real_data"):
            assert "CAMPOS PRODUCTOS.xlsx" in data and "Fila" in data, exercise["folder"]
