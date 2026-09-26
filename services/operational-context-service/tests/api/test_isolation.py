"""Aislamiento por empresa en **todas** las rutas (US3; FR-040 a FR-045; DS-06, C-14; RC-02, RC-03).

Un usuario con todos los permisos CRUD del servicio (sin `platform:*`) y
membresía `ACTIVE` solo en la empresa B intenta operar recursos de la empresa
A: cada ruta responde `404` con el mismo cuerpo que un UUID inexistente, salvo
las excepciones deliberadas documentadas en la tabla. La prueba falla si se
registra una ruta funcional que no figure en la tabla.
"""

import pytest

# Permisos CRUD completos sin acción `all`: no conceden `platform:*` (RC-03).
CRUD = tuple(f"perm:operational-context:all:{action}" for action in ("read", "create", "update", "delete"))

# (método, plantilla, cuerpo, estado esperado, nota)
ROUTES = [
    ("GET", "/api/v1/companies", None, "collection", "solo empresas del alcance"),
    ("POST", "/api/v1/companies", "company", 403, "exige platform:administer"),
    ("GET", "/api/v1/companies/{company_id}", None, 404, ""),
    ("PUT", "/api/v1/companies/{company_id}", "company_put", 404, ""),
    ("POST", "/api/v1/companies/{company_id}/deactivate", "version", 403, "exige platform:administer"),
    ("POST", "/api/v1/companies/{company_id}/reactivate", "version", 403, "exige platform:administer"),
    ("GET", "/api/v1/companies/{company_id}/branches", None, 404, ""),
    ("POST", "/api/v1/companies/{company_id}/branches", "branch", 404, ""),
    ("GET", "/api/v1/branches/{branch_id}", None, 404, ""),
    ("PUT", "/api/v1/branches/{branch_id}", "branch_put", 404, ""),
    ("POST", "/api/v1/branches/{branch_id}/deactivate", "version", 404, ""),
    ("POST", "/api/v1/branches/{branch_id}/reactivate", "version", 404, ""),
    ("GET", "/api/v1/companies/{company_id}/application-users", None, 404, ""),
    ("POST", "/api/v1/companies/{company_id}/application-users", "member", 404, ""),
    ("GET", "/api/v1/application-users/{application_user_id}", None, 404, ""),
    ("PUT", "/api/v1/application-users/{application_user_id}", "member_put", 404, ""),
    ("POST", "/api/v1/application-users/{application_user_id}/deactivate", "version", 404, ""),
    ("POST", "/api/v1/application-users/{application_user_id}/reactivate", "version", 404, ""),
    ("GET", "/api/v1/application-users/{application_user_id}/user-branches", None, 404, ""),
    ("POST", "/api/v1/application-users/{application_user_id}/user-branches", "assign", 404, ""),
    ("GET", "/api/v1/branches/{branch_id}/user-branches", None, 404, ""),
    ("GET", "/api/v1/user-branches/{user_branch_id}", None, 404, ""),
    ("POST", "/api/v1/user-branches/{user_branch_id}/deactivate", "version", 404, ""),
    ("POST", "/api/v1/user-branches/{user_branch_id}/reactivate", "version", 404, ""),
    ("GET", "/api/v1/companies/{company_id}/advisor-assignments", None, 404, ""),
    ("POST", "/api/v1/companies/{company_id}/advisor-assignments", "advisor", 404, ""),
    ("GET", "/api/v1/advisor-assignments/{assignment_id}", None, 404, ""),
    ("POST", "/api/v1/advisor-assignments/{assignment_id}/close", "version", 404, ""),
    ("POST", "/api/v1/companies/{company_id}/advisor-assignments/change-primary", "change", 404, ""),
    ("GET", "/api/v1/me/operational-context", None, "me", "solo membresías propias"),
    ("GET", "/api/v1/operational-access", None, "access", "C-14: 200 USER_NOT_MEMBER"),
]


