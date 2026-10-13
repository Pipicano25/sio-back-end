"""Integración: cargar_gold.py contra la aplicación REAL de Product Catalog y su base de pruebas AISLADA.

Usa las fixtures de la suite del servicio (base exclusiva de pruebas, vaciada en cada prueba; Party Identity simulado).
Party Identity, Operational Context, Commercial Relationship y Geography usan el doble de test_cargar_gold.py.
Datos sintéticos; no toca la base del servicio ni ningún dato de una empresa real. Desde services/product-catalog-service:

    set -a; . ./.env; set +a   # PRODUCT_CATALOG_TEST_DATABASE_URL
    .venv/bin/python -m pytest -p tests.conftest -p no:cacheprovider \
        ../../tools/data-migration/ia-tools/test_cargar_gold_product_catalog.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("product_catalog_service", reason="se ejecuta con el entorno de product-catalog-service")
_DM = Path(__file__).resolve().parents[1]
sys.path.extend(str(p) for p in sorted((_DM / ".venv" / "lib").glob("python*/site-packages")))  # al final: solo aporta
sys.path.insert(0, str(Path(__file__).resolve().parent))                                       # jsonschema y frictionless

from tests import factories  # noqa: E402  (suite del servicio)

import cargar_gold  # noqa: E402
from test_cargar_gold import ESPERADO_CREADO, GTIN_1, IUM_1, SioFalso, cargar, empresa, reporte  # noqa: E402,F401

CATALOGO = {"packaging_types", "brands", "attribute_definitions", "categories", "category_attributes", "products",
            "product_presentations", "product_identifiers", "product_categories", "product_attribute_values"}


class SioMixto(SioFalso):
    """Product Catalog real (TestClient con permisos de prueba); el resto, el doble en memoria."""

    def __init__(self, api) -> None:
        super().__init__()
        self.pc = api
        self.envios_pc: list[tuple[str, str]] = []

    def spec(self, service: str) -> dict:
        return self.pc.get("/openapi.json").json() if service == "product-catalog" else super().spec(service)

    def get(self, service: str, path: str, params: dict | None = None, all_pages: bool = False):
        if service != "product-catalog":
            return super().get(service, path, params, all_pages)
        params = dict(params or {})
        for nombre in re.findall(r"\{([^}]+)\}", path):
            path = path.replace("{" + nombre + "}", str(params.pop(nombre)))
        respuesta = self.pc.get(path, params=params)
        cuerpo = respuesta.json()
        if all_pages and respuesta.status_code == 200 and isinstance(cuerpo, dict) and cuerpo.get("total_pages", 1) > 1:
            items = list(cuerpo["items"])
            for pagina in range(2, cuerpo["total_pages"] + 1):
                items += self.pc.get(path, params={**params, "page": pagina}).json()["items"]
            cuerpo = {"items": items}
        return respuesta.status_code, cuerpo

    def send(self, method: str, service: str, path: str, body: dict):
        if service != "product-catalog":
            return super().send(method, service, path, body)
        if not self.escritura:
            raise PermissionError("escritura no habilitada")
        self.envios_pc.append((method, path))
        respuesta = self.pc.request(method, path, json=body)
        return respuesta.status_code, respuesta.json()


@pytest.fixture
def sio(api, session_factory, fake_manufacturer_directory) -> SioMixto:
    for codigo in ("UND", "G", "ML"):
        factories.unit(session_factory, codigo)
    factories.packaging(session_factory, "BOX")
    mixto = SioMixto(api)
    # Product Catalog consulta el fabricante en Party Identity: aquí, el doble donde el cargador lo creó.
    fake_manufacturer_directory.exists = lambda organization_id: str(organization_id) in {
        o["id"] for o in mixto.creados("/api/v1/organization-identities")}
    return mixto


def test_cargue_sintetico_contra_product_catalog_real(sio: SioMixto, empresa: Path, tmp_path: Path) -> None:
    # 1. Simulación: nada se escribe en la base de pruebas.
    _, simulacion = cargar(sio, empresa, escribir=False)
    assert sio.envios_pc == [] and sio.pc.get("/api/v1/brands").json()["items"] == []
    assert simulacion["conteo"]["product_identifiers"] == {"CREARIA": 3}  # el contrato real ya admite IUM

    # 2. Escritura: todo el catálogo se crea con los contratos y reglas reales del servicio.
    _, escritura = cargar(sio, empresa, escribir=True)
    assert escritura["estado"] == "COMPLETA", escritura["motivo"]
    filas = reporte(escritura)
    errores = [f for f in filas if f["resultado"] in ("ERROR", "INVALIDA", "CONFLICTO")]
    assert errores == []
    creados = {t: c.get("CREADO", 0) for t, c in escritura["conteo"].items() if c.get("CREADO")}
    assert creados == ESPERADO_CREADO
    hallado = sio.pc.get(f"/api/v1/products/by-identifier/{GTIN_1}").json()
    assert hallado["presentation"]["code"] == "VIAL-1G"
    ium = sio.pc.get(f"/api/v1/products/by-identifier/{IUM_1}").json()
    assert ium["presentation"]["id"] == hallado["presentation"]["id"]
    producto = hallado["product"]["id"]
    assert [v["text_value"] for v in sio.pc.get(f"/api/v1/products/{producto}/attribute-values").json()] == ["N01AX03"]
    empaque = sio.pc.get("/api/v1/packaging-types", params={"code": "VIALSINT"}).json()["items"][0]
    assert hallado["presentation"]["packaging_type_id"] == empaque["id"]

    # 3. Reanudación con el diario: no se envía nada más.
    escrituras = len(sio.envios_pc)
    _, repetida = cargar(sio, empresa, escribir=True)
    assert len(sio.envios_pc) == escrituras
    assert all(set(c) <= {"YA_CARGADO", "BLOQUEADA", "DEPENDENCIA"} for c in repetida["conteo"].values())

    # 4. Sin diario: la búsqueda por identidad en el servicio real evita duplicados.
    _, sin_diario = cargar(sio, empresa, escribir=True, salida=tmp_path / "sin-diario")
    assert len(sio.envios_pc) == escrituras
    reusados = {t: c.get("REUSADO", 0) for t, c in sin_diario["conteo"].items() if t in CATALOGO}
    assert reusados == {t: n for t, n in ESPERADO_CREADO.items() if t in CATALOGO}
    assert len(sio.pc.get("/api/v1/brands").json()["items"]) == 1
