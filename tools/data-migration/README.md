# Preparación de datos para SIO (data-migration)

Prepara la información de una empresa para cargarla en SIO con la arquitectura **Medallion**. Los datos de cada
empresa se normalizan en CSV estándar, se validan contra los contratos reales de los microservicios y solo lo
validado queda listo para el cargue. Solo `cargar_gold.py` puede escribir en SIO, y únicamente con una habilitación
explícita; por defecto simula (sección 11).

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
│   ├── validate_csv.py     validación de los CSV de una empresa
│   ├── cargar_gold.py      cargue de un Gold a SIO por API (simulación por defecto)
│   └── test_*.py           pruebas del cargador y de la obtención de tokens (sin datos reales)
├── templates/
│   ├── schemas/<entidad>.schema.json   27 esquemas Table Schema (iguales para Silver, Gold y toda empresa)
│   └── required_information.xlsx       plantilla de información requerida
└── <EMPRESA>/              datos privados, NO versionados (una línea en .gitignore por empresa)
    ├── bronze/             archivos originales
    ├── silver/             27 CSV con todos los registros
    ├── gold/               27 CSV con solo lo validado
    ├── assets/             imágenes <sha256>.<ext>
    └── reports/            estado por registro, evidencia, faltantes, resumen, decisiones pendientes y respaldos
        └── cargue/         reportes de cada ejecución del cargador y diario sio_ids.csv
```

`.venv/` es el entorno local de Python y no se versiona.

## 3. Entorno

Se necesita Python 3.12 o superior (el entorno actual usa 3.13). Las herramientas solo dependen de `frictionless`
(que instala `jsonschema`, usado por el cargador para validar contra los contratos) y `requests`; las pruebas usan
`pytest`.

```bash
cd tools/data-migration
python3 -m venv .venv
.venv/bin/pip install "frictionless==5.20.0" "requests==2.34.2" "pytest==8.4.2"
```

`sio_query.py` obtiene el token con `services/get_token.py`, sin duplicar la autenticación:

- **Usuarios de prueba** (`--rol consulta`, `admin`…): `obtener_token(rol)`. La contraseña se lee de
  `KEYCLOAK_TEST_USER_PASSWORD`.
- **Clientes técnicos** (`--rol cliente:<client_id>`, p. ej. `cliente:sio-data-importer`): `obtener_token_cliente`,
  con `client_credentials`. El secreto se lee de `<CLIENTE>_CLIENT_SECRET` (p. ej.
  `SIO_DATA_IMPORTER_CLIENT_SECRET`).

Ambos valores se leen del entorno o de `infrastructure/.env`. El token solo vive en memoria: nunca se imprime ni se
guarda.

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

### `cargar_gold.py`: cargar un Gold a SIO

Simula por defecto. Escribe solo con `--escribir --confirmar <EMPRESA>`. Uso, reglas, reanudación, reportes y
limitaciones en la sección 11.

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
- **Propuesta de resolución de decisiones y cargue piloto (Fase N):** `DAO/reports/fase-n-propuesta.md`, con la
  selección de productos del piloto en `DAO/reports/piloto-propuesto.csv`.
- **Cargador y piloto (Fase O):** `DAO/reports/fase-o-cargador.md`, con la simulación del piloto en
  `DAO/reports/cargue/`.

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

## 11. Cargue a SIO por API (`cargar_gold.py`)

Un único script que lee el Gold de una empresa y llama a las API públicas de SIO, sin colas, motores, servicios ni
bases de datos adicionales. Sirve para cualquier empresa: todo lo que necesita sale de los 27 esquemas
(`templates/schemas`) y de los contratos OpenAPI desplegados. **Por defecto solo simula.**

### Uso

```bash
# Simulación (por defecto): solo GET, no modifica nada
.venv/bin/python ia-tools/cargar_gold.py DAO
.venv/bin/python ia-tools/cargar_gold.py DAO --productos DAO/reports/piloto-propuesto.csv
.venv/bin/python ia-tools/cargar_gold.py DAO --entidades packaging_types,brands,attribute_definitions,categories,category_attributes

# Escritura real: SOLO con autorización expresa del cargue
.venv/bin/python ia-tools/cargar_gold.py DAO --productos DAO/reports/piloto-propuesto.csv \
    --escribir --confirmar DAO --rol <rol autorizado>
