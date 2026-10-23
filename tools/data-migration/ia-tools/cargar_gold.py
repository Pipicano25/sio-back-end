"""Cargue del Gold de una empresa a SIO por sus API públicas. SIMULACIÓN por defecto.

Uso:
    tools/data-migration/.venv/bin/python tools/data-migration/ia-tools/cargar_gold.py tools/data-migration/DAO \
        [--productos DAO/reports/piloto-propuesto.csv] [--entidades brands,products] [--rol consulta]
    # Escritura (solo con autorización): --escribir --confirmar <NOMBRE_DE_LA_CARPETA_DE_LA_EMPRESA> --rol <rol>

Para cada fila de Gold, en orden de dependencias:
1. Si ya tiene `sio_id` (columna del CSV o diario de ejecuciones anteriores) se da por cargada (`YA_CARGADO`).
2. Traduce cada `*_ref` al id de SIO de la fila referenciada; si esa fila no está cargada → `DEPENDENCIA`.
3. Construye el cuerpo con las propiedades del contrato OpenAPI desplegado y lo valida contra su esquema.
4. Busca la fila en SIO por su clave natural (GET); si existe se reutiliza (`REUSADO`) y nunca se sobrescribe.
5. Si no existe: en simulación `CREARIA`; con escritura habilitada, POST/PUT → `CREADO`, `CONFLICTO` (409) o `ERROR`.
6. Spec 021, `company_product_purchase_taxes`: actualiza la tasa de compra de un producto ya cargado solo si en SIO
   está sin configurar (`ACTUALIZARIA` / `ACTUALIZADO`); con la misma tasa `REUSADO`, con otra `CONFLICTO`.

- No modifica ningún CSV. Los id obtenidos se anotan en `<empresa>/reports/cargue/sio_ids.csv` (diario, solo en
  escritura), que permite detener y reanudar sin duplicar. Cada ejecución deja su reporte en el mismo directorio.
- Reutiliza `sio_query.py` (contratos, GET y token con `services/get_token.py`) y `validate_csv.py` (validación previa).
- 401 (tras renovar el token), 403, 5xx o servicio caído detienen la ejecución; el resto de errores se registra y se
  continúa con las filas independientes.
- No borra, no sube archivos (MinIO) y no envía filas cuyo dato faltante la API convertiría en un valor por defecto.
- Spec 024: las imágenes se registran por referencia en su presentación
  (`POST /products/{id}/presentations/{presentation_id}/assets`, columna `product_presentation_ref`). La respuesta
  no expone `storage_uri`, así que la identidad no se busca por GET: un `409 DUPLICATE_ASSET_CONTENT` con
  `existing_asset_id` (la misma imagen ya está en la presentación) se toma como `REUSADO` con ese id.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import requests
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sio_query  # noqa: E402
import validate_csv  # noqa: E402

ORDEN = [
    "organization_identities", "companies", "branches",
    "packaging_types", "brands", "attribute_definitions", "categories", "category_attributes",
    "products", "product_presentations", "product_identifiers", "product_categories", "product_attribute_values",
    "product_assets", "company_products", "company_product_presentations",
    # Spec 021: tasa de impuesto de compra de productos de empresa ya existentes (PUT, nunca sobrescribe otra tasa).
    "company_product_purchase_taxes",
]
# Los activos solo registran la referencia (storage_uri): el archivo debe estar ya en MinIO, subido con la cuenta de
# migración (README, sección 11). Sin --con-imagenes no se procesan.
SIN_IMAGENES = "registrar la imagen exige subir antes el archivo a MinIO y ejecutar con --con-imagenes"
NO_SOPORTADAS = {
    "source_classifications": "solo evidencia de la empresa; nunca se carga",
    **{tabla: "no soportado por esta versión del cargador" for tabla in (
        "company_suppliers", "supplier_payment_conditions", "supplier_products", "price_lists", "price_list_items",
        "purchase_sequences", "purchases", "purchase_details", "groups", "product_group_assignments")},
}
# Su identidad no depende de un padre: se buscan en SIO aunque un padre esté solo simulado.
SIN_PADRE_EN_LA_BUSQUEDA = {"organization_identities", "packaging_types", "brands", "attribute_definitions", "categories",
                            "products"}
CATALOGOS_COMPLETOS = {"packaging_types", "attribute_definitions", "categories", "category_attributes"}
# Campos que una API guardaría con un valor por defecto si se omiten: vacío ≠ 0, la fila no se envía. Solo aplica si
# el contrato desplegado todavía tiene el campo (desde la spec 019, CompanyProduct no tiene precio ni costo).
SIN_VALOR_POR_DEFECTO = {"company_products": ("sale_price", "reference_cost")}
TIPOS_DE_IDENTIDAD = ("GTIN", "EAN", "UPC", "BARCODE", "IUM")
PARAMETROS_DE_RUTA = {"company_id": "company_ref", "product_id": "product_ref", "category_id": "category_ref",
                      "definition_id": "attribute_definition_ref", "company_product_id": "company_product_ref",
                      "presentation_id": "product_presentation_ref"}
DUPLICADO_EN_LA_PRESENTACION = "PRODUCT_CATALOG.DUPLICATE_ASSET_CONTENT"
CATALOGO_SIO = {  # propiedad del contrato -> (columna del CSV, catálogo global de SIO)
    "country_id": ("country_iso3", "country"), "base_unit_id": ("base_unit_code", "unit"),
    "content_unit_id": ("content_unit_code", "unit"), "unit_of_measure_id": ("unit_code", "unit"),
    "packaging_type_id": ("packaging_type_code", "packaging"),
}
REFERENCIA = {  # propiedad del contrato -> columna *_ref del CSV
    "global_brand_id": "brand_ref", "manufacturer_organization_id": "manufacturer_organization_ref",
    "organization_identity_id": "organization_identity_ref", "parent_category_id": "parent_category_ref",
    "attribute_definition_id": "attribute_definition_ref", "global_product_id": "product_ref",
    "global_product_presentation_id": "product_presentation_ref", "global_category_id": "category_ref",
    "company_product_id": "company_product_ref",
}
VALORES_DE_ATRIBUTO = ("option_id", "text_value", "integer_value", "decimal_value", "boolean_value", "date_value")
COLUMNAS_REPORTE = ["orden", "csv", "ref", "resultado", "metodo", "servicio", "ruta", "http", "sio_id", "codigo", "detalle"]
NS_SIMULACION = uuid.UUID("5f0d6a52-6b7e-4e0f-9a0c-2f5d1a1e0d01")

plegar = lambda texto: unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().upper().strip()


class Detener(Exception):
    """Fallo que impide continuar con seguridad (autenticación, permisos o servicio no disponible)."""


class Api(sio_query.SioQuery):
    """SioQuery (contratos, GET y token de services/get_token.py) más el envío de escrituras, solo si se habilita."""

    def __init__(self, rol: str = "consulta", escritura: bool = False, **kwargs: Any) -> None:
        super().__init__(rol, **kwargs)
        self.escritura = escritura

    def send(self, method: str, service: str, path: str, body: dict) -> tuple[int, Any]:
        if not self.escritura:
            raise PermissionError("La escritura no está habilitada (modo simulación).")
        url = self.base_url(service) + path
        response = self.session.request(method, url, json=body, headers=self._authorization(), timeout=self.timeout)
        if response.status_code == 401:
            response = self.session.request(method, url, json=body, headers=self._authorization(renew=True),
                                            timeout=self.timeout)
        try:
            return response.status_code, response.json()
        except ValueError:
            return response.status_code, {"raw": response.text[:2000]}


def leer_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def tipado(valor: str, esquema: dict) -> Any:
    tipos = {esquema.get("type")} | {a.get("type") for a in esquema.get("anyOf", [])}
    if valor == "":
        return None
    if "boolean" in tipos:
        return valor == "true"
    if "integer" in tipos and re.fullmatch(r"-?\d+", valor):
        return int(valor)
    if "number" in tipos and "string" not in tipos:
        return float(valor)
    return valor


class Cargador:
    def __init__(self, api, empresa_dir: Path, *, escribir: bool = False, productos: set[str] | None = None,
                 entidades: set[str] | None = None, salida: Path | None = None, con_imagenes: bool = False) -> None:
        self.con_imagenes = con_imagenes
        self.api, self.empresa_dir, self.escribir = api, Path(empresa_dir), escribir
        if escribir and not getattr(api, "escritura", False):
            raise ValueError("El cliente no tiene la escritura habilitada.")
        self.esquemas = validate_csv.load_schemas()
        self.gold = {n: leer_csv(self.empresa_dir / "gold" / f"{n}.csv") for n in self.esquemas}
        self.pk = {n: e["primaryKey"][0] for n, e in self.esquemas.items()}
        self.fk = {n: {f["fields"][0]: f["reference"]["resource"] for f in e.get("foreignKeys", [])}
                   for n, e in self.esquemas.items()}
        self.entidades = entidades
        self.seleccion = self._seleccionar(productos)
        self.salida = Path(salida) if salida else self.empresa_dir / "reports" / "cargue"
        self.ids: dict[tuple[str, str], str] = {}        # (csv, ref) -> id en SIO (real o simulado)
        self.resultado: dict[tuple[str, str], str] = {}  # (csv, ref) -> resultado de esta ejecución
        self.simulados: set[str] = set()
        self.paquetes = {r["code"]: r[self.pk["packaging_types"]] for r in self.gold["packaging_types"]}
        self.identificadores = defaultdict(list)
        for fila in self.gold["product_identifiers"]:
            self.identificadores[fila["product_ref"]].append(fila)
        for tabla, filas in self.gold.items():  # sio_id ya anotado en el CSV
            for fila in filas:
                if fila.get("sio_id"):
                    self.ids[(tabla, fila[self.pk[tabla]])] = fila["sio_id"]
        self.diario_path = self.salida / "sio_ids.csv"
        if self.diario_path.is_file():
            for fila in leer_csv(self.diario_path):
                self.ids.setdefault((fila["csv"], fila["ref"]), fila["sio_id"])
        self.ya_cargados = set(self.ids)
        self._catalogos: dict[str, dict[str, str]] = {}
        self._divisiones: dict[str, dict[str, str]] = {}
        self.conteo: dict[str, Counter] = defaultdict(Counter)

    # --- selección --------------------------------------------------------------------------------
    def _seleccionar(self, productos: set[str] | None) -> dict[str, set[str] | None]:
        todas = {n: None for n in self.esquemas}
        if productos is None:
            return todas
        conocidos = {r["product_ref"] for r in self.gold["products"]}
        faltan = sorted(set(productos) - conocidos)
        if faltan:
            raise SystemExit(f"Productos de la selección que no están en Gold: {', '.join(faltan[:10])}")
        sel = dict(todas)
        sel["products"] = set(productos)
        for tabla in ("product_presentations", "product_identifiers", "product_categories", "product_attribute_values",
                      "product_assets", "company_products"):
            sel[tabla] = {r[self.pk[tabla]] for r in self.gold[tabla] if r["product_ref"] in productos}
        sel["company_product_presentations"] = {r[self.pk["company_product_presentations"]]
                                                for r in self.gold["company_product_presentations"]
                                                if r["company_product_ref"] in sel["company_products"]}
        sel["company_product_purchase_taxes"] = {r[self.pk["company_product_purchase_taxes"]]
                                                 for r in self.gold["company_product_purchase_taxes"]
                                                 if r["company_product_ref"] in sel["company_products"]}
        elegidos = [r for r in self.gold["products"] if r["product_ref"] in productos]
        sel["brands"] = {r["brand_ref"] for r in elegidos if r["brand_ref"]}
        sel["organization_identities"] = ({r["manufacturer_organization_ref"] for r in elegidos
                                           if r["manufacturer_organization_ref"]}
                                          | {r["organization_identity_ref"] for r in self.gold["companies"]})
        for tabla in set(self.esquemas) - CATALOGOS_COMPLETOS - {"companies", "branches"}:
            if sel[tabla] is None:  # tablas sin relación con los productos elegidos (proveedores, compras…)
                sel[tabla] = set()
        return sel

    def filas(self, tabla: str) -> list[dict[str, str]]:
        elegidas = self.seleccion.get(tabla)
        filas = [r for r in self.gold[tabla] if elegidas is None or r[self.pk[tabla]] in elegidas]
        propias = [col for col, destino in self.fk[tabla].items() if destino == tabla]  # p. ej. categoría padre
        if not propias:
            return filas
        refs, ordenadas, vistas = {r[self.pk[tabla]]: r for r in filas}, [], set()

        def visitar(fila: dict) -> None:
            ref = fila[self.pk[tabla]]
            if ref in vistas:
                return
            vistas.add(ref)
            for col in propias:
                if fila.get(col) in refs:
                    visitar(refs[fila[col]])
            ordenadas.append(fila)

        for fila in filas:
            visitar(fila)
        return ordenadas

    # --- catálogos globales de SIO (solo GET) -----------------------------------------------------
    def _get(self, service: str, path: str, params: dict | None = None, all_pages: bool = False) -> tuple[int, Any]:
        try:
            status, body = self.api.get(service, path, params or {}, all_pages=all_pages)
        except requests.RequestException as error:
            raise Detener(f"{service} no disponible: {type(error).__name__}") from None
        if status in (401, 403):
            raise Detener(f"{service} rechazó la consulta {path} con HTTP {status} (token o permisos)")
        if status >= 500:
            raise Detener(f"{service} respondió HTTP {status} en {path}")
        return status, body

    def _items(self, service: str, path: str, params: dict | None = None) -> list[dict]:
        status, body = self._get(service, path, params, all_pages=True)
        if status != 200:
            raise Detener(f"No se pudo leer {service} {path}: HTTP {status}")
        return body.get("items", []) if isinstance(body, dict) else body

    def catalogo(self, nombre: str) -> dict[str, str]:
        if nombre not in self._catalogos:
            fuente = {"unit": ("product-catalog", "/api/v1/units-of-measure", "code"),
                      "packaging": ("product-catalog", "/api/v1/packaging-types", "code"),
                      "country": ("geography", "/global-countries", "iso3_code")}[nombre]
            self._catalogos[nombre] = {plegar(i[fuente[2]]): i["id"] for i in self._items(fuente[0], fuente[1])}
        return self._catalogos[nombre]

    def division(self, country_id: str, nombre: str) -> str | None:
        if country_id not in self._divisiones:
            items = self._items("geography", "/global-administrative-divisions", {"country_id": country_id})
            self._divisiones[country_id] = {plegar(i["name"]): i["id"] for i in items}
        divisiones = self._divisiones[country_id]
        # Geography nombra algunos departamentos con su tipo ("Cauca Department"): igualdad exacta sin ese sufijo.
        sin_sufijo = {re.sub(r" (DEPARTMENT|DEPARTAMENTO)$", "", k): v for k, v in divisiones.items()}
        return divisiones.get(plegar(nombre)) or sin_sufijo.get(plegar(nombre))

    def ciudad(self, country_id: str, division_id: str | None, nombre: str) -> str | None:
        params = {"country_id": country_id, "search": nombre[:4]}
        if division_id:
            params["administrative_division_id"] = division_id
        hits = [c for c in self._items("geography", "/global-cities", params) if plegar(c["name"]) == plegar(nombre)]
        return hits[0]["id"] if len(hits) == 1 else None

    # --- construcción de la solicitud ------------------------------------------------------------
    def contrato(self, tabla: str) -> tuple[str, str, str, dict, dict]:
        sio = self.esquemas[tabla]["sio"]
        metodo, plantilla = sio["endpoint"].split(" ")[:2]
        componentes = self.api.spec(sio["service"])["components"]["schemas"]
        return sio["service"], metodo, plantilla, componentes, componentes[sio["contract"]]

    def dependencias(self, tabla: str, fila: dict) -> list[tuple[str, str]]:
        deps = [(destino, fila[col]) for col, destino in self.fk[tabla].items() if fila.get(col)]
        codigo = fila.get("packaging_type_code")
        if codigo in self.paquetes:  # tipo de empaque nuevo, creado en este mismo cargue
            deps.append(("packaging_types", self.paquetes[codigo]))
        return deps

    def construir(self, tabla: str, fila: dict) -> tuple[str, str, str, dict, list[str]]:
        servicio, metodo, plantilla, _, contrato = self.contrato(tabla)
        faltas: list[str] = []
        ruta = plantilla
        for param, col in PARAMETROS_DE_RUTA.items():
            if "{" + param + "}" in ruta:
                ruta = ruta.replace("{" + param + "}", self.ids[(self.fk[tabla][col], fila[col])])
        cuerpo: dict[str, Any] = {}
        for prop, esquema in contrato.get("properties", {}).items():
            if prop in REFERENCIA and fila.get(REFERENCIA[prop]):
                cuerpo[prop] = self.ids[(self.fk[tabla][REFERENCIA[prop]], fila[REFERENCIA[prop]])]
            elif prop in CATALOGO_SIO and fila.get(CATALOGO_SIO[prop][0]):
                col, nombre = CATALOGO_SIO[prop]
                if nombre == "packaging" and fila[col] in self.paquetes:
                    cuerpo[prop] = self.ids[("packaging_types", self.paquetes[fila[col]])]
                elif (valor := self.catalogo(nombre).get(plegar(fila[col]))) is not None:
                    cuerpo[prop] = valor
                else:
                    faltas.append(f"{col}={fila[col]} no existe en el catálogo de SIO")
            elif prop in fila and prop != "version":
                valor = tipado(fila[prop], esquema)
                if valor is not None:
                    cuerpo[prop] = valor
        country = cuerpo.get("country_id")
        if country and "city_id" in contrato.get("properties", {}):
            division = self.division(country, fila["administrative_division_name"]) if fila.get(
                "administrative_division_name") else None
            if fila.get("administrative_division_name") and division is None:
                faltas.append(f"división '{fila['administrative_division_name']}' no existe en Geography")
            if division:
                cuerpo["administrative_division_id"] = division
            if fila.get("city_name"):
                ciudad = self.ciudad(country, division, fila["city_name"])
                if ciudad is None:
                    faltas.append(f"ciudad '{fila['city_name']}' no se resuelve de forma única en Geography")
                else:
                    cuerpo["city_id"] = ciudad
        return servicio, metodo, ruta, cuerpo, faltas

    def validar_contrato(self, tabla: str, cuerpo: dict) -> list[str]:
        _, _, _, componentes, contrato = self.contrato(tabla)
        raiz = {"$ref": f"#/components/schemas/{self.esquemas[tabla]['sio']['contract']}",
                "components": {"schemas": componentes}}
        return [f"{'/'.join(map(str, e.path)) or 'cuerpo'}: {e.message[:160]}"
                for e in Draft202012Validator(raiz).iter_errors(cuerpo)]

    def tipo_admitido(self, tipo: str) -> bool:
        propiedad = self.contrato("product_identifiers")[4]["properties"]["identifier_type"]
        return tipo in propiedad.get("enum", [tipo])

    # --- identidad en SIO (clave natural, solo GET) ------------------------------------------------
    def buscar(self, tabla: str, fila: dict, cuerpo: dict, ruta: str) -> list[dict]:
        def lista(servicio, path, params=None):
            status, body = self._get(servicio, path, params)
            if status != 200:
                raise LookupError(f"GET {path} respondió HTTP {status}")
            return body.get("items", []) if isinstance(body, dict) else body

        mismo = lambda a, b: plegar(str(a)) == plegar(str(b))
        if tabla == "organization_identities":
            items = lista("party-identity", "/api/v1/organization-identities",
                          {"country_id": cuerpo["country_id"], "identification_type": fila["identification_type"],
                           "search": fila["identification_number"]})
            return [i for i in items if mismo(i["identification_number"], fila["identification_number"])
                    and mismo(i["identification_type"], fila["identification_type"])]
        if tabla == "companies":
            return lista("operational-context", "/api/v1/companies",
                         {"organization_identity_id": cuerpo["organization_identity_id"]})
        if tabla == "branches":
            return [i for i in lista("operational-context", ruta, {"search": fila["code"]}) if mismo(i["code"], fila["code"])]
        if tabla in ("packaging_types", "brands", "attribute_definitions", "categories"):
            return [i for i in lista("product-catalog", ruta, {"code": fila["code"]}) if mismo(i["code"], fila["code"])]
        if tabla == "category_attributes":
            return [i for i in lista("product-catalog", ruta) if i["attribute_definition_id"] == cuerpo["attribute_definition_id"]]
        if tabla == "products":
            encontrados = {}
            for ident in self.identificadores[fila["product_ref"]]:
                if ident["identifier_type"] not in TIPOS_DE_IDENTIDAD or not self.tipo_admitido(ident["identifier_type"]):
                    continue
                status, body = self._get("product-catalog", "/api/v1/products/by-identifier/{value}",
                                         {"value": ident["value"]})
                if status == 200:
                    encontrados[body["product"]["id"]] = body["product"]
                elif status != 404:
                    raise LookupError(f"by-identifier {ident['value']} respondió HTTP {status}")
            return list(encontrados.values())
        if tabla == "product_presentations":
            return [i for i in lista("product-catalog", ruta) if mismo(i["code"], fila["code"])]
        if tabla == "product_identifiers":
            return [i for i in lista("product-catalog", ruta) if i["identifier_type"] == fila["identifier_type"]
                    and fila["value"] in (i["value"], i.get("canonical_value"))]
        if tabla == "product_categories":
            return [i for i in lista("product-catalog", ruta) if i["global_category_id"] == cuerpo["global_category_id"]]
        if tabla == "product_attribute_values":
            definicion = ruta.rsplit("/", 1)[1]
            return [i for i in lista("product-catalog", ruta.rsplit("/", 1)[0]) if i["attribute_definition_id"] == definicion]
        if tabla == "product_assets":  # spec 024: sin storage_uri en la respuesta; la identidad la resuelve el 409
            return []
        if tabla == "company_products":
            return lista("commercial-relationship", ruta, {"global_product_id": cuerpo["global_product_id"]})
        if tabla == "company_product_presentations":
            return lista("commercial-relationship", ruta, {"company_product_id": cuerpo["company_product_id"],
                                                           "global_product_presentation_id": cuerpo["global_product_presentation_id"]})
        raise ValueError(f"Sin búsqueda de identidad para {tabla}")

    # --- proceso de una fila ----------------------------------------------------------------------
    def procesar(self, tabla: str, fila: dict) -> dict:
        ref = fila[self.pk[tabla]]
        r = {"csv": tabla, "ref": ref}
        if tabla in NO_SOPORTADAS:
            return {**r, "resultado": "OMITIDO", "detalle": NO_SOPORTADAS[tabla]}
        if tabla == "product_assets" and not self.con_imagenes:
            return {**r, "resultado": "OMITIDO", "detalle": SIN_IMAGENES}
        if (tabla, ref) in self.ya_cargados:
            return {**r, "resultado": "YA_CARGADO", "sio_id": self.ids[(tabla, ref)]}
        if tabla == "company_product_purchase_taxes":
            return self._tasa_de_compra(r, fila)
        simulada = False
        for destino, dep in self.dependencias(tabla, fila):
            if (destino, dep) in self.ids:
                simulada |= self.ids[(destino, dep)] in self.simulados
                continue
            estado = self.resultado.get((destino, dep), "no cargada ni seleccionada")
            return {**r, "resultado": "DEPENDENCIA", "detalle": f"depende de {dep} ({estado})"}
        if tabla == "product_identifiers" and not self.tipo_admitido(fila["identifier_type"]):
            return {**r, "resultado": "DEPENDENCIA",
                    "detalle": f"el contrato desplegado de Product Catalog no admite identifier_type={fila['identifier_type']}"}
        propiedades = self.contrato(tabla)[4].get("properties", {}) if tabla in SIN_VALOR_POR_DEFECTO else {}
        vacios = [c for c in SIN_VALOR_POR_DEFECTO.get(tabla, ()) if c in propiedades and not fila.get(c)]
        if vacios:
            return {**r, "resultado": "BLOQUEADA",
                    "detalle": f"{', '.join(vacios)} vacío: la API lo guardaría como valor por defecto (vacío ≠ 0)"}
        servicio, metodo, ruta, cuerpo, faltas = self.construir(tabla, fila)
        r.update(metodo=metodo, servicio=servicio, ruta=ruta)
        if faltas:
            return {**r, "resultado": "DEPENDENCIA", "detalle": "; ".join(faltas)}
        errores = self.validar_contrato(tabla, cuerpo)
        if errores:
            return {**r, "resultado": "INVALIDA", "detalle": "; ".join(errores)}
        if not simulada or tabla in SIN_PADRE_EN_LA_BUSQUEDA:  # bajo un padre simulado no hay nada que buscar
            try:
                existentes = self.buscar(tabla, fila, cuerpo, ruta)
            except LookupError as error:
                return {**r, "resultado": "ERROR", "detalle": str(error)}
            if len(existentes) > 1:
                return {**r, "resultado": "CONFLICTO",
                        "detalle": "varias coincidencias en SIO: " + ", ".join(e["id"] for e in existentes)}
            if existentes:
                return self._reusar(r, tabla, cuerpo, existentes[0])
        if not self.escribir:
            sid = str(uuid.uuid5(NS_SIMULACION, f"{tabla}:{ref}"))
            self.simulados.add(sid)
            return {**r, "resultado": "CREARIA", "sio_id": sid, "detalle": json.dumps(cuerpo, ensure_ascii=False)[:600]}
        return self._crear(r, servicio, metodo, ruta, cuerpo)

    def _tasa_de_compra(self, r: dict, fila: dict) -> dict:
        """Spec 021: configura la tasa de un producto de empresa existente, solo con el valor explícito de la fila.

        - Producto sin cargar → `DEPENDENCIA`; producto simulado → `ACTUALIZARIA` sin consultar SIO.
        - SIO ya tiene esa tasa → `REUSADO`; tiene otra → `CONFLICTO` (nunca se sobrescribe).
        - Sin tasa en SIO: simulación → `ACTUALIZARIA`; escritura → `PUT` con la `version` leída → `ACTUALIZADO`.
        """
        clave = ("company_products", fila["company_product_ref"])
        if clave not in self.ids:
            estado = self.resultado.get(clave, "no cargada ni seleccionada")
            return {**r, "resultado": "DEPENDENCIA", "detalle": f"depende de {fila['company_product_ref']} ({estado})"}
        producto = self.ids[clave]
        servicio, metodo, ruta, _, _ = self.construir("company_product_purchase_taxes", fila)
        valor = fila["purchase_tax_percentage"]
        r.update(metodo=metodo, servicio=servicio, ruta=ruta)
        if producto in self.simulados:
            return {**r, "resultado": "ACTUALIZARIA", "sio_id": producto, "detalle": f"tasa {valor} (producto simulado)"}
        status, actual = self._get(servicio, f"/api/v1/company-products/{producto}")
        if status != 200:
            return {**r, "resultado": "ERROR", "detalle": f"GET del producto respondió HTTP {status}"}
        configurada = actual.get("purchase_tax_percentage")
        if configurada is not None:
            if Decimal(str(configurada)) == Decimal(valor):
                return {**r, "resultado": "REUSADO", "sio_id": producto, "detalle": f"tasa {configurada} ya configurada"}
            return {**r, "resultado": "CONFLICTO", "sio_id": producto,
                    "detalle": f"SIO ya tiene la tasa {configurada}; no se sobrescribe con {valor}"}
        cuerpo = {"version": actual["version"], "purchase_tax_percentage": valor}
        errores = self.validar_contrato("company_product_purchase_taxes", cuerpo)
        if errores:
            return {**r, "resultado": "INVALIDA", "detalle": "; ".join(errores)}
        if not self.escribir:
            return {**r, "resultado": "ACTUALIZARIA", "sio_id": producto, "detalle": json.dumps(cuerpo, ensure_ascii=False)}
        resultado = self._crear(r, servicio, metodo, ruta, cuerpo)
        if resultado["resultado"] == "CREADO":
            resultado["resultado"] = "ACTUALIZADO"
        return resultado

    def _reusar(self, r: dict, tabla: str, cuerpo: dict, existente: dict) -> dict:
        if tabla == "product_attribute_values":
            distintos = [k for k in VALORES_DE_ATRIBUTO if str(existente.get(k) or "") != str(cuerpo.get(k) or "")]
            if distintos:
                return {**r, "resultado": "CONFLICTO", "sio_id": existente["id"],
                        "detalle": f"SIO ya tiene otro valor ({', '.join(distintos)}); no se sobrescribe"}
        igual = lambda k, v: plegar(str(existente[k])) == plegar(str(v)) if k == "code" else str(existente[k]) == str(v)
        diferencias = [k for k, v in cuerpo.items() if k in existente and not igual(k, v)]  # códigos: RN-02
        detalle = f"existe en SIO; difiere en {', '.join(diferencias)} (no se modifica)" if diferencias else "existe en SIO"
        return {**r, "resultado": "REUSADO", "sio_id": existente["id"], "detalle": detalle}

    def _crear(self, r: dict, servicio: str, metodo: str, ruta: str, cuerpo: dict) -> dict:
        try:
            status, body = self.api.send(metodo, servicio, ruta, cuerpo)
        except requests.RequestException as error:
            raise Detener(f"{servicio} no disponible: {type(error).__name__}") from None
        r["http"] = status
        if status in (200, 201):
            avisos = "; ".join(w.get("code", "") for w in (body.get("warnings") or []))
            return {**r, "resultado": "CREADO", "sio_id": body["id"], "detalle": f"advertencias: {avisos}" if avisos else ""}
        codigo = body.get("code", "") if isinstance(body, dict) else ""
        detalle = (body.get("detail") or body.get("title") or "") if isinstance(body, dict) else ""
        if status in (401, 403):
            raise Detener(f"{servicio} respondió HTTP {status} {codigo} (token o permisos)")
        if status >= 500:
            raise Detener(f"{servicio} respondió HTTP {status} {codigo}")
        if status == 409 and codigo == DUPLICADO_EN_LA_PRESENTACION and body.get("existing_asset_id"):
            return {**r, "resultado": "REUSADO", "sio_id": body["existing_asset_id"],
                    "detalle": "la presentación ya tiene esta imagen (no se modifica)"}
        resultado = "CONFLICTO" if status == 409 else "ERROR"
        return {**r, "resultado": resultado, "codigo": codigo, "detalle": str(detalle)[:500]}

    # --- ejecución -------------------------------------------------------------------------------
    def ejecutar(self, validar_sio: bool = True) -> dict:
        validacion = validate_csv.validate(self.empresa_dir, "gold", validar_sio)
        if validacion["errores"]:
            raise SystemExit(f"Gold no pasa validate_csv.py ({validacion['errores']} errores); no se carga nada.")
        self.salida.mkdir(parents=True, exist_ok=True)
        modo = "escritura" if self.escribir else "simulacion"
        nombre = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{modo}"
        reporte_path = self.salida / f"{nombre}.csv"
        estado, motivo, orden = "COMPLETA", "", 0
        with reporte_path.open("w", newline="", encoding="utf-8") as reporte, \
                (self.diario_path.open("a", newline="", encoding="utf-8") if self.escribir else open(os.devnull, "w")) as diario:
            escritor = csv.DictWriter(reporte, fieldnames=COLUMNAS_REPORTE, extrasaction="ignore")
            escritor.writeheader()
            anotar = csv.writer(diario)
            if self.escribir and self.diario_path.stat().st_size == 0:
                anotar.writerow(["csv", "ref", "sio_id", "resultado", "ejecucion"])
            try:
                for tabla in ORDEN + sorted(NO_SOPORTADAS):
                    if self.entidades is not None and tabla not in self.entidades:
                        continue
                    for fila in self.filas(tabla):
                        orden += 1
                        r = self.procesar(tabla, fila)
                        clave = (tabla, r["ref"])
                        self.resultado[clave] = r["resultado"]
                        if r.get("sio_id") and r["resultado"] in (
                                "CREADO", "REUSADO", "CREARIA", "YA_CARGADO", "ACTUALIZADO", "ACTUALIZARIA"):
                            self.ids[clave] = r["sio_id"]
                        if self.escribir and r["resultado"] in ("CREADO", "REUSADO", "ACTUALIZADO"):
                            anotar.writerow([tabla, r["ref"], r["sio_id"], r["resultado"], nombre])
                            diario.flush()
                            os.fsync(diario.fileno())
                        escritor.writerow({"orden": orden, **r})
                        reporte.flush()
                        self.conteo[tabla][r["resultado"]] += 1
            except Detener as error:
                estado, motivo = "DETENIDA", str(error)
            except KeyboardInterrupt:
                estado, motivo = "INTERRUMPIDA", "interrumpida por el usuario"
        resumen = {"empresa": self.empresa_dir.name, "modo": modo, "estado": estado, "motivo": motivo,
                   "rol": getattr(self.api, "rol", None), "reporte": str(reporte_path),
                   "seleccion_productos": None if self.seleccion["products"] is None else len(self.seleccion["products"]),
                   "conteo": {t: dict(c) for t, c in self.conteo.items()}}
        reporte_path.with_suffix(".json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
        return resumen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Carga el Gold de una empresa a SIO por API (simulación por defecto).")
    parser.add_argument("empresa_dir", type=Path, help="Carpeta de la empresa (p. ej. tools/data-migration/DAO)")
    parser.add_argument("--productos", type=Path, help="CSV con una columna product_ref: limita el cargue a esos productos")
    parser.add_argument("--entidades", help="CSV de Gold a procesar, separados por comas (por defecto todos)")
    parser.add_argument("--rol", default="consulta",
                        help="Rol de services/get_token.py (por defecto consulta), cliente:<client_id> o usuario:<nombre>")
    parser.add_argument("--salida", type=Path, help="Carpeta de reportes y diario (por defecto <empresa>/reports/cargue)")
    parser.add_argument("--escribir", action="store_true", help="Habilita POST/PUT reales (exige --confirmar)")
    parser.add_argument("--confirmar", help="Nombre exacto de la carpeta de la empresa, para confirmar la escritura")
    parser.add_argument("--con-imagenes", action="store_true",
                        help="Registra product_assets (los archivos ya deben estar en MinIO; ver README)")
    args = parser.parse_args(argv)
    empresa = args.empresa_dir.resolve()
    if args.escribir and args.confirmar != empresa.name:
        parser.error(f"--escribir exige --confirmar {empresa.name}")
    entidades = set(args.entidades.split(",")) if args.entidades else None
    if entidades and (desconocidas := entidades - set(ORDEN) - set(NO_SOPORTADAS)):
        parser.error(f"Entidades desconocidas: {', '.join(sorted(desconocidas))}")
    productos = {r["product_ref"] for r in leer_csv(args.productos)} if args.productos else None
    cargador = Cargador(Api(args.rol, escritura=args.escribir), empresa, escribir=args.escribir,
                        productos=productos, entidades=entidades, salida=args.salida, con_imagenes=args.con_imagenes)
    resumen = cargador.ejecutar()
    print(json.dumps(resumen, ensure_ascii=False, indent=2))
    if resumen["estado"] != "COMPLETA":
        return 3
    malos = sum(c.get(k, 0) for c in resumen["conteo"].values() for k in ("ERROR", "INVALIDA"))
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
