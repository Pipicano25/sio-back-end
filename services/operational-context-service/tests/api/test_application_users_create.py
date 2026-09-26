"""Alta de usuarios operativos (US1; FR-010 a FR-019; RC-04, RC-05, RC-14)."""

import pytest
from sqlalchemy import text

BASE = "/api/v1/companies/{company_id}/application-users"


def _count(test_engine) -> int:
    with test_engine.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM application_users")).scalar_one()


@pytest.fixture
def company(create_company):
    return create_company()


@pytest.fixture
def person(fake_persons):
    return fake_persons.add()


@pytest.fixture
def account(fake_accounts):
    return fake_accounts.add("compras.test")


def _body(person_id, **overrides):
    body = {
        "person_identity_id": str(person_id),
        "display_name": "Compras Ficticio",
        "reference_email": "compras@empresa-ficticia.co",
    }
    body.update(overrides)
    return body


def test_create_by_sub(api, company, person, account):
    response = api.post(
        BASE.format(company_id=company["id"]),
        json=_body(person, keycloak_user_id=account),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert response.headers["Location"] == f"/api/v1/application-users/{body['id']}"
    assert body["keycloak_user_id"] == account
    assert body["person_identity_id"] == str(person)
    assert body["status"] == "ACTIVE"
    assert body["company_id"] == company["id"]
    assert body["company_status"] == "ACTIVE"
    assert body["created_by"] == "user-admin"
    assert "username" not in body


def test_create_by_username_stores_only_the_sub(api, company, person, account, test_engine):
    response = api.post(
        BASE.format(company_id=company["id"]),
        json=_body(person, username="  Compras.Test "),
    )

    assert response.status_code == 201, response.text
    assert response.json()["keycloak_user_id"] == account

    with test_engine.connect() as connection:
        columns = {
            row[0]
            for row in connection.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'application_users'")
            )
        }
    assert "username" not in columns


@pytest.mark.parametrize(
    "account_fields",
    [{}, {"keycloak_user_id": "x", "username": "compras.test"}],
    ids=["ninguno", "ambos"],
)
def test_exactly_one_account_reference(api, company, person, account_fields):
    response = api.post(BASE.format(company_id=company["id"]), json=_body(person, **account_fields))

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.VALIDATION_ERROR"


def test_unknown_account_is_422(api, company, person, fake_persons, test_engine):
    response = api.post(BASE.format(company_id=company["id"]), json=_body(person, username="nadie"))

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.KEYCLOAK_USER_NOT_FOUND"
    assert fake_persons.count() == 0
    assert _count(test_engine) == 0


def test_disabled_account_is_422(api, company, person, fake_accounts):
    sub = fake_accounts.add("deshabilitado", enabled=False)

    response = api.post(BASE.format(company_id=company["id"]), json=_body(person, keycloak_user_id=sub))

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.KEYCLOAK_USER_DISABLED"


def test_technical_account_is_rejected(api, company, person, fake_accounts):
    sub = fake_accounts.add("service-account-inventory-service", service_account=True)

    response = api.post(BASE.format(company_id=company["id"]), json=_body(person, keycloak_user_id=sub))

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.TECHNICAL_ACCOUNT_NOT_ALLOWED"


def test_person_is_required(api, company, account):
    body = _body("x", keycloak_user_id=account)
    body.pop("person_identity_id")

    response = api.post(BASE.format(company_id=company["id"]), json=body)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("status", "code"),
    [(None, "PERSON_IDENTITY_NOT_FOUND"), ("INACTIVE", "PERSON_IDENTITY_INACTIVE")],
)
def test_person_not_found_or_inactive_is_422(api, company, account, fake_persons, test_engine, status, code):
    person = fake_persons.add(status) if status else "00000000-0000-4000-8000-00000000abcd"

    response = api.post(BASE.format(company_id=company["id"]), json=_body(person, keycloak_user_id=account))

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == f"OPERATIONAL_CONTEXT.{code}"
    assert body["errors"][0]["field"] == "person_identity_id"
    assert _count(test_engine) == 0