```

| Parámetro | Uso |
|---|---|
| `empresa_dir` | Carpeta de la empresa (`DAO`). |
| `--productos <csv>` | CSV con una columna `product_ref`: limita el cargue a esos productos y a lo que necesitan (sus marcas, fabricantes, presentaciones, identificadores, categorías, valores y datos de empresa), más la empresa, sus sedes y los catálogos de categorías, atributos y empaques, que siempre van completos. |
| `--entidades a,b` | Procesa solo esos CSV (p. ej. primero los catálogos). Las filas que dependan de otros CSV no cargados quedan en `DEPENDENCIA`. |
| `--rol` | Rol de `services/get_token.py` (por defecto `consulta`, suficiente para simular), cliente técnico `cliente:<client_id>` o usuario nominal `usuario:<nombre>` (contraseña en `<NOMBRE>_PASSWORD`, nunca en el código). |
| `--salida <dir>` | Carpeta de reportes y diario (por defecto `<EMPRESA>/reports/cargue/`). |
| `--con-imagenes` | Registra `product_assets` (`POST …/assets`). Úsalo solo después de subir los archivos a MinIO (ver "Imágenes"); sin él, las imágenes salen `OMITIDO`. |
| `--escribir` | Habilita POST y PUT. Exige además `--confirmar <nombre exacto de la carpeta de la empresa>`; sin ambos no se escribe. |

**Código de salida:** 0 sin errores; 1 si hubo filas `ERROR` o `INVALIDA`; 2 si Gold no pasa la validación previa;
3 si la ejecución se detuvo o se interrumpió.

### Cargue completo por etapas (identidades)

La cuenta técnica `sio-data-importer` no puede crear empresas ni sedes: Operational Context exige
`platform:administer`. Por eso el cargue completo se hace en tres ejecuciones que comparten el mismo diario (sin
`--productos`, para cubrir todo Gold):

```bash
# 1. Organizaciones (cuenta técnica)
.venv/bin/python ia-tools/cargar_gold.py <EMPRESA> --entidades organization_identities \
    --rol cliente:sio-data-importer --escribir --confirmar <EMPRESA>
# 2. Empresa y sedes (identidad administrativa autorizada)
.venv/bin/python ia-tools/cargar_gold.py <EMPRESA> --entidades companies,branches \
    --rol <rol administrativo> --escribir --confirmar <EMPRESA>
# 3. Todo lo demás: catálogos, marcas, productos, presentaciones, identificadores, categorías, atributos (cuenta técnica)
.venv/bin/python ia-tools/cargar_gold.py <EMPRESA> --rol cliente:sio-data-importer --escribir --confirmar <EMPRESA>
```

En la etapa 3, lo ya cargado sale como `YA_CARGADO` y las imágenes, `OMITIDO` (salvo con `--con-imagenes`; ver
"Imágenes").

**Etapa 4, asociación comercial (spec 019):**

- `CompanyProduct` ya no tiene precio ni costo, así que los productos y presentaciones de empresa se asocian sin
  ellos.
- Commercial Relationship exige un usuario miembro `ACTIVE` de la empresa, no la cuenta técnica:

  ```bash
  .venv/bin/python ia-tools/cargar_gold.py <EMPRESA> --entidades company_products,company_product_presentations \
      --rol usuario:<miembro> --escribir --confirmar <EMPRESA>
  ```

- **Seguridad:** si el contrato desplegado todavía tiene `sale_price` o `reference_cost` (spec 019 sin desplegar),
  esas filas quedan `BLOQUEADA` y no se envían, porque la API guardaría 0.
- **Precios:** se cargan después, por presentación, con `price_lists` y `price_list_items`.

**Verificación posterior contra SIO:** una simulación con otra carpeta de salida (sin diario) busca cada fila por
su identidad en las API. Todo lo cargado debe salir `REUSADO`, sin `CREARIA`, `CONFLICTO` ni `ERROR`.

Operational Context solo muestra empresas y sedes a administradores de plataforma o a miembros de la empresa, así
que esas dos entidades se verifican con la identidad administrativa:

```bash
.venv/bin/python ia-tools/cargar_gold.py <EMPRESA> --entidades organization_identities,companies,branches \
    --rol <rol administrativo> --salida <EMPRESA>/reports/cargue/verificacion
