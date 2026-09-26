"""Ejercicio de docs/ejemplo/ (Principio XXII): datos de las llamadas y su justificación."""

from tests.examples.spec_common import API, call, get_group_type, get_manufacturer, get_packaging, get_unit, group_block, step

PRODUCT_SHOW = ["id", "version", "status", "canonical_name", "global_brand_id", "manufacturer_organization_id",
                "base_unit_id", "completeness", "eligible_for_adoption"]

TALLAS = [
    ("RN", "Recién nacido"), ("P", "Pequeña"), ("M", "Mediana"), ("G", "Grande"),
    ("XG", "Extra grande"), ("XXG", "Extra extra grande"), ("XXXG", "Triple extra grande"),
]


def talla(order, code, name):
    why = ["Talla del producto de este ejercicio (`XXXG` en el nombre del Excel)."] if code == "XXXG" else [
        "Completa la lista de tallas para los demás pañales del Excel (Huggies, Winny, Content…)."
    ]
    return call(
        f"Opción `{code}`",
        "POST", f"{API}/attribute-definitions/<ATR_TALLA_PANAL>/options",
        body={"code": code, "name": name, "display_order": order},
        why=why + (["`display_order` sigue el orden natural de tallas (de menor a mayor), no el alfabético."] if order == 1 else []),
        save={f"OPC_TALLA_{code}": "id"},
        show=["id", "code", "name", "display_order"],
    )


