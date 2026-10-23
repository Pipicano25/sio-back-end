"""Ejercicio de docs/ejemplo/ (Principio XXII): datos de las llamadas y su justificación."""

from tests.examples.spec_common import API, call, get_group_type, get_manufacturer, get_packaging, get_unit, group_block, step

PRODUCT_SHOW = ["id", "version", "status", "canonical_name", "global_brand_id", "manufacturer_organization_id",
                "base_unit_id", "completeness", "eligible_for_adoption"]

DUREZAS = [("EXTRA_SUAVE", "Extra suave"), ("SUAVE", "Suave"), ("MEDIO", "Medio"), ("DURO", "Duro")]


def dureza(order, code, name):
    why = ["Dureza de este producto (\"EXTRA SUAVE\" en el nombre del Excel)."] if code == "EXTRA_SUAVE" else [
        "Completa la lista para los demás cepillos del Excel."
    ]
    return call(
        f"Opción `{code}`",
        "POST", f"{API}/attribute-definitions/<ATR_DUREZA_CERDAS>/options",
        body={"code": code, "name": name, "display_order": order},
        why=why + (["El código usa guion bajo (`EXTRA_SUAVE`); el nombre, texto legible."] if order == 1 else []),
        save={f"OPC_{code}": "id"},
        show=["id", "code", "name", "display_order"],
    )


