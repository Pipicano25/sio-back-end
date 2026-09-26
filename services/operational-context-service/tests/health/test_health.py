"""Salud del servicio (FR-072 de la Fase A; FR-090 de la Fase B)."""

from fastapi.testclient import TestClient

from operational_context_service.config import Settings
from operational_context_service.main import create_app


def test_live_has_no_dependency_details(anonymous):
    response = anonymous.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_ok_with_database(anonymous):
    response = anonymous.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_depends_only_on_the_database(
    anonymous, fake_organizations, fake_geography, fake_persons, fake_accounts
):
    """FR-090: Keycloak, Party Identity y Geography no disponibles → `ready` sigue `200`.

    Además, ni `live` ni `ready` llaman a ninguna dependencia externa.
    """
    fake_organizations.mode = "unavailable"
    fake_geography.mode = "unavailable"
    fake_persons.mode = "unavailable"
    fake_accounts.mode = "unavailable"

    assert anonymous.get("/health/live").status_code == 200
    assert anonymous.get("/health/ready").status_code == 200
    assert fake_organizations.count() == 0
    assert fake_geography.count() == 0
    assert fake_persons.count() == 0
    assert fake_accounts.count() == 0


def test_ready_is_503_without_details_when_database_is_down(test_auth):
    settings = Settings(
        docs_enabled=False,
        database_url="postgresql+psycopg://nadie:nada@127.0.0.1:1/inexistente_test",
        party_identity_base_url="http://party-identity.test/api/v1",
        geography_base_url="http://geography.test",
        keycloak_base_url="http://keycloak.test",
        keycloak_client_id="operational-context-service",
        keycloak_client_secret="test-only-secret",
    )
    app = create_app(
        settings,
        auth=test_auth,
        organization_directory_factory=lambda request: None,
        geography_directory_factory=lambda request: None,
        person_directory_factory=lambda request: None,
        account_directory_factory=lambda request: None,
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/health/ready")
        live = client.get("/health/live")

    assert response.status_code == 503
    assert "psycopg" not in response.text.lower()
    assert "127.0.0.1" not in response.text
    assert live.status_code == 200
