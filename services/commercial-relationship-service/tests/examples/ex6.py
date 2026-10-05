"""Ejercicio 6 de docs/ejemplo/: listas de precios, cambio de precio y precio aplicable (FR-040 a FR-056).

Precio real de `docs/CAMPOS PRODUCTOS.xlsx` (fila 16577, `Precio Lista 10` = 30420, el único precio por lista de la
fuente); el resto de precios es ficticio.
"""

from tests.examples.spec_common import (
    API,
    EMPRESA_EJ6,
    GP_ACETAMINOFEN,
    GP_IRBESARTAN,
    call,
    get_company,
    get_global_product,
    step,
)

LIST_SHOW = ["id", "code", "name", "currency_code", "is_default", "status", "version"]
PRICE_SHOW = ["id", "price_list_id", "company_product_id", "company_product_presentation_id", "unit_price",
              "currency_code", "status", "version"]
ERROR_SHOW = ["status", "code", "detail", "errors"]
FAR_FUTURE = "2099-01-01T00:00:00Z"

EX6 = dict(
    folder="6-listas-de-precios",
    title="Ejercicio 6 — Listas de precios y precio aplicable",
    data_file="00-datos-del-excel.md",
    real_data=True,
    focus=(
        "Crear una **lista de precios predeterminada**, registrar el **precio** real de la fuente, ver el rechazo de un "
        "**precio solapado** y de un **precio en vigencia modificado**, **cambiar el precio** con vigencia futura y "
        "resolver el **precio aplicable** con precio de lista, con **respaldo** en el precio simple y **sin respaldo** "
        "cuando se indica una lista explícita."
    ),
    data=[
        ("Fuente", "`docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2)"),
        ("Fila 16577", "`Código` 022315 · `Nombre` IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA "
         "CAJAX30MK · `Código Barras 1` 7702057716226 · `Precio Lista 10` **30420** (único precio por lista de toda la "
         "fuente)"),
        ("Fila 40", "`Código` 000045 · ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED · sin precios por lista"),
        ("Precios ficticios", "Precio simple del acetaminofén 12000.00 COP y nuevo precio del irbesartán 31500.00 COP "
         "desde 2099 son **ficticios**."),
        ("Empresa", "DROGUERÍA PRECIOS FICTICIA S.A.S. (**ficticia**), registrada en Operational Context."),
    ],
    interpretation=[
        ("Lista", "`Precio Lista 10` → una `PriceList` con código `LISTA-10`; cada columna `Precio Lista N` sería otra "
         "lista. El precio concreto es un `PriceListItem`."),
        ("Moneda", "La lista fija la moneda de sus precios (`COP`, 2 decimales) y no se puede cambiar."),
        ("Historia", "Un precio en vigencia no se reescribe: se cierra o se cambia con `change-price`, que cierra el "
         "vigente y crea el nuevo en una sola operación."),
        ("Respaldo", "Sin lista indicada y sin precio en la predeterminada se usa `sale_price` del producto empresarial; "
         "con una lista explícita sin precio **no** hay respaldo (aclaración 2)."),
    ],
    order_rules=[
        ("Productos y lista antes de precios", "El precio une una lista y un producto empresarial `ACTIVE`."),
        ("Cambiar antes de resolver en el futuro", "La consulta con `at` en 2099 muestra el precio nuevo."),
    ],
    steps=[
        step("01-consultar-datos.md", "Consultar la empresa y los productos globales",
             "Obtener `<EMPRESA>` y los productos globales.", [
                 get_company("EMPRESA", EMPRESA_EJ6, "DROGUERÍA PRECIOS FICTICIA S.A.S."),
                 get_global_product("GP_IRBESARTAN", GP_IRBESARTAN, "7702057716226",
                                    "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK"),
                 get_global_product("GP_ACETAMINOFEN", GP_ACETAMINOFEN, "7707355056876",
                                    "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"),
             ]),
        step("02-adoptar-productos.md", "Adoptar los productos", "Crear los productos empresariales.", [
            call("Adoptar el irbesartán (fila 16577)", "POST", f"{API}/companies/<EMPRESA>/company-products",
                 body={"global_product_id": "<GP_IRBESARTAN>", "internal_code": "022315",
                       "display_name": "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK",
                       "currency_code": "COP"},
                 why=["Ejercicio 1."], save={"IRBESARTAN": "id"}, show=["id", "internal_code", "sale_price"]),
            call("Adoptar el acetaminofén con precio simple (ficticio)", "POST",
                 f"{API}/companies/<EMPRESA>/company-products",
                 body={"global_product_id": "<GP_ACETAMINOFEN>", "internal_code": "000045",
                       "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED",
                       "currency_code": "COP", "sale_price": "12000.00"},
                 why=["`sale_price` es el precio simple de respaldo cuando no hay precio de lista (FR-056)."],
                 save={"ACETAMINOFEN": "id"}, show=["id", "internal_code", "sale_price"]),
        ]),
        step("03-lista-y-precio.md", "Crear la lista y registrar el precio",
             "Lista predeterminada en COP con el precio real y el rechazo por solapamiento.", [
                 call("Crear la lista 10 como predeterminada en COP", "POST", f"{API}/companies/<EMPRESA>/price-lists",
                      body={"code": "LISTA-10", "name": "Precio Lista 10", "currency_code": "COP", "is_default": True},
                      why=["Hay como máximo una lista predeterminada `ACTIVE` por empresa y moneda."],
                      save={"LISTA": "id"}, show=LIST_SHOW),
                 call("Registrar el precio real del irbesartán", "POST", f"{API}/companies/<EMPRESA>/price-list-items",
                      body={"price_list_id": "<LISTA>", "company_product_id": "<IRBESARTAN>", "unit_price": "30420",
                            "valid_from": "2026-01-01T00:00:00Z"},
                      why=["Precio general del producto (sin presentación), vigente desde 2026 y sin fin. La moneda es "
                           "la de la lista y admite 2 decimales."],
                      save={"PRECIO": "id"}, show=PRICE_SHOW),
                 call("Registrar otro precio que se cruza (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/price-list-items",
                      body={"price_list_id": "<LISTA>", "company_product_id": "<IRBESARTAN>", "unit_price": "31000",
                            "valid_from": "2026-06-01T00:00:00Z"},
                      why=["Las vigencias de una misma lista, producto y presentación no se solapan: "
                           "`409 PRICE_PERIOD_OVERLAP`."],
                      expect=409, show=ERROR_SHOW),
             ]),
        step("04-cambiar-precio.md", "Cambiar el precio",
             "Un precio en vigencia no se reescribe; se usa change-price.", [
                 call("Modificar el valor del precio en vigencia (rechazado)", "PUT",
                      f"{API}/price-list-items/<PRECIO>",
                      body={"unit_price": "31500", "valid_from": "2026-01-01T00:00:00Z", "valid_to": None, "version": 1},
                      why=["`422 PRICE_IN_EFFECT_NOT_MODIFIABLE`: el precio ya entró en vigencia (DS-08)."],
                      expect=422, show=ERROR_SHOW),
                 call("Cambiar el precio desde 2099 (ficticio)", "POST", f"{API}/price-list-items/<PRECIO>/change-price",
                      body={"unit_price": "31500", "effective_from": FAR_FUTURE, "version": 1},
                      why=["En una sola operación cierra el precio vigente en el instante de efecto y crea el nuevo "
                           "desde ese instante (FR-054a). Exige `update`."],
                      save={"PRECIO_NUEVO": "item.id"},
                      show=["item.unit_price", "item.status", "item.version", "previous.unit_price",
                            "previous.version"]),
             ]),
        step("05-precio-aplicable.md", "Resolver el precio aplicable",
             "Precio de lista, respaldo en el precio simple y lista explícita sin precio.", [
                 call("Resolver hoy: irbesartán y acetaminofén con la lista predeterminada", "POST",
                      f"{API}/companies/<EMPRESA>/applicable-prices/resolve",
                      body={"at": "2027-01-01T00:00:00Z", "lines": [
                          {"line_id": "1", "company_product_id": "<IRBESARTAN>"},
                          {"line_id": "2", "company_product_id": "<ACETAMINOFEN>"},
                      ]},
                      why=["Línea 1: precio de la lista predeterminada (`PRICE_LIST_ITEM`, por unidad base). Línea 2: "
                           "sin precio en la lista se usa `sale_price` (`COMPANY_PRODUCT_SALE_PRICE`)."],
                      show=["items[].line_id", "items[].resolution", "items[].basis", "items[].unit_price",
                            "items[].currency_code"]),
                 call("Resolver con la lista explícita para el acetaminofén", "POST",
                      f"{API}/companies/<EMPRESA>/applicable-prices/resolve",
                      body={"at": "2027-01-01T00:00:00Z", "lines": [
                          {"line_id": "1", "company_product_id": "<ACETAMINOFEN>", "price_list_id": "<LISTA>"},
                      ]},
                      why=["Con lista explícita y sin precio no hay respaldo: `NO_PRICE_IN_LIST` (aclaración 2)."],
                      show=["items[].line_id", "items[].resolution", "items[].unit_price"]),
                 call("Resolver en 2099: precio nuevo", "POST", f"{API}/companies/<EMPRESA>/applicable-prices/resolve",
                      body={"at": "2099-06-01T00:00:00Z", "lines": [{"line_id": "1", "company_product_id": "<IRBESARTAN>"}]},
                      why=["La consulta con un instante resuelve con los precios vigentes en ese instante; el precio "
                           "histórico se conserva (SC-009)."],
                      show=["items[].resolution", "items[].unit_price"]),
             ]),
    ],
)
