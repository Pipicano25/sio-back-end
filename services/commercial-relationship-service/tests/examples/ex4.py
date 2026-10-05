"""Ejercicio 4 de docs/ejemplo/: presentaciones empresariales (FR-010 a FR-017; DS-04, DS-05).

Producto real de `docs/CAMPOS PRODUCTOS.xlsx` (fila 40); las presentaciones globales son ficticias.
"""

from tests.examples.spec_common import (
    API,
    EMPRESA_EJ4,
    GP_ACETAMINOFEN,
    GP_AGUJA,
    GPRES_ACETA_CAJA,
    GPRES_ACETA_SOBRE,
    GPRES_AGUJA_CAJA,
    call,
    get_company,
    get_global_presentation,
    get_global_product,
    step,
)

PRESENTATION_SHOW = [
    "id", "company_product_id", "global_product_presentation_id", "internal_code", "sku", "is_purchasable",
    "is_sellable", "is_default_purchase", "is_default_sale", "status", "version",
]
ERROR_SHOW = ["status", "code", "detail", "errors"]

EX4 = dict(
    folder="4-presentaciones",
    title="Ejercicio 4 — Presentaciones de un producto empresarial",
    data_file="00-datos-del-excel.md",
    real_data=True,
    focus=(
        "**Adoptar presentaciones** globales para un producto ya adoptado, marcar la **predeterminada de compra** y "
        "ver cómo marcar otra **retira la marca anterior en la misma operación**, el **rechazo** de una presentación "
        "de otro producto y de una adopción repetida, e **inactivar** la predeterminada (pierde la marca)."
    ),
    data=[
        ("Fuente", "`docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2)"),
        ("Fila 40", "`Código` 000045 · `Nombre` ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED · "
         "`Unidad Medida` CAJA · `Contenido Interno` 100 · `Maneja Presentaciones` S"),
        ("Presentaciones", "**Ficticias**: «Caja x100» y «Sobre x10» del acetaminofén y «Caja x100» de la aguja (fila "
         "413), registradas en Product Catalog. La fuente no trae presentaciones por fila."),
        ("SKU", "**Ficticios** (`ACE-CJ100`, `ACE-SB10`)."),
        ("Empresa", "DROGUERÍA PRESENTACIONES FICTICIA S.A.S. (**ficticia**), registrada en Operational Context."),
    ],
    interpretation=[
        ("Qué se adopta", "La presentación global ya existe en Product Catalog; la empresa decide cuáles compra o vende "
         "y les pone su código o SKU. Solo se guarda el `id` de la presentación global."),
        ("Mismo producto", "La presentación debe ser del **mismo** producto global que adoptó el producto empresarial."),
        ("Primer uso", "Antes de guardar, Product Catalog registra el primer uso de la presentación; si falla, no se "
         "guarda nada."),
        ("Predeterminada", "Hay como máximo una predeterminada de compra y una de venta por producto. Marcar otra retira "
         "la anterior en la misma operación, que sube su `version` (aclaración 4). Inactivar retira la marca (DS-05)."),
    ],
    order_rules=[
        ("Producto adoptado primero", "La presentación empresarial pertenece a un producto empresarial `ACTIVE`."),
        ("Marcar antes de inactivar", "Se inactiva la predeterminada para mostrar que pierde la marca."),
    ],
    steps=[
        step("01-consultar-datos.md", "Consultar la empresa, el producto y sus presentaciones globales",
             "Obtener `<EMPRESA>`, el producto global y las presentaciones.", [
                 get_company("EMPRESA", EMPRESA_EJ4, "DROGUERÍA PRESENTACIONES FICTICIA S.A.S."),
                 get_global_product("GP_ACETAMINOFEN", GP_ACETAMINOFEN, "7707355056876",
                                    "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"),
                 get_global_presentation("GPRES_CAJA", GPRES_ACETA_CAJA, "GP_ACETAMINOFEN", "Caja x100"),
                 get_global_presentation("GPRES_SOBRE", GPRES_ACETA_SOBRE, "GP_ACETAMINOFEN", "Sobre x10"),
                 get_global_product("GP_AGUJA", GP_AGUJA, "7706634002856", "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO"),
                 get_global_presentation("GPRES_AGUJA", GPRES_AGUJA_CAJA, "GP_AGUJA", "Caja x100 de la aguja"),
             ]),
        step("02-adoptar-producto.md", "Adoptar el producto en la empresa",
             "Crear el producto empresarial al que pertenecerán las presentaciones.", [
                 call("Adoptar el acetaminofén (fila 40)", "POST", f"{API}/companies/<EMPRESA>/company-products",
                      body={"global_product_id": "<GP_ACETAMINOFEN>", "internal_code": "000045",
                            "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED",
                            "currency_code": "COP"},
                      why=["Ejercicio 1: la adopción registra el primer uso del producto global."],
                      save={"PRODUCTO": "id"}, show=["id", "internal_code", "status"]),
             ]),
        step("03-adoptar-presentaciones.md", "Adoptar presentaciones y cambiar la predeterminada",
             "Adoptar la caja como predeterminada de compra y luego el sobre, que toma la marca.", [
                 call("Adoptar la caja x100 como predeterminada de compra", "POST",
                      f"{API}/companies/<EMPRESA>/company-product-presentations",
                      body={"company_product_id": "<PRODUCTO>", "global_product_presentation_id": "<GPRES_CAJA>",
                            "sku": "ACE-CJ100", "is_default_purchase": True},
                      why=["El servicio comprueba en Product Catalog que la presentación esté `ACTIVE`, sea elegible y "
                           "sea del mismo producto global, y registra su primer uso."],
                      save={"PRES_CAJA": "id"}, show=PRESENTATION_SHOW),
                 call("Adoptar el sobre x10 y marcarlo predeterminado de compra", "POST",
                      f"{API}/companies/<EMPRESA>/company-product-presentations",
                      body={"company_product_id": "<PRODUCTO>", "global_product_presentation_id": "<GPRES_SOBRE>",
                            "sku": "ACE-SB10", "is_default_purchase": True},
                      why=["Marcar una nueva predeterminada retira la de la caja en la misma operación (aclaración 4)."],
                      save={"PRES_SOBRE": "id"}, show=PRESENTATION_SHOW),
                 call("Consultar la caja: ya no es predeterminada", "GET",
                      f"{API}/company-product-presentations/<PRES_CAJA>",
                      why=["La caja perdió la marca y subió a `version` 2, con `updated_by` del usuario que marcó el "
                           "sobre (Principio VII)."],
                      show=PRESENTATION_SHOW),
             ]),
        step("04-rechazos.md", "Rechazos esperados",
             "Presentación de otro producto y adopción repetida.", [
                 call("Adoptar la caja de la aguja para el acetaminofén (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/company-product-presentations",
                      body={"company_product_id": "<PRODUCTO>", "global_product_presentation_id": "<GPRES_AGUJA>"},
                      why=["La presentación pertenece a otro producto global: `422 GLOBAL_PRESENTATION_OF_OTHER_PRODUCT` "
                           "sin registrar primer uso."],
                      expect=422, show=ERROR_SHOW),
                 call("Adoptar otra vez la caja (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/company-product-presentations",
                      body={"company_product_id": "<PRODUCTO>", "global_product_presentation_id": "<GPRES_CAJA>"},
                      why=["Cada presentación se adopta una sola vez por producto, en cualquier estado: "
                           "`409 DUPLICATE_PRESENTATION_ADOPTION`."],
                      expect=409, show=ERROR_SHOW),
             ]),
        step("05-inactivar-y-consultar.md", "Inactivar la predeterminada y consultar",
             "Inactivar el sobre (pierde la marca) y listar las presentaciones del producto.", [
                 call("Inactivar el sobre", "POST", f"{API}/company-product-presentations/<PRES_SOBRE>/deactivate",
                      body={"version": 1},
                      why=["Inactivar exige `delete` y retira la marca de predeterminada (DS-05)."],
                      show=PRESENTATION_SHOW),
                 call("Listar todas las presentaciones del producto", "GET",
                      f"{API}/companies/<EMPRESA>/company-product-presentations?company_product_id=<PRODUCTO>&status=ALL",
                      why=["Sin `status` solo se listan las `ACTIVE`; `status=ALL` incluye las inactivas: aquí la caja "
                           "(`ACTIVE`) y el sobre (`INACTIVE`, sin marca)."],
                      show=["total_records", "page", "page_size"]),
             ]),
    ],
)