.venv/bin/python ia-tools/cargar_gold.py <EMPRESA> --rol cliente:sio-data-importer --salida <EMPRESA>/reports/cargue/verificacion
```

En la segunda, `companies` y `branches` no se deben interpretar: la cuenta técnica no las ve.

### Qué hace con cada fila

Antes de empezar ejecuta `validate_csv.py --layer gold --sio`; con un solo error no procesa nada. Después recorre
los CSV en orden de dependencias (Party Identity → Operational Context → catálogos de Product Catalog → productos →
Commercial Relationship) y, dentro de un CSV que se referencia a sí mismo (categorías), los padres antes que los hijos.

| Paso | Regla |
|---|---|
| 1. ¿Ya cargada? | Si la fila tiene `sio_id` en el CSV o en el diario de ejecuciones anteriores → `YA_CARGADO`; no se consulta ni se envía nada. |
| 2. Dependencias | Cada `*_ref` (claves foráneas del esquema) y cada tipo de empaque nuevo deben tener ya su id en SIO. Si no → `DEPENDENCIA`, con el motivo; la fila se intentará en la siguiente ejecución. |
| 3. Datos faltantes | Si falta un dato que la API guardaría con un valor por defecto → `BLOQUEADA`. Vacío nunca es 0. Solo aplica si el contrato desplegado tiene ese campo (`sale_price`/`reference_cost` de `company_products` antes de la spec 019). |
| 4. Cuerpo | Solo con las propiedades del contrato desplegado: referencias traducidas a id, códigos de catálogo (unidades, empaques, país) resueltos por GET y división y ciudad resueltas en Geography (igualdad exacta, admitiendo el sufijo "Department"). |
| 5. Contrato | El cuerpo se valida contra el esquema del contrato OpenAPI. Si no cumple → `INVALIDA` y no se envía. Un identificador de un tipo que el contrato desplegado no admite (p. ej. `IUM` antes de la migración `0004`) → `DEPENDENCIA`. |
| 6. Identidad | GET por la clave natural: organización por (país, sigla, número); empresa por organización; sede, empaque, marca, atributo y categoría por código; producto por sus identificadores globales (`by-identifier`, **nunca por nombre**); presentación por código dentro del producto; identificador por tipo y valor; categoría, valor de atributo y datos de empresa por su pareja. Si existe → `REUSADO`, sin modificarlo (las diferencias quedan anotadas). Varias coincidencias, o un valor de atributo distinto en SIO → `CONFLICTO`, sin escribir. |
| 7. Creación | Simulación: `CREARIA` (con el cuerpo en el reporte). Escritura: POST o PUT → `CREADO` (con las advertencias del servicio, p. ej. posible duplicado), `CONFLICTO` (409) o `ERROR` (otros 4xx, con el `code` del problema). |

### Simulación

- Solo GET: no escribe en ningún servicio ni sube nada a MinIO.
- No modifica ningún CSV y no escribe el diario.
- Las filas que se crearían reciben un id simulado para que sus hijas también se evalúen. Bajo un padre simulado no
  se buscan los hijos en SIO (no pueden existir). Los productos, catálogos y organizaciones sí se buscan siempre.
- Detecta duplicados (lo que ya existe en SIO), dependencias, datos faltantes e incompatibilidades con el contrato.
- Es reproducible: el mismo Gold y el mismo estado de SIO dan el mismo reporte.

### Reanudación y diario

- En escritura, cada id obtenido (`CREADO` o `REUSADO`) se anota en `<EMPRESA>/reports/cargue/sio_ids.csv` justo
  después de la respuesta, con `fsync`. Los CSV de Gold y Silver **no se modifican**.
- El cargue puede detenerse en cualquier momento (Ctrl+C o un fallo) y volver a ejecutarse con los mismos
  parámetros: lo anotado se omite (`YA_CARGADO`) y lo demás continúa.
- Sin diario (perdido o en otra carpeta), la búsqueda por identidad del paso 6 evita los duplicados (`REUSADO`).
  Las restricciones únicas de cada servicio son la última barrera (409 → `CONFLICTO`).
- **Única ventana sin protección:** si el proceso muere entre la respuesta de creación de un producto y su anotación
  en el diario, y el producto todavía no tiene identificadores, una nueva ejecución lo crearía otra vez. El servicio
  lo advierte (posible duplicado) y queda en el reporte. Se evita reanudando con el diario intacto.

### Errores

| Situación | Efecto |
|---|---|
| 401 (tras renovar el token una vez), 403, 5xx o servicio caído | La ejecución se detiene (`DETENIDA`) sin perder lo hecho; se reanuda después. |
| 409 | `CONFLICTO`; no se resuelve automáticamente. |
| Otro 4xx | `ERROR` con el `code` del problema; se continúa con las filas independientes y sus dependientes quedan en `DEPENDENCIA`. |

### Imágenes (`product_assets`)

Product Catalog no recibe el archivo: guarda la referencia `storage_uri = s3://<bucket>/assets/<sha256>.<ext>` y
sirve el contenido desde MinIO (`GET …/assets/{id}/content`, con su cuenta de solo lectura).

1. **Verificar en local:** `validate_csv.py --layer gold` comprueba que cada archivo de `<EMPRESA>/assets/`
   exista y que su SHA-256 coincida con su nombre.
