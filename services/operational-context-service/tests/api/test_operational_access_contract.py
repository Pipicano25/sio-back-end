"""Contrato `GET /api/v1/operational-access` (US4; FR-071, FR-075; DS-08, C-14; RC-07, RC-11).

Contrato: `specs/005-operational-context-users/contracts/operational-access-provider.md`.
"""

import pytest

URL = "/api/v1/operational-access"
UNKNOWN = "00000000-0000-4000-8000-000000000999"
READ = "perm:operational-context:application_users:read"
LOOKUP = "perm:operational-context:platform:lookup"


@pytest.fixture
def world(api, create_company, create_branch, fake_accounts, fake_persons):
    """Empresa con sucursal, usuario `compras.test` asignado y una empresa ajena."""
    company = create_company()
    foreign = create_company()
    branch = create_branch(company["id"], code="S-1")
    other_branch = create_branch(company["id"], code="S-2")
    foreign_branch = create_branch(foreign["id"], code="F-1")
    sub = fake_accounts.add("compras.test", roles=("perm:inventory:all:all",))
    user = api.post(
        f"/api/v1/companies/{company['id']}/application-users",
        json={"keycloak_user_id": sub, "person_identity_id": str(fake_persons.add()), "display_name": "C"},
    ).json()
    assignment = api.post(
        f"/api/v1/application-users/{user['id']}/user-branches",
        json={"branch_id": branch["id"]},
    ).json()
    fake_accounts.reset()
    return {
        "company": company,
        "foreign": foreign,
        "branch": branch,
        "other_branch": other_branch,
        "foreign_branch": foreign_branch,
        "sub": sub,
        "user": user,
        "assignment": assignment,
    }


@pytest.fixture
def own(api_as, world):
    """El propio usuario con su token (permisos de su grupo)."""
    return api_as(READ, "perm:inventory:all:all", sub=world["sub"])


@pytest.fixture
def technical(api_as):
    """Consumidor técnico: token con `platform:lookup` pero SIN permisos de inventario."""
    return api_as(READ, LOOKUP, sub="service-account-inventory-service")


# --------------------------------------------------------------- vía propia


def test_own_allowed_with_permission(own, world, fake_accounts):
    response = own.get(URL, params={"branch_id": world["branch"]["id"], "permission": "perm:inventory:movements:create"})

    assert response.status_code == 200
    assert response.json() == {
        "allowed": True,
        "reason": None,
        "keycloak_user_id": world["sub"],
        "company_id": world["company"]["id"],
        "branch_id": world["branch"]["id"],
        "application_user_id": world["user"]["id"],
        "permission": "perm:inventory:movements:create",
    }
    assert fake_accounts.count() == 0  # la vía propia usa el token, no Keycloak


def test_own_permission_denied(own, world):
    body = own.get(URL, params={"branch_id": world["branch"]["id"], "permission": "perm:sales:sales:create"}).json()

    assert body["allowed"] is False and body["reason"] == "PERMISSION_DENIED"


def test_own_company_level(own, world):
    body = own.get(URL, params={"company_id": world["company"]["id"]}).json()

    assert body["allowed"] is True and body["branch_id"] is None


def test_own_branch_not_assigned(own, world):
    assert own.get(URL, params={"branch_id": world["other_branch"]["id"]}).json()["reason"] == "BRANCH_NOT_ASSIGNED"


def test_own_reasons_follow_the_order(api, own, world):
    branch_id = world["branch"]["id"]

    api.post(f"/api/v1/user-branches/{world['assignment']['id']}/deactivate", json={"version": 1})
    assert own.get(URL, params={"branch_id": branch_id}).json()["reason"] == "USER_BRANCH_INACTIVE"

    api.post(f"/api/v1/branches/{branch_id}/deactivate", json={"version": 1})
    assert own.get(URL, params={"branch_id": branch_id}).json()["reason"] == "BRANCH_INACTIVE"

    api.post(f"/api/v1/companies/{world['company']['id']}/deactivate", json={"version": 1})
    assert own.get(URL, params={"branch_id": branch_id}).json()["reason"] == "COMPANY_INACTIVE"

    api.post(f"/api/v1/application-users/{world['user']['id']}/deactivate", json={"version": 1})
    body = own.get(URL, params={"branch_id": branch_id}).json()
    assert body["reason"] == "USER_MEMBERSHIP_INACTIVE"
    assert body["application_user_id"] == world["user"]["id"]