EX5 = dict(
    folder="5-cepillo-colgate-inactivo",
    title="Ejercicio 5 — Cepillo Colgate infantil pack x 2 (producto inactivo)",
    focus=(
        "Un producto con `Estado = I` en el Excel: se carga **completo** y al final se **inactiva**. En el camino: un "
        "\"código de barras\" que en realidad es el **código interno** (no se registra), una **imagen** del producto "
        "(activo digital) y qué se puede y qué no se puede hacer sobre un producto inactivo."
    ),
    excel_ids="26396",
    excel=[
        ("ID", "26396"),
        ("Código", "022348"),
        ("Referencia", "NT"),
        ("Nombre", "CEPILLO COLGATE INFANTIL 2-5 AÑOS EXTRA SUAVE NIÑA PACK X2"),
        ("Nombre Tipo Producto", "CONSUMO"),
        ("Unidad Medida", "PACK"),
        ("Contenido Interno", "vacío"),
        ("Código Barras 1", "022348 (6 dígitos: **igual a la columna `Código`**)"),
        ("Estado", "**I** (es el único producto inactivo del Excel)"),
        ("Grupo 1 / 2 / 4", "0005 MEDICO QUIRURGICOS / 0016 DISPOSITIVOS MEDICOS / 0213 COLGATE PALMOLIVE"),
        ("Grupo 3 / 5", "0133 NO APLICA / 0695 NO APLICA"),
        ("% Impuesto", "19"),
    ],
    interpretation=[
        ("Qué es el producto", "\"Colgate cepillo dental infantil 2 a 5 años extra suave niña\"."),
        ("Marca / fabricante", "Marca `COLGATE`; fabricante Colgate-Palmolive (Party Identity)."),
        ("Unidad base", "`UND` = un cepillo."),
        ("Presentación", "`PACK_X2`: empaque `PACK`, factor 2. `Contenido Interno` viene vacío, pero el nombre dice `PACK X2`."),
        ("Categoría", "`CUIDADO_ORAL > CEPILLOS_DENTALES`. `Nombre Tipo Producto = CONSUMO` no describe qué es el producto."),
        ("Atributos", "Dureza de cerdas = Extra suave (`OPTION`) y rango de edad = \"2 a 5 años\" (`TEXT`)."),
        ("Código de barras", "**Ninguno**. `022348` es igual a la columna `Código` (código interno de la empresa) y no cumple GS1. "
         "Va a `CompanyProduct.internal_code` en Commercial Relationship Service."),
        ("Grupos", "`GROUP_1` 0005 y `GROUP_2` 0016 (los mismos del ejercicio 4) y `GROUP_4` 0213. Se importan **tal como vienen**, "
         "aunque un cepillo no es un dispositivo médico: ver nota en el paso 11."),
        ("Estado `I`", "Se carga todo y se inactiva al final (paso 12)."),
    ],
    steps=[
        step(
            "01-consultar-datos-base.md",
            "Consultar los datos base",
            "Obtener los `id` de la unidad, el empaque, los tipos de grupo y el fabricante (registrándolo si todavía no existe).",
            [
                get_unit("UND", "UND", ["Los cepillos se cuentan por unidades enteras."]),
                get_packaging("PACK", "PACK", ["`Unidad Medida = PACK` → empaque `PACK`."]),
                get_group_type(1), get_group_type(2), get_group_type(4),
                *get_manufacturer("COLGATE", "FABRICANTE_COLGATE", "Colgate-Palmolive", "Colgate-Palmolive"),
            ],
        ),
        step(
            "02-crear-marca.md",
            "Crear la marca Colgate",
            "Registrar la marca comercial.",
            [
                call(
                    "Crear la marca `COLGATE`",
                    "POST", f"{API}/brands",
                    body={"code": "COLGATE", "name": "Colgate"},
                    why=["La marca es Colgate; el fabricante es Colgate-Palmolive (`Grupo 4`). Aquí coinciden en nombre, "
                         "pero siguen siendo datos distintos: la marca es del catálogo y el fabricante de Party Identity."],
                    save={"MARCA_COLGATE": "id"},
                    show=["id", "code", "name"],
                ),
            ],
            after="Si responde `409 DUPLICATE_CODE`, consulte `GET /api/v1/brands?code=COLGATE` y use ese `id`.",
        ),
        step(
            "03-crear-categorias.md",
            "Crear las categorías",
            "Crear `CUIDADO_ORAL > CEPILLOS_DENTALES`.",
            [
                call(
                    "Crear la categoría raíz `CUIDADO_ORAL`",
                    "POST", f"{API}/categories",
                    body={"code": "CUIDADO_ORAL", "name": "Cuidado oral"},
                    why=["`CONSUMO` en el Excel mezcla miles de productos distintos; la categoría debe decir qué es el producto."],
                    save={"CAT_CUIDADO_ORAL": "id"},
                    show=["id", "code", "name", "parent_category_id"],
                ),
                call(
                    "Crear la subcategoría `CEPILLOS_DENTALES`",
                    "POST", f"{API}/categories",
                    body={"code": "CEPILLOS_DENTALES", "name": "Cepillos dentales", "parent_category_id": "<CAT_CUIDADO_ORAL>"},
                    why=["Hoja donde se clasifica el producto y donde se asocian sus atributos."],
                    save={"CAT_CEPILLOS": "id"},
                    show=["id", "code", "name", "parent_category_id"],
                ),
            ],
            after="Si alguna responde `409 DUPLICATE_CODE`, consúltela con `GET /api/v1/categories?code=<código>` y use su `id`.",
        ),
        step(
            "04-crear-atributos.md",
            "Crear los atributos",
            "Dureza de las cerdas (lista) y rango de edad (texto).",
            [
                call(
                    "Crear el atributo `DUREZA_CERDAS` (lista de opciones)",
                    "POST", f"{API}/attribute-definitions",
                    body={"code": "DUREZA_CERDAS", "name": "Dureza de las cerdas",
                          "description": "Firmeza de las cerdas del cepillo.", "data_type": "OPTION"},
                    why=["Valores cerrados y conocidos: extra suave, suave, medio, duro."],
                    save={"ATR_DUREZA_CERDAS": "id"},
                    show=["id", "code", "data_type"],
                ),
                *[dureza(i + 1, code, name) for i, (code, name) in enumerate(DUREZAS)],
                call(
                    "Crear el atributo `RANGO_EDAD` (texto)",
                    "POST", f"{API}/attribute-definitions",
                    body={"code": "RANGO_EDAD", "name": "Rango de edad",
                          "description": "Edad recomendada de uso indicada por el fabricante.", "data_type": "TEXT"},
                    why=["`TEXT` porque cada fabricante expresa el rango a su manera (\"2-5 años\", \"6+ años\", \"0-2 años\")."],
                    save={"ATR_RANGO_EDAD": "id"},
                    show=["id", "code", "data_type"],
                ),
            ],
        ),
        step(
            "05-asociar-atributos-a-la-categoria.md",
            "Asociar los atributos a la categoría",
            "Dureza obligatoria y filtrable; rango de edad opcional.",
            [
                call(
                    "Asociar `DUREZA_CERDAS`",
                    "POST", f"{API}/categories/<CAT_CEPILLOS>/attributes",
                    body={"attribute_definition_id": "<ATR_DUREZA_CERDAS>", "is_required": True, "is_filterable": True, "display_order": 1},
                    why=["Todo cepillo declara su dureza."],
                    save={"CA_DUREZA": "id"},
                    show=["id", "attribute_definition_id", "is_required", "is_filterable"],
                ),
                call(
                    "Asociar `RANGO_EDAD`",
                    "POST", f"{API}/categories/<CAT_CEPILLOS>/attributes",
                    body={"attribute_definition_id": "<ATR_RANGO_EDAD>", "is_required": False, "is_filterable": False, "display_order": 2},
                    why=["Opcional: los cepillos de adulto no indican edad."],
                    save={"CA_RANGO_EDAD": "id"},
                    show=["id", "attribute_definition_id", "is_required", "is_filterable"],
                ),
            ],
        ),
        step(
            "06-crear-producto.md",
            "Crear el producto",
            "Registrar el cepillo **activo**, aunque el Excel diga `I`.",
            [
                call(
                    "Crear el producto",
                    "POST", f"{API}/products",
                    body={
                        "product_type": "GOOD",
                        "canonical_name": "Colgate cepillo dental infantil 2 a 5 años extra suave niña",
                        "global_brand_id": "<MARCA_COLGATE>",
                        "manufacturer_organization_id": "<FABRICANTE_COLGATE>",
                        "base_unit_id": "<UND>",
                    },
                    why=[
                        "El cuerpo **no admite** `status`: todo producto nace `ACTIVE`. El estado se cambia con acciones "
                        "(`/deactivate`, `/reactivate`), no con un campo.",
                        "Se inactiva **al final** porque sobre un producto inactivo no se pueden agregar categorías, "
                        "presentaciones, atributos ni grupos (`422 PRODUCT_INACTIVE`). Se carga completo primero para que "
                        "la información quede íntegra si algún día se reactiva.",
                        "\"NIÑA\" se conserva en el nombre: el diseño niña y el diseño niño son productos distintos con códigos distintos.",
                    ],
                    save={"PRODUCTO": "id"},
                    show=PRODUCT_SHOW,
                ),
            ],
        ),
        step(
            "07-clasificar-y-registrar-atributos.md",
            "Clasificar y registrar atributos",
            "Asignar la categoría y dar valor a los atributos.",
            [
                call(
                    "Asignar la categoría `CEPILLOS_DENTALES`",
                    "POST", f"{API}/products/<PRODUCTO>/categories",
                    body={"global_category_id": "<CAT_CEPILLOS>"},
                    why=["Primera categoría → principal. Debe ir **antes** de los atributos: un atributo solo se puede registrar "
                         "si alguna categoría del producto lo usa (si no, `422 ATTRIBUTE_NOT_APPLICABLE`)."],
                    save={"PC_CEPILLOS": "id"},
                    show=["id", "global_category_id", "is_primary"],
                ),
                call(
                    "Dureza = Extra suave",
                    "PUT", f"{API}/products/<PRODUCTO>/attribute-values/<ATR_DUREZA_CERDAS>",
                    body={"option_id": "<OPC_EXTRA_SUAVE>"},
                    why=["`OPTION` → `option_id`."],
                    show=["attribute_definition_id", "option_id"],
                ),
                call(
                    "Rango de edad = 2 a 5 años",
                    "PUT", f"{API}/products/<PRODUCTO>/attribute-values/<ATR_RANGO_EDAD>",
                    body={"text_value": "2 a 5 años"},
                    why=["Aunque es opcional, el dato existe en el nombre del Excel (`2-5 AÑOS`) y se registra."],
                    show=["attribute_definition_id", "text_value"],
                ),
            ],
        ),
        step(
            "08-crear-presentacion.md",
            "Crear la presentación",
            "Pack x 2 cepillos.",
            [
                call(
                    "Presentación `PACK_X2`",
                    "POST", f"{API}/products/<PRODUCTO>/presentations",
                    body={"code": "PACK_X2", "name": "Pack x 2 cepillos", "packaging_type_id": "<PACK>",
                          "base_quantity": 2, "display_order": 1, "is_base": False},
                    why=[
                        "`base_quantity: 2` sale del nombre (`PACK X2`); la columna `Contenido Interno` vino vacía.",
                        "No se crea presentación unidad: el pack no se abre para vender cepillos sueltos.",
                    ],
                    save={"PRES_PACK_X2": "id"},
                    show=["id", "code", "name", "packaging_type_id", "base_quantity", "is_base"],
                ),
            ],
        ),
        step(
            "09-codigo-interno-no-es-codigo-de-barras.md",
            "El código `022348` no se registra",
            "Entender por qué el \"código de barras\" del Excel no va al catálogo.",
            [
                call(
                    "Error esperado: registrarlo como EAN",
                    "POST", f"{API}/products/<PRODUCTO>/identifiers",
                    body={"identifier_type": "EAN", "value": "022348",
                          "global_product_presentation_id": "<PRES_PACK_X2>"},
                    expect=422,
                    why=[
                        "Un EAN/GTIN tiene 8, 12, 13 o 14 dígitos. `022348` tiene 6: responde `422 INVALID_GTIN_FORMAT`.",
                        "Este error es **la señal** de que el dato no es un código de barras real.",
                    ],
                    show=["status", "code", "detail"],
                ),
                call(
                    "Confirmar que el producto no tiene identificadores",
                    "GET", f"{API}/products/<PRODUCTO>/identifiers",
                    why=["Un producto **puede estar completo sin códigos de barras**: la completitud no los exige."],
                    show=[],
                ),
            ],
            intro=(
                "`Código Barras 1 = 022348` es **exactamente** la columna `Código` de la misma fila: el sistema anterior copió "
                "el código interno en el campo de código de barras.\n\n"
                "¿Por qué no registrarlo como `BARCODE` u `OTHER`, que sí lo aceptarían?\n\n"
                "- El catálogo es **global** (compartido por todas las empresas). `022348` solo significa algo dentro de "
                "la empresa que exportó el Excel; en otra empresa ese número es otro producto.\n"
                "- `BARCODE` exige unicidad global: el código interno de una empresa bloquearía ese valor para todas.\n"
                "- Su lugar es `CompanyProduct.internal_code` en Commercial Relationship Service, cuando la empresa adopte el producto."
            ),
        ),
        step(
            "10-agregar-imagen.md",
            "Agregar la imagen de la presentación",
            "Cargar la foto del pack x 2 y dejarla como imagen principal de esa presentación (spec 024).",
            [
                call(
                    "Cargar la imagen de la presentación",
                    "POST", f"{API}/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/upload",
                    upload={"file_name": "colgate-cepillo-infantil-2-5-nina-pack-x2.png", "content": "png",
                            "color": [40, 120, 200]},
                    why=[
                        "El Excel no trae imágenes: la foto de este paso es **ficticia** (un PNG generado) y solo "
                        "muestra cómo se carga una.",
                        "Las imágenes pertenecen a una **presentación**, no al producto: cada presentación puede "
                        "tener su propia foto. Esta es la del pack x 2.",
                        "Se envía el archivo (`multipart/form-data`, campo `file`). El catálogo lo guarda en el "
                        "almacenamiento de SIO y responde sin exponer bucket ni clave: `content_url` (con token) e "
                        "`image_url` (URL pública firmada, o `null` si está deshabilitada).",
                        "La última imagen cargada queda **principal** automáticamente.",
                        "El tipo se toma del **contenido** (JPEG, PNG o WebP); la extensión y el tipo declarado se ignoran.",
                    ],
                    save={"ACTIVO_IMAGEN": "id"},
                    show=["id", "global_product_presentation_id", "asset_type", "file_name", "mime_type", "is_primary",
                          "status", "content_url"],
                ),
                call(
                    "Error esperado: cargar otra vez el mismo archivo",
                    "POST", f"{API}/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/upload",
                    upload={"file_name": "copia-del-mismo-archivo.png", "content": "png", "color": [40, 120, 200]},
                    expect=409,
                    why=["El catálogo compara el **contenido** (SHA-256), no el nombre: la presentación ya tiene esa "
                         "imagen. `existing_asset_id` dice cuál es; no se crea otra ni se vuelve a guardar el archivo."],
                    show=["status", "code", "existing_asset_id"],
                ),
                call(
                    "Cargar una segunda imagen (foto lateral)",
                    "POST", f"{API}/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/upload",
                    upload={"file_name": "colgate-cepillo-infantil-pack-x2-lateral.png", "content": "png",
                            "color": [230, 90, 150]},
                    why=["Una presentación puede tener varias imágenes. La recién cargada pasa a ser la principal; "
                         "la anterior sigue `ACTIVE` como secundaria."],
                    save={"ACTIVO_IMAGEN_2": "id", "VERSION_IMAGEN_2": "version"},
                    show=["id", "file_name", "is_primary", "status"],
                ),
                call(
                    "Listar las imágenes de la presentación",
                    "GET", f"{API}/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets",
                    why=["Solo las `ACTIVE`, la principal primero. Para ver las eliminadas: `?status=INACTIVE`."],
                    show=["[].id", "[].file_name", "[].is_primary", "[].status"],
                ),
                call(
                    "Eliminar la segunda imagen",
                    "POST", f"{API}/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/<ACTIVO_IMAGEN_2>/deactivate",
                    body={"version": "<VERSION_IMAGEN_2>"},
                    why=["La eliminación es lógica: la imagen queda `INACTIVE` y el archivo **no** se borra del "
                         "almacenamiento.",
                         "Era la principal, así que la imagen `ACTIVE` más reciente (la foto del frente) vuelve a "
                         "serlo automáticamente.",
                         "Exige `perm:product-catalog:products:deactivate`."],
                    save={"VERSION_IMAGEN_2": "version"},
                    show=["id", "is_primary", "status", "version"],
                ),
                call(
                    "Reactivar la segunda imagen",
                    "POST", f"{API}/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/<ACTIVO_IMAGEN_2>/reactivate",
                    body={"version": "<VERSION_IMAGEN_2>"},
                    why=["Vuelve a `ACTIVE`, pero **no** se marca como principal: la principal sigue siendo la del frente."],
                    save={"VERSION_IMAGEN_2": "version"},
                    show=["id", "is_primary", "status", "version"],
                ),
                call(
                    "Marcar la segunda imagen como principal",
                    "POST", f"{API}/products/<PRODUCTO>/presentations/<PRES_PACK_X2>/assets/<ACTIVO_IMAGEN_2>/set-primary",
                    body={"version": "<VERSION_IMAGEN_2>"},
                    why=["La principal anterior deja de serlo en la misma operación: nunca hay dos.",
                         "El contenido de cada imagen se descarga con su `content_url` (con token) o se muestra con "
                         "`image_url` en `<img src>`."],
                    show=["id", "is_primary", "status", "version"],
                ),
                call(
                    "Error esperado: registrar la imagen en el producto",
                    "POST", f"{API}/products/<PRODUCTO>/assets",
                    body={
                        "asset_type": "IMAGE",
                        "file_name": "colgate-cepillo-infantil-2-5-nina-pack-x2.jpg",
                        "storage_uri": "s3://sio-product-catalog/productos/colgate-cepillo-infantil-2-5-nina-pack-x2.jpg",
                        "mime_type": "image/jpeg",
                        "is_primary": True,
                    },
                    expect=422,
                    why=["Los productos no tienen imágenes directas: `422 IMAGE_REQUIRES_PRESENTATION`. Las fichas "
                         "técnicas, manuales y certificados sí se siguen registrando en el producto."],
                    show=["status", "code", "detail"],
                ),
            ],
        ),
        step(
            "11-crear-y-asignar-grupos.md",
            "Crear y asignar los grupos",
            "Conservar la agrupación del sistema anterior.",
            group_block(1, "0005", "Médico quirúrgicos")
            + group_block(2, "0016", "Dispositivos médicos")
            + group_block(4, "0213", "Colgate-Palmolive"),
            intro=(
                "`0005` y `0016` también los usa el ejercicio 4. Si ya lo ejecutó, la consulta los encuentra y **no** se crean de nuevo.\n\n"
                "**Nota de calidad de datos:** el Excel clasifica este cepillo en `MEDICO QUIRURGICOS / DISPOSITIVOS MEDICOS`, lo cual no es "
                "correcto. Los grupos se importan tal como vienen porque representan la agrupación del sistema anterior; la clasificación "
                "correcta la da la **categoría** (`CEPILLOS_DENTALES`). Corregir los grupos es una decisión del negocio: se puede hacer "
                "después inactivando la asignación (`POST /products/{id}/group-assignments/{id}/deactivate`)."
            ),
        ),
        step(
            "12-inactivar-producto.md",
            "Inactivar el producto (`Estado = I`)",
            "Comprobar que quedó completo y luego inactivarlo.",
            [
                call(
                    "Consultar el producto antes de inactivar",
                    "GET", f"{API}/products/<PRODUCTO>",
                    why=["Se necesita la `version` actual: la inactivación la exige para evitar pisar un cambio de otra persona "
                         "(si no coincide, `409 VERSION_CONFLICT`).",
                         "Se ve que está completo y elegible."],
                    show=["version", "status", "completeness", "eligible_for_adoption"],
                ),
                call(
                    "Inactivar",
                    "POST", f"{API}/products/<PRODUCTO>/deactivate",
                    body={"version": 1},
                    why=[
                        "`version` es la que devolvió la consulta anterior (aquí `1`: asignar categorías, presentaciones o "
                        "códigos no cambia la versión del producto; solo la cambian `PUT` y las acciones de estado).",
                        "**No hay cascada**: presentaciones, códigos, grupos e imagen siguen `ACTIVE`.",
                        "El producto sigue `is_complete: true`, pero `eligible_for_adoption: false`: ninguna empresa lo puede adoptar.",
                    ],
                    show=["version", "status", "completeness", "eligible_for_adoption"],
                ),
            ],
        ),
        step(
            "13-verificar-producto-inactivo.md",
            "Verificar el comportamiento del producto inactivo",
            "Ver qué se puede y qué no se puede hacer con un producto inactivo.",
            [
                call(
                    "Error esperado: agregar una presentación",
                    "POST", f"{API}/products/<PRODUCTO>/presentations",
                    body={"code": "UNIDAD", "name": "Cepillo individual", "base_quantity": 1, "is_base": True},
                    expect=422,
                    why=["Sobre un producto inactivo solo se consultan o inactivan sus elementos: `422 PRODUCT_INACTIVE`."],
                    show=["status", "code", "detail"],
                ),
                call(
                    "Buscar productos inactivos",
                    "GET", f"{API}/products?status=INACTIVE&search=cepillo",
                    why=["Los inactivos se siguen consultando: el filtro `status` los separa de los activos."],
                    show=["items[].canonical_name", "items[].status", "total_records"],
                ),
                call(
                    "Consultar el detalle",
                    "GET", f"{API}/products/<PRODUCTO>?expand=detail",
                    why=["Toda la información se conserva. Si se reactiva (`POST /products/{id}/reactivate` con la `version` actual), "
                         "vuelve a ser elegible sin recargar nada."],
                    show=["status", "eligible_for_adoption", "detail.presentations[].code", "detail.presentations[].status",
                          "detail.identifiers"],
                ),
            ],
        ),
        step(
            "14-consultas-por-lotes.md",
            "Consultar el producto por lotes y por filtros (spec 022)",
            "Ver el resumen del catálogo de un lote de productos y buscar productos por marca, para consumidores como "
            "el servicio de consultas consolidadas.",
            [
                call(
                    "Resumen del producto por lotes",
                    "POST", f"{API}/products/summaries/batch-lookup",
                    body={"ids": ["<PRODUCTO>"]},
                    why=[
                        "Hasta 100 productos en una llamada: nombre canónico, marca, unidad base, categorías e "
                        "identificadores `ACTIVE`, sin pedir cada producto por separado.",
                        "Las imágenes **no** vienen en este resumen: pertenecen a las presentaciones y se consultan "
                        "por presentación (`POST /presentations/batch-lookup`, siguiente llamada).",
                    ],
                    show=["items[].found", "items[].canonical_name", "items[].status", "items[].brand",
                          "items[].base_unit", "items[].categories", "items[].identifiers"],
                ),
                call(
                    "Imagen de la presentación por lotes",
                    "POST", f"{API}/presentations/batch-lookup?include_images=true",
                    body={"ids": ["<PRES_PACK_X2>"]},
                    why=[
                        "Cada presentación trae su imagen principal: `has_image`, `image_asset_id` e `image_url`.",
                        "Con `include_images=true` agrega `images[]` con todas sus imágenes `ACTIVE`, la principal primero.",
                    ],
                    show=["items[].code", "items[].has_image", "items[].image_asset_id", "items[].images[].is_primary"],
                ),
                call(
                    "Productos de la marca, incluidos los inactivos",
                    "POST", f"{API}/products/match",
                    body={"brand_ids": ["<MARCA_COLGATE>"], "status": "ALL", "limit": 20},
                    why=[
                        "Modo conductor: los productos que cumplen los filtros en orden de nombre canónico normalizado e "
                        "`id`, de a `limit`. Cada uno trae su `position` para seguir con `after`.",
                        "Por defecto `status` es `ACTIVE`; el cepillo está inactivo, por eso se pide `ALL`.",
                        "No hay conteos: `has_more` dice si quedan productos.",
                    ],
                    show=["items[].id", "items[].position", "has_more"],
                ),
                call(
                    "¿El cepillo tiene alguna presentación con imagen?",
                    "POST", f"{API}/products/match",
                    body={"candidate_ids": ["<PRODUCTO>"], "has_image": True, "status": "ALL"},
                    why=["Modo evaluador: devuelve los candidatos que cumplen. `has_image: true` significa \"al menos "
                         "una presentación con imagen principal `ACTIVE`\": es solo una condición de búsqueda."],
                    show=["ids"],
                ),
            ],
        ),
    ],
)
