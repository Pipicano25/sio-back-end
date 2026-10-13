# Preparación de datos para SIO (data-migration)

Prepara la información de una empresa para cargarla en SIO con la arquitectura **Medallion**. Los datos de cada
empresa se normalizan en CSV estándar, se validan contra los contratos reales de los microservicios y solo lo
validado queda listo para el cargue. Esta herramienta **no escribe en SIO**: el cargue es una tarea aparte.

## 1. Arquitectura

| Capa | Contenido | Regla |
|---|---|---|
| **Bronze** | Archivos originales del cliente | Copia exacta, en solo lectura y con SHA-256 registrado. Nunca se modifica. |
| **Silver** | 27 CSV normalizados con **todos** los registros | Cada fila tiene `migration_status` (`PENDIENTE`, `VALIDADO` o `CONFLICTO`) y su motivo. Nada se descarta: lo pendiente queda en Silver. |
| **Gold** | Los mismos 27 CSV, solo con filas `VALIDADO` | Cada fila es idéntica a su fila de Silver y tiene integridad referencial completa. Es lo único cargable. |

## 2. Estructura

```text
tools/data-migration/
├── README.md
├── ia-tools/
│   ├── sio_query.py        consultas de solo lectura (GET) a las API de SIO
│   └── validate_csv.py     validación de los CSV de una empresa
├── templates/
│   ├── schemas/<entidad>.schema.json   27 esquemas Table Schema (iguales para Silver, Gold y toda empresa)
│   └── required_information.xlsx       plantilla de información requerida
└── <EMPRESA>/              datos privados, NO versionados (una línea en .gitignore por empresa)
    ├── bronze/             archivos originales
    ├── silver/             27 CSV con todos los registros
    ├── gold/               27 CSV con solo lo validado
    ├── assets/             imágenes <sha256>.<ext>
    └── reports/            estado por registro, evidencia, faltantes, resumen, decisiones pendientes y respaldos
```

`.venv/` es el entorno local de Python y no se versiona.

## 3. Entorno

Se necesita Python 3.12 o superior (el entorno actual usa 3.13). Las herramientas solo dependen de `frictionless`
y `requests`.

```bash
cd tools/data-migration
python3 -m venv .venv
.venv/bin/pip install "frictionless==5.20.0" "requests==2.34.2"
```

`sio_query.py` obtiene el token con `obtener_token(rol)` de `services/get_token.py`, sin duplicar la autenticación.
La contraseña de los usuarios de prueba se lee de `KEYCLOAK_TEST_USER_PASSWORD` (entorno o `infrastructure/.env`).
El token solo vive en memoria: nunca se imprime ni se guarda.

Los servicios deben publicar `/openapi.json` (`SIO_DOCS_ENABLED`). Si no lo hacen, `sio_query.py` se detiene con un
mensaje claro.

## 4. Herramientas

### `sio_query.py`: consultar SIO (solo lectura)

Valida cada ruta y cada parámetro contra el OpenAPI publicado por el servicio. Rechaza rutas inventadas y cualquier
operación que no sea GET.

```bash
# Operaciones GET disponibles en un servicio y sus parámetros
.venv/bin/python ia-tools/sio_query.py product-catalog --list

# Consulta concreta (los parámetros de ruta y de consulta se pasan con --param)
.venv/bin/python ia-tools/sio_query.py product-catalog /api/v1/products/by-identifier/{value} --param value=07702031244486
.venv/bin/python ia-tools/sio_query.py product-catalog /api/v1/categories --param code=MEDICAMENTO --all-pages
```

- **Servicios:** audit, commercial-relationship, geography, inventory, operational-context, party-identity,
  payment-reference, product-catalog, purchase y sales. Los puertos se leen de `infrastructure/.env`.
- **Salida:** el JSON va a stdout y `HTTP <código>` a stderr. El rol por defecto es `consulta` (`--rol` lo cambia).
- **Uso desde Python:** `SioQuery(rol).get(servicio, ruta, params, all_pages)`.

### `validate_csv.py`: validar una empresa

```bash
.venv/bin/python ia-tools/validate_csv.py DAO --layer silver --sio
.venv/bin/python ia-tools/validate_csv.py DAO --layer gold --sio
```

**Qué comprueba:**

