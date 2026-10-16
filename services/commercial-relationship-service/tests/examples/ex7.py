"""Ejercicio 7 de docs/ejemplo/: políticas de ganancia de una lista (spec 021, FR-021-01..06).

Productos reales de `docs/CAMPOS PRODUCTOS.xlsx` (filas 40 y 16577); los porcentajes, la lista y la empresa son
**ficticios**. Ninguna llamada de este ejercicio modifica precios: las políticas solo rigen desde la siguiente
recepción física de una compra.
"""

from tests.examples.spec_common import (
    API,
    EMPRESA_EJ7,
    GP_ACETAMINOFEN,
    GP_IRBESARTAN,
    GPRES_ACETA_CAJA,
    GPRES_ACETA_SOBRE,
    GPRES_IRBE_CAJA,
    call,
    get_company,
    get_global_presentation,
    get_global_product,
    step,
)

POLICY_SHOW = ["id", "price_list_id", "name", "markup_percentage", "presentation_count", "status", "version"]
ERROR_SHOW = ["status", "code", "detail", "errors"]

EX7 = dict(
    folder="7-politicas-de-precios",
    title="Ejercicio 7 — Políticas de ganancia de una lista de precios",
    data_file="00-datos-del-excel.md",
    real_data=True,
    focus=(
        "Crear **políticas de ganancia** en una lista (porcentaje de recargo sobre el costo real de compra), ver que "
        "una presentación no puede estar en **dos políticas de la misma lista**, **cambiar el porcentaje**, "
        "**retirar** una presentación e **inactivar** una política. Nada de esto cambia precios: los cambios rigen "
        "desde la siguiente recepción física de una compra (spec 021)."
    ),
    data=[
        ("Fuente", "`docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2)"),
        ("Fila 40", "`Código` 000045 · ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"),
        ("Fila 16577", "`Código` 022315 · IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK"),
        ("Porcentajes", "15 %, 20 % y 50 % son **ficticios**: la fuente no tiene políticas de ganancia."),
        ("Empresa y lista", "DROGUERÍA POLÍTICAS FICTICIA S.A.S. y la lista `PUBLICO` son **ficticias**."),
    ],
    interpretation=[
        ("Política", "Agrupa presentaciones de una lista con un mismo porcentaje de recargo: "
         "`precio = costo real de compra × (1 + porcentaje / 100)`. Una lista puede tener varias."),
        ("Pertenencia", "Una presentación está a lo sumo en una política de la misma lista; puede estar en políticas "
         "de otras listas. La base lo garantiza también ante operaciones simultáneas."),
        ("Historial", "Cambiar el porcentaje o las presentaciones no reescribe nada: cierra la vigencia anterior y abre "
         "otra. Cada recepción usa las condiciones vigentes en el momento en que se recibió."),
        ("Sin efecto inmediato", "Ninguna operación de políticas modifica precios (RC-021-2)."),
    ],
    order_rules=[
        ("Producto, presentaciones y lista antes de las políticas", "La política pertenece a una lista `ACTIVE` y solo "
         "admite presentaciones `ACTIVE` y vendibles de la empresa."),
        ("Inactivar al final", "Una política inactiva es un estado final: no se modifica ni se reactiva."),
    ],
    steps=[
        step("01-consultar-datos.md", "Consultar la empresa y los productos globales",
             "Obtener `<EMPRESA>`, los productos y sus presentaciones globales.", [
                 get_company("EMPRESA", EMPRESA_EJ7, "DROGUERÍA POLÍTICAS FICTICIA S.A.S."),
                 get_global_product("GP_ACETAMINOFEN", GP_ACETAMINOFEN, "7707355056876",
                                    "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"),
                 get_global_product("GP_IRBESARTAN", GP_IRBESARTAN, "7702057716226",
                                    "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK"),
                 get_global_presentation("GPRES_CAJA", GPRES_ACETA_CAJA, "GP_ACETAMINOFEN", "caja x100 del acetaminofén"),
                 get_global_presentation("GPRES_SOBRE", GPRES_ACETA_SOBRE, "GP_ACETAMINOFEN", "sobre x10 del acetaminofén"),
                 get_global_presentation("GPRES_IRBE", GPRES_IRBE_CAJA, "GP_IRBESARTAN", "caja x30 del irbesartán"),
             ]),
        step("02-preparar-la-lista.md", "Adoptar los productos y crear la lista",
             "Productos, presentaciones vendibles y la lista `PUBLICO`.", [
                 call("Adoptar el acetaminofén (fila 40)", "POST", f"{API}/companies/<EMPRESA>/company-products",
                      body={"global_product_id": "<GP_ACETAMINOFEN>", "internal_code": "000045",
                            "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED", "currency_code": "COP"},
                      why=["Ejercicio 1."], save={"ACETAMINOFEN": "id"}, show=["id", "internal_code"]),
                 call("Adoptar el irbesartán (fila 16577)", "POST", f"{API}/companies/<EMPRESA>/company-products",
                      body={"global_product_id": "<GP_IRBESARTAN>", "internal_code": "022315",
                            "display_name": "IRBESARTAN+HIDROCLOROTIAZIDA (IRBESARTAN/HCT) 150+12.5MG TABLETA CAJAX30MK",
                            "currency_code": "COP"},
                      why=["Ejercicio 1."], save={"IRBESARTAN": "id"}, show=["id", "internal_code"]),
                 call("Adoptar la caja x100 del acetaminofén", "POST",
                      f"{API}/companies/<EMPRESA>/company-product-presentations",
                      body={"company_product_id": "<ACETAMINOFEN>", "global_product_presentation_id": "<GPRES_CAJA>"},
                      why=["Ejercicio 4. Las políticas se definen por **presentación**, la unidad que tiene precio."],
                      save={"CAJA": "id"}, show=["id", "is_sellable", "status"]),
                 call("Adoptar el sobre x10 del acetaminofén", "POST",
                      f"{API}/companies/<EMPRESA>/company-product-presentations",
                      body={"company_product_id": "<ACETAMINOFEN>", "global_product_presentation_id": "<GPRES_SOBRE>"},
                      why=["Otra presentación del mismo producto: puede tener otra política."],
                      save={"SOBRE": "id"}, show=["id", "is_sellable", "status"]),
                 call("Adoptar la caja x30 del irbesartán", "POST",
                      f"{API}/companies/<EMPRESA>/company-product-presentations",
                      body={"company_product_id": "<IRBESARTAN>", "global_product_presentation_id": "<GPRES_IRBE>"},
                      why=["Ejercicio 4."], save={"IRBE": "id"}, show=["id", "is_sellable", "status"]),
                 call("Crear la lista PUBLICO en COP", "POST", f"{API}/companies/<EMPRESA>/price-lists",
                      body={"code": "PUBLICO", "name": "Público", "currency_code": "COP"},
                      why=["Ejercicio 6. Una lista con al menos una política activa recibe precios automáticos; una "
                           "lista sin políticas conserva sus precios manuales (spec 021, B-3)."],
                      save={"LISTA": "id"}, show=["id", "code", "currency_code", "status"]),
             ]),
        step("03-crear-politicas.md", "Crear las políticas",
             "Dos políticas con porcentajes distintos y el rechazo de una presentación repetida.", [
                 call("Crear la política Alimentos (15 %) con la caja y el sobre", "POST",
                      f"{API}/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies",
                      body={"name": "Alimentos", "markup_percentage": "15",
                            "company_product_presentation_ids": ["<CAJA>", "<SOBRE>"]},
                      why=["El porcentaje va de 0 a 1000 con hasta 4 decimales. **No cambia ningún precio**: se usará "
                           "en la siguiente recepción de estas presentaciones."],
                      save={"ALIMENTOS": "id"}, show=POLICY_SHOW),
                 call("Crear la política Especiales (50 %) con la caja (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies",
                      body={"name": "Especiales", "markup_percentage": "50", "company_product_presentation_ids": ["<CAJA>"]},
                      why=["La caja ya está en Alimentos de esta lista: `409 PRESENTATION_ALREADY_IN_POLICY`."],
                      expect=409, show=ERROR_SHOW),
                 call("Crear la política Especiales (50 %) con el irbesartán", "POST",
                      f"{API}/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies",
                      body={"name": "Especiales", "markup_percentage": "50", "company_product_presentation_ids": ["<IRBE>"]},
                      why=["Cada presentación usa el porcentaje de su propia política."],
                      save={"ESPECIALES": "id"}, show=POLICY_SHOW),
                 call("Crear una política con 1000,0001 % (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies",
                      body={"name": "Excesiva", "markup_percentage": "1000.0001", "company_product_presentation_ids": []},
                      why=["Fuera de 0 a 1000: `422 MARKUP_PERCENTAGE_OUT_OF_RANGE`."],
                      expect=422, show=ERROR_SHOW),
                 call("Listar las políticas de la lista", "GET",
                      f"{API}/companies/<EMPRESA>/price-lists/<LISTA>/pricing-policies",
                      why=["Solo administradores y supervisores: las políticas exponen porcentajes internos."],
                      show=["items[].name", "items[].markup_percentage", "items[].presentation_count", "total_records"]),
             ]),
        step("04-modificar-politicas.md", "Cambiar el porcentaje, retirar e inactivar",
             "Historial de porcentajes y presentaciones; inactivación final.", [
                 call("Cambiar Alimentos a 20 %", "POST", f"{API}/pricing-policies/<ALIMENTOS>/percentage",
                      body={"version": 1, "markup_percentage": "20"},
                      why=["Cierra el término del 15 % y abre el del 20 %. Una recepción anterior que aún esté pendiente "
                           "usará el 15 % con el que se recibió (RC-021-5)."],
                      show=POLICY_SHOW),
                 call("Consultar el historial de porcentajes", "GET", f"{API}/pricing-policies/<ALIMENTOS>/terms",
                      why=["El historial no se borra ni se reescribe."],
                      show=["[].markup_percentage", "[].valid_to"]),
                 call("Retirar el sobre de Alimentos", "POST", f"{API}/pricing-policies/<ALIMENTOS>/presentations/remove",
                      body={"version": 2, "company_product_presentation_ids": ["<SOBRE>"]},
                      why=["En esta lista con políticas, la siguiente recepción del sobre **finalizará su precio** en "
                           "`PUBLICO` hasta que alguien registre uno manual o lo asigne a otra política."],
                      show=POLICY_SHOW),
                 call("Inactivar Especiales", "POST", f"{API}/pricing-policies/<ESPECIALES>/deactivate",
                      body={"version": 1, "reason": "Fin de la temporada de ofertas"},
                      why=["Estado final: cierra su porcentaje y sus presentaciones. No hay reactivación: se crea otra."],
                      show=POLICY_SHOW),
                 call("Cambiar el porcentaje de la política inactiva (rechazado)", "POST",
                      f"{API}/pricing-policies/<ESPECIALES>/percentage",
                      body={"version": 2, "markup_percentage": "40"},
                      why=["`409 POLICY_INACTIVE`."], expect=409, show=ERROR_SHOW),
             ]),
    ],
)
