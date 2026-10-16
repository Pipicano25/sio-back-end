"""Ejercicio 9 de docs/ejemplo/: actualizaciones automáticas de precio (spec 021, FR-021-21..27 y FR-021-32a).

Producto real de `docs/CAMPOS PRODUCTOS.xlsx` (fila 40); los costos, el porcentaje, las recepciones y la empresa son
**ficticios**. Las recepciones las entrega Purchase y las procesa el worker de precios: en la validación automática se
simulan como procesos (no son llamadas del usuario), y la falla de la segunda es simulada.
"""

from tests.examples.spec_common import (
    API,
    COMPRA_EJ9_1,
    COMPRA_EJ9_2,
    DETALLE_EJ9_1,
    DETALLE_EJ9_2,
    EMPRESA_EJ9,
    GP_ACETAMINOFEN,
    GPRES_ACETA_CAJA,
    call,
    get_company,
    get_global_presentation,
    get_global_product,
    process,
    step,
)

APPLICATION_SHOW = [
    "sequence", "status", "markup_percentage", "current_unit_cost", "previous_unit_cost", "reference_cost",
    "previous_price", "new_price", "attempts", "last_error_code", "resolved_by", "resolution_reason", "version",
]
LIST_SHOW = ["items[].sequence", "items[].status", "items[].new_price", "items[].last_error_code", "total_records"]
ERROR_SHOW = ["status", "code", "detail"]
REASON = "Se revisó la compra: el costo de la segunda recepción no debe cambiar el precio (ficticio)."
RECEIPT = {"company": "<EMPRESA>", "product": "<ACETAMINOFEN>", "presentation": "<CAJA>"}

