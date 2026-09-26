"""Historia 1: tipos de empaque y unicidad cruzada con unidades (FR-016, FR-017, R-09)."""

import threading

from sqlalchemy.orm import sessionmaker

from product_catalog_service.application.exceptions import DomainError
from product_catalog_service.application.packaging_type_service import PackagingTypeService
from product_catalog_service.application.unit_of_measure_service import UnitOfMeasureService

UNITS = "/api/v1/units-of-measure"
PACKAGING = "/api/v1/packaging-types"


def test_create_packaging_type(api) -> None:
    response = api.post(PACKAGING, json={"code": "box", "name": "Caja"})

    assert response.status_code == 201
    assert response.json()["code"] == "BOX"


def test_packaging_code_cannot_match_unit(api) -> None:
    api.post(
        UNITS,
        json={"code": "KG", "name": "Kilogramo", "symbol": "kg", "measurement_type": "MASS", "allows_decimals": True},
    )

    response = api.post(PACKAGING, json={"code": "KG", "name": "Kilo"})

    assert response.status_code == 409
    assert response.json()["code"] == "PRODUCT_CATALOG.CODE_USED_BY_UNIT_OF_MEASURE"


def test_unit_code_cannot_match_packaging(api) -> None:
    api.post(PACKAGING, json={"code": "BOX", "name": "Caja"})

    response = api.post(
        UNITS,
        json={"code": "BOX", "name": "Caja", "symbol": "box", "measurement_type": "UNIT", "allows_decimals": False},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "PRODUCT_CATALOG.CODE_USED_BY_PACKAGING_TYPE"


def test_concurrent_cross_code_creation_allows_only_one(session_factory: sessionmaker) -> None:
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def create(kind: str) -> None:
        with session_factory() as session:
            barrier.wait()
            try:
                if kind == "unit":
                    UnitOfMeasureService(session).create(
                        code="PK",
                        name="Paquete",
                        symbol="pk",
                        measurement_type="UNIT",
                        allows_decimals=False,
                        actor="t",
                    )
                else:
                    PackagingTypeService(session).create(code="PK", name="Paquete", actor="t")
                outcomes.append("ok")
            except DomainError as exc:
                outcomes.append(exc.code)

    threads = [threading.Thread(target=create, args=(kind,)) for kind in ("unit", "packaging")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes).count("ok") == 1


def test_update_rejects_code(api) -> None:
    created = api.post(PACKAGING, json={"code": "BOX", "name": "Caja"}).json()

    response = api.put(
        f"{PACKAGING}/{created['id']}",
        json={"code": "BAG", "name": "Bolsa", "version": 1},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "PRODUCT_CATALOG.IMMUTABLE_FIELD"