EX3 = dict(
    folder="3-panal-winny-gold-etapa-6",
    title="Ejercicio 3 — Pañal Winny Gold etapa 6 XXXG, paquete x 30",
    focus=(
        "Un dato que en el Excel solo está **dentro del nombre** (la talla `XXXG`) se convierte en un **atributo de lista "
        "(`OPTION`) filtrable**, con todas sus opciones ordenadas. Se termina **buscando productos por atributos**."
    ),
    excel_ids="17747",
    excel=[
        ("ID", "17747"),
        ("Código", "015721"),
        ("Referencia", "74865"),
        ("Nombre", "WINNY GOLD ETAPA 6 XXXG PAQUETEX30 TECNOQUIMICAS"),
        ("Nombre Tipo Producto", "PAÑALES"),
        ("Unidad Medida", "PAQUETE"),
        ("Contenido Interno", "30"),
        ("Talla / Nombre Talla", "0 / vacío"),
        ("Código Barras 1", "7701021118264 (EAN-13 válido)"),
        ("Código Barras 2", "7701021118912 (EAN-13 válido)"),
        ("Estado", "A"),
        ("Grupo 1 / 2 / 4", "0113 ASEO Y LIMPIEZA / 0691 PAÑALES / 0125 TECNOQUIMICAS (WINNY)"),
        ("Grupo 3 / 5 / 6", "0133 NO APLICA / 0695 NO APLICA / 0836 EXCLUIR VIERNES DAO"),
        ("% Impuesto", "19"),
    ],
    interpretation=[
        ("Qué es el producto", "\"Winny Gold pañal etapa 6 talla XXXG\"."),
        ("Marca / fabricante", "Marca `WINNY` (Gold es la línea, forma parte del nombre); fabricante Tecnoquímicas."),
        ("Talla", "Las columnas `Talla` y `Nombre Talla` vienen **vacías** en todo el Excel; la talla está en el nombre. "
         "Se crea el atributo `TALLA_PANAL` (`OPTION`) con todas las tallas."),
        ("Etapa", "`ETAPA_PANAL` = 6 (`INTEGER`)."),
        ("Unidad base", "`UND` = un pañal."),
        ("Presentación", "`PAQUETE_X30`: empaque `PACK`, factor 30 (`Contenido Interno = 30`)."),
        ("Categoría", "`CUIDADO_BEBE > PANALES_BEBE`."),
        ("Códigos de barras", "Dos EAN-13 válidos, ambos del paquete."),
        ("Grupos", "`GROUP_1` 0113, `GROUP_2` 0691, `GROUP_4` 0125. No se importan `NO APLICA` ni `EXCLUIR VIERNES DAO`."),
        ("No va al catálogo", "`% Impuesto = 19` (tributario, sin dueño definido aún), código interno, referencia, precios, stock."),
    ],
    steps=[
        step(
            "01-consultar-datos-base.md",
            "Consultar los datos base",
            "Obtener los `id` de la unidad, el empaque, los tipos de grupo y el fabricante (registrándolo si todavía no existe).",
            [
                get_unit("UND", "UND", ["El pañal se cuenta por unidades enteras: la unidad base es `UND`."]),
                get_packaging("PACK", "PACK", ["`Unidad Medida = PAQUETE` es un empaque: en el catálogo es `PACK`."]),
                get_group_type(1), get_group_type(2), get_group_type(4),
                *get_manufacturer("TECNOQUIMICAS", "FABRICANTE_TECNOQUIMICAS", "Tecnoquímicas", "Tecnoquímicas"),
            ],
        ),
        step(
            "02-crear-marca.md",
            "Crear la marca Winny",
            "Registrar la marca comercial.",
            [
                call(
                    "Crear la marca `WINNY`",
                    "POST", f"{API}/brands",
                    body={"code": "WINNY", "name": "Winny", "description": "Marca de pañales de Tecnoquímicas."},
                    why=[
                        "La marca es `WINNY`; \"Gold\" es una línea de la marca y queda en el nombre del producto.",
                        "El Excel lo confirma en `Grupo 4 = TECNOQUIMICAS (WINNY)`.",
                    ],
                    save={"MARCA_WINNY": "id"},
                    show=["id", "code", "name"],
                ),
            ],
            after="Si responde `409 DUPLICATE_CODE`, consulte `GET /api/v1/brands?code=WINNY` y use ese `id`.",
        ),
        step(
            "03-crear-categorias.md",
            "Crear las categorías",
            "Crear `CUIDADO_BEBE > PANALES_BEBE`.",
            [
                call(
                    "Crear la categoría raíz `CUIDADO_BEBE`",
                    "POST", f"{API}/categories",
                    body={"code": "CUIDADO_BEBE", "name": "Cuidado del bebé"},
                    why=["Raíz para pañales, pañitos y otros productos de bebé. El Excel los tiene en `ASEO Y LIMPIEZA`, "
                         "que es demasiado amplio para clasificar."],
                    save={"CAT_CUIDADO_BEBE": "id"},
                    show=["id", "code", "name", "parent_category_id"],
                ),
                call(
                    "Crear la subcategoría `PANALES_BEBE`",
                    "POST", f"{API}/categories",
                    body={"code": "PANALES_BEBE", "name": "Pañales para bebé", "parent_category_id": "<CAT_CUIDADO_BEBE>"},
                    why=[
                        "Sale de `Nombre Tipo Producto = PAÑALES`.",
                        "El código va **sin Ñ ni tildes** (`PANALES_BEBE`); el nombre sí las lleva.",
                        "Se separa de los pañales de adulto (Tena), que usan otras tallas.",
                    ],
                    save={"CAT_PANALES_BEBE": "id"},
                    show=["id", "code", "name", "parent_category_id"],
                ),
            ],
            after="Si alguna responde `409 DUPLICATE_CODE`, consúltela con `GET /api/v1/categories?code=<código>` y use su `id`.",
        ),
        step(
            "04-crear-atributos.md",
            "Crear los atributos y las opciones de talla",
            "Definir la talla como lista cerrada y la etapa como número.",
            [
                call(
                    "Crear el atributo `TALLA_PANAL` (lista de opciones)",
                    "POST", f"{API}/attribute-definitions",
                    body={"code": "TALLA_PANAL", "name": "Talla de pañal",
                          "description": "Talla del pañal según el peso del bebé.", "data_type": "OPTION"},
                    why=[
                        "`OPTION` porque las tallas son una lista fija. Con `TEXT` aparecerían \"XXXG\", \"XXX-G\", \"XXXL\" y no se podría filtrar.",
                        "El Excel tiene las columnas `Talla`/`Nombre Talla`, pero vacías: el dato hay que sacarlo del nombre.",
                    ],
                    save={"ATR_TALLA_PANAL": "id"},
                    show=["id", "code", "data_type"],
                ),
                *[talla(i + 1, code, name) for i, (code, name) in enumerate(TALLAS)],
                call(
                    "Crear el atributo `ETAPA_PANAL` (entero)",
                    "POST", f"{API}/attribute-definitions",
                    body={"code": "ETAPA_PANAL", "name": "Etapa del pañal",
                          "description": "Etapa de crecimiento indicada por el fabricante.", "data_type": "INTEGER"},
                    why=["`INTEGER`: \"ETAPA **6**\" en el nombre del Excel."],
                    save={"ATR_ETAPA_PANAL": "id"},
                    show=["id", "code", "data_type"],
                ),
            ],
        ),
        step(
            "05-asociar-atributos-a-la-categoria.md",
            "Asociar los atributos a la categoría",
            "La talla obligatoria y filtrable; la etapa opcional y filtrable.",
            [
                call(
                    "Asociar `TALLA_PANAL` (obligatorio y filtrable)",
                    "POST", f"{API}/categories/<CAT_PANALES_BEBE>/attributes",
                    body={"attribute_definition_id": "<ATR_TALLA_PANAL>", "is_required": True, "is_filterable": True, "display_order": 1},
                    why=["Todo pañal tiene talla: sin ella el producto queda incompleto.",
                         "Filtrable: es la búsqueda más habitual en punto de venta (\"pañales talla XXXG\")."],
                    save={"CA_TALLA_PANAL": "id"},
                    show=["id", "attribute_definition_id", "is_required", "is_filterable"],
                ),
                call(
                    "Asociar `ETAPA_PANAL` (opcional y filtrable)",
                    "POST", f"{API}/categories/<CAT_PANALES_BEBE>/attributes",
                    body={"attribute_definition_id": "<ATR_ETAPA_PANAL>", "is_required": False, "is_filterable": True, "display_order": 2},
                    why=["Opcional: no todas las marcas numeran etapas (Huggies usa etapas, otras solo talla)."],
                    save={"CA_ETAPA_PANAL": "id"},
                    show=["id", "attribute_definition_id", "is_required", "is_filterable"],
                ),
            ],
        ),
        step(
            "06-crear-producto.md",
            "Crear el producto",
            "Registrar el pañal.",
            [
                call(
                    "Crear el producto",
                    "POST", f"{API}/products",
                    body={
                        "product_type": "GOOD",
                        "canonical_name": "Winny Gold pañal etapa 6 talla XXXG",
                        "global_brand_id": "<MARCA_WINNY>",
                        "manufacturer_organization_id": "<FABRICANTE_TECNOQUIMICAS>",
                        "base_unit_id": "<UND>",
                    },
                    why=[
                        "La talla **sí** va en el nombre: un pañal XXXG y uno G son productos distintos (se compran por separado), "
                        "no presentaciones del mismo producto. Además queda en el atributo para poder filtrar.",
                        "No lleva `PAQUETEX30` (es la presentación) ni `TECNOQUIMICAS` (es el fabricante).",
                        "`description` se omite: es opcional.",
                    ],
                    save={"PRODUCTO": "id"},
                    show=PRODUCT_SHOW,
                ),
            ],
        ),
        step(
            "07-clasificar-producto.md",
            "Clasificar el producto",
            "Asignar `PANALES_BEBE`.",
            [
                call(
                    "Asignar la categoría `PANALES_BEBE`",
                    "POST", f"{API}/products/<PRODUCTO>/categories",
                    body={"global_category_id": "<CAT_PANALES_BEBE>"},
                    why=["Queda como principal por ser la primera."],
                    save={"PC_PANALES": "id"},
                    show=["id", "global_category_id", "is_primary"],
                ),
            ],
        ),
        step(
            "08-registrar-valores-de-atributos.md",
            "Registrar los valores de los atributos",
            "Talla XXXG y etapa 6.",
            [
                call(
                    "Talla = XXXG",
                    "PUT", f"{API}/products/<PRODUCTO>/attribute-values/<ATR_TALLA_PANAL>",
                    body={"option_id": "<OPC_TALLA_XXXG>"},
                    why=["Se envía el `id` de la opción `XXXG`, no el texto."],
                    show=["attribute_definition_id", "option_id", "version"],
                ),
                call(
                    "Etapa = 6",
                    "PUT", f"{API}/products/<PRODUCTO>/attribute-values/<ATR_ETAPA_PANAL>",
                    body={"integer_value": 6},
                    why=["`INTEGER` → `integer_value`."],
                    show=["attribute_definition_id", "integer_value", "version"],
                ),
            ],
        ),
        step(
            "09-crear-presentacion.md",
            "Crear la presentación",
            "Paquete x 30 pañales.",
            [
                call(
                    "Presentación `PAQUETE_X30`",
                    "POST", f"{API}/products/<PRODUCTO>/presentations",
                    body={"code": "PAQUETE_X30", "name": "Paquete x 30 pañales", "packaging_type_id": "<PACK>",
                          "base_quantity": 30, "display_order": 1, "is_base": False},
                    why=[
                        "`base_quantity: 30`: un paquete = 30 pañales (`Contenido Interno = 30`).",
                        "`is_base: false` y no se crea la presentación \"unidad\": el Excel no indica que el pañal se venda suelto. "
                        "Si una farmacia lo vendiera suelto, se agregaría después una presentación `UNIDAD` con `is_base: true` y `base_quantity: 1`.",
                    ],
                    save={"PRES_PAQUETE_X30": "id"},
                    show=["id", "code", "name", "packaging_type_id", "base_quantity", "is_base", "eligible_for_adoption"],
                ),
            ],
        ),
        step(
            "10-registrar-codigos-de-barras.md",
            "Registrar los códigos de barras",
            "Los dos EAN del paquete.",
            [
                call(
                    "EAN `7701021118264` (principal)",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "EAN", "value": "7701021118264",
                          "global_product_presentation_id": "<PRES_PAQUETE_X30>", "is_primary": True},
                    why=["`Código Barras 1` del Excel, EAN-13 válido. Se liga al paquete, que es lo que se escanea."],
                    save={"ID_EAN_1": "id"},
                    show=["id", "identifier_type", "value", "is_primary"],
                ),
                call(
                    "EAN `7701021118912`",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "EAN", "value": "7701021118912",
                          "global_product_presentation_id": "<PRES_PAQUETE_X30>", "is_primary": False},
                    why=["`Código Barras 2`. Mismo paquete, segundo código; no es principal."],
                    save={"ID_EAN_2": "id"},
                    show=["id", "identifier_type", "value", "is_primary"],
                ),
            ],
        ),
        step(
            "11-crear-y-asignar-grupos.md",
            "Crear y asignar los grupos",
            "Importar los grupos útiles.",
            group_block(1, "0113", "Aseo y limpieza")
            + group_block(2, "0691", "Pañales")
            + group_block(4, "0125", "Tecnoquímicas (Winny)"),
            intro="No se importan `Grupo 3 = 0133 NO APLICA`, `Grupo 5 = 0695 NO APLICA` ni `Grupo 6 = 0836 EXCLUIR VIERNES DAO` "
                  "(regla comercial de una empresa).",
        ),
        step(
            "12-verificar-y-buscar-por-atributos.md",
            "Verificar y buscar por atributos",
            "Comprobar el producto y usar los filtros por atributo.",
            [
                call(
                    "Consultar el producto",
                    "GET", f"{API}/products/<PRODUCTO>",
                    why=["Sin `expand` la respuesta es más liviana: basta para ver completitud y elegibilidad."],
                    show=["canonical_name", "completeness", "eligible_for_adoption"],
                ),
                call(
                    "Buscar pañales talla XXXG",
                    "GET", f"{API}/products?attribute_filters=TALLA_PANAL:XXXG",
                    why=["En atributos `OPTION` el filtro usa el **código** de la opción (`XXXG`), no su `id`."],
                    show=["items[].canonical_name", "total_records"],
                ),
                call(
                    "Buscar pañales talla XXXG de etapa 6 en la categoría",
                    "GET", f"{API}/products?category_id=<CAT_PANALES_BEBE>&attribute_filters=TALLA_PANAL:XXXG&attribute_filters=ETAPA_PANAL:6",
                    why=["Los filtros se combinan (todos deben cumplirse). `attribute_filters` se repite una vez por atributo."],
                    show=["items[].canonical_name", "total_records"],
                ),
                call(
                    "Error esperado: filtrar por un atributo no filtrable",
                    "GET", f"{API}/products?attribute_filters=NO_EXISTE:1",
                    expect=422,
                    why=["Si el atributo no existe o no es filtrable en ninguna categoría, responde `422 ATTRIBUTE_NOT_FILTERABLE`."],
                    show=["status", "code", "detail"],
                ),
            ],
        ),
    ],
)
