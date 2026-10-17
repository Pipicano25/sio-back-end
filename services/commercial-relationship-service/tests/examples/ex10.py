"""Ejercicio 10 de docs/ejemplo/: búsqueda progresiva y presentaciones por productos (spec 022, CR-1 y CR-2).

Productos reales de `docs/CAMPOS PRODUCTOS.xlsx` (filas 40, 413 y 16577); las presentaciones, los SKU y la empresa
son **ficticios**.
"""

from tests.examples.spec_common import (
    API,
    EMPRESA_EJ10,
    GP_ACETAMINOFEN,
    GP_AGUJA,
    GP_IRBESARTAN,
    GPRES_ACETA_CAJA,
    GPRES_ACETA_SOBRE,
    call,
    get_company,
    get_global_presentation,
    get_global_product,
    step,
)

SEARCH = f"{API}/companies/<EMPRESA>/company-products/search"
BY_PRODUCTS = f"{API}/companies/<EMPRESA>/company-product-presentations/by-products"
ITEM_SHOW = ["items[].id", "items[].internal_code", "items[].display_name", "items[].position", "has_more"]
PRESENTATION_SHOW = ["items[].company_product_id", "items[].status"]
ERROR_SHOW = ["status", "code", "detail", "errors"]

ACETAMINOFEN_NAME = "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"
AGUJA_NAME = "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO"
IRBESARTAN_NAME = "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK"


def _adopt(title, variable, product_variable, code, name):
    return call(
        title, "POST", f"{API}/companies/<EMPRESA>/company-products",
        body={"global_product_id": f"<{product_variable}>", "internal_code": code, "display_name": name,
              "currency_code": "COP"},
        why=["Ejercicio 1: la adopción registra el primer uso del producto global."],
        save={variable: "id"}, show=["id", "internal_code", "display_name"],
    )


