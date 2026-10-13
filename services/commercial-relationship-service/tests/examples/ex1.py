"""Ejercicio 1 de docs/ejemplo/: adopción de productos (FR-010 a FR-018, DS-01, DS-09, DS-17).

Productos reales de `docs/CAMPOS PRODUCTOS.xlsx` (hoja `Hoja1`); ver `mapeo-campos-excel.md`.
"""

from tests.examples.spec_common import (
    API,
    EMPRESA_EJ1,
    GP_ACETAMINOFEN,
    GP_AGUJA,
    GP_CEPILLO,
    GP_INCOMPLETO,
    GP_WINNY,
    call,
    get_company,
    get_global_product,
    step,
)

PRODUCT_SHOW = [
    "id", "global_product_id", "internal_code", "reference_code", "display_name", "short_name",
    "currency_code", "inventory_control_enabled", "lot_tracking_enabled",
    "expiration_tracking_enabled", "is_purchasable", "is_sellable", "status", "version",
]
ERROR_SHOW = ["status", "code", "detail", "errors"]

EX1 = dict(
    folder="1-adopcion-de-productos",
    title="Ejercicio 1 — Adopción de productos del Excel",
    data_file="00-datos-del-excel.md",
    real_data=True,
    focus=(
        "**Adoptar** productos globales en la empresa con los datos privados del sistema anterior (código interno, "
        "referencia, nombre corto, lotes, vencimiento, control de inventario), ver los **rechazos** de un producto "
        "inactivo, uno incompleto, una adopción repetida y un código repetido, cambiar **precio y moneda** respetando "
        "los decimales de cada moneda, consultar por lotes e **inactivar y reactivar**."
    ),
    data=[
        ("Fuente", "`docs/CAMPOS PRODUCTOS.xlsx`, hoja `Hoja1` (encabezados en la fila 2)"),
        ("Fila 40", "`Código` 000045 · `Referencia` 48691 · `Nombre` ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 "
         "SIEGFRIED · `Nombre Corto` ACETAMINOFEN · `Control Inventario` S · `Maneja Lotes` S · `Maneja Fecha "
         "Vencimiento` S · `Código Barras 1` 7707355056876"),
        ("Fila 413", "`Código` 000537 · `Referencia` 71430 · `Nombre` AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO · "
         "`Nombre Corto` AGUJA 18GX1 1/2 · `Control Inventario` S · `Maneja Lotes` S · `Maneja Fecha Vencimiento` S · "
         "`Código Barras 2` 7706634002856"),
        ("Fila 11499", "`Código` 015721 · `Referencia` 74865 · `Nombre` WINNY GOLD ETAPA 6 XXXG PAQUETEX30 "
         "TECNOQUIMICAS · `Código Barras 1` 7701021118264"),
        ("Fila 16610", "`Código` 022348 · `Referencia` NT · `Nombre` CEPILLO COLGATE INFANTIL 2-5 AÑOS EXTRA SUAVE NIÑA "
         "PACK X2 · `Estado` I · `Maneja Lotes` S · `Maneja Fecha Vencimiento` N"),
        ("Precios y costos", "Las cuatro filas tienen `Precio Lista 1` y `Costo` **vacíos**: se adoptan con el precio y "
         "el costo por defecto (`0`). El precio en pesos chilenos del paso 05 es **ficticio** y solo ilustra los "
         "decimales por moneda."),
        ("Producto incompleto", "**Ficticio**: un producto global sin completar en Product Catalog, para mostrar el "
         "rechazo por elegibilidad."),
        ("Empresa", "DROGUERÍA EJEMPLO FICTICIA S.A.S. (**ficticia**), registrada en Operational Context."),
    ],
    interpretation=[
        ("Qué se adopta", "Cada fila del Excel es un producto del catálogo **de la empresa**; el producto global ya "
         "existe en Product Catalog (ejercicios de ese servicio). Se adopta con su `id`, no con sus datos."),
        ("Código y referencia", "`Código` → `internal_code` (único en la empresa, sin distinguir mayúsculas); "
         "`Referencia` → `reference_code` (no único)."),
        ("Nombre visible", "`Nombre` → `display_name` y `Nombre Corto` → `short_name`: los escribe el usuario; el "
         "servicio no los copia de Product Catalog ni los sugiere (DS-14)."),
        ("Inventario", "`Control Inventario`, `Maneja Lotes` y `Maneja Fecha Vencimiento` (`S`/`N`) → las tres "
         "banderas. Lotes exige control de inventario y vencimiento exige lotes."),
        ("Producto inactivo", "La fila 16610 tiene `Estado = I`: en Product Catalog quedó `INACTIVE` y no se puede "
         "adoptar."),
        ("Primer uso", "Antes de guardar, el servicio registra el **primer uso** del producto en Product Catalog con su "
         "propia identidad técnica; si falla, no se guarda nada (DS-01)."),
        ("Moneda", "Lista cerrada de 38 monedas con sus decimales ISO 4217: `COP` admite 2 decimales, `CLP` ninguno."),
    ],
    order_rules=[
        ("Empresa y productos globales primero", "La adopción une una empresa (Operational Context) con un producto "
         "global (Product Catalog); ambos deben existir antes."),
        ("Adoptar antes de cambiar", "Los cambios de precio, moneda y estado se hacen sobre el producto empresarial."),
        ("Rechazos después de una adopción", "La adopción repetida y el código repetido necesitan una adopción previa."),
    ],
    steps=[
        step("01-consultar-datos-base.md", "Consultar la empresa y los productos globales",
             "Obtener `<EMPRESA>` y los `id` de los productos globales.", [
                 get_company("EMPRESA", EMPRESA_EJ1, "DROGUERÍA EJEMPLO FICTICIA S.A.S."),
                 get_global_product("GP_ACETAMINOFEN", GP_ACETAMINOFEN, "7707355056876",
                                    "Acetaminofén (Adorem) 500 mg tableta"),
                 get_global_product("GP_AGUJA", GP_AGUJA, "7706634002856", "Aguja 18G x 1 1/2"),
                 get_global_product("GP_WINNY", GP_WINNY, "7701021118264", "Winny Gold etapa 6 XXXG"),
                 get_global_product("GP_CEPILLO", GP_CEPILLO, None, "Cepillo Colgate infantil 2-5 años",
                                    status="INACTIVE", eligible=False, search="CEPILLO%20COLGATE%20INFANTIL"),
                 get_global_product("GP_INCOMPLETO", GP_INCOMPLETO, None, "Producto incompleto (ficticio)",
                                    eligible=False, search="INCOMPLETO"),
             ]),
        step("02-adoptar-acetaminofen.md", "Adoptar el acetaminofén (fila 40)",
             "Adoptar el producto con lotes y vencimiento.", [
                 call("Adoptar el acetaminofén", "POST", f"{API}/companies/<EMPRESA>/company-products",
                      body={
                          "global_product_id": "<GP_ACETAMINOFEN>",
                          "internal_code": "000045",
                          "reference_code": "48691",
                          "display_name": "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED",
                          "short_name": "ACETAMINOFEN",
                          "currency_code": "COP",
                          "inventory_control_enabled": True,
                          "lot_tracking_enabled": True,
                          "expiration_tracking_enabled": True,
                      },
                      why=[
                          "`Código` 000045 → `internal_code`; `Referencia` 48691 → `reference_code`.",
                          "`Maneja Lotes` = S y `Maneja Fecha Vencimiento` = S → ambas banderas en `true`; exigen "
                          "`inventory_control_enabled` (`Control Inventario` = S).",
                          "El producto de la empresa no tiene precio ni costo (spec 019): los precios de venta se registran "
                          "en las listas, por presentación, y los costos vienen de las compras y de Inventory.",
                          "El servicio comprueba que el producto global esté `ACTIVE` y completo y registra su primer "
                          "uso en Product Catalog **antes** de guardar.",
                      ],
                      save={"CP_ACETAMINOFEN": "id"}, show=PRODUCT_SHOW),
             ]),
        step("03-adoptar-aguja.md", "Adoptar la aguja (fila 413)",
             "Adoptar un segundo producto de la misma empresa.", [
                 call("Adoptar la aguja", "POST", f"{API}/companies/<EMPRESA>/company-products",
                      body={
                          "global_product_id": "<GP_AGUJA>",
                          "internal_code": "000537",
                          "reference_code": "71430",
                          "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO",
                          "short_name": "AGUJA 18GX1 1/2",
                          "currency_code": "COP",
                          "lot_tracking_enabled": True,
                          "expiration_tracking_enabled": True,
                      },
                      why=["`RFZC18B` dentro del nombre es la referencia **del fabricante** (es un identificador del "
                           "producto global en Product Catalog); la columna `Referencia` 71430 es de la empresa.",
                           "`inventory_control_enabled` se omite: por defecto es `true`."],
                      save={"CP_AGUJA": "id"}, show=PRODUCT_SHOW),
             ]),
        step("04-rechazos.md", "Rechazos de la adopción",
             "Ver los errores de elegibilidad y de unicidad.", [
                 call("Adoptar otra vez el acetaminofén (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/company-products",
                      body={"global_product_id": "<GP_ACETAMINOFEN>", "internal_code": "000045-B",
                            "display_name": "Duplicado", "currency_code": "COP"},
                      why=["Una empresa adopta cada producto global **una sola vez**, aunque la adopción esté "
                           "inactiva (en ese caso se reactiva): `409 DUPLICATE_ADOPTION`. No se llama a Product Catalog."],
                      expect=409, show=ERROR_SHOW),
                 call("Adoptar el cepillo inactivo (rechazado)", "POST", f"{API}/companies/<EMPRESA>/company-products",
                      body={"global_product_id": "<GP_CEPILLO>", "internal_code": "022348",
                            "display_name": "CEPILLO COLGATE INFANTIL 2-5 AÑOS EXTRA SUAVE NIÑA PACK X2",
                            "currency_code": "COP", "lot_tracking_enabled": True},
                      why=["La fila 16610 tiene `Estado = I`: el producto global está `INACTIVE` y no admite nuevas "
                           "adopciones: `422 GLOBAL_PRODUCT_INACTIVE`."],
                      expect=422, show=ERROR_SHOW),
                 call("Adoptar un producto incompleto (rechazado)", "POST", f"{API}/companies/<EMPRESA>/company-products",
                      body={"global_product_id": "<GP_INCOMPLETO>", "internal_code": "FICT-01",
                            "display_name": "Producto incompleto (ficticio)", "currency_code": "COP"},
                      why=["Solo se adopta un producto **completo** (elegible). Como no es elegible, no se registra el "
                           "primer uso ni se guarda nada: `422 GLOBAL_PRODUCT_NOT_ELIGIBLE`."],
                      expect=422, show=ERROR_SHOW),
                 call("Adoptar los pañales con un código ya usado (rechazado)", "POST",
                      f"{API}/companies/<EMPRESA>/company-products",
                      body={"global_product_id": "<GP_WINNY>", "internal_code": "000045",
                            "display_name": "WINNY GOLD ETAPA 6 XXXG PAQUETEX30 TECNOQUIMICAS", "currency_code": "COP"},
                      why=["`internal_code` es único en la empresa (sin distinguir mayúsculas): 000045 ya es del "
                           "acetaminofén: `409 DUPLICATE_INTERNAL_CODE`."],
                      expect=409, show=ERROR_SHOW),
                 call("Adoptar los pañales con su código del Excel", "POST",
                      f"{API}/companies/<EMPRESA>/company-products",
                      body={"global_product_id": "<GP_WINNY>", "internal_code": "015721", "reference_code": "74865",
                            "display_name": "WINNY GOLD ETAPA 6 XXXG PAQUETEX30 TECNOQUIMICAS", "currency_code": "COP"},
                      why=["Con el `Código` 015721 de la fila 11499 la adopción procede."],
                      save={"CP_WINNY": "id"}, show=["id", "internal_code", "status"]),
             ]),
        step("05-precio-y-moneda.md", "Cambiar la moneda (sin precio en el producto)",
             "El producto de la empresa no admite precio ni costo (spec 019); la moneda sí se cambia.", [
                 call("Intentar fijar un precio en el producto (rechazado)", "PUT",
                      f"{API}/company-products/<CP_AGUJA>",
                      body={"internal_code": "000537", "reference_code": "71430",
                            "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO", "short_name": "AGUJA 18GX1 1/2",
                            "sale_price": "1500.50", "currency_code": "CLP", "reference_cost": "0",
                            "inventory_control_enabled": True, "lot_tracking_enabled": True,
                            "expiration_tracking_enabled": True, "is_purchasable": True, "is_sellable": True,
                            "version": 1},
                      why=["El `PUT` reemplaza todos los campos modificables y exige la `version` vigente.",
                           "`sale_price` y `reference_cost` ya no existen (spec 019): enviarlos responde "
                           "`422 VALIDATION_ERROR`, aunque sean `0`. El precio se registra en una lista, por presentación."],
                      expect=422, show=ERROR_SHOW),
                 call("Cambiar la moneda", "PUT", f"{API}/company-products/<CP_AGUJA>",
                      body={"internal_code": "000537", "reference_code": "71430",
                            "display_name": "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO", "short_name": "AGUJA 18GX1 1/2",
                            "currency_code": "clp",
                            "inventory_control_enabled": True, "lot_tracking_enabled": True,
                            "expiration_tracking_enabled": True, "is_purchasable": True, "is_sellable": True,
                            "version": 1},
                      why=["`clp` se normaliza a `CLP`; la moneda elige la lista de precios predeterminada.",
                           "El `PUT` no consulta Product Catalog y la versión sube a 2."],
                      show=["id", "currency_code", "version"]),
             ]),
        step("06-consultar-y-estados.md", "Consultar, inactivar y reactivar",
             "Ver el listado, la consulta por lotes y el ciclo de vida.", [
                 call("Listar los productos de la empresa", "GET",
                      f"{API}/companies/<EMPRESA>/company-products?search=0005",
                      why=["Búsqueda parcial por código interno, referencia o nombre; sin `status` solo `ACTIVE`."],
                      show=["items[].internal_code", "items[].display_name", "items[].status", "total_records"]),
                 call("Consultar varios productos por lotes", "POST", f"{API}/company-products/batch-lookup",
                      body={"ids": ["<CP_ACETAMINOFEN>", "<CP_WINNY>", "00000000-0000-4000-8000-000000000000"]},
                      why=["Contrato para Inventory, Purchase y Sales: de 1 a 100 `id`; los inexistentes vuelven con "
                           "`found: false`, sin error."],
                      show=["items[].id", "items[].found", "items[].internal_code", "items[].is_sellable"]),
                 call("Inactivar el acetaminofén", "POST", f"{API}/company-products/<CP_ACETAMINOFEN>/deactivate",
                      body={"version": 1},
                      why=["Inactivar exige `delete` aunque no borra nada; deja de ser apto para operaciones nuevas."],
                      show=["id", "status", "version"]),
                 call("Reactivar el acetaminofén", "POST", f"{API}/company-products/<CP_ACETAMINOFEN>/reactivate",
                      body={"version": 2},
                      why=["Reactivar exige `update`; comprueba que el producto global siga `ACTIVE`, sin volver a "
                           "exigir completitud ni registrar el primer uso."],
                      show=["id", "status", "version"]),
             ]),
        step("07-resumen-de-empresas.md", "Ver el resumen de mis empresas",
             "Recorrer, una por página, las empresas del usuario con sus conteos (FR-046).", [
                 call("Ver la primera empresa del resumen", "GET", f"{API}/company-summaries",
                      why=["Sin parámetros devuelve **una empresa por página** (`page_size` por defecto 1, máximo "
                           "100); para la siguiente se envía `?page=2`.",
                           "Solo aparecen las empresas donde el usuario tiene membresía `ACTIVE` en Operational "
                           "Context; no hay vista de plataforma (DS-03). Aquí el usuario es miembro de las tres "
                           "empresas ficticias de los ejercicios.",
                           "La razón social se lee en Operational Context y Party Identity y no se guarda. Los "
                           "conteos de clientes y proveedores salen `null` si el usuario no tiene su permiso de "
                           "lectura."],
                      show=["items[].company_id", "items[].company_status", "items[].legal_name",
                            "items[].company_products", "items[].company_customers", "items[].company_suppliers",
                            "page", "page_size", "total_records", "total_pages"]),
             ]),
    ],
)