1. **Frictionless (Table Schema):**
   - encabezados, tipos y obligatorios;
   - valores permitidos, patrones, longitudes y mínimos;
   - claves primarias y claves foráneas entre los 27 CSV.
2. **Reglas declaradas en cada esquema**, que Frictionless no aplica:
   - `uniqueKeys` (unicidad compuesta);
   - `sio.rules`: `positive`, `one_true`, `unique_where`, `check_where`, `same_parent`, `exactly_one_of`, `catalog`,
     `catalog_or_file`, `file_hash` y `gold_requires`. Reflejan las restricciones reales de los servicios: una
     presentación base, un identificador principal por producto, presentación y tipo, GTIN y BARCODE únicos, IUM
     con presentación y único, imágenes con su SHA-256…
3. **En Gold:** todas las filas en `VALIDADO` e idénticas a su fila de Silver.
4. **Con `--sio`:** los códigos de catálogos globales (unidades, tipos de empaque, tipos de grupo…) se comparan con
   SIO por GET.

**Resultado:** un JSON con `errores`, `errores_por_control` y `pendientes_esperados`. En Silver, los problemas de
filas `PENDIENTE` o `CONFLICTO` cuentan como pendientes esperados; los de filas `VALIDADO` son errores. Termina con
código 1 si hay errores. No modifica archivos.

## 5. Esquemas CSV (`templates/schemas/`)

Hay un esquema por entidad de SIO, más `source_classifications`:

- **Organizaciones y empresa:** `organization_identities`, `companies`, `branches`.
- **Catálogos:** `packaging_types`, `brands`, `categories`, `groups`, `attribute_definitions`, `category_attributes`.
- **Producto:** `products`, `product_presentations`, `product_identifiers`, `product_assets`, `product_categories`,
  `product_group_assignments`, `product_attribute_values`.
- **Producto de empresa:** `company_products`, `company_product_presentations`.
- **Compras y precios:** `company_suppliers`, `supplier_payment_conditions`, `supplier_products`, `price_lists`,
  `price_list_items`, `purchase_sequences`, `purchases`, `purchase_details`.
- **Evidencia:** `source_classifications`.

**Cada esquema indica:**

- los campos, con su tipo, obligatoriedad y valores permitidos;
- la clave primaria (`<entidad>_ref`) y las claves foráneas;
- un bloque `sio` con el servicio, el endpoint y el contrato de origen, la identidad natural y las reglas.

**Columnas comunes a todos los CSV:**

| Columna | Significado |
|---|---|
| `<entidad>_ref` | Referencia local estable. Se asigna una vez y no se recalcula. Las relaciones entre CSV usan `*_ref`. |
| `sio_id` | UUID existente en SIO, verificado por API. Vacío si aún no existe; nunca se inventa. |
| `source_ref` | Origen: `<archivo>#<hoja>#<fila>` (varios separados por ` \| `), `CONTEXTO` o `DECISION:<id>`. |
| `migration_status` | `PENDIENTE` (falta un dato o una decisión), `VALIDADO` (listo para Gold) o `CONFLICTO` (evidencia contradictoria). |
| `status_reason` | Qué falta o qué conflicto hay. En Gold, `DEPENDENCIA: …` marca filas válidas que **no son cargables** hasta resolver algo en SIO (p. ej. crear un tipo de empaque nuevo o desplegar el tipo de identificador IUM). |

Los catálogos globales de SIO (unidades, tipos de empaque existentes, tipos de grupo, tipos de condición de pago,
país y ciudad) se referencian por `*_code` y **no** tienen CSV.

**Formatos de referencia:**

| Entidad | Formato |
|---|---|
| Organización | `ORG-<ISO3>-<tipo>-<número>` |
| Empresa | `CMP-<EMPRESA>` |
| Sede | `BRN-<EMPRESA>-<código>` |
| Marca | `BRD-<código>` |
| Producto | `PRD-GTIN-…`, `PRD-INVIMA-…`, `PRD-REG-…` o `PRD-SRC-<EMPRESA>-…` |
| Presentación | `PRS-<sufijo del producto>-<código>` |
| Identificador | `IDN-<tipo>-<valor>` |
| Imagen | `AST-<sufijo>-<sha12>` |
| Producto y presentación de empresa | `CPR-…` y `CPP-…` |
| Tipo de empaque · categoría · grupo · atributo | `PKG-<código>` · `CAT-<código>` · `GRP-<GROUP_n>-<código>` · `ATR-<código>` |
| Asignaciones | `PCT-…`, `PGA-…`, `CTA-…`, `PAV-…` |
| Clasificación original | `SCL-…` |

