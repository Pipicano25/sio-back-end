"""Etapa `preflight`: precondiciones E-01..E-12 del entorno integrado (quickstart.md §1).

Si alguna falla, run.py termina con código 2 sin ejecutar más etapas. Solo E-09 escribe por API: registra
un usuario operativo en una empresa propia del preflight (datos ficticios con el RUN_ID) para comprobar
la Admin API de Keycloak desde Operational Context.
"""

from __future__ import annotations

import json
import os
import re

import pytest

from scenario import reference
from sio_mvp import config
from sio_mvp.auth import TEST_USERS, decode_claims, token_permissions
from sio_mvp.identities import conforming_number

ALEMBIC_SERVICES = [
    service
    for service in config.SERVICES
    if service.key
    in {
        "geography",
        "product-catalog",
        "party-identity",
        "operational-context",
        "commercial-relationship",
        "payment-reference",
        "audit",
        "inventory",
        "purchase",
        "sales",
    }
]
RECONCILERS = {
    "sio-purchase-reconciler": "purchase_service.reconciler",
    "sio-sales-reconciler": "sales_service.reconciler",
}
REVISION = re.compile(r"^([0-9A-Za-z_]+) \(head\)", re.MULTILINE)


def requested_stages() -> set[str]:
    return set(filter(None, os.environ.get("SIO_MVP_STAGES", "").split(",")))


def test_e01_docker_running(docker, journal):
    code, output = docker.run(["info", "--format", "{{json .}}"])
    assert code == 0, "Docker no responde (E-01): inicie Docker y repita."
    info = json.loads(output)
    journal.record(
        {
            "step_id": "E-01",
            "docker": {
                "server_version": info.get("ServerVersion"),
                "memory_bytes": info.get("MemTotal"),
                "cpus": info.get("NCPU"),
                "containers_running": info.get("ContainersRunning"),
            },
        }
    )


@pytest.mark.parametrize("container", ["sio-keycloak", "sio-keycloak-db"])
def test_e02_keycloak_healthy(docker, container):
    state = docker.inspect(container)
    assert state.healthy, f"{container} no está sano: {state.status}/{state.health} (E-02)"


@pytest.mark.parametrize("username", TEST_USERS)
def test_e03_test_users_tokens_match_template(clients, realm, username):
    token = clients.tokens.user_token(username)
    claims = decode_claims(token)
    assert claims.get("sub") == realm.user_id(username), (
        f"{username}: el sub del token no es el id fijo de la plantilla; reconstruya Keycloak y reinicie "
        "Operational Context (E-03)"
    )
    expected = {role for role in realm.user_roles(username) if role.startswith("perm:")}
    missing = expected - token_permissions(token)
    assert not missing, f"{username}: faltan permisos de su grupo en el token: {sorted(missing)} (E-03)"


@pytest.mark.parametrize("service", config.SERVICES, ids=lambda item: item.key)
def test_e04_services_healthy_and_ready(docker, clients, service):
    state = docker.inspect(service.container)
    assert state.healthy, f"{service.container} no está sano: {state.status}/{state.health} (E-04)"
    client = clients.anonymous()
    status = client.get(service.key, "/health/ready", step_id="E-04", root=True).status
    assert status == 200, f"{service.key}: /health/ready = {status} (E-04)"


@pytest.mark.parametrize("service", ALEMBIC_SERVICES, ids=lambda item: item.key)
def test_e05_migrations_at_head(docker, journal, service):
    code_current, current = docker.run(["exec", service.container, "alembic", "current"])
    code_heads, heads = docker.run(["exec", service.container, "alembic", "heads"])
    assert code_current == 0 and code_heads == 0, f"{service.key}: no se pudo consultar Alembic (E-05)"
    current_revisions = set(REVISION.findall(current))
    head_revisions = set(REVISION.findall(heads))
    journal.record({"step_id": "E-05", "service": service.key, "current": sorted(current_revisions), "heads": sorted(head_revisions)})
    assert head_revisions and current_revisions == head_revisions, (
        f"{service.key}: migraciones no están en head (actual {sorted(current_revisions)}, head {sorted(head_revisions)}) (E-05)"
    )


@pytest.mark.parametrize(
    "container",
    [service.worker_container for service in config.SERVICES if service.worker_container],
)
def test_e06_audit_workers_healthy(docker, container):
    state = docker.inspect(container)
    assert state.healthy, f"{container} no está sano: {state.status}/{state.health} (E-06)"


