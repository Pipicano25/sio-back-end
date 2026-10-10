"""Lecturas de los datos de referencia cargados por los seeds (E-08).

Se usan en el preflight y como primeros pasos del recorrido. Solo lecturas por API.
"""

from __future__ import annotations

from dataclasses import dataclass

from sio_mvp.auth import ApiClient

COUNTRY_ISO3 = "COL"
CITY_SEARCH = "Bogot"
BASE_UNIT_CODE = "UND"


class ReferenceError_(AssertionError):
    """Falta un dato de referencia que deben cargar los seeds."""


def _items(response, what: str) -> list[dict]:
    if response.status != 200:
        raise ReferenceError_(f"{what}: HTTP {response.status}")
    return list((response.body or {}).get("items", []))


def colombia(client: ApiClient, step_id: str) -> dict:
    items = _items(client.get("geography", "/global-countries", params={"iso3_code": COUNTRY_ISO3}, step_id=step_id), "Geography COL")
    if len(items) != 1:
        raise ReferenceError_(f"Geography: se esperaba 1 país {COUNTRY_ISO3}, hay {len(items)}")
    return items[0]


def city(client: ApiClient, country_id: str, step_id: str) -> dict:
    items = _items(
        client.get("geography", "/global-cities", params={"country_id": country_id, "search": CITY_SEARCH}, step_id=step_id),
        "Geography ciudad",
    )
    if not items:
        raise ReferenceError_("Geography: sin ciudades de Colombia (seed)")
    return items[0]


def identification_rule(client: ApiClient, country_id: str, party_kind: str, sigla: str, step_id: str) -> dict:
    items = _items(
        client.get(
            "party-identity",
            "/identification-type-rules",
            params={"party_kind": party_kind, "country_id": country_id, "sigla": sigla, "is_active": "true"},
            step_id=step_id,
        ),
        f"Party Identity regla {party_kind}/{sigla}",
    )
    if not items:
        raise ReferenceError_(f"Party Identity: sin regla activa {party_kind}/{sigla} para Colombia (seed)")
    return items[0]


def unit_of_measure(client: ApiClient, step_id: str, code: str = BASE_UNIT_CODE) -> dict:
    items = _items(
        client.get("product-catalog", "/units-of-measure", params={"status": "ACTIVE", "page_size": 100}, step_id=step_id),
        "Product Catalog unidades",
    )
    for item in items:
        if item.get("code") == code:
            return item
    raise ReferenceError_(f"Product Catalog: sin unidad activa {code} (seed)")


def payment_condition_type(client: ApiClient, code: str, step_id: str) -> dict:
    items = _items(
        client.get("payment-reference", "/global-payment-condition-types", params={"page_size": 100}, step_id=step_id),
        "Payment Reference tipos de condición",
    )
    for item in items:
        if item.get("code") == code:
            return item
    raise ReferenceError_(f"Payment Reference: sin tipo de condición {code} (seed)")


@dataclass(frozen=True)
class References:
    country_id: str
    city_id: str
    division_id: str | None
    person_rule: dict
    organization_rule: dict
    unit_id: str
    credit_type_id: str


def load(client: ApiClient, step_prefix: str) -> References:
    country = colombia(client, f"{step_prefix}-pais")
    found_city = city(client, country["id"], f"{step_prefix}-ciudad")
    return References(
        country_id=country["id"],
        city_id=found_city["id"],
        division_id=found_city.get("administrative_division_id"),
        person_rule=identification_rule(client, country["id"], "PERSON", "CC", f"{step_prefix}-regla-persona"),
        organization_rule=identification_rule(client, country["id"], "ORGANIZATION", "NIT", f"{step_prefix}-regla-organizacion"),
        unit_id=unit_of_measure(client, f"{step_prefix}-unidad")["id"],
        credit_type_id=payment_condition_type(client, "CREDIT", f"{step_prefix}-tipo-credito")["id"],
    )
