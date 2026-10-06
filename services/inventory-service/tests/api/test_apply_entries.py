"""Entradas de compra (Historia 1; FR-010 a FR-018; RC-04, RC-07, RC-10; T025)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.conftest import count_rows, line, operation_body, service_sub

ENTRIES = "/api/v1/inventory-entries"


def balance(test_engine, world, product, branch=None) -> str:
    """Saldo leído directamente de la base (la consulta por API es de la US5)."""
    with test_engine.connect() as connection:
        value = connection.execute(
            text("SELECT quantity FROM inventory_balances WHERE company_id = :c AND branch_id = :b AND company_product_id = :p"),
            {"c": world.company, "b": branch or world.branch, "p": product},
        ).scalar_one_or_none()
    return f"{value if value is not None else 0:.4f}"


def nothing_written(test_engine) -> bool:
    return all(count_rows(test_engine, t) == 0 for t in ("inventory_operations", "inventory_movements", "inventory_balances"))


def errors_of(response) -> dict[str, str]:
    return {error["field"]: error["code"] for error in response.json()["errors"]}


def test_first_entry_creates_balances_and_kardex(operator, test_engine, world, fake_oc) -> None:
    p1, p2 = world.products[:2]
    body = operation_body(world, line(p1, "10", unit_cost="1500.25"), line(p2, 5.5))
    response = operator.post(ENTRIES, json=body)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["operation_type"] == "ENTRY"
    assert data["operation_key"] == body["operation_key"]
    assert data["created_by"] == service_sub("inventory-test-operator")
    assert data["application_user_id"] == str(world.user)
    assert data["reverses_operation_id"] is None and data["reversed_by_operation_id"] is None
    first, second = data["movements"]
    assert (first["movement_type"], first["quantity"], first["previous_balance"], first["new_balance"]) == (
        "PURCHASE_ENTRY", "10.0000", "0.0000", "10.0000"
    )
    assert first["unit_cost"] == "1500.2500" and first["balance_sequence"] == 1 and first["line_index"] == 0
    assert (second["quantity"], second["new_balance"], second["unit_cost"]) == ("5.5000", "5.5000", None)
    assert {b["company_product_id"]: b["quantity"] for b in data["balances"]} == {str(p1): "10.0000", str(p2): "5.5000"}
    assert balance(test_engine, world, p1) == "10.0000"


def test_second_entry_adds_to_the_balance(operator, test_engine, world) -> None:
    product = world.products[0]
    operator.post(ENTRIES, json=operation_body(world, line(product, "10")))
    response = operator.post(ENTRIES, json=operation_body(world, line(product, "5.5")))
    movement = response.json()["movements"][0]
    assert (movement["previous_balance"], movement["new_balance"], movement["balance_sequence"]) == ("10.0000", "15.5000", 2)
    assert balance(test_engine, world, product) == "15.5000"


def test_unit_cost_is_optional(operator, world) -> None:
    response = operator.post(ENTRIES, json=operation_body(world, line(world.products[0], "1")))
    assert response.status_code == 201
    assert response.json()["movements"][0]["unit_cost"] is None


def test_product_of_other_company_rejects_whole_operation(operator, world, test_engine) -> None:
    body = operation_body(world, line(world.products[0], "1"), line(world.products[1], "1"), line(world.other_company_product, "1"))
    response = operator.post(ENTRIES, json=body)
    assert response.status_code == 422
    assert errors_of(response) == {"lines[2].company_product_id": "COMPANY_PRODUCT_NOT_FOUND"}
    assert nothing_written(test_engine)


@pytest.mark.parametrize(
    ("product_kwargs", "code"),
    [
        ({"inventory_control_enabled": False}, "INVENTORY_CONTROL_DISABLED"),
        ({"status": "INACTIVE"}, "COMPANY_PRODUCT_INACTIVE"),
    ],
)
def test_product_not_apt(operator, world, fake_cr, test_engine, product_kwargs, code) -> None:
    product = fake_cr.add_product(world.company, **product_kwargs)
    response = operator.post(ENTRIES, json=operation_body(world, line(product, "1")))
    assert response.status_code == 422
    assert errors_of(response) == {"lines[0].company_product_id": code}
    assert nothing_written(test_engine)


def test_unknown_product(operator, world, test_engine) -> None:
    response = operator.post(ENTRIES, json=operation_body(world, line(uuid4(), "1")))
    assert errors_of(response) == {"lines[0].company_product_id": "COMPANY_PRODUCT_NOT_FOUND"}


@pytest.mark.parametrize(
    ("setup", "field", "code"),
    [
        (lambda w, oc: {"branch_id": str(uuid4())}, "branch_id", "BRANCH_NOT_FOUND"),
        (lambda w, oc: {"branch_id": str(w.other_company_branch)}, "branch_id", "BRANCH_NOT_IN_COMPANY"),
        (lambda w, oc: {"branch_id": str(oc.add_branch(w.company, status="INACTIVE"))}, "branch_id", "BRANCH_INACTIVE"),
        (lambda w, oc: {"branch_id": str(oc.add_branch(w.company, company_status="INACTIVE"))}, "company_id", "COMPANY_INACTIVE"),
        (lambda w, oc: {"application_user_id": str(uuid4())}, "application_user_id", "APPLICATION_USER_NOT_FOUND"),
        (lambda w, oc: {"application_user_id": str(w.other_company_user)}, "application_user_id", "APPLICATION_USER_NOT_FOUND"),
        (lambda w, oc: {"application_user_id": str(oc.add_user(w.company, status="INACTIVE"))}, "application_user_id", "APPLICATION_USER_INACTIVE"),
    ],
)
def test_invalid_operational_references(operator, world, fake_oc, test_engine, setup, field, code) -> None:
    body = operation_body(world, line(world.products[0], "1"), **setup(world, fake_oc))
    response = operator.post(ENTRIES, json=body)
    assert response.status_code == 422, response.text
    assert errors_of(response)[field] == code
    assert nothing_written(test_engine)


@pytest.mark.parametrize(
    ("change", "field", "code"),
    [
        (lambda b: b.update(lines=[]), "lines", "LINES_OUT_OF_RANGE"),
        (lambda b: b.update(lines=[line(uuid4(), "1") for _ in range(101)]), "lines", "LINES_OUT_OF_RANGE"),
        (lambda b: b["lines"][0].update(quantity="0"), "lines[0].quantity", "QUANTITY_NOT_POSITIVE"),
        (lambda b: b["lines"][0].update(quantity="-1"), "lines[0].quantity", "QUANTITY_NOT_POSITIVE"),
        (lambda b: b["lines"][0].update(quantity="1.00001"), "lines[0].quantity", "TOO_MANY_DECIMALS"),
        (lambda b: b["lines"][0].update(quantity="abc"), "lines[0].quantity", "INVALID_FORMAT"),
        (lambda b: b["lines"][0].update(unit_cost="-1"), "lines[0].unit_cost", "UNIT_COST_NEGATIVE"),
        (lambda b: b.update(origin_type="SALE"), "origin_type", "ORIGIN_TYPE_MISMATCH"),
        (lambda b: b.update(extra="x"), "extra", "UNKNOWN_FIELD"),
        (lambda b: b["lines"][0].update(source_service="x"), "lines[0].source_service", "UNKNOWN_FIELD"),
        (lambda b: b.pop("correlation_id"), "correlation_id", "REQUIRED"),
        (lambda b: b.update(operation_key="no-uuid"), "operation_key", "INVALID_FORMAT"),
    ],
)
def test_format_errors(operator, world, test_engine, change, field, code) -> None:
    body = operation_body(world, line(world.products[0], "1"))
    change(body)
    response = operator.post(ENTRIES, json=body)
    assert response.status_code == 422, response.text
    assert errors_of(response).get(field) == code, response.json()["errors"]
    assert nothing_written(test_engine)


def test_duplicate_origin_detail(operator, world, test_engine) -> None:
    detail = uuid4()
    body = operation_body(world, line(world.products[0], "1", origin_detail_id=detail), line(world.products[1], "1", origin_detail_id=detail))
    response = operator.post(ENTRIES, json=body)
    assert errors_of(response) == {"lines[1].origin_detail_id": "DUPLICATE_ORIGIN_DETAIL"}
    assert nothing_written(test_engine)


def test_resulting_balance_out_of_range(operator, world, test_engine) -> None:
    product = world.products[0]
    assert operator.post(ENTRIES, json=operation_body(world, line(product, "99999999999999"))).status_code == 201
    response = operator.post(ENTRIES, json=operation_body(world, line(product, "1")))
    assert response.status_code == 422
    assert errors_of(response) == {"lines[0].quantity": "QUANTITY_OUT_OF_RANGE"}
    assert count_rows(test_engine, "inventory_movements") == 1


@pytest.mark.parametrize(("fake", "dependency"), [("fake_oc", "operational-context"), ("fake_cr", "commercial-relationship")])
def test_dependency_unavailable_applies_nothing(operator, world, test_engine, request, fake, dependency) -> None:
    request.getfixturevalue(fake).unavailable = True
    response = operator.post(ENTRIES, json=operation_body(world, line(world.products[0], "1")))
    assert response.status_code == 503
    assert response.json()["dependency"] == dependency
    assert nothing_written(test_engine)


def test_never_touches_other_company_or_branch(operator, test_engine, world) -> None:
    product = world.products[0]
    operator.post(ENTRIES, json=operation_body(world, line(product, "3")))
    assert balance(test_engine, world, product, branch=world.other_branch) == "0.0000"
