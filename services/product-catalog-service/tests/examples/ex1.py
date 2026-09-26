"""Ejercicio de docs/ejemplo/ (Principio XXII): datos de las llamadas y su justificación."""

from tests.examples.spec_common import API, call, get_group_type, get_manufacturer, get_packaging, get_unit, group_block, step

PRODUCT_SHOW = ["id", "version", "status", "canonical_name", "global_brand_id", "manufacturer_organization_id",
                "base_unit_id", "completeness", "eligible_for_adoption", "warnings"]

EX1 = dict(
    folder="1-acetaminofen-adorem-caja-x100",
    title="Ejercicio 1 — Acetaminofén Adorem 500 mg, caja x 100",
    focus=(
        "Medicamento ético con **marca comercial**, **unidad de medida nueva** (`MG`), atributos de tres "
        "tipos (`TEXT`, `DECIMAL` con unidad y `OPTION`), una **presentación base** (la tableta) y una "
        "presentación con **factor de conversión** (la caja x 100) con **dos códigos EAN**."
    ),
    excel_ids="45",
    excel=[
        ("ID", "45"),
        ("Código", "000045"),
        ("Referencia", "48691"),
        ("Nombre", "ACETAMINOFEN (ADOREM) 500MG TABLETA CAJAX100 SIEGFRIED"),
        ("Nombre Marca", "GENERAL"),
        ("Nombre Tipo Producto", "ETICOS"),
        ("Nombre Corto", "ACETAMINOFEN"),
        ("Unidad Medida", "CAJA"),
        ("Contenido Interno", "100"),
        ("Código Barras 1", "7707355056876 (EAN-13 válido)"),
        ("Código Barras 2", "7707355052038 (EAN-13 válido)"),
        ("Estado", "A"),
        ("Grupo 1", "0001 MEDICAMENTOS ETICOS"),
        ("Grupo 2", "0012 OTC"),
        ("Grupo 3", "0085 ANALGESICOS"),
        ("Grupo 4", "0170 SIEGFRIED"),
        ("Grupo 5", "0695 NO APLICA"),
        ("Maneja Lotes / Fecha Vencimiento", "S / S"),
    ],
    interpretation=[
        ("Qué es el producto", "\"Acetaminofén 500 mg tableta\". Del nombre se separa lo que es del producto "
         "(principio activo, concentración, forma) de lo que es de la presentación (`CAJAX100`) y del fabricante (`SIEGFRIED`)."),
        ("Marca", "`ADOREM`, que viene entre paréntesis en el nombre. La columna `Nombre Marca` dice `GENERAL` en casi todo "
         "el Excel, así que no sirve."),
        ("Fabricante", "Siegfried → organización en Party Identity (sale del nombre y de `Grupo 4`)."),
        ("Unidad base", "`UND` = una tableta. Es la unidad más pequeña en que se puede vender."),
        ("Presentaciones", "`TABLETA` (base, factor 1) y `CAJA_X100` (empaque `BOX`, factor 100). `Contenido Interno = 100` es el factor."),
        ("Categoría", "`MEDICAMENTOS > MEDICAMENTOS_ETICOS` (sale de `Nombre Tipo Producto = ETICOS`)."),
        ("Atributos", "Principio activo = Acetaminofén (`TEXT`), concentración = 500 `MG` (`DECIMAL`), forma farmacéutica = Tableta (`OPTION`)."),
        ("Códigos de barras", "Dos EAN-13 válidos. Los dos identifican la caja (la tableta suelta no lleva código)."),
        ("Grupos", "`GROUP_1` a `GROUP_4` con el código y nombre del Excel. `Grupo 5 = NO APLICA` no se importa."),
        ("No va al catálogo", "`Código` (000045), `Referencia` (48691), `Nombre Corto`, precios, costos, stock, impuestos, lotes y "
         "vencimientos: son datos de cada empresa (Commercial Relationship / Inventory)."),
    ],
    steps=[
        step(
            "01-consultar-datos-base.md",
            "Consultar los datos base",
            "Obtener los `id` de lo que ya existe (unidad, empaque, tipos de grupo y fabricante) y registrar el fabricante si todavía no existe.",
            [
                get_unit("UND", "UND", [
                    "La unidad base del producto es la **tableta**: se cuenta en unidades enteras, así que es `UND`.",
                    "`UND` la crea la carga inicial (`python -m product_catalog_service.seed load`); no se crea a mano.",
                    "Se filtra por `code` porque el `id` cambia en cada base de datos; el código no.",
                ]),
                get_packaging("BOX", "BOX", [
                    "En el Excel `Unidad Medida = CAJA`. Pese al nombre de la columna, **caja no es una unidad de medida sino "
                    "un tipo de empaque**; en el catálogo es `BOX`.",
                ]),
                get_group_type(1), get_group_type(2), get_group_type(3), get_group_type(4),
                *get_manufacturer("SIEGFRIED", "FABRICANTE_SIEGFRIED", "Siegfried", "Siegfried"),
            ],
        ),
        step(
            "02-crear-unidad-mg.md",
            "Crear la unidad de medida miligramo (`MG`)",
            "Tener una unidad para expresar la concentración (500 mg).",
            [
                call(
                    "Crear la unidad `MG`",
                    "POST", f"{API}/units-of-measure",
                    body={"code": "MG", "name": "Miligramo", "symbol": "mg", "measurement_type": "MASS", "allows_decimals": True},
                    why=[
                        "La carga inicial trae `G` y `KG`, pero no `MG`. Las concentraciones de medicamentos se expresan en mg.",
                        "`measurement_type: MASS` porque el miligramo mide masa, igual que `G` y `KG`.",
                        "`allows_decimals: true` porque hay concentraciones como 2.5 mg o 0.25 mg.",
                        "`code`, `measurement_type` y `allows_decimals` **no se pueden cambiar después** (son inmutables): "
                        "revíselos antes de enviar.",
                    ],
                    save={"MG": "id"},
                    show=["id", "code", "name", "symbol", "measurement_type", "allows_decimals", "status"],
                ),
            ],
            after="Si responde `409 DUPLICATE_CODE`, la unidad ya existe (por ejemplo, de una carga anterior): "
                  "consúltela con `GET /api/v1/units-of-measure?code=MG` y use ese `id` como `<MG>`.",
        ),
        step(
            "03-crear-marca.md",
            "Crear la marca Adorem",
            "Registrar la marca comercial que el Excel esconde dentro del nombre.",
            [
                call(
                    "Crear la marca `ADOREM`",
                    "POST", f"{API}/brands",
                    body={"code": "ADOREM", "name": "Adorem", "description": "Marca comercial de acetaminofén de Siegfried."},
                    why=[
                        "En el nombre del Excel, lo que va entre paréntesis — `(ADOREM)` — es la marca comercial del medicamento.",
                        "La columna `Nombre Marca` no sirve: vale `GENERAL` en 16 883 de las 16 889 filas.",
                        "La marca es distinta del fabricante: Adorem es la marca, Siegfried quien lo fabrica.",
                        "`code` se guarda en mayúsculas y no se puede cambiar; `name` y `description` sí.",
                    ],
                    save={"MARCA_ADOREM": "id"},
                    show=["id", "code", "name", "status"],
                ),
            ],
        ),
        step(
            "04-crear-categorias.md",
            "Crear las categorías",
            "Crear el árbol `MEDICAMENTOS > MEDICAMENTOS_ETICOS` donde se clasifica el producto.",
            [
                call(
                    "Crear la categoría raíz `MEDICAMENTOS`",
                    "POST", f"{API}/categories",
                    body={"code": "MEDICAMENTOS", "name": "Medicamentos", "description": "Productos farmacéuticos."},
                    why=[
                        "Es la raíz del árbol: no lleva `parent_category_id`.",
                        "Agrupa éticos, genéricos y populares, que en el Excel son valores distintos de `Nombre Tipo Producto`.",
                    ],
                    save={"CAT_MEDICAMENTOS": "id"},
                    show=["id", "code", "name", "parent_category_id", "status"],
                ),
                call(
                    "Crear la subcategoría `MEDICAMENTOS_ETICOS`",
                    "POST", f"{API}/categories",
                    body={"code": "MEDICAMENTOS_ETICOS", "name": "Medicamentos éticos", "parent_category_id": "<CAT_MEDICAMENTOS>"},
                    why=[
                        "Sale de `Nombre Tipo Producto = ETICOS`.",
                        "`parent_category_id` la cuelga de `MEDICAMENTOS`.",
                        "El producto se clasifica en la categoría **hoja** (`MEDICAMENTOS_ETICOS`) porque es la más precisa.",
                    ],
                    save={"CAT_MEDICAMENTOS_ETICOS": "id"},
                    show=["id", "code", "name", "parent_category_id", "status"],
                ),
            ],
            after="Si alguna categoría responde `409 DUPLICATE_CODE`, ya existe: consúltela con "
                  "`GET /api/v1/categories?code=<código>` y use su `id`.",
        ),
        step(
            "05-crear-atributos.md",
            "Crear las definiciones de atributo y sus opciones",
            "Definir los datos técnicos que describen al medicamento: principio activo, concentración y forma farmacéutica.",
            [
                call(
                    "Crear el atributo `PRINCIPIO_ACTIVO` (texto)",
                    "POST", f"{API}/attribute-definitions",
                    body={"code": "PRINCIPIO_ACTIVO", "name": "Principio activo",
                          "description": "Sustancia responsable del efecto del medicamento.", "data_type": "TEXT"},
                    why=[
                        "`TEXT` porque el principio activo es un nombre libre (acetaminofén, ibuprofeno, …).",
                        "`description` es **obligatoria** en las definiciones de atributo.",
                        "`data_type` no se puede cambiar después.",
                    ],
                    save={"ATR_PRINCIPIO_ACTIVO": "id"},
                    show=["id", "code", "name", "data_type", "unit_of_measure_id", "status"],
                ),
                call(
                    "Crear el atributo `CONCENTRACION_MG` (decimal en mg)",
                    "POST", f"{API}/attribute-definitions",
                    body={"code": "CONCENTRACION_MG", "name": "Concentración (mg)",
                          "description": "Cantidad de principio activo por unidad, en miligramos.",
                          "data_type": "DECIMAL", "unit_of_measure_id": "<MG>"},
                    why=[
                        "`DECIMAL` porque es una cantidad que puede tener decimales.",
                        "`unit_of_measure_id` fija la unidad (mg) para todos los productos: así el valor guardado es solo el número (`500`).",
                        "Solo `INTEGER` y `DECIMAL` admiten unidad; en otro tipo responde `422 UNIT_NOT_ALLOWED_FOR_DATA_TYPE`.",
                    ],
                    save={"ATR_CONCENTRACION_MG": "id"},
                    show=["id", "code", "name", "data_type", "unit_of_measure_id", "status"],
                ),
                call(
                    "Crear el atributo `FORMA_FARMACEUTICA` (lista de opciones)",
                    "POST", f"{API}/attribute-definitions",
                    body={"code": "FORMA_FARMACEUTICA", "name": "Forma farmacéutica",
                          "description": "Forma en que se presenta el medicamento.", "data_type": "OPTION"},
                    why=[
                        "`OPTION` porque los valores posibles son una lista cerrada (tableta, cápsula, jarabe, …). "
                        "Con texto libre aparecerían variantes como \"TAB\", \"tableta\", \"Tabletas\" que no se pueden filtrar.",
                    ],
                    save={"ATR_FORMA_FARMACEUTICA": "id"},
                    show=["id", "code", "name", "data_type", "status"],
                ),
                call(
                    "Crear la opción `TABLETA`",
                    "POST", f"{API}/attribute-definitions/<ATR_FORMA_FARMACEUTICA>/options",
                    body={"code": "TABLETA", "name": "Tableta", "display_order": 1},
                    why=["Es la forma de este producto (`TABLETA` en el nombre del Excel).",
                         "`display_order` ordena las opciones en las listas de selección."],
                    save={"OPC_TABLETA": "id"},
                    show=["id", "attribute_definition_id", "code", "name", "display_order", "status"],
                ),
                call(
                    "Crear la opción `CAPSULA`",
                    "POST", f"{API}/attribute-definitions/<ATR_FORMA_FARMACEUTICA>/options",
                    body={"code": "CAPSULA", "name": "Cápsula", "display_order": 2},
                    why=["No la usa este producto, pero la necesitan otros medicamentos del Excel. "
                         "Las opciones se definen una vez para toda la lista."],
                    save={"OPC_CAPSULA": "id"},
                    show=["id", "code", "name", "display_order"],
                ),
                call(
                    "Crear la opción `JARABE`",
                    "POST", f"{API}/attribute-definitions/<ATR_FORMA_FARMACEUTICA>/options",
                    body={"code": "JARABE", "name": "Jarabe", "display_order": 3},
                    why=["Igual que la anterior: completa la lista para otros productos."],
                    save={"OPC_JARABE": "id"},
                    show=["id", "code", "name", "display_order"],
                ),
            ],
        ),
        step(
            "06-asociar-atributos-a-la-categoria.md",
            "Asociar los atributos a la categoría",
            "Indicar qué atributos usan los productos de `MEDICAMENTOS_ETICOS` y cuáles son obligatorios.",
            [
                call(
                    "Asociar `PRINCIPIO_ACTIVO` (obligatorio)",
                    "POST", f"{API}/categories/<CAT_MEDICAMENTOS_ETICOS>/attributes",
                    body={"attribute_definition_id": "<ATR_PRINCIPIO_ACTIVO>", "is_required": True, "is_filterable": False, "display_order": 1},
                    why=[
                        "`is_required: true`: todo medicamento ético debe decir su principio activo; si falta, el producto queda **incompleto**.",
                        "`is_filterable: false`: al ser texto libre, se busca mejor con `search` que con filtros exactos.",
                    ],
                    save={"CA_PRINCIPIO_ACTIVO": "id"},
                    show=["id", "global_category_id", "attribute_definition_id", "is_required", "is_filterable", "display_order"],
                ),
                call(
                    "Asociar `CONCENTRACION_MG` (obligatorio y filtrable)",
                    "POST", f"{API}/categories/<CAT_MEDICAMENTOS_ETICOS>/attributes",
                    body={"attribute_definition_id": "<ATR_CONCENTRACION_MG>", "is_required": True, "is_filterable": True, "display_order": 2},
                    why=["`is_filterable: true` permite buscar, por ejemplo, todos los productos de 500 mg "
                         "(`attribute_filters=CONCENTRACION_MG:500`)."],
                    save={"CA_CONCENTRACION_MG": "id"},
                    show=["id", "attribute_definition_id", "is_required", "is_filterable", "display_order"],
                ),
                call(
                    "Asociar `FORMA_FARMACEUTICA` (obligatorio y filtrable)",
                    "POST", f"{API}/categories/<CAT_MEDICAMENTOS_ETICOS>/attributes",
                    body={"attribute_definition_id": "<ATR_FORMA_FARMACEUTICA>", "is_required": True, "is_filterable": True, "display_order": 3},
                    why=["Permite filtrar por tableta, cápsula, etc."],
                    save={"CA_FORMA_FARMACEUTICA": "id"},
                    show=["id", "attribute_definition_id", "is_required", "is_filterable", "display_order"],
                ),
            ],
            after="**No hay herencia entre niveles**: si los atributos se asociaran solo a `MEDICAMENTOS`, no aplicarían a "
                  "productos clasificados en `MEDICAMENTOS_ETICOS`. Se asocian a la categoría donde se clasifica el producto.",
        ),
        step(
            "07-crear-producto.md",
            "Crear el producto",
            "Registrar el producto global con sus datos mínimos, marca y fabricante.",
            [
                call(
                    "Crear el producto",
                    "POST", f"{API}/products",
                    body={
                        "product_type": "GOOD",
                        "canonical_name": "Acetaminofén 500 mg tableta",
                        "description": "Analgésico y antipirético.",
                        "global_brand_id": "<MARCA_ADOREM>",
                        "manufacturer_organization_id": "<FABRICANTE_SIEGFRIED>",
                        "base_unit_id": "<UND>",
                    },
                    why=[
                        "`product_type: GOOD` es el único tipo admitido en el MVP (bien físico).",
                        "`canonical_name` describe **el producto**, no la presentación: no lleva \"caja x 100\" (eso va en la "
                        "presentación) ni el laboratorio (eso va en el fabricante). Se escribe legible, con tildes.",
                        "`global_brand_id` es la marca creada en el paso 3.",
                        "`manufacturer_organization_id` es el `id` de Siegfried en Party Identity; el catálogo lo valida al recibirlo.",
                        "`base_unit_id: UND`: el producto se cuenta en tabletas. Toda cantidad de las presentaciones se expresa en esta unidad.",
                        "No se envían `Código`, `Referencia`, precios ni stock: el cuerpo rechaza campos desconocidos (`422`).",
                    ],
                    save={"PRODUCTO": "id"},
                    show=PRODUCT_SHOW,
                ),
            ],
            after="La respuesta muestra `is_complete: false` con los faltantes: aún no tiene categoría "
                  "(`NO_ACTIVE_CATEGORY`) ni presentación (`NO_ACTIVE_PRESENTATION`). Es normal: se completan en los pasos siguientes.",
        ),
        step(
            "08-clasificar-producto.md",
            "Clasificar el producto en su categoría",
            "Asignar la categoría principal y ver qué atributos quedan exigidos.",
            [
                call(
                    "Asignar la categoría `MEDICAMENTOS_ETICOS`",
                    "POST", f"{API}/products/<PRODUCTO>/categories",
                    body={"global_category_id": "<CAT_MEDICAMENTOS_ETICOS>"},
                    why=[
                        "La **primera** categoría asignada queda automáticamente como principal (`is_primary: true`).",
                        "Un producto completo necesita exactamente una categoría principal.",
                    ],
                    save={"PC_ETICOS": "id"},
                    show=["id", "global_category_id", "is_primary", "status"],
                ),
                call(
                    "Consultar los atributos que ahora aplican",
                    "GET", f"{API}/products/<PRODUCTO>/applicable-attributes",
                    why=["Confirma qué atributos pide la categoría y cuáles son obligatorios antes de registrar valores."],
                    show=["[].code", "[].data_type", "[].is_required", "[].is_filterable"],
                ),
                call(
                    "Consultar la completitud",
                    "GET", f"{API}/products/<PRODUCTO>/completeness",
                    why=["Ya no aparece `NO_ACTIVE_CATEGORY`; ahora falta registrar los atributos obligatorios "
                         "(`MISSING_REQUIRED_ATTRIBUTE`) y crear una presentación."],
                    show=["is_complete", "issues", "missing_attribute_definition_ids"],
                ),
            ],
        ),
        step(
            "09-registrar-valores-de-atributos.md",
            "Registrar los valores de los atributos",
            "Dar valor a los tres atributos obligatorios.",
            [
                call(
                    "Principio activo = Acetaminofén",
                    "PUT", f"{API}/products/<PRODUCTO>/attribute-values/<ATR_PRINCIPIO_ACTIVO>",
                    body={"text_value": "Acetaminofén"},
                    why=[
                        "Es `PUT` porque registra **o reemplaza** el valor del atributo en la ruta. La primera vez responde `201`.",
                        "Se envía **un solo** campo de valor, el que corresponde al tipo: `TEXT` → `text_value`.",
                    ],
                    show=["attribute_definition_id", "text_value", "version", "out_of_classification"],
                ),
                call(
                    "Concentración = 500 mg",
                    "PUT", f"{API}/products/<PRODUCTO>/attribute-values/<ATR_CONCENTRACION_MG>",
                    body={"decimal_value": 500},
                    why=["`DECIMAL` → `decimal_value`. Se envía solo el número; la unidad (mg) ya la fija la definición."],
                    show=["attribute_definition_id", "decimal_value", "version"],
                ),
                call(
                    "Forma farmacéutica = Tableta",
                    "PUT", f"{API}/products/<PRODUCTO>/attribute-values/<ATR_FORMA_FARMACEUTICA>",
                    body={"option_id": "<OPC_TABLETA>"},
                    why=["`OPTION` → `option_id`, el `id` de la opción (no su código ni su nombre).",
                         "Si la opción es de otro atributo o está inactiva responde `422 OPTION_NOT_IN_DEFINITION`."],
                    show=["attribute_definition_id", "option_id", "version"],
                ),
            ],
            after="Para **corregir** un valor después se usa el mismo `PUT` agregando `\"version\"` con la versión actual del valor.",
        ),
        step(
            "10-crear-presentaciones.md",
            "Crear las presentaciones",
            "Registrar cómo se vende: por tableta suelta y por caja de 100.",
            [
                call(
                    "Presentación base `TABLETA`",
                    "POST", f"{API}/products/<PRODUCTO>/presentations",
                    body={"code": "TABLETA", "name": "Tableta", "base_quantity": 1, "display_order": 1, "is_base": True},
                    why=[
                        "`is_base: true`: es la presentación que equivale a **una** unidad base; por eso `base_quantity` debe ser `1` "
                        "(otro valor da `422 BASE_QUANTITY_MUST_BE_ONE`).",
                        "Sin `packaging_type_id`: la tableta suelta no tiene empaque propio.",
                        "Permite que las farmacias vendan tabletas sueltas y conviertan entre caja y tableta.",
                        "Solo puede haber **una** presentación base activa por producto (`409 BASE_PRESENTATION_EXISTS`).",
                    ],
                    save={"PRES_TABLETA": "id"},
                    show=["id", "code", "name", "packaging_type_id", "base_quantity", "is_base", "status", "eligible_for_adoption"],
                ),
                call(
                    "Presentación `CAJA_X100`",
                    "POST", f"{API}/products/<PRODUCTO>/presentations",
                    body={"code": "CAJA_X100", "name": "Caja x 100 tabletas", "packaging_type_id": "<BOX>",
                          "base_quantity": 100, "display_order": 2, "is_base": False},
                    why=[
                        "`base_quantity: 100` es el **factor de conversión**: una caja = 100 tabletas (`Contenido Interno = 100` en el Excel).",
                        "`packaging_type_id: BOX` porque `Unidad Medida = CAJA`.",
                        "No se usa `content_quantity`: ese campo es para contenido medido en otra unidad (p. ej. un frasco de 120 mL).",
                        "`code` es único dentro del producto y no se puede cambiar ni reutilizar.",
                    ],
                    save={"PRES_CAJA_X100": "id"},
                    show=["id", "code", "name", "packaging_type_id", "base_quantity", "is_base", "status", "eligible_for_adoption"],
                ),
            ],
        ),
        step(
            "11-registrar-codigos-de-barras.md",
            "Registrar los códigos de barras",
            "Asociar los dos EAN del Excel a la caja.",
            [
                call(
                    "EAN `7707355056876` (principal de la caja)",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "EAN", "value": "7707355056876",
                          "global_product_presentation_id": "<PRES_CAJA_X100>", "is_primary": True},
                    why=[
                        "`EAN` porque son 13 dígitos con dígito de control GS1 válido (el servicio lo verifica: si no, `422 INVALID_CHECK_DIGIT`).",
                        "`global_product_presentation_id` lo liga a la **caja**: al escanearlo se sabe que se vendió una caja de 100, no una tableta.",
                        "`is_primary: true`: es el código que se mostrará por defecto para la caja.",
                        "El valor se envía como **texto**, nunca como número: así no se pierden ceros a la izquierda.",
                    ],
                    save={"ID_EAN_1": "id"},
                    show=["id", "global_product_presentation_id", "identifier_type", "value", "canonical_value", "is_primary"],
                ),
                call(
                    "EAN `7707355052038` (segundo código de la caja)",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "EAN", "value": "7707355052038",
                          "global_product_presentation_id": "<PRES_CAJA_X100>", "is_primary": False},
                    why=[
                        "Una misma presentación puede tener varios códigos (por ejemplo, empaque antiguo y nuevo). Los dos deben leerse en caja.",
                        "`is_primary: false` porque la caja ya tiene un principal.",
                        "`canonical_value` completa a 14 dígitos: con él el catálogo detecta el mismo código aunque se registre como GTIN, EAN o UPC.",
                    ],
                    save={"ID_EAN_2": "id"},
                    show=["id", "global_product_presentation_id", "identifier_type", "value", "canonical_value", "is_primary"],
                ),
            ],
            after="Si el mismo código ya está registrado en **otro** producto, responde `409 IDENTIFIER_COLLISION` con el "
                  "producto que lo tiene: hay que revisar cuál de los dos está mal, no forzar el registro.",
        ),
        step(
            "12-crear-y-asignar-grupos.md",
            "Crear y asignar los grupos",
            "Conservar la agrupación del sistema anterior (`Grupo 1` a `Grupo 4`).",
            group_block(1, "0001", "Medicamentos éticos")
            + group_block(2, "0012", "OTC")
            + group_block(3, "0085", "Analgésicos")
            + group_block(4, "0170", "Siegfried"),
            intro="Por cada grupo se hacen tres llamadas: **consultar** si existe, **crearlo** solo si no existe y "
                  "**asignarlo** al producto. `Grupo 5 = 0695 NO APLICA` **no** se importa: no agrupa nada.",
        ),
        step(
            "13-verificar-resultado.md",
            "Verificar el resultado",
            "Comprobar que el producto quedó completo, elegible y que se encuentra por código y por atributos.",
            [
                call(
                    "Consultar el producto con todo su detalle",
                    "GET", f"{API}/products/<PRODUCTO>?expand=detail",
                    why=["`expand=detail` trae en una sola respuesta categorías, presentaciones, códigos, atributos, grupos y activos."],
                    show=["canonical_name", "status", "completeness", "eligible_for_adoption",
                          "detail.presentations[].code", "detail.presentations[].base_quantity",
                          "detail.identifiers[].value", "detail.identifiers[].is_primary"],
                ),
                call(
                    "Buscar por el segundo código de barras",
                    "GET", f"{API}/products/by-identifier/7707355052038",
                    why=["Simula el escaneo en caja: devuelve el producto **y la presentación** (la caja x 100)."],
                    show=["product.canonical_name", "presentation.code", "presentation.base_quantity", "identifier.value", "is_current"],
                ),
                call(
                    "Buscar por atributos filtrables",
                    "GET", f"{API}/products?attribute_filters=FORMA_FARMACEUTICA:TABLETA&attribute_filters=CONCENTRACION_MG:500",
                    why=["Solo funciona con atributos marcados `is_filterable: true`. En `OPTION` se filtra por el **código** de la opción."],
                    show=["items[].canonical_name", "total_records"],
                ),
            ],
            after="Resultado esperado: `is_complete: true` y `eligible_for_adoption: true`. Desde este momento una empresa "
                  "puede adoptar el producto en Commercial Relationship Service.",
        ),
    ],
)
