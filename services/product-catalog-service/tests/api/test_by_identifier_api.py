"""Búsqueda por código escaneado (FR-058)."""

from tests import factories

URL = "/api/v1/products/by-identifier"


def test_lookup_by_presentation_code(api, session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory)
    box = factories.presentation(session_factory, product.id, "CAJA_X_20", base_quantity=20)
    factories.identifier(session_factory, product.id, "7702004003508", "EAN", presentation_id=box.id)

    body = api.get(f"{URL}/7702004003508").json()

    assert body["product"]["id"] == str(product.id)
    assert body["presentation"]["id"] == str(box.id)
    assert body["identifier"]["identifier_type"] == "EAN"
    assert body["is_current"] is True


def test_lookup_uses_canonical_form_across_family(api, session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory)
    factories.identifier(session_factory, product.id, "036000291452", "UPC")

    for scanned in ("036000291452", "0036000291452", "00036000291452", "0-36000-29145-2"):
        response = api.get(f"{URL}/{scanned}")
        assert response.status_code == 200, scanned
        assert response.json()["product"]["id"] == str(product.id)


def test_lookup_barcode(api, session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory)
    factories.identifier(session_factory, product.id, "XYZ999", "BARCODE")

    # El valor escaneado se normaliza igual que al registrar (sin espacios ni guiones).
    assert api.get(f"{URL}/XYZ-999").json()["product"]["id"] == str(product.id)
    assert api.get(f"{URL}/XYZ998").status_code == 404


def test_not_current_when_any_part_inactive(api, session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory)
    old = factories.presentation(session_factory, product.id, "VIEJA", status="INACTIVE")
    factories.identifier(session_factory, product.id, "96385074", "EAN", presentation_id=old.id)
    factories.identifier(session_factory, product.id, "4006381333931", "EAN", status="INACTIVE")

    assert api.get(f"{URL}/96385074").json()["is_current"] is False
    assert api.get(f"{URL}/4006381333931").json()["is_current"] is False


def test_unknown_code(api) -> None:
    response = api.get(f"{URL}/0000000000000")
    assert response.status_code == 404
    assert response.json()["code"] == "PRODUCT_CATALOG.NOT_FOUND"
