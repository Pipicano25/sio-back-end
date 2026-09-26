"""Ejercicio de docs/ejemplo/ (Principio XXII): datos de las llamadas y su justificación."""

from tests.examples.spec_common import API, call, get_group_type, get_manufacturer, get_packaging, get_unit, group_block, step

PRODUCT_SHOW = ["id", "version", "status", "canonical_name", "global_brand_id", "manufacturer_organization_id",
                "base_unit_id", "completeness", "eligible_for_adoption"]
ID_SHOW = ["id", "global_product_presentation_id", "identifier_type", "value", "canonical_value", "is_primary"]

EX4 = dict(
    folder="4-aguja-rymco-gtin14-y-ean13",
    title="Ejercicio 4 — Aguja hipodérmica 18G x 1½\" Rymco, caja x 100",
    focus=(
        "Tipos de identificador: un **GTIN-14** y un **EAN-13** que según la regla GS1 identifican niveles distintos "
        "(caja y unidad), y la **referencia del fabricante** como identificador `OTHER`. Además: **unidad nueva** "
        "(pulgada), producto **sin marca**, y dos **errores esperados** que protegen la calidad de los códigos."
    ),
    excel_ids="537",
    excel=[
        ("ID", "537"),
        ("Código", "000537"),
        ("Referencia", "71430"),
        ("Nombre", "AGUJA 18GX1 1/2 CAJAX100 RFZC18B RYMCO"),
        ("Nombre Tipo Producto", "HOSPITALARIOS"),
        ("Nombre Corto", "AGUJA 18GX1 1/2"),
        ("Unidad Medida", "CAJA"),
        ("Contenido Interno", "100"),
        ("Código Barras 1", "27706634002850 (GTIN-14 válido)"),
        ("Código Barras 2", "7706634002856 (EAN-13 válido)"),
        ("Estado", "A"),
        ("Grupo 1 / 2 / 4", "0005 MEDICO QUIRURGICOS / 0016 DISPOSITIVOS MEDICOS / 0278 RYMCO"),
        ("Grupo 5", "0695 NO APLICA"),
        ("% Impuesto", "19"),
    ],
    interpretation=[
        ("Qué es el producto", "\"Aguja hipodérmica 18G x 1 1/2 pulgadas\"."),
        ("Marca", "**Ninguna**. Rymco es el fabricante; no hay una marca comercial distinta. `global_brand_id` es opcional."),
        ("Fabricante", "Rymco (Party Identity)."),
        ("Referencia `RFZC18B`", "Es la referencia de catálogo **del fabricante** (viene en el nombre). Se registra como identificador `OTHER`. "
         "No confundir con la columna `Referencia` (71430), que es de la empresa."),
        ("Unidad base", "`UND` = una aguja."),
        ("Presentaciones", "`UNIDAD` (base) y `CAJA_X100` (empaque `BOX`, factor 100)."),
        ("Códigos", "El GTIN-14 `2 770663400285 0` se construye con los mismos 12 dígitos del EAN-13 `770663400285 6` más un "
         "**dígito indicador** (`2`). En GS1 eso significa: el GTIN-14 identifica un **agrupamiento** del artículo que "
         "identifica el EAN-13. Por eso: EAN-13 → `UNIDAD`, GTIN-14 → `CAJA_X100`."),
        ("Categoría", "`DISPOSITIVOS_MEDICOS > AGUJAS_HIPODERMICAS`."),
        ("Atributos", "Calibre = 18 (`INTEGER`, escala gauge) y longitud = 1.5 `PULG` (`DECIMAL` con unidad)."),
        ("Grupos", "`GROUP_1` 0005, `GROUP_2` 0016, `GROUP_4` 0278. `NO APLICA` no se importa."),
    ],
    steps=[
        step(
            "01-consultar-datos-base.md",
            "Consultar los datos base",
            "Obtener los `id` de la unidad, el empaque, los tipos de grupo y el fabricante (registrándolo si todavía no existe).",
            [
                get_unit("UND", "UND", ["Las agujas se cuentan por unidades enteras."]),
                get_packaging("BOX", "BOX", ["`Unidad Medida = CAJA` → empaque `BOX`."]),
                get_group_type(1), get_group_type(2), get_group_type(4),
                *get_manufacturer("RYMCO", "FABRICANTE_RYMCO", "Rymco", "Rymco"),
            ],
        ),
        step(
            "02-crear-unidad-pulgada.md",
            "Crear la unidad pulgada (`PULG`)",
            "Poder expresar la longitud de la aguja (1½\").",
            [
                call(
                    "Crear la unidad `PULG`",
                    "POST", f"{API}/units-of-measure",
                    body={"code": "PULG", "name": "Pulgada", "symbol": "in", "measurement_type": "LENGTH", "allows_decimals": True},
                    why=[
                        "Las agujas se identifican en pulgadas (`1 1/2` = 1.5\"). Convertirlas a cm (3.81) haría el dato irreconocible para quien compra.",
                        "`measurement_type: LENGTH` (mide longitud, como `M` y `CM`).",
                        "`allows_decimals: true` por medidas como 1.5 o 0.5 pulgadas.",
                        "`symbol: in` es el símbolo internacional de la pulgada.",
                    ],
                    save={"PULG": "id"},
                    show=["id", "code", "name", "symbol", "measurement_type", "allows_decimals"],
                ),
            ],
            after="Si responde `409 DUPLICATE_CODE`, consulte `GET /api/v1/units-of-measure?code=PULG` y use ese `id`.",
        ),
        step(
            "03-crear-categorias.md",
            "Crear las categorías",
            "Crear `DISPOSITIVOS_MEDICOS > AGUJAS_HIPODERMICAS`.",
            [
                call(
                    "Crear la categoría raíz `DISPOSITIVOS_MEDICOS`",
                    "POST", f"{API}/categories",
                    body={"code": "DISPOSITIVOS_MEDICOS", "name": "Dispositivos médicos"},
                    why=["`Nombre Tipo Producto = HOSPITALARIOS` es un nombre comercial del sistema anterior; la clase de producto es dispositivo médico."],
                    save={"CAT_DISPOSITIVOS_MEDICOS": "id"},
                    show=["id", "code", "name", "parent_category_id"],
                ),
                call(
                    "Crear la subcategoría `AGUJAS_HIPODERMICAS`",
                    "POST", f"{API}/categories",
                    body={"code": "AGUJAS_HIPODERMICAS", "name": "Agujas hipodérmicas", "parent_category_id": "<CAT_DISPOSITIVOS_MEDICOS>"},
                    why=["Categoría hoja: permite exigir calibre y longitud solo a las agujas, no a guantes o jeringas."],
                    save={"CAT_AGUJAS": "id"},
                    show=["id", "code", "name", "parent_category_id"],
                ),
            ],
            after="Si alguna responde `409 DUPLICATE_CODE`, consúltela con `GET /api/v1/categories?code=<código>` y use su `id`.",
        ),
        step(
            "04-crear-atributos.md",
            "Crear los atributos",
            "Calibre y longitud de la aguja.",
            [
                call(
                    "Crear el atributo `CALIBRE_AGUJA` (entero, sin unidad)",
                    "POST", f"{API}/attribute-definitions",
                    body={"code": "CALIBRE_AGUJA", "name": "Calibre (G)",
                          "description": "Calibre de la aguja en la escala gauge; a mayor número, aguja más delgada.",
                          "data_type": "INTEGER"},
                    why=[
                        "`18G` es el calibre en la escala **gauge**: un número entero de una escala, no una magnitud física.",
                        "Por eso no lleva `unit_of_measure_id`: la \"G\" de 18G **no** es gramos.",
                    ],
                    save={"ATR_CALIBRE_AGUJA": "id"},
                    show=["id", "code", "data_type", "unit_of_measure_id"],
                ),
                call(
                    "Crear el atributo `LONGITUD_AGUJA` (decimal en pulgadas)",
                    "POST", f"{API}/attribute-definitions",
                    body={"code": "LONGITUD_AGUJA", "name": "Longitud",
                          "description": "Longitud de la aguja en pulgadas.",
                          "data_type": "DECIMAL", "unit_of_measure_id": "<PULG>"},
                    why=["`DECIMAL` con unidad `PULG`: `1 1/2` se guarda como `1.5`."],
                    save={"ATR_LONGITUD_AGUJA": "id"},
                    show=["id", "code", "data_type", "unit_of_measure_id"],
                ),
            ],
        ),
        step(
            "05-asociar-atributos-a-la-categoria.md",
            "Asociar los atributos a la categoría",
            "Ambos obligatorios y filtrables.",
            [
                call(
                    "Asociar `CALIBRE_AGUJA`",
                    "POST", f"{API}/categories/<CAT_AGUJAS>/attributes",
                    body={"attribute_definition_id": "<ATR_CALIBRE_AGUJA>", "is_required": True, "is_filterable": True, "display_order": 1},
                    why=["Sin calibre no se puede despachar una aguja: obligatorio. Filtrable para buscar \"agujas 18G\"."],
                    save={"CA_CALIBRE": "id"},
                    show=["id", "attribute_definition_id", "is_required", "is_filterable"],
                ),
                call(
                    "Asociar `LONGITUD_AGUJA`",
                    "POST", f"{API}/categories/<CAT_AGUJAS>/attributes",
                    body={"attribute_definition_id": "<ATR_LONGITUD_AGUJA>", "is_required": True, "is_filterable": True, "display_order": 2},
                    why=["Mismo criterio que el calibre."],
                    save={"CA_LONGITUD": "id"},
                    show=["id", "attribute_definition_id", "is_required", "is_filterable"],
                ),
            ],
        ),
        step(
            "06-crear-producto.md",
            "Crear el producto (sin marca)",
            "Registrar la aguja.",
            [
                call(
                    "Crear el producto",
                    "POST", f"{API}/products",
                    body={
                        "product_type": "GOOD",
                        "canonical_name": "Aguja hipodérmica 18G x 1 1/2 pulgadas",
                        "description": "Aguja hipodérmica estéril de un solo uso.",
                        "manufacturer_organization_id": "<FABRICANTE_RYMCO>",
                        "base_unit_id": "<UND>",
                    },
                    why=[
                        "No se envía `global_brand_id`: el producto no tiene marca comercial propia. Inventar una marca \"RYMCO\" "
                        "mezclaría fabricante y marca.",
                        "`RFZC18B` no va en el nombre: se registra como identificador `OTHER` (paso 9).",
                    ],
                    save={"PRODUCTO": "id"},
                    show=PRODUCT_SHOW,
                ),
            ],
        ),
        step(
            "07-clasificar-producto.md",
            "Clasificar el producto",
            "Asignar `AGUJAS_HIPODERMICAS`.",
            [
                call(
                    "Asignar la categoría",
                    "POST", f"{API}/products/<PRODUCTO>/categories",
                    body={"global_category_id": "<CAT_AGUJAS>"},
                    why=["Primera categoría → principal."],
                    save={"PC_AGUJAS": "id"},
                    show=["id", "global_category_id", "is_primary"],
                ),
            ],
        ),
        step(
            "08-registrar-valores-y-presentaciones.md",
            "Registrar atributos y presentaciones",
            "Calibre 18, longitud 1.5 pulgadas; presentaciones unidad y caja x 100.",
            [
                call(
                    "Calibre = 18",
                    "PUT", f"{API}/products/<PRODUCTO>/attribute-values/<ATR_CALIBRE_AGUJA>",
                    body={"integer_value": 18},
                    why=["`INTEGER` → `integer_value`."],
                    show=["attribute_definition_id", "integer_value"],
                ),
                call(
                    "Longitud = 1.5 pulgadas",
                    "PUT", f"{API}/products/<PRODUCTO>/attribute-values/<ATR_LONGITUD_AGUJA>",
                    body={"decimal_value": 1.5},
                    why=["`1 1/2` del Excel → `1.5`. Se admiten hasta 8 decimales."],
                    show=["attribute_definition_id", "decimal_value"],
                ),
                call(
                    "Presentación base `UNIDAD`",
                    "POST", f"{API}/products/<PRODUCTO>/presentations",
                    body={"code": "UNIDAD", "name": "Aguja individual", "base_quantity": 1, "display_order": 1, "is_base": True},
                    why=[
                        "Cada aguja viene en su empaque estéril individual y se vende suelta en farmacias.",
                        "El EAN-13 identifica este nivel (ver paso 9). `base_quantity: 1` por ser base.",
                    ],
                    save={"PRES_UNIDAD": "id"},
                    show=["id", "code", "base_quantity", "is_base"],
                ),
                call(
                    "Presentación `CAJA_X100`",
                    "POST", f"{API}/products/<PRODUCTO>/presentations",
                    body={"code": "CAJA_X100", "name": "Caja x 100 agujas", "packaging_type_id": "<BOX>",
                          "base_quantity": 100, "display_order": 2, "is_base": False},
                    why=["Factor 100 (`Contenido Interno = 100`)."],
                    save={"PRES_CAJA_X100": "id"},
                    show=["id", "code", "packaging_type_id", "base_quantity", "is_base"],
                ),
            ],
        ),
        step(
            "09-registrar-identificadores.md",
            "Registrar los identificadores",
            "EAN-13 a la unidad, GTIN-14 a la caja y referencia del fabricante como `OTHER`.",
            [
                call(
                    "EAN-13 `7706634002856` → unidad",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "EAN", "value": "7706634002856",
                          "global_product_presentation_id": "<PRES_UNIDAD>", "is_primary": True},
                    why=[
                        "13 dígitos con dígito de control válido → `EAN`.",
                        "Va a la `UNIDAD` porque es el código \"base\" del que se deriva el GTIN-14.",
                    ],
                    save={"ID_EAN13": "id"},
                    show=ID_SHOW,
                ),
                call(
                    "GTIN-14 `27706634002850` → caja",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "GTIN", "value": "27706634002850",
                          "global_product_presentation_id": "<PRES_CAJA_X100>", "is_primary": True},
                    why=[
                        "14 dígitos → `GTIN` (el tipo `EAN` es para 8 o 13 dígitos por convención; el servicio acepta 8, 12, 13 o 14 en la familia GTIN).",
                        "El primer dígito (`2`) es el **indicador de empaque** GS1: marca un agrupamiento del artículo `770663400285`.",
                        "`canonical_value` es el mismo valor (ya tiene 14 dígitos) y **distinto** del canónico del EAN "
                        "(`07706634002856`), por eso no chocan.",
                    ],
                    save={"ID_GTIN14": "id"},
                    show=ID_SHOW,
                ),
                call(
                    "Referencia del fabricante `RFZC18B` → `OTHER`",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "OTHER", "value": "RFZC18B"},
                    why=[
                        "No es un código de barras: es la referencia de catálogo de Rymco. Sirve para encontrar el producto con "
                        "`GET /products?identifier=RFZC18B` cuando llega en una orden de compra.",
                        "Sin `global_product_presentation_id`: la referencia identifica al producto, no a un empaque.",
                        "`OTHER` solo exige unicidad **dentro del producto**; otro fabricante podría usar la misma referencia.",
                    ],
                    save={"ID_REF_FABRICANTE": "id"},
                    show=ID_SHOW,
                ),
                call(
                    "Error esperado: el mismo código como GTIN",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "GTIN", "value": "07706634002856"},
                    expect=409,
                    why=[
                        "`07706634002856` es el EAN-13 de la llamada 1 con un cero a la izquierda. GTIN, EAN y UPC se comparan por su "
                        "forma canónica de 14 dígitos: es **el mismo código**.",
                        "Responde `409 IDENTIFIER_COLLISION` e indica en `conflict` qué registro ya lo tiene.",
                    ],
                    show=["status", "code", "detail", "conflict"],
                ),
                call(
                    "Error esperado: un GTIN registrado como `BARCODE`",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "BARCODE", "value": "7706634002856"},
                    expect=422,
                    why=[
                        "`BARCODE` es para códigos de barras **que no son GS1**. Si el valor cumple el formato GTIN/EAN/UPC, "
                        "el servicio exige registrarlo con su tipo específico: `422 BARCODE_IS_GTIN`.",
                        "El formato se valida **antes** que la unicidad: por eso responde `422` y no `409`, aunque el código ya esté registrado.",
                        "Así no se evita la validación del dígito de control ni la detección de duplicados.",
                    ],
                    show=["status", "code", "detail"],
                ),
            ],
            after="**Antes de cargar, confirme en el empaque físico** qué código está en la unidad y cuál en la caja: un identificador "
                  "no se puede mover a otra presentación (solo inactivar) y su valor **no se puede volver a registrar**, "
                  "aunque esté inactivo.",
        ),
        step(
            "10-crear-y-asignar-grupos.md",
            "Crear y asignar los grupos",
            "Importar los grupos útiles.",
            group_block(1, "0005", "Médico quirúrgicos")
            + group_block(2, "0016", "Dispositivos médicos")
            + group_block(4, "0278", "Rymco"),
            intro="Los grupos `0005` y `0016` también los usa el ejercicio 5: el que se ejecute primero los crea y el otro "
                  "los encuentra en la consulta. `Grupo 5 = 0695 NO APLICA` no se importa.",
        ),
        step(
            "11-verificar-resultado.md",
            "Verificar el resultado",
            "Escanear ambos códigos y buscar por la referencia del fabricante.",
            [
                call(
                    "Escanear el GTIN-14 (caja)",
                    "GET", f"{API}/products/by-identifier/27706634002850",
                    why=["Devuelve la presentación `CAJA_X100`: se vendió una caja de 100 agujas."],
                    show=["product.canonical_name", "presentation.code", "presentation.base_quantity", "identifier.identifier_type"],
                ),
                call(
                    "Escanear el EAN-13 (unidad)",
                    "GET", f"{API}/products/by-identifier/7706634002856",
                    why=["Devuelve la presentación `UNIDAD`."],
                    show=["product.canonical_name", "presentation.code", "presentation.base_quantity", "identifier.identifier_type"],
                ),
                call(
                    "Buscar por la referencia del fabricante",
                    "GET", f"{API}/products?identifier=RFZC18B",
                    why=["El filtro `identifier` busca en todos los tipos de identificador, incluido `OTHER`."],
                    show=["items[].canonical_name", "items[].eligible_for_adoption", "total_records"],
                ),
            ],
        ),
    ],
)
