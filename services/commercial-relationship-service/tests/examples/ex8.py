"""Ejercicio 8 de docs/ejemplo/: tasa de impuesto de compra del producto (spec 021, FR-021-07 y FR-021-08).

Productos reales de `docs/CAMPOS PRODUCTOS.xlsx` (filas 40 y 16577); las tasas y la empresa son **ficticias**: el 19 %
no representa una tarifa real.
"""

from tests.examples.spec_common import (
    API,
    EMPRESA_EJ8,
    GP_ACETAMINOFEN,
    GP_IRBESARTAN,
    call,
    get_company,
    get_global_product,
    step,
)

TAX_SHOW = ["id", "internal_code", "purchase_tax_percentage", "version"]
ERROR_SHOW = ["status", "code", "detail", "errors"]

EX8 = dict(
    folder="8-impuesto-de-compra",
    title="Ejercicio 8 — Tasa de impuesto de compra del producto",
    data_file="00-datos-del-excel.md",
    real_data=True,
    focus=(
        "Configurar la **tasa de impuesto de compra** predeterminada de los productos de la empresa: un producto nuevo "
        "queda **sin configurar** (distinto de 0 %), se configura uno por uno o en **lote** (todo o nada) y una tasa "
        "configurada no vuelve a quedar sin configurar. Compras la usa para calcular el impuesto de cada línea y no "
        "deja confirmar una compra con productos sin tasa (spec 021)."
    ),
    data=[
        ("Fuente", "`docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2)"),
        ("Fila 40", "`Código` 000045 · ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"),
        ("Fila 16577", "`Código` 022315 · IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK"),
        ("Tasas", "19 % y 0 % son **ficticias**: la fuente no informa impuestos de compra y SIO no asigna ninguna "
         "tasa por su cuenta."),
        ("Empresa", "DROGUERÍA IMPUESTOS FICTICIA S.A.S. (**ficticia**)."),
    ],
    interpretation=[
        ("Sin configurar ≠ 0 %", "`null` significa que nadie definió la tasa; `0` es una tasa válida (por ejemplo, un "
         "producto exento). Solo con tasa se puede confirmar una compra del producto."),
        ("Permiso propio", "La tasa se modifica con `company_product_purchase_taxes:update`, no con el `PUT` del "
         "producto. Solo administradores y supervisores."),
        ("Sin efecto en compras confirmadas", "Cada línea de compra congela su tasa al confirmar; cambiar la tasa del "
         "producto no modifica compras históricas."),
    ],
    order_rules=[
        ("Adoptar antes de configurar", "La tasa es un atributo del producto de la empresa."),
    ],
    steps=[
        step("01-consultar-datos.md", "Consultar la empresa y los productos globales",
             "Obtener `<EMPRESA>` y los productos globales.", [
                 get_company("EMPRESA", EMPRESA_EJ8, "DROGUERÍA IMPUESTOS FICTICIA S.A.S."),
                 get_global_product("GP_ACETAMINOFEN", GP_ACETAMINOFEN, "7707355056876",
                                    "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"),
                 get_global_product("GP_IRBESARTAN", GP_IRBESARTAN, "7702057716226",
                                    "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK"),
             ]),
        step("02-adoptar-productos.md", "Adoptar los productos", "Productos sin tasa configurada.", [
            call("Adoptar el acetaminofén (fila 40)", "POST", f"{API}/companies/<EMPRESA>/company-products",
                 body={"global_product_id": "<GP_ACETAMINOFEN>", "internal_code": "000045",
                       "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED", "currency_code": "COP"},
                 why=["`purchase_tax_percentage` nace en `null`: **sin configurar**."],
                 save={"ACETAMINOFEN": "id"}, show=TAX_SHOW),
            call("Adoptar el irbesartán (fila 16577)", "POST", f"{API}/companies/<EMPRESA>/company-products",
                 body={"global_product_id": "<GP_IRBESARTAN>", "internal_code": "022315",
                       "display_name": "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK",
                       "currency_code": "COP"},
                 save={"IRBESARTAN": "id"}, show=TAX_SHOW),
        ]),
        step("03-configurar-tasas.md", "Configurar las tasas",
             "Una tasa individual, un rechazo y un lote.", [
                 call("Configurar 19 % al acetaminofén (ficticio)", "PUT",
                      f"{API}/company-products/<ACETAMINOFEN>/purchase-tax",
                      body={"version": 1, "purchase_tax_percentage": "19"},
                      why=["De 0 a 100 con hasta 4 decimales. Incrementa la `version` del producto y se audita como "
                           "`UPDATE_COMPANY_PRODUCT_PURCHASE_TAX`."],
                      show=TAX_SHOW),
                 call("Dejar el acetaminofén sin configurar (rechazado)", "PUT",
                      f"{API}/company-products/<ACETAMINOFEN>/purchase-tax",
                      body={"version": 2, "purchase_tax_percentage": None},
                      why=["Una tasa configurada no vuelve a `null`: `422 PURCHASE_TAX_REQUIRED`."],
                      expect=422, show=ERROR_SHOW),
                 call("Configurar en lote: acetaminofén 19 % y irbesartán 0 %", "POST",
                      f"{API}/companies/<EMPRESA>/company-products/purchase-taxes/batch",
                      body={"items": [
                          {"company_product_id": "<ACETAMINOFEN>", "version": 2, "purchase_tax_percentage": "19"},
                          {"company_product_id": "<IRBESARTAN>", "version": 1, "purchase_tax_percentage": "0"},
                      ]},
                      why=["Hasta 100 productos, **todo o nada**: si uno falla (versión vieja, tasa inválida), no "
                           "cambia ninguno. El acetaminofén ya tenía 19 %: no cambia su versión. 0 % es válido."],
                      show=["items[].internal_code", "items[].purchase_tax_percentage", "items[].version"]),
             ]),
    ],
)