@pytest.mark.parametrize("container", sorted(RECONCILERS))
def test_e07_reconcilers_running_and_check(docker, journal, container):
    state = docker.inspect(container)
    assert state.status == "running", f"{container} no está en ejecución: {state.status} (E-07)"
    code, _ = docker.run(["exec", container, "python", "-m", RECONCILERS[container], "--check"])
    # La salud lenta del healthcheck (D-04 de la 015) es informativa; --check debe pasar.
    journal.record({"step_id": "E-07", "container": container, "health": state.health, "check_exit_code": code})
    assert code == 0, f"{container}: --check falló (E-07)"


def test_e08_seeds_loaded(clients):
    admin = clients.user("admin.test")
    references = reference.load(admin, "E-08")
    for item in (references.person_rule, references.organization_rule):
        assert item["number_pattern"], "Regla de identificación sin patrón (E-08)"
    cash = reference.payment_condition_type(admin, "CASH", "E-08-tipo-contado")
    assert cash["status"] == "ACTIVE" if "status" in cash else True


def test_e09_operational_context_admin_api(clients, run_context, journal):
    """Registro de un usuario operativo en una empresa propia del preflight (Admin API de Keycloak)."""
    admin = clients.user("admin.test")
    references = reference.load(admin, "E-09-ref")
    label = run_context.label("PREFLIGHT SIO MVP")
    organization = None
    for attempt in range(1, 6):
        number = conforming_number(references.organization_rule["number_pattern"], run_context, "E-09-org", attempt)
        journal.protect(number)
        response = admin.post(
            "party-identity",
            "/organization-identities",
            step_id="E-09",
            json_body={
                "country_id": references.country_id,
                "identification_type": "NIT",
                "identification_number": number,
                "legal_name": label.upper(),
            },
        )
        if response.status == 201:
            organization = response.body["id"]
            break
        assert response.status == 409, f"Party Identity respondió {response.status} (E-09)"
    assert organization, "No se obtuvo un NIT libre para el preflight (E-09)"
    company = admin.post("operational-context", "/companies", step_id="E-09", json_body={"organization_identity_id": organization})
    assert company.status == 201, f"Operational Context respondió {company.status} al crear la empresa (E-09)"
    person = None
    for attempt in range(1, 6):
        number = conforming_number(references.person_rule["number_pattern"], run_context, "E-09-persona", attempt)
        journal.protect(number)
        response = admin.post(
            "party-identity",
            "/person-identities",
            step_id="E-09",
            json_body={
                "identification_country_id": references.country_id,
                "identification_type": "CC",
                "identification_number": number,
                "first_name": f"PREFLIGHT{run_context.run_id}",
                "last_name": "DATO FICTICIO DE VALIDACION",
                "birth_date": "1990-01-01",
            },
        )
        if response.status == 201:
            person = response.body["id"]
            break
        assert response.status == 409, f"Party Identity respondió {response.status} (E-09)"
    assert person, "No se obtuvo una cédula libre para el preflight (E-09)"
    user = admin.post(
        "operational-context",
        f"/companies/{company.body['id']}/application-users",
        step_id="E-09",
        json_body={
            "username": "consulta.test",
            "person_identity_id": person,
            "display_name": run_context.label("Preflight consulta"),
        },
    )
    assert user.status == 201, (
        f"Operational Context respondió {user.status} al registrar el usuario operativo: si es 503, "
        "reinicie sio-operational-context-service tras reconstruir Keycloak (E-09)"
    )


def test_e10_variables_available(settings):
    for name in ("KEYCLOAK_TEST_USER_PASSWORD", "SALES_SERVICE_CLIENT_SECRET", "PURCHASE_SERVICE_CLIENT_SECRET"):
        assert settings.secret(name) is not None, f"Falta {name} en el entorno o en infrastructure/.env (E-10)"


def test_e11_test_databases_for_regression(docker, settings):
    if "regresion" not in requested_stages():
        pytest.skip("E-11 solo aplica cuando se pide la etapa regresion")
    from sio_mvp import regression

    regression.ensure_test_databases(docker, settings)
    for service in config.SERVICES:
        state = docker.inspect(service.test_db_container)
        assert state.healthy, f"{service.test_db_container} no está sana (E-11)"


def test_e12_no_other_validation_running(report_dir, journal):
    """E-12 es manual (otras pruebas sobre el entorno); se deja constancia en el diario."""
    journal.record(
        {
            "step_id": "E-12",
            "note": "Precondición manual: sin otras pruebas usando el entorno durante la corrida.",
            "report_dir": report_dir.name,
        }
    )
