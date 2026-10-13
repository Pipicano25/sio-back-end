"""Pruebas de cargar_gold.py con datos SINTÉTICOS y un doble en memoria de las API de SIO (sin red ni bases reales).

    tools/data-migration/.venv/bin/python -m pytest tools/data-migration/ia-tools/test_cargar_gold.py -q
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import uuid
from collections import defaultdict
from pathlib import Path

import pytest
import requests

import cargar_gold
from cargar_gold import Cargador, plegar

# --- contratos mínimos (propiedades y tipos de los contratos reales de SIO) ------------------------
S, B, I = {"type": "string"}, {"type": "boolean"}, {"type": "integer"}
D = {"anyOf": [{"type": "number"}, {"type": "string"}]}


def _contrato(requeridas: list[str], **props: dict) -> dict:
    return {"type": "object", "required": requeridas, "properties": props}


def contratos(ium: bool) -> dict:
    tipos = ["GTIN", "EAN", "UPC", "BARCODE", "OTHER"] + (["IUM"] if ium else [])
    return {
        "OrganizationIdentityCreate": _contrato(["country_id", "identification_type", "identification_number", "legal_name"],
                                                country_id=S, identification_type=S, identification_number=S, legal_name=S,
                                                trade_name=S, organization_type=S, registration_status=S, website=S),
        "CompanyCreate": _contrato(["organization_identity_id"], organization_identity_id=S, email=S, phone=S,
                                   address_line=S, country_id=S, administrative_division_id=S, city_id=S, postal_code=S,
                                   latitude=D, longitude=D, timezone=S, default_currency=S),
        "BranchCreate": _contrato(["code", "name"], code=S, name=S, email=S, phone=S, address_line=S, country_id=S,
                                  administrative_division_id=S, city_id=S, postal_code=S, latitude=D, longitude=D, timezone=S),
        "PackagingTypeCreate": _contrato(["code", "name"], code=S, name=S, description=S),
        "BrandCreate": _contrato(["code", "name"], code=S, name=S, description=S),
        "AttributeDefinitionCreate": _contrato(["code", "name", "description", "data_type"], code=S, name=S,
                                               description=S, data_type=S, unit_of_measure_id=S),
        "CategoryCreate": _contrato(["code", "name"], code=S, name=S, description=S, parent_category_id=S),
        "CategoryAttributeCreate": _contrato(["attribute_definition_id"], attribute_definition_id=S, is_required=B,
                                             is_filterable=B, display_order=I),
        "ProductCreate": _contrato(["product_type", "canonical_name", "base_unit_id"], product_type=S, canonical_name=S,
                                   description=S, global_brand_id=S, manufacturer_organization_id=S, base_unit_id=S),
        "PresentationCreate": _contrato(["code", "name"], code=S, name=S, packaging_type_id=S, base_quantity=D,
                                        content_quantity=D, content_unit_id=S, display_order=I, is_base=B),
        "IdentifierCreate": _contrato(["identifier_type", "value"], identifier_type={"type": "string", "enum": tipos},
                                      value=S, global_product_presentation_id=S, is_primary=B),
        "ProductCategoryAssign": _contrato(["global_category_id"], global_category_id=S),
        "AttributeValuePut": _contrato([], option_id=S, text_value=S, integer_value=I, decimal_value=D,
                                       boolean_value=B, date_value=S, version=I),
        "CompanyProductCreate": _contrato(["global_product_id", "internal_code", "display_name", "currency_code"],
                                          global_product_id=S, internal_code=S, reference_code=S, display_name=S,
                                          short_name=S, sale_price=D, currency_code=S, reference_cost=D,
                                          inventory_control_enabled=B, lot_tracking_enabled=B,
                                          expiration_tracking_enabled=B, is_purchasable=B, is_sellable=B),
        "CompanyProductPresentationCreate": _contrato(["company_product_id", "global_product_presentation_id"],
                                                      company_product_id=S, global_product_presentation_id=S,
                                                      internal_code=S, sku=S, reference_code=S, is_purchasable=B,
                                                      is_sellable=B, is_default_purchase=B, is_default_sale=B),
    }


# --- doble de las API de SIO ---------------------------------------------------------------------
LISTAS_SIN_PAGINAR = re.compile(r"^/api/v1/(products/[^/]+/(presentations|identifiers|categories|attribute-values)"
                                r"|categories/[^/]+/attributes)$")


class SioFalso:
    """Reproduce lo que usa el cargador: listas con filtros, by-identifier, unicidad (409) y fallos configurables."""

    def __init__(self, ium: bool = True) -> None:
        self.rol, self.escritura, self.ium = "importador-sintetico", True, ium
        self.datos: dict[tuple[str, str], list[dict]] = defaultdict(list)
        self.envios: list[tuple[str, str, str, dict]] = []
        self.fallar_tras: int | None = None   # ConnectionError después de N escrituras
        self.estado_envio: int | None = None  # p. ej. 401 o 403 en toda escritura
        self.estado_consulta: int | None = None
        self.datos[("geography", "/global-countries")] = [{"id": "pais-col", "iso3_code": "COL", "name": "Colombia"}]
        self.datos[("geography", "/global-administrative-divisions")] = [
            {"id": "div-cauca", "name": "Cauca Department", "country_id": "pais-col"}]
        self.datos[("geography", "/global-cities")] = [
            {"id": "ciu-popayan", "name": "Popayán", "country_id": "pais-col", "administrative_division_id": "div-cauca"}]
        self.datos[("product-catalog", "/api/v1/units-of-measure")] = [
            {"id": f"und-{c}", "code": c} for c in ("UND", "G", "ML")]
        self.datos[("product-catalog", "/api/v1/packaging-types")] = [{"id": "emp-box", "code": "BOX"}]

    def spec(self, service: str) -> dict:
        return {"components": {"schemas": contratos(self.ium)}}

    def _identificadores(self):
        for (servicio, ruta), objetos in self.datos.items():
            if ruta.endswith("/identifiers"):
                yield from objetos

    def get(self, service: str, path: str, params: dict | None = None, all_pages: bool = False):
        if self.estado_consulta:
            return self.estado_consulta, {"code": "SIMULADO"}
        params = dict(params or {})
        if path == "/api/v1/products/by-identifier/{value}":
            for ident in self._identificadores():
                if params["value"] in (ident["value"], ident.get("canonical_value")):
                    return 200, {"product": {"id": ident["global_product_id"]}, "identifier": ident}
            return 404, {"code": "NOT_FOUND"}
        objetos = self.datos.get((service, path), [])
        for clave, valor in params.items():
            if clave in ("page", "page_size"):
                continue
            if clave == "search":
                objetos = [o for o in objetos if any(plegar(str(valor)) in plegar(str(o.get(k, "")))
                                                     for k in ("code", "name", "identification_number"))]
            else:
                objetos = [o for o in objetos if plegar(str(o.get(clave))) == plegar(str(valor))]
        return 200, (list(objetos) if LISTAS_SIN_PAGINAR.match(path) else {"items": list(objetos)})

    def send(self, method: str, service: str, path: str, body: dict):
        if not self.escritura:
            raise PermissionError("escritura no habilitada")
        if self.fallar_tras is not None and len(self.envios) >= self.fallar_tras:
            raise requests.ConnectionError("servicio caído (simulado)")
        self.envios.append((method, service, path, body))
        if self.estado_envio:
            return self.estado_envio, {"code": "SIMULADO.AUTH", "detail": "token o permisos"}
        if method == "PUT":  # valor de atributo por (producto, definición)
            coleccion, definicion = path.rsplit("/", 1)
            producto = coleccion.split("/")[4]
            objeto = {"id": str(uuid.uuid4()), "global_product_id": producto, "attribute_definition_id": definicion, **body}
            self.datos[(service, coleccion)].append(objeto)
            return 200, objeto
        existentes = self.datos[(service, path)]
        if "code" in body and any(plegar(o.get("code", "")) == plegar(body["code"]) for o in existentes):
            return 409, {"code": "DUPLICATE_CODE", "detail": "código repetido"}
        if path.endswith("/identifiers") and any(i["identifier_type"] == body["identifier_type"] and i["value"] == body["value"]
                                                 for i in self._identificadores()):
            return 409, {"code": "IDENTIFIER_COLLISION", "detail": "identificador en otro producto"}
        objeto = {"id": str(uuid.uuid4()), **body}
        partes = path.split("/")
        if path.startswith("/api/v1/products/") and len(partes) > 4:
            objeto["global_product_id"] = partes[4]
        if path.startswith("/api/v1/categories/"):
            objeto["global_category_id"] = partes[4]
        if path.startswith("/api/v1/companies/"):
            objeto["company_id"] = partes[4]
        if path == "/api/v1/products":
            parecidos = [o["id"] for o in existentes if o["canonical_name"] == body["canonical_name"]]
            objeto["warnings"] = [{"code": "POSSIBLE_DUPLICATE", "matching_product_ids": parecidos}] if parecidos else []
        existentes.append(objeto)
        return 201, objeto

    def creados(self, ruta_final: str) -> list[dict]:
        return [o for (s, r), objs in self.datos.items()
                if (r == ruta_final if ruta_final.startswith("/api/") else r.endswith(ruta_final)) for o in objs]


# --- empresa sintética ---------------------------------------------------------------------------
def gtin14(cuerpo13: str) -> str:
    total = sum(int(c) * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(cuerpo13)))
    return cuerpo13 + str((10 - total % 10) % 10)


def nit(numero: str) -> str:
    pesos = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
    resto = sum(int(d) * p for d, p in zip(reversed(numero), pesos)) % 11
    return f"{numero}-{resto if resto < 2 else 11 - resto}"


GTIN_1, GTIN_2, IUM_1 = gtin14("0770000000001"), gtin14("0770000000002"), "2H1005971005105"
NIT_FAB, NIT_EMP = nit("900123456"), nit("900654321")
ORG_FAB, ORG_EMP = f"ORG-COL-NIT-{NIT_FAB}", f"ORG-COL-NIT-{NIT_EMP}"


def filas_sinteticas() -> dict[str, list[dict]]:
    comun = {"source_ref": "SINTETICO", "migration_status": "VALIDADO"}
    lugar = {"country_iso3": "COL", "administrative_division_name": "CAUCA", "city_name": "POPAYAN"}
    return {
        "organization_identities": [
            {"organization_identity_ref": ORG_FAB, "country_iso3": "COL", "identification_type": "NIT",
             "identification_number": NIT_FAB, "legal_name": "LABORATORIO SINTETICO S A S"},
            {"organization_identity_ref": ORG_EMP, "country_iso3": "COL", "identification_type": "NIT",
             "identification_number": NIT_EMP, "legal_name": "EMPRESA SINTETICA S A S"}],
        "companies": [{"company_ref": "CMP-SINT", "organization_identity_ref": ORG_EMP, "timezone": "America/Bogota",
                       "default_currency": "COP", **lugar}],
        "branches": [{"branch_ref": "BRN-SINT-PPAL", "company_ref": "CMP-SINT", "code": "SINT-PPAL",
                      "name": "Sede principal", **lugar}],
        "packaging_types": [{"packaging_type_ref": "PKG-VIALSINT", "code": "VIALSINT", "name": "Vial sintético"}],
        "brands": [{"brand_ref": "BRD-MARCASINT", "code": "MARCASINT", "name": "Marca sintética"}],
        "attribute_definitions": [{"attribute_definition_ref": "ATR-ATCSINT", "code": "ATCSINT", "name": "ATC sintético",
                                   "description": "Prueba", "data_type": "TEXT"}],
        # La subcategoría va antes que su padre: el cargador debe ordenarlas.
        "categories": [{"category_ref": "CAT-MEDSINT", "code": "MEDSINT", "name": "Medicamento sintético",
                        "parent_category_ref": "CAT-SALUDSINT"},
                       {"category_ref": "CAT-SALUDSINT", "code": "SALUDSINT", "name": "Salud sintética"}],
        "category_attributes": [{"category_attribute_ref": "CTA-MEDSINT-ATCSINT", "category_ref": "CAT-MEDSINT",
                                 "attribute_definition_ref": "ATR-ATCSINT", "is_required": "false",
                                 "is_filterable": "false", "display_order": "0"}],
        "products": [
            {"product_ref": "PRD-SINT-1", "product_type": "GOOD", "canonical_name": "Producto sintético 1 g",
             "brand_ref": "BRD-MARCASINT", "manufacturer_organization_ref": ORG_FAB, "base_unit_code": "UND"},
            {"product_ref": "PRD-SINT-2", "product_type": "GOOD", "canonical_name": "Tableta sintética 10 mg",
             "manufacturer_organization_ref": ORG_FAB, "base_unit_code": "UND"}],
        "product_presentations": [
            {"product_presentation_ref": "PRS-SINT-1-VIAL", "product_ref": "PRD-SINT-1", "code": "VIAL-1G",
             "name": "Vial x 1 g", "packaging_type_code": "VIALSINT", "base_quantity": "1", "content_quantity": "1",
             "content_unit_code": "G", "display_order": "0", "is_base": "true"},
            {"product_presentation_ref": "PRS-SINT-2-UNIT", "product_ref": "PRD-SINT-2", "code": "UNIT",
             "name": "Tableta", "base_quantity": "1", "display_order": "0", "is_base": "true"},
            {"product_presentation_ref": "PRS-SINT-2-BOX-10", "product_ref": "PRD-SINT-2", "code": "BOX-10",
             "name": "Caja x 10 tabletas", "packaging_type_code": "BOX", "base_quantity": "10", "display_order": "1",
             "is_base": "false"}],
        "product_identifiers": [
            {"product_identifier_ref": f"IDN-GTIN-{GTIN_1}", "product_ref": "PRD-SINT-1",
             "product_presentation_ref": "PRS-SINT-1-VIAL", "identifier_type": "GTIN", "value": GTIN_1, "is_primary": "true"},
            {"product_identifier_ref": f"IDN-IUM-{IUM_1}", "product_ref": "PRD-SINT-1",
             "product_presentation_ref": "PRS-SINT-1-VIAL", "identifier_type": "IUM", "value": IUM_1, "is_primary": "false"},
            {"product_identifier_ref": f"IDN-GTIN-{GTIN_2}", "product_ref": "PRD-SINT-2",
             "product_presentation_ref": "PRS-SINT-2-BOX-10", "identifier_type": "GTIN", "value": GTIN_2, "is_primary": "true"}],
        "product_categories": [
            {"product_category_ref": "PCT-SINT-1", "product_ref": "PRD-SINT-1", "category_ref": "CAT-MEDSINT",
             "classification_level": "VERIFICADA"},
            {"product_category_ref": "PCT-SINT-2", "product_ref": "PRD-SINT-2", "category_ref": "CAT-MEDSINT",
             "classification_level": "VERIFICADA"}],
        "product_attribute_values": [
            {"product_attribute_value_ref": "PAV-SINT-1", "product_ref": "PRD-SINT-1",
             "attribute_definition_ref": "ATR-ATCSINT", "text_value": "N01AX03"},
            {"product_attribute_value_ref": "PAV-SINT-2", "product_ref": "PRD-SINT-2",
             "attribute_definition_ref": "ATR-ATCSINT", "text_value": "M01AE01"}],
        "company_products": [
            {"company_product_ref": "CPR-SINT-1", "company_ref": "CMP-SINT", "product_ref": "PRD-SINT-1",
             "internal_code": "000001", "display_name": "Producto sintético 1 g", "sale_price": "1000",
             "currency_code": "COP", "reference_cost": "600", "is_purchasable": "true", "is_sellable": "true"},
            {"company_product_ref": "CPR-SINT-2", "company_ref": "CMP-SINT", "product_ref": "PRD-SINT-2",
             "internal_code": "000002", "display_name": "Tableta sintética 10 mg", "currency_code": "COP",
             "is_purchasable": "true", "is_sellable": "true"}],  # sin precio ni costo: no debe enviarse
        "company_product_presentations": [
            {"company_product_presentation_ref": "CPP-SINT-1", "company_ref": "CMP-SINT",
             "company_product_ref": "CPR-SINT-1", "product_presentation_ref": "PRS-SINT-1-VIAL",
             "internal_code": "000001", "is_sellable": "true"},
            {"company_product_presentation_ref": "CPP-SINT-2", "company_ref": "CMP-SINT",
             "company_product_ref": "CPR-SINT-2", "product_presentation_ref": "PRS-SINT-2-BOX-10",
             "internal_code": "000002", "is_sellable": "true"}],
    }, comun


@pytest.fixture
def empresa(tmp_path: Path) -> Path:
    directorio = tmp_path / "SINT"
    filas, comun = filas_sinteticas()
    for nombre, esquema in cargar_gold.validate_csv.load_schemas().items():
        campos = [f["name"] for f in esquema["fields"]]
        for capa in ("silver", "gold"):
            (directorio / capa).mkdir(parents=True, exist_ok=True)
            with (directorio / capa / f"{nombre}.csv").open("w", newline="", encoding="utf-8") as handle:
                escritor = csv.DictWriter(handle, fieldnames=campos)
                escritor.writeheader()
                for fila in filas.get(nombre, []):
                    escritor.writerow({c: {**comun, **fila}.get(c, "") for c in campos})
    return directorio


def huellas(directorio: Path) -> dict[str, str]:
    return {str(p.relative_to(directorio)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directorio.rglob("*.csv")) if "reports" not in p.parts}


def cargar(api, empresa: Path, escribir: bool, **kwargs) -> tuple[Cargador, dict]:
    api.escritura = escribir
    cargador = Cargador(api, empresa, escribir=escribir, **kwargs)
    return cargador, cargador.ejecutar(validar_sio=False)


def reporte(resumen: dict) -> list[dict]:
    return list(csv.DictReader(open(resumen["reporte"], encoding="utf-8")))


ESPERADO_CREADO = {"organization_identities": 2, "companies": 1, "branches": 1, "packaging_types": 1, "brands": 1,
                   "attribute_definitions": 1, "categories": 2, "category_attributes": 1, "products": 2,
                   "product_presentations": 3, "product_identifiers": 3, "product_categories": 2,
                   "product_attribute_values": 2, "company_products": 1, "company_product_presentations": 1}


# --- pruebas -------------------------------------------------------------------------------------
def test_la_empresa_sintetica_es_un_gold_valido(empresa: Path) -> None:
    resultado = cargar_gold.validate_csv.validate(empresa, "gold", False)
    assert resultado["errores"] == 0, resultado["detalle_errores"]


def test_simulacion_no_escribe_ni_modifica_csv(empresa: Path) -> None:
    api, antes = SioFalso(), huellas(empresa)
    _, resumen = cargar(api, empresa, escribir=False)
    assert api.envios == []
    assert huellas(empresa) == antes
    assert not (empresa / "reports" / "cargue" / "sio_ids.csv").exists()
    conteo = resumen["conteo"]
    assert conteo["products"] == {"CREARIA": 2} and conteo["categories"] == {"CREARIA": 2}
    assert conteo["company_products"] == {"CREARIA": 1, "BLOQUEADA": 1}
    assert conteo["company_product_presentations"] == {"CREARIA": 1, "DEPENDENCIA": 1}
    assert resumen["estado"] == "COMPLETA" and Path(resumen["reporte"]).with_suffix(".json").is_file()


def test_la_simulacion_no_puede_escribir_aunque_se_le_pida() -> None:
    api = cargar_gold.Api("consulta", escritura=False)
    with pytest.raises(PermissionError):
        api.send("POST", "product-catalog", "/api/v1/brands", {"code": "X", "name": "X"})


def test_escritura_completa_respeta_dependencias_y_no_envia_valores_por_defecto(empresa: Path) -> None:
    api = SioFalso()
    _, resumen = cargar(api, empresa, escribir=True)
    creados = {t: c.get("CREADO", 0) for t, c in resumen["conteo"].items() if c.get("CREADO")}
    assert creados == ESPERADO_CREADO
    filas = reporte(resumen)
    assert {f["ref"]: f["resultado"] for f in filas}["CPR-SINT-2"] == "BLOQUEADA"
    assert {f["ref"]: f["resultado"] for f in filas}["CPP-SINT-2"] == "DEPENDENCIA"
    assert not any(b.get("internal_code") == "000002" for _, _, _, b in api.envios)  # nunca se envió sin precio
    # Orden: la categoría padre se crea antes que la hija; el tipo de empaque nuevo antes que la presentación.
    orden = [f["ref"] for f in filas if f["resultado"] == "CREADO"]
    assert orden.index("CAT-SALUDSINT") < orden.index("CAT-MEDSINT")
    assert orden.index("PKG-VIALSINT") < orden.index("PRS-SINT-1-VIAL")
    vial = api.creados("/packaging-types")[-1]
    assert api.creados("/presentations")[0]["packaging_type_id"] == vial["id"]
    hija = next(c for c in api.creados("/api/v1/categories") if c["code"] == "MEDSINT")
    padre = next(c for c in api.creados("/api/v1/categories") if c["code"] == "SALUDSINT")
    assert hija["parent_category_id"] == padre["id"]
    # GTIN e IUM ligados a su presentación; atributo después de la categoría (RN-10).
    vial_pres = next(p for p in api.creados("/presentations") if p["code"] == "VIAL-1G")
    ium = next(i for i in api.creados("/identifiers") if i["identifier_type"] == "IUM")
    assert ium["global_product_presentation_id"] == vial_pres["id"]
    assert orden.index("PCT-SINT-1") < orden.index("PAV-SINT-1")
    empresa_creada = api.creados("/api/v1/companies")[0]
    assert empresa_creada["administrative_division_id"] == "div-cauca" and empresa_creada["city_id"] == "ciu-popayan"


def test_reanudacion_por_diario_e_idempotencia(empresa: Path) -> None:
    api = SioFalso()
    _, primero = cargar(api, empresa, escribir=True)
    envios = len(api.envios)
    _, segundo = cargar(api, empresa, escribir=True)
    assert len(api.envios) == envios  # nada se vuelve a enviar
    assert {r for c in segundo["conteo"].values() for r in c} <= {"YA_CARGADO", "BLOQUEADA", "DEPENDENCIA", "OMITIDO"}
    diario = list(csv.DictReader(open(empresa / "reports" / "cargue" / "sio_ids.csv", encoding="utf-8")))
    assert len(diario) == sum(ESPERADO_CREADO.values())


def test_sin_diario_reutiliza_por_identidad_y_no_duplica(empresa: Path, tmp_path: Path) -> None:
    api = SioFalso()
    cargar(api, empresa, escribir=True)
    envios = len(api.envios)
    _, otra = cargar(api, empresa, escribir=True, salida=tmp_path / "otra-salida")  # sin diario previo
    assert len(api.envios) == envios
    reusados = {t: c.get("REUSADO", 0) for t, c in otra["conteo"].items() if c.get("REUSADO")}
    assert reusados == ESPERADO_CREADO


def test_detenerse_por_caida_y_reanudar_sin_duplicar(empresa: Path) -> None:
    api = SioFalso()
    api.fallar_tras = 9
    _, cortado = cargar(api, empresa, escribir=True)
    assert cortado["estado"] == "DETENIDA" and "no disponible" in cortado["motivo"]
    api.fallar_tras = None
    _, final = cargar(api, empresa, escribir=True)
    assert final["estado"] == "COMPLETA"
    assert len(api.creados("/api/v1/products")) == 2 and len(api.creados("/identifiers")) == 3
    assert len(api.creados("/api/v1/brands")) == 1 and len(api.creados("/api/v1/categories")) == 2


@pytest.mark.parametrize("estado", [401, 403])
def test_error_de_autenticacion_o_permisos_detiene_sin_continuar(empresa: Path, estado: int) -> None:
    api = SioFalso()
    api.estado_envio = estado
    _, resumen = cargar(api, empresa, escribir=True)
    assert resumen["estado"] == "DETENIDA" and str(estado) in resumen["motivo"]
    assert len(api.envios) == 1  # se detiene en la primera escritura rechazada
    api2 = SioFalso()
    api2.estado_consulta = 401
    _, consulta = cargar(api2, empresa, escribir=False)
    assert consulta["estado"] == "DETENIDA"


def test_duplicados_en_sio_se_reutilizan_y_conflictos_no_se_sobrescriben(empresa: Path) -> None:
    api = SioFalso()
    api.datos[("product-catalog", "/api/v1/brands")].append({"id": "marca-existente", "code": "marcasint", "name": "Otra"})
    # GTIN_1 ya existe en SIO en un producto: el producto sintético 1 se reutiliza, no se crea otro.
    api.datos[("product-catalog", "/api/v1/products/prod-existente/identifiers")].append(
        {"id": "i1", "global_product_id": "prod-existente", "identifier_type": "GTIN", "value": GTIN_1})
    _, resumen = cargar(api, empresa, escribir=True)
    filas = {f["ref"]: f for f in reporte(resumen)}
    assert filas["BRD-MARCASINT"]["resultado"] == "REUSADO" and "difiere en name" in filas["BRD-MARCASINT"]["detalle"]
    assert filas["PRD-SINT-1"]["resultado"] == "REUSADO" and filas["PRD-SINT-1"]["sio_id"] == "prod-existente"
    assert filas[f"IDN-GTIN-{GTIN_1}"]["resultado"] == "REUSADO"
    assert len(api.creados("/api/v1/brands")) == 1  # no se creó otra marca
    # Un producto cuyos identificadores apuntan a dos productos distintos de SIO es un conflicto, sin escribir nada.
    api2 = SioFalso()
    for producto, tipo, valor in (("prod-a", "GTIN", GTIN_1), ("prod-b", "IUM", IUM_1)):
        api2.datos[("product-catalog", f"/api/v1/products/{producto}/identifiers")].append(
            {"id": f"i-{producto}", "global_product_id": producto, "identifier_type": tipo, "value": valor})
    _, otro = cargar(api2, empresa, escribir=True, salida=empresa / "reports" / "otra")
    filas = {f["ref"]: f for f in reporte(otro)}
    assert filas["PRD-SINT-1"]["resultado"] == "CONFLICTO" and "prod-a" in filas["PRD-SINT-1"]["detalle"]
    assert filas["PRS-SINT-1-VIAL"]["resultado"] == "DEPENDENCIA"
    assert not any("/products/prod-" in e[2] for e in api2.envios)


def test_valor_de_atributo_distinto_en_sio_es_conflicto_y_no_se_sobrescribe(empresa: Path) -> None:
    api = SioFalso()
    cargar(api, empresa, escribir=True)
    valor = next(v for v in api.creados("/attribute-values") if v["text_value"] == "N01AX03")
    valor["text_value"] = "CAMBIADO-EN-SIO"
    puts = sum(1 for e in api.envios if e[0] == "PUT")
    _, resumen = cargar(api, empresa, escribir=True, salida=empresa / "reports" / "sin-diario")
    filas = {f["ref"]: f for f in reporte(resumen)}
    assert filas["PAV-SINT-1"]["resultado"] == "CONFLICTO"
    assert sum(1 for e in api.envios if e[0] == "PUT") == puts and valor["text_value"] == "CAMBIADO-EN-SIO"


def test_ium_queda_pendiente_si_el_contrato_desplegado_no_lo_admite(empresa: Path) -> None:
    api = SioFalso(ium=False)
    _, resumen = cargar(api, empresa, escribir=True)
    filas = {f["ref"]: f for f in reporte(resumen)}
    assert filas[f"IDN-IUM-{IUM_1}"]["resultado"] == "DEPENDENCIA" and "IUM" in filas[f"IDN-IUM-{IUM_1}"]["detalle"]
    assert filas[f"IDN-GTIN-{GTIN_1}"]["resultado"] == "CREADO"
    api.ium = True  # tras desplegar la migración, la siguiente ejecución solo agrega el IUM
    envios = len(api.envios)
    _, despues = cargar(api, empresa, escribir=True)
    assert len(api.envios) == envios + 1 and despues["conteo"]["product_identifiers"]["CREADO"] == 1


def test_fila_invalida_para_el_contrato_no_se_envia(empresa: Path) -> None:
    api = SioFalso()
    contrato = contratos(True)
    contrato["BrandCreate"]["properties"]["name"] = {"type": "string", "maxLength": 3}
    api.spec = lambda service: {"components": {"schemas": contrato}}
    _, resumen = cargar(api, empresa, escribir=True)
    filas = {f["ref"]: f for f in reporte(resumen)}
    assert filas["BRD-MARCASINT"]["resultado"] == "INVALIDA"
    assert filas["PRD-SINT-1"]["resultado"] == "DEPENDENCIA"  # su marca no se cargó
    assert filas["PRD-SINT-2"]["resultado"] == "CREADO"        # independiente: continúa
    assert not any(e[2] == "/api/v1/brands" for e in api.envios)


def test_seleccion_de_productos_y_sus_dependencias(empresa: Path) -> None:
    api = SioFalso()
    _, resumen = cargar(api, empresa, escribir=False, productos={"PRD-SINT-2"})
    refs = {f["ref"] for f in reporte(resumen)}
    assert "PRD-SINT-2" in refs and "PRD-SINT-1" not in refs and "BRD-MARCASINT" not in refs
    assert ORG_FAB in refs and ORG_EMP in refs and "CAT-SALUDSINT" in refs  # catálogos completos y la empresa
    with pytest.raises(SystemExit):
        Cargador(api, empresa, productos={"PRD-NO-EXISTE"})


def test_productos_sin_imagenes_son_validos_y_las_imagenes_se_omiten(empresa: Path) -> None:
    _, resumen = cargar(SioFalso(), empresa, escribir=True)
    assert resumen["conteo"]["products"] == {"CREADO": 2}
    assert "product_assets" not in resumen["conteo"]  # no hay imágenes: nada que omitir ni que subir


def test_gold_invalido_no_carga_nada(empresa: Path) -> None:
    ruta = empresa / "gold" / "brands.csv"
    ruta.write_text(ruta.read_text(encoding="utf-8").replace("Marca sintética", "Marca cambiada"), encoding="utf-8")
    api = SioFalso()
    with pytest.raises(SystemExit):
        cargar(api, empresa, escribir=True)
    assert api.envios == []


def test_la_escritura_exige_confirmar_la_empresa(empresa: Path) -> None:
    with pytest.raises(SystemExit):
        cargar_gold.main([str(empresa), "--escribir"])
    with pytest.raises(SystemExit):
        cargar_gold.main([str(empresa), "--escribir", "--confirmar", "OTRA"])


def test_imagenes_solo_con_habilitacion_sin_duplicar_y_en_su_producto(empresa: Path, tmp_path: Path) -> None:
    import hashlib
    contenido = b"\x89PNG\r\n\x1a\n imagen sintetica"
    sha = hashlib.sha256(contenido).hexdigest()
    (empresa / "assets").mkdir()
    (empresa / "assets" / f"{sha}.png").write_bytes(contenido)
    esquema = cargar_gold.validate_csv.load_schemas()["product_assets"]
    fila = {"product_asset_ref": f"AST-SINT-1-{sha[:12]}", "source_ref": "SINTETICO", "migration_status": "VALIDADO",
            "product_ref": "PRD-SINT-1", "asset_type": "IMAGE", "file_name": f"VIAL-1G__{sha[:12]}.png",
            "storage_uri": f"s3://sio-product-assets/assets/{sha}.png", "mime_type": "image/png", "is_primary": "true",
            "product_presentation_ref": "PRS-SINT-1-VIAL", "local_file": f"assets/{sha}.png"}
    for capa in ("silver", "gold"):
        with (empresa / capa / "product_assets.csv").open("a", newline="", encoding="utf-8") as handle:
            csv.DictWriter(handle, fieldnames=[f["name"] for f in esquema["fields"]]).writerow(
                {c: fila.get(c, "") for c in (f["name"] for f in esquema["fields"])})
    api = SioFalso()
    contratos_con_activo = contratos(True)
    contratos_con_activo["AssetCreate"] = _contrato(["asset_type", "file_name", "storage_uri"], asset_type=S,
                                                     file_name=S, storage_uri=S, mime_type=S, is_primary=B)
    api.spec = lambda service: {"components": {"schemas": contratos_con_activo}}
    _, sin = cargar(api, empresa, escribir=True)
    assert sin["conteo"]["product_assets"] == {"OMITIDO": 1} and api.creados("/assets") == []
    cargador = Cargador(api, empresa, escribir=True, con_imagenes=True)
    con = cargador.ejecutar(validar_sio=False)
    assert con["conteo"]["product_assets"] == {"CREADO": 1}
    activo = api.creados("/assets")[0]
    producto = next(p for p in api.creados("/api/v1/products") if p["canonical_name"] == "Producto sintético 1 g")
    assert activo["global_product_id"] == producto["id"] and activo["storage_uri"] == fila["storage_uri"]
    assert activo["is_primary"] is True
    envios = len(api.envios)
    Cargador(api, empresa, escribir=True, con_imagenes=True).ejecutar(validar_sio=False)
    otra = Cargador(api, empresa, escribir=True, con_imagenes=True, salida=tmp_path / "sin-diario").ejecutar(validar_sio=False)
    assert len(api.envios) == envios and otra["conteo"]["product_assets"] == {"REUSADO": 1}


def test_spec_019_productos_de_empresa_sin_precio_ni_costo(empresa: Path) -> None:
    api = SioFalso()
    contrato = contratos(True)
    for campo in ("sale_price", "reference_cost"):  # contrato desplegado de la spec 019
        contrato["CompanyProductCreate"]["properties"].pop(campo)
    api.spec = lambda service: {"components": {"schemas": contrato}}
    _, resumen = cargar(api, empresa, escribir=True)
    assert resumen["conteo"]["company_products"] == {"CREADO": 2}
    assert resumen["conteo"]["company_product_presentations"] == {"CREADO": 2}
    enviados = [b for _, _, ruta, b in api.envios if ruta.endswith("/company-products")]
    assert all("sale_price" not in b and "reference_cost" not in b for b in enviados)  # nunca se envía 0