2. **Subir los archivos** con la cuenta de migración (`MIGRATION_ASSET_STORAGE_*` de `infrastructure/.env`), que
   puede leer y escribir en `assets/*` pero no borrar.
   - **Herramienta:** el `mc` de la misma imagen de MinIO que usa `object-storage-bootstrap`, en `sio-network`,
     con la carpeta de imágenes en solo lectura.
   - **Clave:** `assets/<sha256>.<ext>` (la de `storage_uri`), con `Content-Type` = `mime_type` y el metadato
     `sha256=<sha256>`. Con ese metadato, Product Catalog devuelve `ETag` = SHA-256 y caché inmutable.
   - **Sin duplicados:** la clave se deriva del contenido.
3. **Registrar:** `cargar_gold.py <EMPRESA> --con-imagenes --rol cliente:sio-data-importer --escribir
   --confirmar <EMPRESA>`. Busca por `storage_uri` antes de crear, así que no duplica.
4. **Verificar:** `GET …/content` de cada activo debe dar 200, contenido con el SHA-256 esperado, `Content-Type`
   correcto, `ETag` = SHA-256 y `Cache-Control: … immutable`.

Un producto sin imagen es válido; no es un error.

### Reportes

Por cada ejecución, en `<EMPRESA>/reports/cargue/`:

- `<fecha>-<simulacion|escritura>.csv`: una línea por fila procesada (`orden`, `csv`, `ref`, `resultado`, `metodo`,
  `servicio`, `ruta`, `http`, `sio_id`, `codigo`, `detalle`). Se escribe línea a línea, así que sobrevive a una
  interrupción.
- `<fecha>-<modo>.json`: modo, estado (`COMPLETA`, `DETENIDA` o `INTERRUMPIDA`), motivo, rol usado (nunca el
  token), número de productos seleccionados y conteo por CSV y resultado.
- `sio_ids.csv`: el diario (solo en escritura).

### Seguridad

- El token se obtiene con `services/get_token.py` a través de `sio_query.py` (sección 3): solo en memoria, nunca
  impreso ni guardado.
- Sin DELETE ni inactivaciones. Nunca sobrescribe datos existentes: lo que ya existe se reutiliza o se marca
  `CONFLICTO`.
- Escritura con doble habilitación (`--escribir` y `--confirmar <empresa>`). La simulación no puede escribir: el
  cliente rechaza cualquier envío si la escritura no está habilitada.
- Cada escritura queda auditada por el servicio a nombre del usuario del token.
- **Usuario importador:** cuenta técnica `sio-data-importer` (`--rol cliente:sio-data-importer`). Tiene 13
  permisos: consulta; creación de organizaciones y del catálogo global; actualización de productos (presentaciones,
  identificadores, categorías y valores) y de categorías (asociación de atributos). No tiene `delete`, `deactivate`
  ni `platform:administer`. El cliente existe en el realm y su token se obtiene con
  `python services/get_token.py --cliente sio-data-importer`.
- **Lo que la cuenta técnica no puede hacer:**
  - crear empresas, porque Operational Context exige `platform:administer`;
  - crear sedes, porque exige ser administrador de plataforma o miembro de la empresa;
  - crear datos de empresa en Commercial Relationship, porque exige membresía `ACTIVE`, que una cuenta de
    servicio no puede tener.

  Esas filas necesitan otra identidad autorizada.

### Limitaciones

- No sube archivos a MinIO: las imágenes se suben antes con la cuenta de migración (ver "Imágenes") y el cargador
  solo las registra con `--con-imagenes`.
- No carga proveedores, condiciones de pago, listas de precios, compras ni grupos: esas filas salen como
  `OMITIDO`, con el motivo.
- No actualiza ni corrige datos que ya existen en SIO.
- Necesita que los servicios publiquen `/openapi.json` (`SIO_DOCS_ENABLED`).

### Pruebas

```bash
# Con datos sintéticos y un doble de las API (sin red ni bases): duplicados, autenticación, reanudación,
# idempotencia, dependencias, IUM y GTIN, empaques nuevos, categorías y atributos, selección y validación previa;
# y la obtención de tokens (usuarios de prueba y clientes técnicos)
.venv/bin/python -m pytest ia-tools/test_cargar_gold.py ia-tools/test_tokens.py -q

# Integración con la aplicación real de Product Catalog y su base de pruebas AISLADA (desde el servicio)
cd ../../services/product-catalog-service && set -a && . ./.env && set +a
.venv/bin/python -m pytest -p tests.conftest ../../tools/data-migration/ia-tools/test_cargar_gold_product_catalog.py -q
```

La segunda prueba usa las fixtures de la suite del servicio: una base exclusiva de pruebas, vaciada en cada prueba.
Nunca toca la base del servicio.
