"""Contrato OpenAPI frente a `contracts/rest-api.md` y `contracts/errors.md` (Principio XI; T084)."""

from __future__ import annotations

import re
from pathlib import Path

from purchase_service.api.errors import _STATUS_BY_CODE
from tests.api.routes import ROUTES

SPEC = Path(__file__).resolve().parents[4] / "specs" / "014-purchase-core" / "contracts"
SPEC_020 = Path(__file__).resolve().parents[4] / "specs" / "020-mvp-commercial-rules" / "contracts" / "purchase.md"
DOCUMENTED_EXTRA: set[str] = set()  # D-01 incorporado al catálogo (2026-10-07)


def test_routes_and_methods_match_the_contract(test_client) -> None:
    schema = test_client.get("/openapi.json").json()
    declared = {
        (method.upper(), path)
        for path, item in schema["paths"].items()
        for method in item
        if method in {"get", "post", "put", "delete", "patch"}
    }
    expected = {(method, path.split("?")[0].format(
        company="{company_id}", purchase="{purchase_id}", detail="{detail_id}", operation="{operation_id}", sequence="{sequence_id}"
    )) for method, path, _ in ROUTES}
    assert expected <= declared
    business = {(method, path) for method, path in declared if path.startswith("/api/v1")}
    assert business == expected


def test_every_route_documents_auth_and_problem_responses(test_client) -> None:
    schema = test_client.get("/openapi.json").json()
    for path, item in schema["paths"].items():
        if not path.startswith("/api/v1"):
            continue
        for method, operation in item.items():
            responses = operation["responses"]
            assert {"401", "403", "503"} <= set(responses), (method, path)
            assert operation["security"] == [{"BearerAuth": []}]


def test_error_codes_match_the_catalog() -> None:
    catalog = (SPEC / "errors.md").read_text(encoding="utf-8") + SPEC_020.read_text(encoding="utf-8")
    documented = dict(re.findall(r"^\| `([A-Z_]+)` \| (\d{3}) \|", catalog, re.M))
    assert documented, "catálogo vacío"
    for code, status in documented.items():
        assert _STATUS_BY_CODE.get(code) == int(status), code
    assert set(_STATUS_BY_CODE) - set(documented) == DOCUMENTED_EXTRA


def test_contract_route_table_lists_the_same_routes() -> None:
    table = (SPEC / "rest-api.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| \d+ \| `(GET|POST|PUT|DELETE) ([^`]+)`", table, re.M)
    assert len(rows) == 19
    paths = {(method, path.split("?")[0].split(" ·")[0]) for method, path in rows}
    assert ("POST", "/companies/{c}/purchases/{id}/confirmation") in paths
    assert ("DELETE", "/companies/{c}/purchases/{id}/details/{detail_id}") in paths
    additions = re.findall(r"^\| \d+ \| `(GET|POST|PUT|DELETE) ([^`]+)`", SPEC_020.read_text(encoding="utf-8"), re.M)
    assert additions == [("POST", "/companies/{c}/purchases/{id}/receipt")]  # spec 020
