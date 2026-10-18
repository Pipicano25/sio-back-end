"""Concatenación de páginas frente al oráculo (T122 y T123; CP-130, CP-131, CP-135; SC-022-2).

Con semilla fija se generan al menos 200 combinaciones de endpoint, filtros, alcance de sucursales, `page_size`
(1 a 20) y orden. Para cada una se recorren **todas** las páginas por la API con `next_cursor` y la concatenación
debe ser idéntica, en contenido y en orden, a la evaluación de fuerza bruta: sin duplicados ni omisiones.

- T122: límite de trabajo de la configuración (5 lotes).
- T123: límite bajo (`max_batches = 1`) que fuerza respuestas parciales con cursor `SCAN`, y el caso CP-135.
"""

from __future__ import annotations

import random
from dataclasses import replace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from product_inventory_query_service.api.filters.query_params import parse_query
from product_inventory_query_service.application.listing import Ports
from product_inventory_query_service.domain.query_spec import Endpoint
from product_inventory_query_service.main import create_app
from tests.conftest import build_test_settings
from tests.oracle.brute_force import expected
from tests.oracle.dataset import NAMES, build
from tests.oracle.fakes import load

COMBINATIONS = 200
SEED = 2022


def combinations(data, count: int, seed: int) -> list[tuple[Endpoint, list[tuple[str, str]]]]:
    rng = random.Random(seed)
    products = data.products
    result = []
    while len(result) < count:
        endpoint = rng.choice(list(Endpoint))
        params: list[tuple[str, str]] = []

        def maybe(probability: float) -> bool:
            return rng.random() < probability

        if maybe(0.35):
            params.append(("search", rng.choice([name[: rng.randint(1, 4)].lower() for name in NAMES] + ["0", "1"])))
        if maybe(0.08):
            params.append(("internal_code", rng.choice(products).internal_code.lower()))
        if maybe(0.08):
            with_sku = [p for p in products if p.skus]
            params.append(("sku", rng.choice(rng.choice(with_sku).skus)))
        if maybe(0.08):
            with_code = [p for p in products if p.identifiers]
            params.append((rng.choice(["barcode", "identifier"]), rng.choice(with_code).identifiers[0]))
        for _ in range(rng.choice([0, 0, 1, 2])):
            params.append(("brand_id", str(rng.choice(data.brands))))
        for _ in range(rng.choice([0, 0, 0, 1, 2])):
            params.append(("category_id", str(rng.choice(data.categories))))
        if maybe(0.2):
            params.append(("has_image", rng.choice(["true", "false"])))
        if maybe(0.15):
            params.append(("status", rng.choice(["ACTIVE", "INACTIVE", "ALL"])))
        if maybe(0.1):
            params.append(("product_type", rng.choice(["GOOD", "SERVICE"])))
        if endpoint is not Endpoint.LOW_STOCK_PRODUCTS and maybe(0.3):
            params.append(("stock_state", rng.choice(["IN_STOCK", "OUT_OF_STOCK"])))
        if endpoint is Endpoint.INVENTORY_OVERVIEWS and maybe(0.3):
            params.append(("minimum_state", rng.choice(["NO_POLICY", "BELOW_MINIMUM", "AT_MINIMUM", "ABOVE_MINIMUM"])))
        if maybe(0.4):
            for branch in rng.sample(data.branches, rng.randint(1, len(data.branches))):
                params.append(("branch_id", str(branch)))
        if maybe(0.35):
            key = rng.choice(["display_name", "internal_code", "created_at"])
            params.append(("sort", key + rng.choice(["", ":asc", ":desc"])))
        params.append(("page_size", str(rng.choice([1, 2, 3, 5, 7, 10, 13, 20]))))
        rng.shuffle(params)
        result.append((endpoint, params))
    return result


def key_of(endpoint: Endpoint, item: dict):
    if endpoint is Endpoint.LOW_STOCK_PRODUCTS:
        return item["company_product_id"], item["branch_id"]
    return item["company_product_id"]