@pytest.mark.parametrize(
    ("unavailable", "dependency"),
    [("accounts", "keycloak"), ("persons", "party-identity")],
)
def test_dependency_unavailable_is_503(
    api, company, person, account, fake_accounts, fake_persons, test_engine, unavailable, dependency
):
    (fake_accounts if unavailable == "accounts" else fake_persons).mode = "unavailable"

    response = api.post(BASE.format(company_id=company["id"]), json=_body(person, keycloak_user_id=account))

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == dependency
    assert _count(test_engine) == 0


def test_duplicate_active_person_with_another_account_is_409(api, company, person, account, fake_accounts):
    url = BASE.format(company_id=company["id"])
    assert api.post(url, json=_body(person, keycloak_user_id=account)).status_code == 201
    other_account = fake_accounts.add("otra.cuenta")

    response = api.post(url, json=_body(person, keycloak_user_id=other_account))

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.DUPLICATE_MEMBERSHIP"
    assert body["errors"][0]["field"] == "person_identity_id"


def test_duplicate_active_account_with_another_person_is_409(api, company, person, account, fake_persons):
    url = BASE.format(company_id=company["id"])
    assert api.post(url, json=_body(person, keycloak_user_id=account)).status_code == 201

    response = api.post(url, json=_body(fake_persons.add(), keycloak_user_id=account))

    assert response.status_code == 409
    assert response.json()["errors"][0]["field"] == "keycloak_user_id"


def test_history_does_not_block_a_new_membership(api, company, person, account, test_engine):
    url = BASE.format(company_id=company["id"])
    first = api.post(url, json=_body(person, keycloak_user_id=account)).json()
    assert api.post(
        f"/api/v1/application-users/{first['id']}/deactivate",
        json={"version": first["version"]},
    ).status_code == 200

    response = api.post(url, json=_body(person, keycloak_user_id=account))

    assert response.status_code == 201
    assert response.json()["id"] != first["id"]
    assert _count(test_engine) == 2


def test_same_person_and_account_in_another_company(api, create_company, company, person, account):
    other = create_company()

    first = api.post(BASE.format(company_id=company["id"]), json=_body(person, keycloak_user_id=account))
    second = api.post(BASE.format(company_id=other["id"]), json=_body(person, keycloak_user_id=account))

    assert first.status_code == second.status_code == 201


def test_inactive_company_is_422(api, company, person, account):
    api.post(f"/api/v1/companies/{company['id']}/deactivate", json={"version": company["version"]})

    response = api.post(BASE.format(company_id=company["id"]), json=_body(person, keycloak_user_id=account))

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.COMPANY_INACTIVE"


def test_unknown_company_is_404(api, person, account):
    response = api.post(
        BASE.format(company_id="00000000-0000-4000-8000-000000000999"),
        json=_body(person, keycloak_user_id=account),
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "overrides",
    [
        {"display_name": ""},
        {"display_name": "x" * 161},
        {"reference_email": "no-es-correo"},
        {"reference_email": "a" * 250 + "@x.co"},
        {"created_by": "intruso"},
        {"status": "INACTIVE"},
    ],
)
def test_invalid_fields_are_422(api, company, person, account, overrides):
    response = api.post(
        BASE.format(company_id=company["id"]),
        json=_body(person, keycloak_user_id=account, **overrides),
    )

    assert response.status_code == 422


def test_member_without_platform_scope_cannot_register_in_foreign_company(
    api_as, create_company, company, person, account, make_member
):
    """US1 escenario 6: la empresa ajena se trata como inexistente."""
    other = create_company()
    make_member(company["id"], "supervisor-sub")
    supervisor = api_as(
        "perm:all:all:read", "perm:all:all:create", "perm:all:all:update", sub="supervisor-sub"
    )

    own = supervisor.post(BASE.format(company_id=company["id"]), json=_body(person, keycloak_user_id=account))
    foreign = supervisor.post(BASE.format(company_id=other["id"]), json=_body(person, keycloak_user_id=account))

    assert own.status_code == 201
    assert foreign.status_code == 404
    assert foreign.json()["code"] == "OPERATIONAL_CONTEXT.NOT_FOUND"