**Clasificación (`classification_level`):**

- `VERIFICADA`: un registro oficial confirma la categoría. Es la única que pasa a Gold.
- `PROPUESTA`: solo la indica la clasificación del cliente, p. ej. la condición de venta del POS.
- `AMBIGUA`: evidencia contradictoria.
- `PENDIENTE`.

## 6. Reglas vigentes de preparación

- **Productos:**
  - se identifican por sus identificadores globales (GTIN, BARCODE, IUM), **nunca por nombre**;
  - no se fusionan productos distintos ni se duplican por diferencias de presentación;
  - un GTIN distinto no implica por sí solo un producto distinto.
- **Fabricante:** si no hay un fabricante real verificado se usa `ORG-COL-INTERNAL_CODE-GENERIC_MANUFACTURER`
  (FABRICANTE GENERICO). Nunca se inventan fabricantes.
- **Precios y costos:** vacío significa dato faltante, **nunca 0**. No se generan valores simulados sin aprobación.
- **Categorías:** taxonomía global de SIO (principales y subcategorías), no la de un cliente. Las clasificaciones
  originales del cliente (tipos, grupos, líneas) se guardan por registro en `source_classifications.csv` y nunca se
  cargan. Los grupos del cliente no se cargan como grupos globales, y los tipos `GROUP_n` no se renombran.
- **Atributos:** se asocian a una categoría por su concepto, no porque un producto tenga el dato. En SIO no se
  heredan entre categorías. Solo se usan valores de fuentes oficiales.
- **Empaques:**
  - se reutiliza el tipo de SIO equivalente; solo se proponen tipos nuevos cuando no existe ninguno;
  - las formas del producto (barra), las cantidades (par) y las unidades (galón) no son empaques.
- **IUM:** identifica la presentación comercial. Usa `identifier_type = IUM`, siempre con presentación, con formato
  `^[0-9][A-Z][0-9]{13}$` y único en todo el catálogo (spec 018 de Product Catalog, migración `0004`).
- **Fuentes externas:** no se vuelven a consultar si la evidencia ya existe, y no se descargan imágenes nuevas sin
  autorización.

## 7. Información faltante

`templates/required_information.xlsx` es la plantilla estándar:

- **Escenario B (principal):** la empresa ya entregó archivos. Se genera `<EMPRESA>/reports/missing_information.xlsx`
  con dos hojas:
  - **Faltantes**, con la columna `clasificacion`: `OBLIGATORIA_DAO`, `RECOMENDADA_DAO`, `PENDIENTE_APROBACION`,
    `NO_APLICA`, `SIMULADA_AUTORIZADA`;
  - **Opcionales**, por ejemplo imágenes, que no bloquean.

  El cliente solo diligencia `valor_solicitado`. Con `empresa`, `entidad`, `ref`, `source_ref` y `campo`, la
  respuesta se incorpora a la fila de Silver correcta sin perder referencias. Antes de pedir un dato se aprovecha la
  información existente (Bronze, Silver y evidencias), y las pistas se anotan en `observaciones`.
- **Escenario A:** la empresa entrega su información desde cero, con una hoja por entidad. Las columnas en rojo son
  obligatorias, la fila 2 describe cada campo y hay listas de valores permitidos.

## 8. Empresa nueva

1. Crear `<EMPRESA>/{bronze,silver,gold,assets,reports}` y agregar `tools/data-migration/<EMPRESA>/` a `.gitignore`.
2. Copiar los archivos originales a `bronze/` (solo lectura) y registrar su SHA-256.
3. Llenar los 27 CSV de `silver/` con los esquemas de `templates/schemas/`:
   - todo registro va a Silver, con su estado y motivo;
   - la evidencia por campo va a `reports/field_evidence.csv`;
   - el estado por registro original va a `reports/record_status.csv`.
