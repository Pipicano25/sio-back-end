"""CR-2: campos aditivos del `batch-lookup` de presentaciones (spec 022, FR-022-81, FR-022-87; T016).

Purchase y Sales consumen este lote: los campos anteriores conservan nombre, tipo y valor.
"""

from __future__ import annotations

from uuid import uuid4

from tests.api.helpers import adopt, adopt_presentation

URL = "/api/v1/company-product-presentations/batch-lookup"

PREVIOUS_FIELDS = {
    "id",
    "found",
    "company_id",
    "company_product_id",
    "global_product_presentation_id",
    "is_purchasable",
    "is_sellable",
    "is_default_purchase",
    "is_default_sale",
    "status",
    "version",
}
ADDITIVE_FIELDS = {"internal_code", "sku", "reference_code"}


def test_batch_lookup_adds_codes_without_changing_previous_fields(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog)
    presentation = adopt_presentation(
        client, company, fake_catalog, product, internal_code="PI-1", sku="SKU-1", reference_code="REF-1", is_default_sale=True
    )

    items = client.post(URL, json={"ids": [presentation["id"]]}).json()["items"]
    item = items[0]
    assert set(item) == PREVIOUS_FIELDS | ADDITIVE_FIELDS
    assert (item["internal_code"], item["sku"], item["reference_code"]) == ("PI-1", "SKU-1", "REF-1")
    for name in PREVIOUS_FIELDS - {"found"}:
        assert item[name] == presentation[name], name
    assert item["found"] is True


def test_not_found_items_keep_their_shape(as_user) -> None:
    missing = str(uuid4())
    item = as_user("admin.test").post(URL, json={"ids": [missing]}).json()["items"][0]
    assert item["found"] is False
    assert item["id"] == missing
    assert all(item[name] is None for name in ADDITIVE_FIELDS)
