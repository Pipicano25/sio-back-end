"""Historia 1 de la spec 021: políticas de precios de lista (T017; FR-021-01..06; RC-021-1, RC-021-2).

CP-09, CP-10, CP-11, CP-12, CP-13, CP-14, CP-15, CP-16 y CP-T19. Datos ficticios.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.api.helpers import adopt, adopt_presentation, code_of, create_price, create_price_list

LIST_URL = "/api/v1/companies/{company}/price-lists/{price_list}/pricing-policies"
URL = "/api/v1/pricing-policies/{id}"


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


@pytest.fixture
def supervisor(as_user):
    return as_user("supervisor.test")


@pytest.fixture
def catalog(admin, company, fake_catalog):
    """Producto ficticio con tres presentaciones vendibles."""
    product = adopt(admin, company, fake_catalog)
    presentations = [adopt_presentation(admin, company, fake_catalog, product)["id"] for _ in range(3)]
    return product, presentations


def create_policy(client, company, price_list, presentations=(), *, name="Alimentos", markup="15"):
    response = client.post(
        LIST_URL.format(company=company, price_list=price_list["id"]),
        json={"name": name, "markup_percentage": markup, "company_product_presentation_ids": list(presentations)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def price_count(test_engine) -> int:
    with test_engine.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM price_list_items")).scalar_one()


def test_create_policy_with_presentations(supervisor, company, catalog) -> None:
    _, presentations = catalog
    public = create_price_list(supervisor, company, code="PUB")
    created = create_policy(supervisor, company, public, presentations[:2])
    assert created["status"] == "ACTIVE" and created["markup_percentage"] == "15.0000"
    assert created["presentation_count"] == 2 and created["price_list_id"] == public["id"] and created["version"] == 1

    listed = supervisor.get(LIST_URL.format(company=company, price_list=public["id"])).json()
    assert [item["id"] for item in listed["items"]] == [created["id"]]
    assigned = supervisor.get(URL.format(id=created["id"]) + "/presentations").json()["items"]
    assert {item["company_product_presentation_id"] for item in assigned} == set(presentations[:2])
    terms = supervisor.get(URL.format(id=created["id"]) + "/terms").json()
    assert [(term["markup_percentage"], term["valid_to"]) for term in terms] == [("15.0000", None)]


def test_cp09_presentation_cannot_be_in_two_policies_of_the_same_list(supervisor, company, catalog) -> None:
    _, presentations = catalog
    public = create_price_list(supervisor, company, code="PUB")
    food = create_policy(supervisor, company, public, presentations[:1])

    response = supervisor.post(
        LIST_URL.format(company=company, price_list=public["id"]),
        json={"name": "Aseo", "markup_percentage": "25", "company_product_presentation_ids": presentations[:1]},
    )
    assert response.status_code == 409 and code_of(response) == "PRESENTATION_ALREADY_IN_POLICY"

    cleaning = create_policy(supervisor, company, public, name="Aseo", markup="25")
    response = supervisor.post(
        URL.format(id=cleaning["id"]) + "/presentations",
        json={"version": cleaning["version"], "company_product_presentation_ids": presentations[:1]},
    )
    assert response.status_code == 409 and code_of(response) == "PRESENTATION_ALREADY_IN_POLICY"
    assert supervisor.get(URL.format(id=food["id"])).json()["presentation_count"] == 1


def test_cp10_presentation_can_be_in_policies_of_different_lists(supervisor, company, catalog) -> None:
    _, presentations = catalog
    public = create_price_list(supervisor, company, code="PUB")
    wholesale = create_price_list(supervisor, company, code="MAY")
    create_policy(supervisor, company, public, presentations[:1])
    other = create_policy(supervisor, company, wholesale, presentations[:1], markup="20")
    assert other["presentation_count"] == 1


@pytest.mark.parametrize("markup", ["0", "1000", "12.3456"])
def test_cp11_cp12_markup_limits_accepted(supervisor, company, markup) -> None:
    public = create_price_list(supervisor, company)
    created = create_policy(supervisor, company, public, markup=markup)
    assert created["markup_percentage"] == format(float(markup), ".4f")


@pytest.mark.parametrize("markup", ["-1", "-0.0001", "1000.0001", "12.34567", True])
def test_cp13_cp14_markup_out_of_range_rejected(supervisor, company, markup) -> None:
    public = create_price_list(supervisor, company)
    response = supervisor.post(
        LIST_URL.format(company=company, price_list=public["id"]),
        json={"name": "X", "markup_percentage": markup, "company_product_presentation_ids": []},
    )
    assert response.status_code == 422
    if markup is not True:
        assert code_of(response) == "MARKUP_PERCENTAGE_OUT_OF_RANGE"


def test_name_unique_per_list_case_insensitive(supervisor, company) -> None:
    public = create_price_list(supervisor, company, code="PUB")
    create_policy(supervisor, company, public, name="Alimentos")
    response = supervisor.post(
        LIST_URL.format(company=company, price_list=public["id"]),
        json={"name": " alimentos ", "markup_percentage": "10", "company_product_presentation_ids": []},
    )
    assert response.status_code == 409 and code_of(response) == "POLICY_NAME_DUPLICATE"
    create_policy(supervisor, company, create_price_list(supervisor, company, code="MAY"), name="Alimentos")


def test_cp15_percentage_change_keeps_prices_and_history(supervisor, company, catalog, test_engine) -> None:
    product, presentations = catalog
    public = create_price_list(supervisor, company, code="PUB")
    create_price(supervisor, company, public, product, company_product_presentation_id=presentations[0])
    policy = create_policy(supervisor, company, public, presentations[:1], markup="20")
    before = price_count(test_engine)

    changed = supervisor.post(URL.format(id=policy["id"]) + "/percentage", json={"version": 1, "markup_percentage": "30"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["markup_percentage"] == "30.0000" and changed.json()["version"] == 2
    terms = supervisor.get(URL.format(id=policy["id"]) + "/terms").json()
    assert [term["markup_percentage"] for term in terms] == ["20.0000", "30.0000"]
    assert terms[0]["valid_to"] is not None and terms[1]["valid_to"] is None
    assert price_count(test_engine) == before  # RC-021-2: sin cambios de precio

    same = supervisor.post(URL.format(id=policy["id"]) + "/percentage", json={"version": 2, "markup_percentage": "30.0"})
    assert same.status_code == 200 and same.json()["version"] == 2  # sin cambio: sin término nuevo
    assert len(supervisor.get(URL.format(id=policy["id"]) + "/terms").json()) == 2


def test_cp16_remove_presentation_closes_assignment_without_touching_prices(supervisor, company, catalog, test_engine) -> None:
    product, presentations = catalog
    public = create_price_list(supervisor, company, code="PUB")
    create_price(supervisor, company, public, product, company_product_presentation_id=presentations[0])
    policy = create_policy(supervisor, company, public, presentations[:2])
    before = price_count(test_engine)

    removed = supervisor.post(
        URL.format(id=policy["id"]) + "/presentations/remove",
        json={"version": 1, "company_product_presentation_ids": presentations[:1]},
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["presentation_count"] == 1 and removed.json()["version"] == 2
    current = supervisor.get(URL.format(id=policy["id"]) + "/presentations").json()["items"]
    assert [item["company_product_presentation_id"] for item in current] == [presentations[1]]
    every = supervisor.get(URL.format(id=policy["id"]) + "/presentations", params={"include_closed": "true"}).json()
    assert every["total_records"] == 2
    assert price_count(test_engine) == before

    again = supervisor.post(
        URL.format(id=policy["id"]) + "/presentations/remove",
        json={"version": 2, "company_product_presentation_ids": presentations[:1]},
    )
    assert again.status_code == 409 and code_of(again) == "PRESENTATION_NOT_IN_POLICY"


def test_assigning_a_presentation_already_in_the_policy_is_a_no_op(supervisor, company, catalog) -> None:
    _, presentations = catalog
    policy = create_policy(supervisor, company, create_price_list(supervisor, company), presentations[:1])
    response = supervisor.post(
        URL.format(id=policy["id"]) + "/presentations",
        json={"version": 1, "company_product_presentation_ids": presentations[:2]},
    )
    assert response.status_code == 200 and response.json()["presentation_count"] == 2
    assigned = supervisor.get(URL.format(id=policy["id"]) + "/presentations").json()["total_records"]
    assert assigned == 2


def test_cpt19_deactivated_policy_is_final_and_frees_its_presentations(supervisor, company, catalog) -> None:
    _, presentations = catalog
    public = create_price_list(supervisor, company, code="PUB")
    policy = create_policy(supervisor, company, public, presentations[:1])

    deactivated = supervisor.post(URL.format(id=policy["id"]) + "/deactivate", json={"version": 1, "reason": "Reorganización"})
    assert deactivated.status_code == 200, deactivated.text
    body = deactivated.json()
    assert body["status"] == "INACTIVE" and body["deactivated_at"] and body["presentation_count"] == 0
    assert supervisor.get(URL.format(id=policy["id"]) + "/terms").json()[0]["valid_to"] is not None

    for suffix, payload in (
        ("/percentage", {"version": 2, "markup_percentage": "40"}),
        ("/presentations", {"version": 2, "company_product_presentation_ids": presentations[1:2]}),
        ("/deactivate", {"version": 2, "reason": "Otra vez"}),
    ):
        response = supervisor.post(URL.format(id=policy["id"]) + suffix, json=payload)
        assert response.status_code == 409 and code_of(response) == "POLICY_INACTIVE", suffix
    assert supervisor.post(URL.format(id=policy["id"]) + "/reactivate", json={"version": 2}).status_code in (404, 405)

    reused = create_policy(supervisor, company, public, presentations[:1], name="Alimentos")  # el nombre y la presentación quedan libres
    assert reused["presentation_count"] == 1


def test_validations_on_create(admin, supervisor, company, catalog, fake_catalog) -> None:
    product, presentations = catalog
    inactive = create_price_list(supervisor, company, code="OFF")
    # Inactivar listas exige `price_lists:delete` (solo administradores).
    assert admin.post(f"/api/v1/price-lists/{inactive['id']}/deactivate", json={"version": 1}).status_code == 200
    response = supervisor.post(
        LIST_URL.format(company=company, price_list=inactive["id"]),
        json={"name": "X", "markup_percentage": "10", "company_product_presentation_ids": []},
    )
    assert response.status_code == 422 and code_of(response) == "PRICE_LIST_INACTIVE"

    public = create_price_list(supervisor, company, code="PUB")
    url = LIST_URL.format(company=company, price_list=public["id"])
    unknown = supervisor.post(url, json={"name": "X", "markup_percentage": "10", "company_product_presentation_ids": [str(uuid4())]})
    assert unknown.status_code == 422 and code_of(unknown) == "PRESENTATION_NOT_FOUND"

    not_sellable = adopt_presentation(supervisor, company, fake_catalog, product, is_sellable=False)
    response = supervisor.post(url, json={"name": "X", "markup_percentage": "10", "company_product_presentation_ids": [not_sellable["id"]]})
    assert response.status_code == 422 and code_of(response) == "PRESENTATION_NOT_SELLABLE"

    too_many = supervisor.post(url, json={"name": "X", "markup_percentage": "10", "company_product_presentation_ids": [str(uuid4()) for _ in range(101)]})
    assert too_many.status_code == 422

    repeated = supervisor.post(url, json={"name": "X", "markup_percentage": "10", "company_product_presentation_ids": presentations[:1] * 2})
    assert repeated.status_code == 201 and repeated.json()["presentation_count"] == 1


def test_rename_and_version_conflict(supervisor, company) -> None:
    policy = create_policy(supervisor, company, create_price_list(supervisor, company))
    renamed = supervisor.put(URL.format(id=policy["id"]), json={"version": 1, "name": "Canasta básica"})
    assert renamed.status_code == 200 and renamed.json()["name"] == "Canasta básica" and renamed.json()["version"] == 2
    stale = supervisor.put(URL.format(id=policy["id"]), json={"version": 1, "name": "Otra"})
    assert stale.status_code == 409 and code_of(stale) == "VERSION_CONFLICT"


def test_audit_events(supervisor, company, catalog, outbox, clear_outbox) -> None:
    _, presentations = catalog
    public = create_price_list(supervisor, company)
    clear_outbox()
    policy = create_policy(supervisor, company, public, presentations[:1], markup="20")
    url = URL.format(id=policy["id"])
    supervisor.post(url + "/percentage", json={"version": 1, "markup_percentage": "30"})
    supervisor.post(url + "/presentations", json={"version": 2, "company_product_presentation_ids": presentations[1:2]})
    supervisor.post(url + "/presentations/remove", json={"version": 3, "company_product_presentation_ids": presentations[:1]})
    supervisor.put(url, json={"version": 4, "name": "Canasta"})
    supervisor.post(url + "/deactivate", json={"version": 5, "reason": "Fin de temporada"})

    events = outbox()
    assert [event["action"] for event in events] == [
        "CREATE_PRICING_POLICY",
        "CHANGE_PRICING_POLICY_PERCENTAGE",
        "ASSIGN_PRICING_POLICY_PRESENTATION",
        "UNASSIGN_PRICING_POLICY_PRESENTATION",
        "UPDATE_PRICING_POLICY",
        "DEACTIVATE_PRICING_POLICY",
    ]
    assert all(event["entity_type"] == "PricingPolicy" and event["entity_id"] == policy["id"] for event in events)
    assert events[0]["new_values"]["markup_percentage"] == "20.0000"
    assert events[0]["new_values"]["company_product_presentation_ids"] == presentations[:1]
    assert events[1]["previous_values"]["markup_percentage"] == "20.0000"
    assert events[1]["new_values"]["markup_percentage"] == "30.0000"
    assert events[2]["new_values"]["assigned_presentation_ids"] == presentations[1:2]
    assert events[3]["new_values"]["removed_presentation_ids"] == presentations[:1]
    assert events[5]["reason"] == "Fin de temporada"