EX9 = dict(
    folder="9-actualizaciones-automaticas",
    title="Ejercicio 9 — Actualizaciones automáticas de precio",
    data_file="00-datos-del-excel.md",
    real_data=True,
    focus=(
        "Ver cómo una **recepción física** de compra actualiza el precio de una lista con políticas: el "
        "**costo real** de la línea (con su impuesto) más el porcentaje de la política. Consultar las "
        "**actualizaciones automáticas** (cálculo y estado) y **resolver administrativamente** una que falló, sin "
        "cambiar precios. Solo administradores y supervisores las ven, porque exponen costos (spec 021)."
    ),
    data=[
        ("Fuente", "`docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2)"),
        ("Fila 40", "`Código` 000045 · ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"),
        ("Recepción 1", f"Compra `{COMPRA_EJ9_1}`, línea `{DETALLE_EJ9_1}`: 10 cajas por 23.800 COP con impuesto "
         "(2.380 por caja). **Ficticia.**"),
        ("Recepción 2", f"Compra `{COMPRA_EJ9_2}`, línea `{DETALLE_EJ9_2}`: 10 cajas por 20.000 COP con impuesto "
         "(2.000 por caja). **Ficticia**, y su falla es **simulada**."),
        ("Política", "`Medicamentos`, 30 % sobre el costo (**ficticio**)."),
        ("Empresa", "DROGUERÍA ACTUALIZACIONES FICTICIA S.A.S. (**ficticia**)."),
    ],
    interpretation=[
        ("Costo real", "(subtotal − descuento + impuesto) / cantidad de la presentación, sin volver a sumar el "
         "impuesto: 23.800 / 10 = 2.380. No es el costo FIFO de Inventory."),
        ("Costo de referencia", "Si el costo real baja frente a la recepción anterior, se usa el promedio simple de "
         "ambos; si sube o se mantiene, el actual. 2.380 × 1,30 = 3.094."),
        ("Una actualización por lista", "Cada recepción crea una actualización por cada lista con políticas, y se "
         "procesan en orden de recepción por presentación: si una falla, las siguientes de esa lista y "
         "presentación esperan."),
        ("Resolver", "Una actualización `PENDING` o `FAILED` se puede resolver con un motivo: queda `RESOLVED`, no "
         "cambia precios y libera las siguientes. Las que ya terminaron no se resuelven."),
    ],
    order_rules=[
        ("Política antes de recibir", "Solo las listas con una política activa en el momento de la recepción "
         "reciben precios automáticos; las demás conservan sus precios manuales."),
        ("Consultar antes de resolver", "La resolución pide la `version` vigente de la actualización."),
    ],
    steps=[
        step("01-consultar-datos.md", "Consultar la empresa y el producto global",
             "Obtener `<EMPRESA>`, el producto y su presentación global.", [
                 get_company("EMPRESA", EMPRESA_EJ9, "DROGUERÍA ACTUALIZACIONES FICTICIA S.A.S."),
                 get_global_product("GP_ACETAMINOFEN", GP_ACETAMINOFEN, "7707355056876",
                                    "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"),
                 get_global_presentation("GPRES_CAJA", GPRES_ACETA_CAJA, "GP_ACETAMINOFEN", "caja x100 del acetaminofén"),
             ]),
        step("02-preparar-la-politica.md", "Adoptar el producto, crear la lista y la política",
             "La caja del acetaminofén en la política `Medicamentos` (30 %) de la lista `PUBLICO`.", [
                 call("Adoptar el acetaminofén (fila 40)", "POST", f"{API}/companies/<EMPRESA>/company-products",
                      body={"global_product_id": "<GP_ACETAMINOFEN>", "internal_code": "000045",
                            "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED", "currency_code": "COP"},
                      why=["Ejercicio 1."], save={"ACETAMINOFEN": "id"}, show=["id", "internal_code"]),
                 call("Adoptar la caja x100 del acetaminofén", "POST",
                      f"{API}/companies/<EMPRESA>/company-product-presentations",
                      body={"company_product_id": "<ACETAMINOFEN>", "global_product_presentation_id": "<GPRES_CAJA>"},
                      why=["Ejercicio 4. El precio automático es por presentación."],
                      save={"CAJA": "id"}, show=["id", "is_sellable", "status"]),
                 call("Crear la lista PUBLICO en COP", "POST", f"{API}/companies/<EMPRESA>/price-lists",
                      body={"code": "PUBLICO", "name": "Público", "currency_code": "COP"},
                      why=["Ejercicio 6."], save={"LISTA": "id"}, show=["id", "code", "currency_code", "status"]),
                 call("Crear la política Medicamentos (30 %) con la caja", "POST",
                      f"{API}/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies",
                      body={"name": "Medicamentos", "markup_percentage": "30", "company_product_presentation_ids": ["<CAJA>"]},
                      why=["Ejercicio 7. Desde ahora la lista `PUBLICO` recibe precios automáticos."],
                      save={"MEDICAMENTOS": "id"}, show=["id", "name", "markup_percentage", "presentation_count"]),
             ]),
        step("03-recepciones.md", "Recibir dos compras",
             "Una recepción crea el primer precio; la segunda falla (simulado) y queda pendiente de reintento.", [
                 process("Purchase recibe la compra 1 y el worker actualiza el precio", "recepcion",
                         params={**RECEIPT, "purchase_id": COMPRA_EJ9_1, "purchase_detail_id": DETALLE_EJ9_1,
                                 "sequence": 1, "line_total": "23800.00", "quantity": "10.0000"},
                         why=["Al confirmar la recepción física, Purchase registra el costo de la línea y lo entrega a "
                              "Commercial Relationship con su identidad técnica "
                              "(`POST /api/v1/companies/{company_id}/automatic-price-update-requests`); ningún usuario "
                              "llama esa URL.",
                              "El worker calcula 23.800 / 10 = 2.380 por caja y 2.380 × 1,30 = **3.094**. Crea el precio "
                              "con `origin = AUTOMATIC` y sin fecha de fin."],
                         show=["status", "new_price"]),
                 process("Purchase recibe la compra 2 y el worker falla (simulado)", "recepcion",
                         params={**RECEIPT, "purchase_id": COMPRA_EJ9_2, "purchase_detail_id": DETALLE_EJ9_2,
                                 "sequence": 2, "line_total": "20000.00", "quantity": "10.0000",
                                 "previous": ["23800.00", "10.0000"], "fail": True},
                         why=["La recepción no depende del resultado: el inventario ya entró y Purchase no se detiene.",
                              "El worker registra el error, cuenta el intento y programa un reintento con espera "
                              "creciente. Las siguientes recepciones de esta lista y presentación esperan a que esta "
                              "termine."],
                         show=["status", "new_price", "last_error_code"]),
             ]),
        step("04-consultar-actualizaciones.md", "Consultar las actualizaciones",
             "Ver el cálculo de cada actualización y encontrar la que falló.", [
                 call("Listar las actualizaciones de la empresa", "GET",
                      f"{API}/companies/<EMPRESA>/automatic-price-applications",
                      why=["Paginado. Filtros: `status`, `price_list_id`, `company_product_presentation_id` y "
                           "`purchase_id`.",
                           "Solo administradores y supervisores: la respuesta incluye costos y porcentajes."],
                      show=LIST_SHOW),
                 call("Listar solo las fallidas", "GET",
                      f"{API}/companies/<EMPRESA>/automatic-price-applications?status=FAILED",
                      save={"FALLIDA": "items[0].id"}, show=LIST_SHOW),
                 call("Ver el detalle de la fallida", "GET",
                      f"{API}/companies/<EMPRESA>/automatic-price-applications/<FALLIDA>",
                      why=["Una actualización fallida todavía no tiene cálculo: los costos y el precio se calculan cuando "
                           "se procesa. Al reintentarla, el costo actual (2.000) sería menor que el anterior (2.380), así "
                           "que el costo de referencia sería el promedio simple (2.190) y el precio 2.847.",
                           "`attempts` y `last_error_code` muestran el intento fallido; el detalle técnico del error "
                           "solo queda en el log y en la auditoría."],
                      show=APPLICATION_SHOW),
             ]),
        step("05-resolver.md", "Resolver la actualización fallida",
             "Cerrarla con un motivo, sin cambiar precios.", [
                 call("Resolver la actualización fallida", "POST",
                      f"{API}/companies/<EMPRESA>/automatic-price-applications/<FALLIDA>/resolution",
                      body={"version": 2, "reason": REASON},
                      why=["Solo desde `PENDING` o `FAILED`, con un motivo de 10 a 500 caracteres y la `version` "
                           "vigente. Queda `RESOLVED` (final) y se audita como `RESOLVE_AUTOMATIC_PRICE`.",
                           "No crea ni cierra precios: rige el de la recepción 1."],
                      show=APPLICATION_SHOW),
                 call("Resolverla otra vez (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/automatic-price-applications/<FALLIDA>/resolution",
                      body={"version": 3, "reason": REASON},
                      why=["Una actualización terminada no cambia: `409 APPLICATION_ALREADY_FINAL`."],
                      expect=409, show=ERROR_SHOW),
                 call("Consultar el precio de la caja en la lista", "GET",
                      f"{API}/companies/<EMPRESA>/price-list-items?price_list_id=<LISTA>",
                      why=["Los precios muestran `origin` y `closure_reason`, nunca costos ni porcentajes (los ve "
                           "cualquier usuario con lectura de precios)."],
                      show=["items[].unit_price", "items[].origin", "items[].closure_reason", "items[].valid_to"]),
             ]),
    ],
)