4. Verificar la identidad contra SIO con `sio_query.py`: si algo ya existe, se registra su `sio_id`.
5. Validar Silver con `validate_csv.py --layer silver --sio`.
6. Llevar a `gold/` las filas `VALIDADO` cuyas referencias también estén validadas (copia exacta, sin transformar).
   Validar con `--layer gold --sio`: debe dar 0 errores.
7. Generar `reports/missing_information.xlsx` con los faltantes de lo que está en Gold.

## 9. DAO (primera empresa)

- **Bronze:** `DAO/bronze/DrogueriaDao.xlsx`, con SHA-256 `e725455c056c73feab782e6b8a22c86cf7b85dd8eafab59711d35e92ced288b3`
  (16.889 registros).
- **Estado de cada registro:** `DAO/reports/record_status.csv`.
- **Resumen:** `DAO/reports/summary.md`.
- **Decisiones pendientes con sus simulaciones registro por registro:** `DAO/reports/decisiones-pendientes/`
  (P-CUM-001, P-CAT-002, empaques sin regla, CUM ambiguos, decisiones requeridas, productos sin resolver).
- **Faltantes:** `DAO/reports/missing_information.xlsx`.

## 10. Respaldos y restauración

Los respaldos de DAO están en `DAO/reports/archivo/`, cada uno con su manifiesto SHA-256:

| Respaldo | Contenido |
|---|---|
| `data-runs-2026-10-10.tar.gz` (`runs-sha256.txt`) | Ejecuciones del pipeline anterior, incluida la que dio origen a Silver: evidencia completa por registro, decisiones e historial |
| `codigo-anterior-2026-10-13.tar.gz` (`codigo-anterior-sha256.txt`) | Código, reglas, esquemas y pruebas del pipeline anterior |
| `fuentes-oficiales-y-cache-2026-10-13.tar.gz` (`fuentes-oficiales-y-cache-sha256.txt`) | Fuentes oficiales descargadas (CUM y registros del INVIMA), consultas e imágenes almacenadas. Los índices `.pkl` derivados no se incluyen porque se regeneran |
| `reglas/` (`reglas-sha256.txt`) | Reglas y decisiones del pipeline anterior, en formato legible |
| `documentacion/` (`documentacion-sha256.txt`) | Auditoría, diseño y reportes de conservación de la reestructuración, y el README anterior |
| `dao-silver-gold-reports-v1-…`, `dao-v2…v4-…` | Estados anteriores de Silver, Gold y reportes |
| `d2-indices-antiguos-…` | Índices obsoletos retirados |
| `scripts-traslado/` | Scripts que generaron Silver desde la ejecución anterior |
| `fase-j-dao-sha256.txt` | Hash de cada archivo de `DAO/` antes de la depuración final |
| `d3-…`, `d4a-archivos-eliminados.txt` | Listas de lo eliminado en cada depuración |

**Verificar un respaldo:**

```bash
cd DAO/reports/archivo
mkdir -p /tmp/restaurar && tar -C /tmp/restaurar -xzf codigo-anterior-2026-10-13.tar.gz
(cd /tmp/restaurar && sha256sum -c --quiet "$OLDPWD/codigo-anterior-sha256.txt")
```

**Regenerar Silver de DAO desde los respaldos.** Se comprobó el 2026-10-13: los 27 CSV, `record_status.csv`,
`field_evidence.csv` y las 378 imágenes resultan idénticos. Para hacerlo:

1. En un directorio temporal, extraer `codigo-anterior-2026-10-13.tar.gz`.
2. Extraer `./20261010T195831Z-E9B387` de `data-runs-2026-10-10.tar.gz` en `data/runs/`.
3. Extraer `fuentes-oficiales-y-cache-2026-10-13.tar.gz`, que crea `data/cache/`.
4. Copiar ahí `templates/` actual y crear una carpeta `DAO/` vacía.
5. Ejecutar
   `<.venv>/bin/python <DAO>/reports/archivo/scripts-traslado/build_dao_v5.py <temporal> 20261010T195831Z-E9B387 DAO resumen.json`.
   Necesita además `openpyxl`, `PyYAML` y `jsonschema` en el entorno.
6. Comparar `<temporal>/DAO/silver` con `DAO/silver` (SHA-256). **Nunca** regenerar directamente sobre la carpeta
   `DAO/` real.