@pytest.fixture
def world(api, create_company, create_branch, fake_accounts, fake_persons, make_member):
    """Recursos de la empresa A; el usuario `ajeno` solo es miembro de la empresa B."""
    company_a = create_company()
    company_b = create_company()
    branch = create_branch(company_a["id"])
    user = api.post(
        f"/api/v1/companies/{company_a['id']}/application-users",
        json={
            "keycloak_user_id": fake_accounts.add("usuario.a"),
            "person_identity_id": str(fake_persons.add()),
            "display_name": "A",
        },
    ).json()
    user_branch = api.post(
        f"/api/v1/application-users/{user['id']}/user-branches", json={"branch_id": branch["id"]}
    ).json()
    advisor = api.post(
        f"/api/v1/companies/{company_a['id']}/advisor-assignments",
        json={"person_identity_id": str(fake_persons.add()), "valid_from": "2026-01-01T00:00:00+00:00"},
    ).json()
    make_member(company_b["id"], "ajeno")
    return {
        "company_a": company_a,
        "company_b": company_b,
        "ids": {
            "company_id": company_a["id"],
            "branch_id": branch["id"],
            "application_user_id": user["id"],
            "user_branch_id": user_branch["id"],
            "assignment_id": advisor["id"],
        },
        "company": company_a,
        "branch": branch,
        "user": user,
        "advisor": advisor,
        "persons": fake_persons,
        "accounts": fake_accounts,
    }


def _body(kind, world):
    if kind is None:
        return None
    persons = world["persons"]
    return {
        "version": {"version": 1},
        "company": {"organization_identity_id": "00000000-0000-4000-8000-000000000123"},
        "company_put": {
            "organization_identity_id": world["company"]["organization_identity_id"],
            "timezone": "America/Bogota",
            "default_currency": "COP",
            "version": 1,
        },
        "branch": {"code": "NEW", "name": "Nueva"},
        "branch_put": {"code": world["branch"]["code"], "name": "Otro", "version": 1},
        "member": {
            "keycloak_user_id": world["accounts"].add("nuevo"),
            "person_identity_id": str(persons.add()),
            "display_name": "N",
        },
        "member_put": {"display_name": "X", "version": 1},
        "assign": {"branch_id": world["branch"]["id"]},
        "advisor": {"person_identity_id": str(persons.add()), "is_primary": False},
        "change": {
            "current_assignment_id": world["advisor"]["id"],
            "version": 1,
            "person_identity_id": str(persons.add()),
        },
    }[kind]


@pytest.mark.parametrize(
    ("method", "template", "body", "expected", "note"),
    ROUTES,
    ids=[f"{m} {t}" for m, t, *_ in ROUTES],
)
def test_foreign_company_resources_are_invisible(api_as, world, method, template, body, expected, note):
    outsider = api_as(*CRUD, sub="ajeno")
    path = template.format(**world["ids"])
    params = {"company_id": world["ids"]["company_id"]} if template.endswith("operational-access") else None

    response = outsider.request(method, path, json=_body(body, world), params=params)

    if expected == "collection":
        assert response.status_code == 200
        ids = {item["id"] for item in response.json()["items"]}
        assert world["company_a"]["id"] not in ids and world["company_b"]["id"] in ids
    elif expected == "me":
        assert response.status_code == 200
        assert {m["company_id"] for m in response.json()["memberships"]} == {world["company_b"]["id"]}
    elif expected == "access":
        assert response.status_code == 200
        assert response.json()["reason"] == "USER_NOT_MEMBER"
    else:
        assert response.status_code == expected, response.text
        if expected == 404:
            unknown = outsider.request(
                method,
                template.format(**{key: "00000000-0000-4000-8000-000000000999" for key in world["ids"]}),
                json=_body(body, world),
            )
            assert unknown.status_code == 404
            assert response.json()["code"] == unknown.json()["code"] == "OPERATIONAL_CONTEXT.NOT_FOUND"
            assert response.json()["title"] == unknown.json()["title"]


def test_platform_admin_sees_everything(api, world):
    assert api.get(f"/api/v1/companies/{world['ids']['company_id']}").status_code == 200
    assert api.get(f"/api/v1/advisor-assignments/{world['ids']['assignment_id']}").status_code == 200
    ids = {item["id"] for item in api.get("/api/v1/companies").json()["items"]}
    assert {world["company_a"]["id"], world["company_b"]["id"]} <= ids


def test_member_scope_is_evaluated_on_every_request(api, api_as, world, make_member):
    """C3 / FR-044: sin caché; con el mismo token, inactivar la membresía se refleja al instante."""
    member_id = make_member(world["ids"]["company_id"], "miembro-a")
    member = api_as(*CRUD, sub="miembro-a")
    url = f"/api/v1/companies/{world['ids']['company_id']}"

    assert member.get(url).status_code == 200

    api.post(f"/api/v1/application-users/{member_id}/deactivate", json={"version": 1})

    assert member.get(url).status_code == 404


def test_every_functional_route_is_covered(anonymous):
    spec = anonymous.get("/openapi.json").json()
    registered = {
        (method.upper(), path)
        for path, item in spec["paths"].items()
        if path.startswith("/api/v1")
        for method in item
    }
    covered = {(method, template) for method, template, *_ in ROUTES}

    assert registered == covered
