"""Huella de filtros normalizados (T087; FR-022-148, CP-122, CP-123)."""

from __future__ import annotations

import unicodedata
from uuid import uuid4

from product_inventory_query_service.api.filters.query_params import parse_query
from product_inventory_query_service.domain.fingerprint import fingerprint
from product_inventory_query_service.domain.query_spec import Endpoint

COMPANY = uuid4()
A, B = sorted([uuid4(), uuid4()], key=str)


def fp(*pairs, endpoint=Endpoint.PRODUCT_OVERVIEWS, company=COMPANY) -> str:
    return fingerprint(parse_query(endpoint, company, list(pairs)))


def test_same_fingerprint_for_equivalent_queries() -> None:
    base = fp(("search", "crema dental"), ("brand_id", str(A)), ("brand_id", str(B)), ("has_image", "true"))
    equivalents = [
        fp(("has_image", "true"), ("brand_id", str(B)), ("search", "crema dental"), ("brand_id", str(A))),
        fp(("search", "  Crema   DENTAL "), ("brand_id", str(A)), ("brand_id", str(B)), ("has_image", "1")),
        fp(("search", "crema dental"), ("brand_id", str(B).upper()), ("brand_id", str(A)), ("brand_id", str(A)),
           ("has_image", "true")),
        fp(("search", "crema dental"), ("brand_id", str(A)), ("brand_id", str(B)), ("has_image", "true"),
           ("status", "ACTIVE"), ("scope", "COMPANY"), ("include_descendants", "false")),
    ]
    assert all(value == base for value in equivalents)


def test_nfc_and_nfd_are_the_same() -> None:
    word = "acetaminofén"
    assert fp(("search", unicodedata.normalize("NFC", word))) == fp(("search", unicodedata.normalize("NFD", word)))


def test_empty_search_equals_absent() -> None:
    assert fp(("search", "   ")) == fp()


def test_sort_page_size_and_cursor_are_not_part_of_the_fingerprint() -> None:
    assert fp() == fp(("sort", "internal_code:desc"), ("page_size", "5"), ("cursor", "v1.a.b"))


def test_different_fingerprints() -> None:
    assert fp(("search", "acetaminofen")) != fp(("search", "acetaminofén"))
    assert fp() != fp(("price_list_id", str(uuid4())))
    branch = uuid4()
    assert fp(("scope", "COMPANY")) != fp(("branch_id", str(branch)))
    assert fp() != fp(company=uuid4())
    assert fp(endpoint=Endpoint.PRODUCT_OVERVIEWS) != fp(endpoint=Endpoint.INVENTORY_OVERVIEWS)
    assert fp(("has_image", "true")) != fp(("has_image", "false"))
    assert fp(("status", "ACTIVE")) != fp(("status", "ALL"))