def walk(client, base: str, endpoint: Endpoint, params: list[tuple[str, str]]) -> tuple[list, list[dict]]:
    keys, pages, cursor = [], [], None
    for _ in range(2000):
        query = params + ([("cursor", cursor)] if cursor else [])
        response = client.get(f"{base}/{endpoint.value}", params=query)
        assert response.status_code == 200, (params, response.text)
        body = response.json()
        assert len(body["items"]) <= int(dict(params)["page_size"])
        assert body["pagination_reset"] is False
        pages.append(body)
        keys.extend(key_of(endpoint, item) for item in body["items"])
        if not body["has_next"]:
            assert body["next_cursor"] is None
            return keys, pages
        cursor = body["next_cursor"]
    raise AssertionError(f"el recorrido no terminó: {params}")


@pytest.fixture(scope="module")
def data():
    return build()


def oracle_client(data, test_auth, user_token, **overrides):
    fakes = load(data)
    app = create_app(build_test_settings(**overrides), auth=test_auth, jwks_probe=lambda: True,
                     ports_factory=lambda authorization: Ports(fakes.oc, fakes.cr, fakes.pc, fakes.inventory))
    client = TestClient(app, raise_server_exceptions=False)
    client.headers["Authorization"] = f"Bearer {user_token('supervisor.test')}"
    return client, fakes


def check(client, fakes, data, endpoint, params) -> list[dict]:
    spec = parse_query(endpoint, data.company, params)
    branches = list(spec.branch_ids) if spec.branch_ids else list(data.branches)
    created_at = {p.id: p.created_at.isoformat() for p in fakes.cr.products}
    keys, pages = walk(client, f"/api/v1/companies/{data.company}", endpoint, params)
    assert keys == expected(spec, data, branches, created_at), params
    assert len(keys) == len(set(keys)), params
    sorts = {page["sort_applied"] for page in pages}
    assert len(sorts) == 1, params  # CP-154: el mismo orden en todas las páginas
    return pages


def test_pages_match_the_oracle(data, test_auth, user_token) -> None:
    """CP-130: al menos 200 combinaciones con el límite de trabajo de la configuración."""
    client, fakes = oracle_client(data, test_auth, user_token)
    cases = combinations(data, COMBINATIONS, SEED)
    non_empty = 0
    for endpoint, params in cases:
        pages = check(client, fakes, data, endpoint, params)
        non_empty += any(page["items"] for page in pages)
    assert len(cases) >= 200
    assert non_empty >= COMBINATIONS // 2  # las combinaciones no son triviales: la mayoría trae resultados


def test_pages_match_the_oracle_with_a_low_work_limit(data, test_auth, user_token) -> None:
    """CP-131 y T123: `max_batches = 1` fuerza respuestas parciales con cursor `SCAN`; el resultado no cambia."""
    client, fakes = oracle_client(data, test_auth, user_token, max_batches_per_request=1, batch_min=5, batch_max=5,
                                  batch_factor=1)
    partial = 0
    for endpoint, params in combinations(data, COMBINATIONS, SEED + 1):
        pages = check(client, fakes, data, endpoint, params)
        partial += sum(1 for page in pages if page["partial"])
    assert partial > 0  # el límite bajo sí produjo respuestas parciales


def test_name_changed_between_pages_is_the_documented_behavior(data, test_auth, user_token) -> None:
    """CP-135 y FR-022-67: la posición garantiza exactitud con datos sin cambios; si un nombre cambia entre
    páginas, el producto aparece según su nueva posición. Aquí, renombrado detrás del cursor, se entrega de nuevo
    en la página que le corresponde; nada falla y el recorrido termina."""
    client, fakes = oracle_client(data, test_auth, user_token)
    base = f"/api/v1/companies/{data.company}/product-overviews"
    params = [("status", "ALL"), ("page_size", "10")]
    first = client.get(base, params=params).json()
    moved = UUID(first["items"][0]["company_product_id"])
    index = next(i for i, p in enumerate(fakes.cr.products) if p.id == moved)
    fakes.cr.products[index] = replace(fakes.cr.products[index], display_name="Zzz renombrado")
    keys, cursor = [item["company_product_id"] for item in first["items"]], first["next_cursor"]
    while cursor:
        body = client.get(base, params=params + [("cursor", cursor)]).json()
        keys.extend(item["company_product_id"] for item in body["items"])
        cursor = body["next_cursor"]
    assert keys.count(str(moved)) == 2 and keys[-1] == str(moved)
