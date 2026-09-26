"""Historia 2: taxonomía jerárquica de categorías (FR-009, FR-020 a FR-023, DS-07)."""

URL = "/api/v1/categories"


def _create(api, code: str, parent: str | None = None) -> dict:
    body = {"code": code, "name": code.title()}
    if parent:
        body["parent_category_id"] = parent
    response = api.post(URL, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _update(api, category: dict, **changes):
    current = api.get(f"{URL}/{category['id']}").json()
    body = {
        "name": current["name"],
        "description": current["description"],
        "parent_category_id": current["parent_category_id"],
        "version": current["version"],
        **changes,
    }
    return api.put(f"{URL}/{category['id']}", json=body)


def test_create_child_category(api) -> None:
    alimentos = _create(api, "ALIMENTOS")
    granos = _create(api, "GRANOS", alimentos["id"])
    assert granos["parent_category_id"] == alimentos["id"]


def test_indirect_cycle_rejected(api) -> None:
    alimentos = _create(api, "ALIMENTOS")
    granos = _create(api, "GRANOS", alimentos["id"])
    arroz = _create(api, "ARROZ", granos["id"])

    response = _update(api, alimentos, parent_category_id=arroz["id"])

    assert response.status_code == 422
    assert response.json()["code"] == "PRODUCT_CATALOG.HIERARCHY_CYCLE"


def test_self_parent_rejected(api) -> None:
    alimentos = _create(api, "ALIMENTOS")
    response = _update(api, alimentos, parent_category_id=alimentos["id"])
    assert response.json()["code"] == "PRODUCT_CATALOG.HIERARCHY_CYCLE"


def test_inactive_parent_rejected_for_create_and_move(api) -> None:
    inactive = _create(api, "INACTIVA")
    api.post(f"{URL}/{inactive['id']}/deactivate", json={"version": 1})
    other = _create(api, "OTRA")

    create = api.post(URL, json={"code": "HIJA", "name": "Hija", "parent_category_id": inactive["id"]})
    move = _update(api, other, parent_category_id=inactive["id"])

    assert create.json()["code"] == "PRODUCT_CATALOG.REFERENCE_INACTIVE"
    assert move.json()["code"] == "PRODUCT_CATALOG.REFERENCE_INACTIVE"


def test_unknown_parent_rejected(api) -> None:
    response = api.post(
        URL,
        json={"code": "X", "name": "X", "parent_category_id": "5f0c6c3e-7a8f-4a44-9d0b-1f2b3c4d5e6f"},
    )
    assert response.json()["code"] == "PRODUCT_CATALOG.REFERENCE_NOT_FOUND"


def test_deactivate_with_active_children_rejected(api) -> None:
    alimentos = _create(api, "ALIMENTOS")
    _create(api, "GRANOS", alimentos["id"])

    response = api.post(f"{URL}/{alimentos['id']}/deactivate", json={"version": 1})

    assert response.status_code == 422
    assert response.json()["code"] == "PRODUCT_CATALOG.HAS_ACTIVE_CHILDREN"


def test_reactivate_with_inactive_parent_rejected(api) -> None:
    alimentos = _create(api, "ALIMENTOS")
    granos = _create(api, "GRANOS", alimentos["id"])
    api.post(f"{URL}/{granos['id']}/deactivate", json={"version": 1})
    api.post(f"{URL}/{alimentos['id']}/deactivate", json={"version": 1})

    response = api.post(f"{URL}/{granos['id']}/reactivate", json={"version": 2})

    assert response.json()["code"] == "PRODUCT_CATALOG.PARENT_INACTIVE"


def test_tree_queries(api) -> None:
    alimentos = _create(api, "ALIMENTOS")
    granos = _create(api, "GRANOS", alimentos["id"])
    arroz = _create(api, "ARROZ", granos["id"])

    ancestors = api.get(f"{URL}/{arroz['id']}/ancestors").json()
    children = api.get(f"{URL}/{alimentos['id']}/children").json()
    descendants = api.get(f"{URL}/{alimentos['id']}/descendants").json()

    assert " > ".join(item["name"] for item in ancestors) == "Alimentos > Granos > Arroz"
    assert [item["code"] for item in children["items"]] == ["GRANOS"]
    assert {item["code"] for item in descendants["items"]} == {"GRANOS", "ARROZ"}


def test_move_to_root_and_code_immutable(api) -> None:
    alimentos = _create(api, "ALIMENTOS")
    granos = _create(api, "GRANOS", alimentos["id"])

    moved = _update(api, granos, parent_category_id=None)
    assert moved.status_code == 200
    assert moved.json()["parent_category_id"] is None

    current = moved.json()
    response = api.put(
        f"{URL}/{granos['id']}",
        json={"code": "OTRO", "name": "Granos", "version": current["version"]},
    )
    assert response.json()["code"] == "PRODUCT_CATALOG.IMMUTABLE_FIELD"


def test_list_filters(api) -> None:
    alimentos = _create(api, "ALIMENTOS")
    _create(api, "GRANOS", alimentos["id"])
    bebidas = _create(api, "BEBIDAS")
    api.post(f"{URL}/{bebidas['id']}/deactivate", json={"version": 1})

    def codes(query: str) -> list[str]:
        return [item["code"] for item in api.get(f"{URL}?{query}").json()["items"]]

    assert codes("root_only=true") == ["ALIMENTOS", "BEBIDAS"]
    assert codes(f"parent_category_id={alimentos['id']}") == ["GRANOS"]
    assert codes("status=INACTIVE") == ["BEBIDAS"]
    assert codes("code=granos") == ["GRANOS"]
    assert codes("search=ALIM") == ["ALIMENTOS"]


def test_deactivate_requires_deactivate_permission(api, api_as) -> None:
    category = _create(api, "ALIMENTOS")
    response = api_as("categories:update").post(f"{URL}/{category['id']}/deactivate", json={"version": 1})
    assert response.status_code == 403
