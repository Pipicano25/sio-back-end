"""Historia 4: búsqueda combinada y detalle (FR-033, FR-071)."""

from decimal import Decimal

from tests import factories

URL = "/api/v1/products"


def _names(api, query: str) -> list[str]:
    response = api.get(f"{URL}?{query}")
    assert response.status_code == 200, response.text
    return [item["canonical_name"] for item in response.json()["items"]]


def test_filters_by_text_category_brand_manufacturer_and_identifier(api, session_factory) -> None:
    unit = factories.unit(session_factory)
    brand = factories.brand(session_factory, "ACME")
    granos = factories.category(session_factory, "GRANOS")
    arroz = factories.category(session_factory, "ARROZ", parent=granos.id)
    rice = factories.product(session_factory, unit.id, "Arroz Diana", brand_id=brand.id)
    beans = factories.product(session_factory, unit.id, "Frijol rojo")
    coffee = factories.product(session_factory, unit.id, "Café molido")
    factories.product_category(session_factory, rice.id, arroz.id)
    factories.product_category(session_factory, beans.id, granos.id)
    factories.identifier(session_factory, coffee.id, "036000291452", "UPC")

    with session_factory() as session:
        from product_catalog_service.infrastructure.models import GlobalProductModel

        stored = session.get(GlobalProductModel, beans.id)
        stored.manufacturer_organization_id = brand.id
        session.commit()

    assert _names(api, "search=CAFE") == ["Café molido"]
    assert _names(api, f"category_id={granos.id}") == ["Frijol rojo"]
    assert _names(api, f"category_id={granos.id}&include_descendants=true") == ["Arroz Diana", "Frijol rojo"]
    assert _names(api, f"brand_id={brand.id}") == ["Arroz Diana"]
    assert _names(api, f"manufacturer_organization_id={brand.id}") == ["Frijol rojo"]
    assert _names(api, "identifier=0036000291452") == ["Café molido"]
    assert _names(api, "eligible=true") == ["Arroz Diana", "Café molido", "Frijol rojo"]


def test_attribute_filters(api, session_factory) -> None:
    unit = factories.unit(session_factory)
    leches = factories.category(session_factory, "LECHES")
    fat = factories.definition(session_factory, "PORCENTAJE_GRASA", "DECIMAL")
    color = factories.definition(session_factory, "COLOR", "OPTION")
    factories.category_attribute(session_factory, leches.id, fat.id, required=False, filterable=True)
    factories.category_attribute(session_factory, leches.id, color.id, required=False, filterable=False)
    whole = factories.product(session_factory, unit.id, "Leche entera")
    light = factories.product(session_factory, unit.id, "Leche light")
    for item, amount in ((whole, "3.5"), (light, "1.2")):
        factories.product_category(session_factory, item.id, leches.id)
        factories.value(session_factory, item.id, fat.id, decimal_value=Decimal(amount))

    assert _names(api, "attribute_filters=PORCENTAJE_GRASA:3.5") == ["Leche entera"]

    not_filterable = api.get(f"{URL}?attribute_filters=COLOR:RED")
    assert not_filterable.status_code == 422
    assert not_filterable.json()["code"] == "PRODUCT_CATALOG.ATTRIBUTE_NOT_FILTERABLE"

    bad_value = api.get(f"{URL}?attribute_filters=PORCENTAJE_GRASA:alto")
    assert bad_value.status_code == 422


def test_expand_detail(api, session_factory) -> None:
    product, category, _ = factories.complete_product(session_factory)
    factories.identifier(session_factory, product.id, "7702004003508", "EAN")
    inactive = factories.presentation(session_factory, product.id, "VIEJA", status="INACTIVE")

    body = api.get(f"{URL}/{product.id}?expand=detail").json()
    detail = body["detail"]

    assert [item["global_category_id"] for item in detail["categories"]] == [str(category.id)]
    assert [item["code"] for item in detail["presentations"]] == ["UNIDAD"]
    assert str(inactive.id) not in {item["id"] for item in detail["presentations"]}
    assert detail["presentations"][0]["eligible_for_adoption"] is True
    assert [item["value"] for item in detail["identifiers"]] == ["7702004003508"]
    assert detail["attribute_values"] == []
    assert detail["group_assignments"] == []
    assert detail["assets"] == []

    assert api.get(f"{URL}/{product.id}").json()["detail"] is None


def test_identifier_filter_includes_other_across_products(api, session_factory) -> None:
    """FR-071: el filtro `identifier` también encuentra `OTHER`, aunque coincida en varios productos."""
    unit = factories.unit(session_factory)
    first = factories.product(session_factory, unit.id, "Tornillo A")
    second = factories.product(session_factory, unit.id, "Tornillo B")
    factories.product(session_factory, unit.id, "Tuerca")
    factories.identifier(session_factory, first.id, "REF100", "OTHER")
    factories.identifier(session_factory, second.id, "REF100", "OTHER")

    assert _names(api, "identifier=REF-100") == ["Tornillo A", "Tornillo B"]


def test_by_identifier_does_not_resolve_other(api, session_factory) -> None:
    """Contrato §6.5: `by-identifier` solo resuelve la familia GTIN y `BARCODE`."""
    unit = factories.unit(session_factory)
    product = factories.product(session_factory, unit.id, "Tornillo A")
    factories.identifier(session_factory, product.id, "REF100", "OTHER")

    assert api.get("/api/v1/products/by-identifier/REF100").status_code == 404
