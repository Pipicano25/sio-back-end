"""Forma canónica y huella determinista `request_hash` (R-03; T007)."""

from __future__ import annotations

import re
from copy import deepcopy
from decimal import Decimal
from uuid import UUID

from inventory_service.domain.canonical import canonical_json, request_hash

CLIENT = "inventory-test-operator"


def payload() -> dict:
    return {
        "company_id": UUID("7c1e0000-0000-4000-8000-0000000000aa"),
        "branch_id": UUID("b2a00000-0000-4000-8000-0000000000bb"),
        "origin_type": "PURCHASE",
        "origin_id": UUID("0d4e0000-0000-4000-8000-0000000000cc"),
        "application_user_id": UUID("a41f0000-0000-4000-8000-0000000000dd"),
        "correlation_id": UUID("9e3b0000-0000-4000-8000-0000000000ee"),
        "reason": None,
        "reverses_operation_id": None,
        "lines": [
            {
                "origin_detail_id": UUID("11aa0000-0000-4000-8000-000000000001"),
                "company_product_id": UUID("e9a00000-0000-4000-8000-000000000001"),
                "quantity": Decimal("10"),
                "unit_cost": Decimal("1500.25"),
            },
            {
                "origin_detail_id": UUID("11aa0000-0000-4000-8000-000000000002"),
                "company_product_id": UUID("e9a00000-0000-4000-8000-000000000002"),
                "quantity": Decimal("5.5"),
                "unit_cost": None,
            },
        ],
    }


def test_hash_format_and_determinism() -> None:
    first = request_hash(payload(), CLIENT, "ENTRY")
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert first == request_hash(payload(), CLIENT, "ENTRY")


def test_same_request_in_other_representation_has_same_hash() -> None:
    base = request_hash(payload(), CLIENT, "ENTRY")
    other = payload()
    # Otro orden de claves, UUID en mayúsculas como texto y decimales con ceros a la derecha.
    other = dict(reversed(list(other.items())))
    other["company_id"] = "7C1E0000-0000-4000-8000-0000000000AA"
    other["lines"][0]["quantity"] = Decimal("10.0000")
    other["lines"][1]["quantity"] = Decimal("5.50")
    other["lines"][0] = dict(reversed(list(other["lines"][0].items())))
    assert request_hash(other, CLIENT, "ENTRY") == base


def _changed(mutator) -> str:
    data = deepcopy(payload())
    mutator(data)
    return request_hash(data, CLIENT, "ENTRY")


def test_any_difference_changes_the_hash() -> None:
    base = request_hash(payload(), CLIENT, "ENTRY")
    variants = [
        lambda d: d["lines"][0].update(quantity=Decimal("11")),
        lambda d: d["lines"][0].update(unit_cost=Decimal("1500.26")),
        lambda d: d["lines"][1].update(unit_cost=Decimal("0")),
        lambda d: d["lines"].pop(),
        lambda d: d["lines"].reverse(),
        lambda d: d.update(application_user_id=UUID("a41f0000-0000-4000-8000-0000000000de")),
        lambda d: d.update(company_id=UUID("7c1e0000-0000-4000-8000-0000000000ab")),
        lambda d: d.update(reason="otro"),
    ]
    hashes = {_changed(variant) for variant in variants}
    assert base not in hashes
    assert len(hashes) == len(variants)


def test_client_and_type_are_part_of_the_hash() -> None:
    base = request_hash(payload(), CLIENT, "ENTRY")
    assert request_hash(payload(), "otro-cliente", "ENTRY") != base
    assert request_hash(payload(), CLIENT, "OUTPUT") != base


def test_canonical_json_is_compact_sorted_and_lowercase() -> None:
    text = canonical_json({"b": UUID("7C1E0000-0000-4000-8000-0000000000AA"), "a": Decimal("1.500"), "c": " x "})
    assert text == '{"a":"1.5","b":"7c1e0000-0000-4000-8000-0000000000aa","c":"x"}'
