"""Ejercicio de docs/ejemplo/ (Principio XXII): datos de las llamadas y su justificación."""

from tests.examples.spec_common import API, call, get_group_type, get_manufacturer, get_packaging, get_unit, group_block, step

PRODUCT_SHOW = ["id", "version", "status", "canonical_name", "global_brand_id", "manufacturer_organization_id",
                "base_unit_id", "completeness", "eligible_for_adoption", "warnings"]

EX2 = dict(
    folder="2-leche-nan-1-optipro-tres-latas",
    title="Ejercicio 2 — Leche NAN 1 Optipro: tres filas del Excel, un solo producto",
    focus=(
        "Cómo **tres filas del Excel** (lata de 400 g, 900 g y 1100 g) se cargan como **un solo producto con tres "
        "presentaciones**, usando el **gramo** como unidad base. Además: atributos `INTEGER` y `BOOLEAN`, "
        "un código de barras por presentación y grupos del Excel que **no** se importan."
    ),
    excel_ids="7334, 6138 y 7333",
    excel=[
        ("ID / Código", "7334 / 007334 · 6138 / 006138 · 7333 / 007333"),
        ("Nombre (7334)", "NAN 1 OPTIPRO LECHE POLVO LATAX400G RF12495528 NESTLE"),
        ("Nombre (6138)", "NAN 1 OPTIPRO LECHE POLVO LATAX900G NESTLE"),
        ("Nombre (7333)", "NAN 1 OPTIPRO LECHE POLVO LATAX1100G NESTLE"),
        ("Nombre Tipo Producto", "LECHES"),
        ("Unidad Medida", "LATA (las tres)"),
        ("Contenido Interno", "vacío (las tres)"),
        ("Código Barras 1", "7501059227453 · 7501059227644 · 7501059279124 (EAN-13 válidos)"),
        ("Estado", "A"),
        ("Grupo 1 / 2 / 4", "0687 ALIMENTOS / 0689 LECHES / 0336 NESTLE"),
        ("Grupo 3 / 5", "0133 NO APLICA / 0695 NO APLICA"),
        ("Grupo 6", "0836 EXCLUIR VIERNES DAO"),
        ("Maneja Presentaciones", "N"),
    ],
    interpretation=[
        ("Qué es el producto", "\"NAN 1 Optipro leche en polvo\". Las tres filas describen **el mismo producto** en tres "
         "tamaños de lata. En el sistema anterior cada tamaño era un producto; en el catálogo global es **un producto** con tres presentaciones."),
        ("Marca / fabricante", "Marca `NAN`; fabricante Nestlé (Party Identity)."),
        ("Unidad base", "`G` (gramo). Así cada lata se expresa en gramos y las tres son comparables: 400, 900 y 1100 g."),
        ("Presentaciones", "`LATA_400G`, `LATA_900G`, `LATA_1100G`, empaque `CAN`. **Ninguna** es base: ninguna equivale a 1 g."),
        ("Categoría", "`ALIMENTOS > LECHES`."),
        ("Atributos", "Etapa = 1 (`INTEGER`, sale de \"NAN **1**\") y fórmula infantil = sí (`BOOLEAN`)."),
        ("Códigos de barras", "Uno por fila del Excel → uno por presentación."),
        ("Grupos", "`GROUP_1` 0687, `GROUP_2` 0689 y `GROUP_4` 0336. No se importan `NO APLICA` (G3, G5) ni `EXCLUIR VIERNES DAO` (G6)."),
        ("No va al catálogo", "`RF12495528` (referencia del proveedor dentro del nombre), `Maneja Presentaciones = N` (en el catálogo "
         "todo producto tiene presentaciones), códigos internos, precios, stock y lotes."),
    ],
    steps=[
        step(
            "01-consultar-datos-base.md",
            "Consultar los datos base",
            "Obtener los `id` de la unidad, el empaque, los tipos de grupo y el fabricante (registrándolo si todavía no existe).",
            [
                get_unit("G", "G", [
                    "La leche en polvo se mide por **peso**; el gramo permite expresar cada lata con su contenido real.",
                    "`G` la trae la carga inicial.",
                ]),
                get_packaging("CAN", "CAN", ["`Unidad Medida = LATA` en el Excel es un **empaque**: en el catálogo es `CAN`."]),
                get_group_type(1), get_group_type(2), get_group_type(4),
                *get_manufacturer("NESTLE", "FABRICANTE_NESTLE", "Nestlé", "Nestlé"),
            ],
        ),
        step(
            "02-crear-marca.md",
            "Crear la marca NAN",
            "Registrar la marca comercial.",
            [
                call(
                    "Crear la marca `NAN`",
                    "POST", f"{API}/brands",
                    body={"code": "NAN", "name": "NAN", "description": "Línea de fórmulas infantiles de Nestlé."},
                    why=[
                        "`NAN` es la marca que inicia el nombre; Nestlé (al final del nombre) es el fabricante.",
                        "Se crea una sola vez y la comparten todos los productos NAN del Excel (NAN 2, NAN 3, NAN AR…).",
                    ],
                    save={"MARCA_NAN": "id"},
                    show=["id", "code", "name", "status"],
                ),
            ],
            after="Si responde `409 DUPLICATE_CODE`, consulte `GET /api/v1/brands?code=NAN` y use ese `id`.",
        ),
        step(
            "03-crear-categorias.md",
            "Crear las categorías",
            "Crear `ALIMENTOS > LECHES`.",
            [
                call(
                    "Crear la categoría raíz `ALIMENTOS`",
                    "POST", f"{API}/categories",
                    body={"code": "ALIMENTOS", "name": "Alimentos"},
                    why=["Raíz para leches y otros alimentos (`Grupo 1 = ALIMENTOS` en el Excel lo confirma)."],
                    save={"CAT_ALIMENTOS": "id"},
                    show=["id", "code", "name", "parent_category_id"],
                ),
                call(
                    "Crear la subcategoría `LECHES`",
                    "POST", f"{API}/categories",
                    body={"code": "LECHES", "name": "Leches y fórmulas lácteas", "parent_category_id": "<CAT_ALIMENTOS>"},
                    why=["Sale de `Nombre Tipo Producto = LECHES`. Incluye fórmulas infantiles (NAN, Enfamil) y leches en polvo (Klim)."],
                    save={"CAT_LECHES": "id"},
                    show=["id", "code", "name", "parent_category_id"],
                ),
            ],
            after="Si alguna responde `409 DUPLICATE_CODE`, consúltela con `GET /api/v1/categories?code=<código>` y use su `id`.",
        ),
        step(
            "04-crear-atributos.md",
            "Crear las definiciones de atributo",
            "Definir la etapa de la fórmula y si es fórmula infantil.",
            [
                call(
                    "Crear el atributo `ETAPA_FORMULA` (entero)",
                    "POST", f"{API}/attribute-definitions",
                    body={"code": "ETAPA_FORMULA", "name": "Etapa de la fórmula",
                          "description": "Etapa de alimentación a la que corresponde la fórmula (1, 2, 3…).",
                          "data_type": "INTEGER"},
                    why=[
                        "`INTEGER` porque la etapa es un número entero: \"NAN **1**\", \"NAN **2**\"…",
                        "Sin `unit_of_measure_id`: la etapa no es una magnitud física.",
                    ],
                    save={"ATR_ETAPA_FORMULA": "id"},
                    show=["id", "code", "data_type", "unit_of_measure_id"],
                ),
                call(
                    "Crear el atributo `FORMULA_INFANTIL` (sí/no)",
                    "POST", f"{API}/attribute-definitions",
                    body={"code": "FORMULA_INFANTIL", "name": "Fórmula infantil",
                          "description": "Indica si el producto es una fórmula para lactantes o niños pequeños.",
                          "data_type": "BOOLEAN"},
                    why=["`BOOLEAN` porque la respuesta es sí o no. Separa fórmulas infantiles (NAN) de leches generales (Klim) dentro de `LECHES`."],
                    save={"ATR_FORMULA_INFANTIL": "id"},
                    show=["id", "code", "data_type"],
                ),
            ],
        ),
        step(
            "05-asociar-atributos-a-la-categoria.md",
            "Asociar los atributos a la categoría",
            "Indicar cómo usa `LECHES` cada atributo.",
            [
                call(
                    "Asociar `FORMULA_INFANTIL` (obligatorio y filtrable)",
                    "POST", f"{API}/categories/<CAT_LECHES>/attributes",
                    body={"attribute_definition_id": "<ATR_FORMULA_INFANTIL>", "is_required": True, "is_filterable": True, "display_order": 1},
                    why=["Obligatorio: toda leche debe decir si es fórmula infantil o no. Filtrable para listar solo fórmulas."],
                    save={"CA_FORMULA_INFANTIL": "id"},
                    show=["id", "attribute_definition_id", "is_required", "is_filterable"],
                ),
                call(
                    "Asociar `ETAPA_FORMULA` (opcional y filtrable)",
                    "POST", f"{API}/categories/<CAT_LECHES>/attributes",
                    body={"attribute_definition_id": "<ATR_ETAPA_FORMULA>", "is_required": False, "is_filterable": True, "display_order": 2},
                    why=[
                        "`is_required: false`: una leche que no es fórmula (Klim tradicional) no tiene etapa. Si fuera obligatorio, "
                        "esos productos nunca quedarían completos.",
                        "Aunque sea opcional, se registra cuando existe.",
                    ],
                    save={"CA_ETAPA_FORMULA": "id"},
                    show=["id", "attribute_definition_id", "is_required", "is_filterable"],
                ),
            ],
        ),
        step(
            "06-crear-producto.md",
            "Crear el producto (uno solo para las tres filas)",
            "Registrar un único producto con el gramo como unidad base.",
            [
                call(
                    "Crear el producto",
                    "POST", f"{API}/products",
                    body={
                        "product_type": "GOOD",
                        "canonical_name": "NAN 1 Optipro leche en polvo",
                        "description": "Fórmula láctea infantil en polvo, etapa 1.",
                        "global_brand_id": "<MARCA_NAN>",
                        "manufacturer_organization_id": "<FABRICANTE_NESTLE>",
                        "base_unit_id": "<G>",
                    },
                    why=[
                        "**Un solo producto**: lo que cambia entre las tres filas es el tamaño de la lata, que es una presentación.",
                        "`canonical_name` no lleva el tamaño (`LATAX400G`) ni la referencia `RF12495528`.",
                        "`base_unit_id: G`: con gramos las tres latas quedan en la misma unidad y se pueden convertir entre sí. "
                        "Con `UND` una lata de 400 g y una de 900 g valdrían \"1\" cada una, lo que no permite comparar ni convertir.",
                    ],
                    save={"PRODUCTO": "id"},
                    show=PRODUCT_SHOW,
                ),
            ],
            after="Si alguien vuelve a crear el mismo nombre con la misma marca, el servicio lo acepta pero devuelve la "
                  "advertencia `POSSIBLE_DUPLICATE` en `warnings`. Es la señal de que se está duplicando una fila del Excel.",
        ),
        step(
            "07-clasificar-producto.md",
            "Clasificar el producto",
            "Asignar la categoría `LECHES`.",
            [
                call(
                    "Asignar la categoría `LECHES`",
                    "POST", f"{API}/products/<PRODUCTO>/categories",
                    body={"global_category_id": "<CAT_LECHES>"},
                    why=["Primera categoría → queda como principal automáticamente."],
                    save={"PC_LECHES": "id"},
                    show=["id", "global_category_id", "is_primary"],
                ),
            ],
        ),
        step(
            "08-registrar-valores-de-atributos.md",
            "Registrar los valores de los atributos",
            "Etapa 1 y fórmula infantil = sí.",
            [
                call(
                    "Fórmula infantil = sí",
                    "PUT", f"{API}/products/<PRODUCTO>/attribute-values/<ATR_FORMULA_INFANTIL>",
                    body={"boolean_value": True},
                    why=["`BOOLEAN` → `boolean_value` con `true` o `false` (no `\"S\"`/`\"N\"` como en el Excel)."],
                    show=["attribute_definition_id", "boolean_value", "version"],
                ),
                call(
                    "Etapa = 1",
                    "PUT", f"{API}/products/<PRODUCTO>/attribute-values/<ATR_ETAPA_FORMULA>",
                    body={"integer_value": 1},
                    why=["`INTEGER` → `integer_value`. Si se enviara `1.5` o `\"1\"` en `text_value` respondería `422 VALUE_TYPE_MISMATCH`."],
                    show=["attribute_definition_id", "integer_value", "version"],
                ),
            ],
        ),
        step(
            "09-crear-presentaciones.md",
            "Crear las tres presentaciones",
            "Una presentación por cada fila del Excel.",
            [
                call(
                    "Presentación `LATA_400G` (fila 7334)",
                    "POST", f"{API}/products/<PRODUCTO>/presentations",
                    body={"code": "LATA_400G", "name": "Lata x 400 g", "packaging_type_id": "<CAN>",
                          "base_quantity": 400, "display_order": 1, "is_base": False},
                    why=[
                        "`base_quantity: 400` porque la unidad base es el gramo: una lata = 400 g.",
                        "`is_base: false`: una presentación base debe tener `base_quantity = 1` (1 g), y ninguna lata pesa 1 g. "
                        "Un producto **no necesita** presentación base para estar completo.",
                        "No se envía `content_quantity`: con la unidad base en gramos, `base_quantity` ya dice cuánto contiene.",
                    ],
                    save={"PRES_LATA_400G": "id"},
                    show=["id", "code", "name", "base_quantity", "is_base", "eligible_for_adoption"],
                ),
                call(
                    "Presentación `LATA_900G` (fila 6138)",
                    "POST", f"{API}/products/<PRODUCTO>/presentations",
                    body={"code": "LATA_900G", "name": "Lata x 900 g", "packaging_type_id": "<CAN>",
                          "base_quantity": 900, "display_order": 2, "is_base": False},
                    why=["Misma lógica: 900 g."],
                    save={"PRES_LATA_900G": "id"},
                    show=["id", "code", "base_quantity", "is_base"],
                ),
                call(
                    "Presentación `LATA_1100G` (fila 7333)",
                    "POST", f"{API}/products/<PRODUCTO>/presentations",
                    body={"code": "LATA_1100G", "name": "Lata x 1100 g", "packaging_type_id": "<CAN>",
                          "base_quantity": 1100, "display_order": 3, "is_base": False},
                    why=["Misma lógica: 1100 g. `display_order` ordena de menor a mayor tamaño."],
                    save={"PRES_LATA_1100G": "id"},
                    show=["id", "code", "base_quantity", "is_base"],
                ),
            ],
        ),
        step(
            "10-registrar-codigos-de-barras.md",
            "Registrar los códigos de barras",
            "Cada EAN del Excel va a la presentación de su fila.",
            [
                call(
                    "EAN `7501059227453` → lata 400 g",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "EAN", "value": "7501059227453",
                          "global_product_presentation_id": "<PRES_LATA_400G>", "is_primary": True},
                    why=[
                        "Cada tamaño tiene su propio código: al escanear se debe saber qué lata se vendió.",
                        "`is_primary: true`: la marca de principal es **por presentación**, así que cada lata tiene el suyo.",
                    ],
                    save={"ID_EAN_400G": "id"},
                    show=["id", "global_product_presentation_id", "identifier_type", "value", "is_primary"],
                ),
                call(
                    "EAN `7501059227644` → lata 900 g",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "EAN", "value": "7501059227644",
                          "global_product_presentation_id": "<PRES_LATA_900G>", "is_primary": True},
                    why=["Código de la fila 6138."],
                    save={"ID_EAN_900G": "id"},
                    show=["id", "global_product_presentation_id", "value", "is_primary"],
                ),
                call(
                    "EAN `7501059279124` → lata 1100 g",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "EAN", "value": "7501059279124",
                          "global_product_presentation_id": "<PRES_LATA_1100G>", "is_primary": True},
                    why=["Código de la fila 7333."],
                    save={"ID_EAN_1100G": "id"},
                    show=["id", "global_product_presentation_id", "value", "is_primary"],
                ),
            ],
        ),
        step(
            "11-crear-y-asignar-grupos.md",
            "Crear y asignar los grupos",
            "Importar solo los grupos que agrupan algo.",
            group_block(1, "0687", "Alimentos")
            + group_block(2, "0689", "Leches")
            + group_block(4, "0336", "Nestlé"),
            intro=(
                "Las tres filas del Excel tienen los mismos grupos, así que se asignan **una sola vez** al producto.\n\n"
                "No se importan:\n\n"
                "- `Grupo 3 = 0133 NO APLICA` y `Grupo 5 = 0695 NO APLICA`: no agrupan nada.\n"
                "- `Grupo 6 = 0836 EXCLUIR VIERNES DAO`: es una **regla comercial** de una empresa (excluir de una promoción "
                "los viernes), no una característica del producto. Va en Commercial Relationship Service."
            ),
        ),
        step(
            "12-verificar-resultado.md",
            "Verificar el resultado",
            "Comprobar que cada código lleva a su lata y que el producto quedó elegible.",
            [
                call(
                    "Consultar el producto con su detalle",
                    "GET", f"{API}/products/<PRODUCTO>?expand=detail",
                    why=["Debe mostrar tres presentaciones y tres códigos, cada uno ligado a su presentación."],
                    show=["canonical_name", "completeness", "eligible_for_adoption",
                          "detail.presentations[].code", "detail.presentations[].base_quantity",
                          "detail.identifiers[].value", "detail.identifiers[].global_product_presentation_id"],
                ),
                call(
                    "Escanear el código de la lata de 900 g",
                    "GET", f"{API}/products/by-identifier/7501059227644",
                    why=["Devuelve el producto y la presentación `LATA_900G` con `base_quantity: 900`."],
                    show=["product.canonical_name", "presentation.code", "presentation.base_quantity", "is_current"],
                ),
                call(
                    "Listar las fórmulas infantiles de etapa 1",
                    "GET", f"{API}/products?attribute_filters=FORMULA_INFANTIL:true&attribute_filters=ETAPA_FORMULA:1",
                    why=["En `BOOLEAN` el filtro usa `true` o `false`; en `INTEGER`, el número."],
                    show=["items[].canonical_name", "total_records"],
                ),
            ],
        ),
    ],
)