@pytest.mark.parametrize("target", ["foreign_company", "foreign_branch", "unknown_company", "unknown_branch"])
def test_own_foreign_or_unknown_is_user_not_member_without_details(own, world, target):
    params = {
        "foreign_company": {"company_id": world["foreign"]["id"]},
        "foreign_branch": {"branch_id": world["foreign_branch"]["id"]},
        "unknown_company": {"company_id": UNKNOWN},
        "unknown_branch": {"branch_id": UNKNOWN},
    }[target]

    response = own.get(URL, params=params)

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False and body["reason"] == "USER_NOT_MEMBER"
    assert body["application_user_id"] is None
    assert body["company_id"] == params.get("company_id")
    assert body["branch_id"] == params.get("branch_id")


def test_own_foreign_and_unknown_are_indistinguishable(own, world):
    foreign = own.get(URL, params={"branch_id": world["foreign_branch"]["id"]}).json()
    unknown = own.get(URL, params={"branch_id": UNKNOWN}).json()

    foreign.pop("branch_id")
    unknown.pop("branch_id")
    assert foreign == unknown


# --------------------------------------------------------------- vía técnica


def test_technical_uses_target_user_roles_not_the_technical_token(technical, world, fake_accounts):
    """El token técnico no tiene permisos de inventario; el usuario sí (roles de Keycloak)."""
    response = technical.get(
        URL,
        params={
            "branch_id": world["branch"]["id"],
            "keycloak_user_id": world["sub"],
            "permission": "perm:inventory:movements:create",
        },
    )

    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert fake_accounts.count("get_permission_roles") == 1


def test_technical_token_permissions_never_replace_user_permissions(api_as, world, fake_accounts):
    """Token técnico con el permiso objetivo; el usuario no lo tiene → PERMISSION_DENIED."""
    technical = api_as(READ, LOOKUP, "perm:sales:all:all", sub="service-account-sales-service")

    body = technical.get(
        URL,
        params={
            "branch_id": world["branch"]["id"],
            "keycloak_user_id": world["sub"],
            "permission": "perm:sales:sales:create",
        },
    ).json()

    assert body["allowed"] is False and body["reason"] == "PERMISSION_DENIED"


def test_technical_order_is_company_first(api, technical, world):
    api.post(f"/api/v1/companies/{world['foreign']['id']}/deactivate", json={"version": 1})

    body = technical.get(
        URL, params={"company_id": world["foreign"]["id"], "keycloak_user_id": world["sub"]}
    ).json()

    assert body["reason"] == "COMPANY_INACTIVE"


def test_technical_not_member(technical, world):
    body = technical.get(
        URL, params={"company_id": world["foreign"]["id"], "keycloak_user_id": world["sub"]}
    ).json()

    assert body["reason"] == "USER_NOT_MEMBER"


@pytest.mark.parametrize("param", ["company_id", "branch_id"])
def test_technical_unknown_resource_is_404(technical, world, param):
    response = technical.get(URL, params={param: UNKNOWN, "keycloak_user_id": world["sub"]})

    assert response.status_code == 404


def test_other_sub_without_lookup_is_403(own, world):
    response = own.get(URL, params={"company_id": world["company"]["id"], "keycloak_user_id": "otro"})

    assert response.status_code == 403
    assert "platform:lookup" in response.json()["detail"]


def test_keycloak_unavailable_only_when_permission_is_evaluated(technical, world, fake_accounts):
    fake_accounts.mode = "unavailable"
    params = {"branch_id": world["branch"]["id"], "keycloak_user_id": world["sub"]}

    without_permission = technical.get(URL, params=params)
    with_permission = technical.get(URL, params={**params, "permission": "perm:inventory:movements:create"})

    assert without_permission.status_code == 200
    assert with_permission.status_code == 503
    assert with_permission.json()["code"] == "OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE"
    assert with_permission.json()["dependency"] == "keycloak"


# --------------------------------------------------------------- errores de contrato


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"company_id": UNKNOWN, "branch_id": UNKNOWN},
        {"company_id": UNKNOWN, "permission": "inventory:movements:create"},
        {"company_id": UNKNOWN, "permission": "perm:inventory:all:create"},
        {"company_id": UNKNOWN, "permission": "perm:inventory:movements"},
        {"company_id": "no-uuid"},
    ],
)
def test_invalid_parameters_are_422(own, params):
    response = own.get(URL, params=params)

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.VALIDATION_ERROR"


def test_unauthenticated_and_without_read_permission(anonymous, api_as, world):
    params = {"company_id": world["company"]["id"]}

    assert anonymous.get(URL, params=params).status_code == 401
    assert api_as("perm:inventory:all:all", sub=world["sub"]).get(URL, params=params).status_code == 403
