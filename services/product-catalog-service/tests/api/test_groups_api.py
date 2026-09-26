"""Historia 8: grupos (RC-02, RC-08, FR-009, FR-061 a FR-066)."""

from tests import factories

TYPES = "/api/v1/group-types"


def _type(api, code: str, allows_multiple: bool = False) -> dict:
    response = api.post(TYPES, json={"code": code, "name": code, "allows_multiple": allows_multiple})
    assert response.status_code == 201, response.text
    return response.json()


def _group(api, type_id: str, code: str, parent: str | None = None):
    body = {"code": code, "name": code.title()}
    if parent:
        body["parent_group_id"] = parent
    return api.post(f"{TYPES}/{type_id}/groups", json=body)


def _assign(api, product_id, group_id: str):
    return api.post(f"/api/v1/products/{product_id}/group-assignments", json={"global_product_group_id": group_id})


def _product(session_factory):
    unit = factories.unit(session_factory)
    return factories.product(session_factory, unit.id)


def test_single_value_type(api, session_factory) -> None:
    group_type = _type(api, "GROUP_1")
    medicamentos = _group(api, group_type["id"], "MEDICAMENTOS").json()
    alimentos = _group(api, group_type["id"], "ALIMENTOS").json()
    product = _product(session_factory)

    assert _assign(api, product.id, medicamentos["id"]).status_code == 201
    second = _assign(api, product.id, alimentos["id"])

    assert second.status_code == 422
    assert second.json()["code"] == "PRODUCT_CATALOG.GROUP_TYPE_SINGLE_VALUE"


def test_multi_value_type(api, session_factory) -> None:
    group_type = _type(api, "COLECCION", allows_multiple=True)
    first = _group(api, group_type["id"], "VERANO").json()
    second = _group(api, group_type["id"], "INVIERNO").json()
    product = _product(session_factory)

    assert _assign(api, product.id, first["id"]).status_code == 201
    assert _assign(api, product.id, second["id"]).status_code == 201
    assert len(api.get(f"/api/v1/products/{product.id}/group-assignments").json()) == 2


def test_parent_of_other_type_and_cycles(api) -> None:
    group_1 = _type(api, "GROUP_1")
    group_2 = _type(api, "GROUP_2")
    parent = _group(api, group_1["id"], "PADRE").json()

    other_type = _group(api, group_2["id"], "HIJO", parent=parent["id"])
    assert other_type.json()["code"] == "PRODUCT_CATALOG.PARENT_OF_OTHER_TYPE"

    child = _group(api, group_1["id"], "HIJO", parent=parent["id"]).json()
    cycle = api.put(
        f"/api/v1/groups/{parent['id']}",
        json={"name": "Padre", "parent_group_id": child["id"], "version": 1},
    )
    assert cycle.json()["code"] == "PRODUCT_CATALOG.HIERARCHY_CYCLE"

    ancestors = api.get(f"/api/v1/groups/{child['id']}/ancestors").json()
    assert [item["code"] for item in ancestors] == ["PADRE", "HIJO"]


def test_cannot_disable_multiple_with_existing_assignments(api, session_factory) -> None:
    group_type = _type(api, "COLECCION", allows_multiple=True)
    first = _group(api, group_type["id"], "VERANO").json()
    second = _group(api, group_type["id"], "INVIERNO").json()
    product = _product(session_factory)
    _assign(api, product.id, first["id"])
    _assign(api, product.id, second["id"])

    response = api.put(
        f"{TYPES}/{group_type['id']}",
        json={"name": "Colección", "allows_multiple": False, "display_order": 0, "version": 1},
    )

    assert response.json()["code"] == "PRODUCT_CATALOG.MULTIPLE_ASSIGNMENTS_EXIST"


def test_inactive_type_blocks_assignment(api, session_factory) -> None:
    group_type = _type(api, "GROUP_1")
    group = _group(api, group_type["id"], "A").json()
    api.post(f"{TYPES}/{group_type['id']}/deactivate", json={"version": 1})
    product = _product(session_factory)

    response = _assign(api, product.id, group["id"])

    assert response.json()["code"] == "PRODUCT_CATALOG.REFERENCE_INACTIVE"


def test_group_with_active_children_cannot_be_deactivated(api) -> None:
    group_type = _type(api, "GROUP_1")
    parent = _group(api, group_type["id"], "PADRE").json()
    _group(api, group_type["id"], "HIJO", parent=parent["id"])

    response = api.post(f"/api/v1/groups/{parent['id']}/deactivate", json={"version": 1})

    assert response.json()["code"] == "PRODUCT_CATALOG.HAS_ACTIVE_CHILDREN"


def test_groups_do_not_affect_completeness(api, session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory)
    group_type = _type(api, "GROUP_1")
    group = _group(api, group_type["id"], "A").json()

    _assign(api, product.id, group["id"])

    assert api.get(f"/api/v1/products/{product.id}").json()["eligible_for_adoption"] is True


def test_list_filters_and_deactivate_permission(api, api_as, session_factory) -> None:
    group_type = _type(api, "GROUP_1")
    parent = _group(api, group_type["id"], "PADRE").json()
    _group(api, group_type["id"], "HIJO", parent=parent["id"])

    def codes(query: str) -> list[str]:
        return [item["code"] for item in api.get(f"{TYPES}/{group_type['id']}/groups?{query}").json()["items"]]

    assert codes("root_only=true") == ["PADRE"]
    assert codes(f"parent_group_id={parent['id']}") == ["HIJO"]
    assert codes("code=hijo") == ["HIJO"]
    assert codes("search=pad") == ["PADRE"]

    product = _product(session_factory)
    assignment = _assign(api, product.id, parent["id"]).json()
    denied = api_as("products:update").post(
        f"/api/v1/products/{product.id}/group-assignments/{assignment['id']}/deactivate",
        json={"version": 1},
    )
    assert denied.status_code == 403