EX10 = dict(
    folder="10-busqueda-progresiva",
    title="Ejercicio 10 — Búsqueda progresiva de productos y presentaciones por productos",
    data_file="00-datos-del-excel.md",
    real_data=True,
    focus=(
        "**Buscar** productos de la empresa por nombre, código o **SKU de una presentación**, **continuar** la búsqueda "
        "desde la posición del último producto recibido sin conteos ni páginas numeradas, **evaluar** filtros sobre un "
        "lote de ids y pedir en **una sola llamada** las presentaciones de varios productos (spec 022). Son las "
        "consultas que usa el servicio de consultas consolidadas."
    ),
    data=[
        ("Fuente", "`docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2)"),
        ("Fila 40", f"`Código` 000045 · {ACETAMINOFEN_NAME}"),
        ("Fila 413", f"`Código` 000537 · {AGUJA_NAME}"),
        ("Fila 16577", f"`Código` 022315 · {IRBESARTAN_NAME}"),
        ("Presentaciones y SKU", "**Ficticios**: «Caja x100» (`ACE-CJ100`) y «Sobre x10» (`ACE-SB10`) del acetaminofén. "
         "La fuente no trae presentaciones por fila."),
        ("Empresa", "DROGUERÍA BÚSQUEDAS FICTICIA S.A.S. (**ficticia**), registrada en Operational Context."),
    ],
    interpretation=[
        ("Orden estable", "Los resultados van ordenados por `display_name` (o por la clave de `sort`) y, a igualdad, "
         "por `id`. Ese orden no cambia entre llamadas."),
        ("Posición", "Cada producto trae su `position`: el valor de la clave de orden y su `id`. Para seguir, se envía "
         "en `after` la posición del **último producto que se usó**; la búsqueda devuelve solo los posteriores."),
        ("Sin conteos", "No hay `total_records`: `has_more` dice si quedan productos. Así una búsqueda no recorre toda "
         "la empresa para contar."),
        ("Modo evaluador", "Con `company_product_ids` o `global_product_ids` (hasta 100) se comprueba qué productos de "
         "un lote cumplen los filtros."),
    ],
    order_rules=[
        ("Productos y presentaciones primero", "La búsqueda por SKU necesita una presentación adoptada."),
        ("Primera llamada antes de continuar", "La segunda llamada usa la posición que devolvió la primera."),
    ],
    steps=[
        step("01-consultar-datos.md", "Consultar la empresa, los productos y las presentaciones",
             "Obtener `<EMPRESA>`, los productos globales y las presentaciones del acetaminofén.", [
                 get_company("EMPRESA", EMPRESA_EJ10, "DROGUERÍA BÚSQUEDAS FICTICIA S.A.S."),
                 get_global_product("GP_ACETAMINOFEN", GP_ACETAMINOFEN, "7707355056876", ACETAMINOFEN_NAME),
                 get_global_product("GP_AGUJA", GP_AGUJA, "7706634002856", AGUJA_NAME),
                 get_global_product("GP_IRBESARTAN", GP_IRBESARTAN, "7702057716226", IRBESARTAN_NAME),
                 get_global_presentation("GPRES_CAJA", GPRES_ACETA_CAJA, "GP_ACETAMINOFEN", "Caja x100"),
                 get_global_presentation("GPRES_SOBRE", GPRES_ACETA_SOBRE, "GP_ACETAMINOFEN", "Sobre x10"),
             ]),
        step("02-adoptar-productos.md", "Adoptar los productos y las presentaciones",
             "Crear tres productos empresariales y dos presentaciones con SKU.", [
                 _adopt("Adoptar el acetaminofén (fila 40)", "ACETAMINOFEN", "GP_ACETAMINOFEN", "000045", ACETAMINOFEN_NAME),
                 _adopt("Adoptar la aguja (fila 413)", "AGUJA", "GP_AGUJA", "000537", AGUJA_NAME),
                 _adopt("Adoptar el irbesartán (fila 16577)", "IRBESARTAN", "GP_IRBESARTAN", "022315", IRBESARTAN_NAME),
                 call("Adoptar la caja x100 del acetaminofén", "POST",
                      f"{API}/companies/<EMPRESA>/company-product-presentations",
                      body={"company_product_id": "<ACETAMINOFEN>", "global_product_presentation_id": "<GPRES_CAJA>",
                            "sku": "ACE-CJ100"},
                      why=["Ejercicio 4. El SKU es de la empresa y servirá para buscar el producto."],
                      save={"PRES_CAJA": "id"}, show=["id", "company_product_id", "sku"]),
                 call("Adoptar el sobre x10 del acetaminofén", "POST",
                      f"{API}/companies/<EMPRESA>/company-product-presentations",
                      body={"company_product_id": "<ACETAMINOFEN>", "global_product_presentation_id": "<GPRES_SOBRE>",
                            "sku": "ACE-SB10"},
                      why=["Dos presentaciones del mismo producto: la búsqueda por SKU no repite el producto."],
                      save={"PRES_SOBRE": "id"}, show=["id", "company_product_id", "sku"]),
             ]),
        step("03-buscar.md", "Buscar por nombre, código y SKU",
             "Encontrar productos por partes del nombre, por código exacto y por el SKU de una presentación.", [
                 call("Buscar «tableta» en el nombre", "POST", SEARCH, body={"search": "tableta", "limit": 10},
                      why=["`search` busca sin distinguir mayúsculas en nombre, códigos y SKU. Dos productos tienen "
                           "«TABLETA» en el nombre: vuelven en orden de `display_name`."],
                      show=ITEM_SHOW),
                 call("Buscar por una parte del SKU", "POST", SEARCH, body={"search": "ace-", "limit": 10},
                      why=["Las dos presentaciones del acetaminofén coinciden, pero el producto aparece **una sola** vez."],
                      show=ITEM_SHOW),
                 call("Buscar por código interno exacto", "POST", SEARCH, body={"internal_code": "000537", "limit": 10},
                      why=["`internal_code` y `sku` son coincidencias exactas (sin distinguir mayúsculas), no parciales."],
                      show=ITEM_SHOW),
             ]),
        step("04-continuar.md", "Continuar desde la posición del último producto",
             "Pedir de a dos productos y seguir con la posición del último recibido.", [
                 call("Primeros dos productos", "POST", SEARCH, body={"limit": 2},
                      why=["Sin filtros vuelven los productos `ACTIVE` en orden de `display_name`. `has_more = true`: "
                           "quedan productos."],
                      save={"POS_K": "items[1].position.k[0]", "POS_ID": "items[1].position.id"},
                      show=ITEM_SHOW),
                 call("Continuar después del segundo", "POST", SEARCH,
                      body={"limit": 2, "after": {"k": ["<POS_K>"], "id": "<POS_ID>"}},
                      why=["`after` es la `position` del último producto usado. Vuelve solo el tercero y "
                           "`has_more = false`: no hay más. Ningún producto se repite ni se salta."],
                      show=ITEM_SHOW),
             ]),
        step("05-lotes-y-rechazos.md", "Evaluar un lote, pedir presentaciones y rechazos",
             "Comprobar filtros sobre un lote de ids, traer las presentaciones de varios productos y los errores.", [
                 call("¿Cuáles de estos productos coinciden con «aguja»?", "POST", SEARCH,
                      body={"search": "aguja", "company_product_ids": ["<ACETAMINOFEN>", "<AGUJA>"], "limit": 10},
                      why=["Modo evaluador: solo se miran los ids enviados (hasta 100) y se aplican los filtros."],
                      show=ITEM_SHOW),
                 call("Presentaciones del acetaminofén y la aguja", "POST", BY_PRODUCTS,
                      body={"company_product_ids": ["<ACETAMINOFEN>", "<AGUJA>"]},
                      why=["Una sola llamada para varios productos, en orden `company_product_id, id`. Vuelven las dos "
                           "presentaciones del acetaminofén (`ACE-CJ100` y `ACE-SB10`); la aguja no tiene presentaciones "
                           "adoptadas: no aparece ninguna suya."],
                      show=PRESENTATION_SHOW),
                 call("Pedir 101 productos (rechazado)", "POST", SEARCH, body={"limit": 101},
                      why=["`limit` admite de 1 a 100: `422 VALIDATION_ERROR`."],
                      expect=422, show=ERROR_SHOW),
                 call("Enviar los dos tipos de ids a la vez (rechazado)", "POST", SEARCH,
                      body={"company_product_ids": ["<AGUJA>"], "global_product_ids": ["<GP_AGUJA>"], "limit": 10},
                      why=["Se usa `company_product_ids` **o** `global_product_ids`: `422 VALIDATION_ERROR`."],
                      expect=422, show=ERROR_SHOW),
             ]),
    ],
)
