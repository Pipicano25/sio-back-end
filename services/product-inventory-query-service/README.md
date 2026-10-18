# product-inventory-query-service

Microservicio de **solo lectura** de SIO (spec 022). Compone por HTTP lo que entregan Operational Context, Commercial
Relationship, Product Catalog e Inventory y expone cuatro consultas para el frontend, cada una con una ruta de empresa y una por sucursal (ocho rutas):

| Endpoint | Qué entrega | Permiso funcional |
|---|---|---|
| `GET /api/v1/companies/{c}/product-overviews` | Productos con catálogo, imagen, presentaciones, precio de venta y existencias | `perm:product-inventory-query:product_overviews:read` |
| `GET /api/v1/companies/{c}/inventory-overviews` | Existencias por sucursal y consolidadas, equivalencias y estado frente al mínimo | `perm:product-inventory-query:inventory_overviews:read` |
| `GET /api/v1/companies/{c}/low-stock-products` | Pares producto–sucursal con existencia **estrictamente menor** que el mínimo activo | `perm:product-inventory-query:low_stock_products:read` (más existencias y mínimos) |
| `GET /api/v1/companies/{c}/inventory-summary` | Indicadores operativos por sucursal y consolidados | `perm:product-inventory-query:inventory_summary:read` |

Cada consulta tiene además su variante por sucursal, `GET /api/v1/companies/{c}/branches/{b}/<consulta>`: equivale
a la ruta de la empresa con un único `branch_id` (mismo código, permisos, filtros, paginación y respuesta) y sus
datos de inventario son solo de esa sucursal. No admite `branch_id` ni `scope` por consulta (`422`); una sucursal
de otra empresa responde `404`. La sucursal principal se consulta con su UUID, como cualquier otra.

| Dato | Alcance en la ruta por sucursal | Propietario |
|---|---|---|
| `adopted_products` | **Empresa** (no cambia con la sucursal) | Commercial Relationship: la adopción es por empresa |
| Existencias (`stock`, `products_with_positive_balance`, `products_with_zero_balance`) | Sucursal de la ruta | Inventory |
| Mínimos (`minimum_stock`, `minimum_state`, `products_with_policy`) | Sucursal de la ruta | Inventory |
| Bajo stock (`low-stock-products`, `products_below_minimum`) | Sucursal de la ruta | Inventory |
| `branches` y `consolidated` del resumen | Solo la sucursal de la ruta (`consolidated` = esa sucursal) | Inventory |

Por eso, en el resumen por sucursal **no** se debe comparar ni restar `adopted_products` con los indicadores de
la sucursal: miden alcances distintos (D-022-15; tampoco existe "productos sin existencias", D-022-11).

Contrato completo: `specs/022-product-inventory-query-service/contracts/product-inventory-query-api.md` y el
OpenAPI del servicio (`/docs` con `SIO_DOCS_ENABLED=true`). Ejemplos validados: [`docs/ejemplo/`](docs/ejemplo/README.md).

## Qué es y qué no es

- **Sin base de datos.** No guarda copias ni caché de productos, precios, existencias ni políticas. En memoria solo
  tiene el token técnico, las unidades de medida (5 minutos) y, por solicitud, el registro de llamadas.
- **Origen de cada dato:** los precios de venta y su moneda vienen de Commercial Relationship; las existencias y los
  mínimos, de Inventory; el catálogo y las imágenes, de Product Catalog; la membresía y las sucursales, de
  Operational Context. Sin precio configurado, `unit_price` y `currency_code` son `null`: nunca se inventan.
- **Nunca entrega costos** (adquisición, FIFO, promedio), márgenes ni **valoración económica**. La valoración del
  inventario está fuera del alcance de la spec 022 (D-022-12) y sigue disponible en Inventory con sus propios
  permisos. Los permisos económicos que siguen abiertos en las API originales están en
  [`docs/permisos-existentes-y-exposiciones.md`](docs/permisos-existentes-y-exposiciones.md).
- **Solo lectura:** no escribe ni provoca escrituras en otros servicios.

## Seguridad

1. `sio-auth` valida el token (RS256, JWKS) y el permiso funcional del endpoint (`403` sin revelar el permiso).
2. **Antes de cualquier otra llamada**, Operational Context verifica con el **token del usuario** la membresía
   `ACTIVE` y las sucursales: sin membresía, empresa inexistente o sucursal de otra empresa → `404` (sin distinguir).
   Con membresía y permiso de lectura se consulta **cualquier** sucursal de la empresa, sin asignación (A-08).
3. Después, CR, PC e Inventory se consultan con la identidad técnica `product-inventory-query-service`
   (`client_credentials`, solo lectura). La cuenta técnica nunca amplía lo que ve el usuario: los bloques de la
   respuesta se deciden con los permisos del token del usuario.

| Bloque | Permiso | Sin él |
|---|---|---|
| `presentations[].price` | `perm:commercial-relationship:price_list_items:read` | El bloque no aparece |
| `stock` | `perm:product-inventory-query:stock:read` | El bloque no aparece; `stock_state` responde `403` |
| `minimum_stock`, `minimum_state` | `perm:inventory:product-policies:read` | No aparecen; `minimum_state` responde `403` |

Toda fila de CR o Inventory de otra empresa se descarta y se registra como incidente de integridad. Los logs no
contienen tokens, cursores, referencias de imagen ni datos personales.

## Paginación por cursor

- `page_size` de 1 a 20 (20 por defecto). Sin `total_records`, `total_pages` ni `page`.
- El servicio busca `page_size + 1` válidos en lotes de `min(max(page_size × 2, 20), 40)` candidatos: el servicio
  que conduce entrega candidatos en orden y los demás evalúan sus filtros solo sobre ese lote.
- `next_cursor` es opaco y firmado (HMAC-SHA256, 15 minutos). `PAGE` continúa después del último entregado;
  `SCAN`, después del último examinado cuando se alcanzó el límite de trabajo (`partial = true`,
  `WORK_LIMIT_REACHED`). Un resultado parcial **no** es el final: continúe con `next_cursor`.
- Si cambian los filtros, el orden o `page_size`, o el cursor vence, la consulta se reinicia sin error
  (`pagination_reset = true` y el motivo). Un cursor alterado, de otra empresa o de otro endpoint es `422`
  `INVALID_CURSOR`.

Orden predeterminado (`sort_applied`): `display_name:asc` sin filtros o con `search`, `internal_code` o `sku`;
`canonical_name:asc` con `barcode`, `identifier` o filtros de catálogo; `company_product_id:asc` con solo
`stock_state=IN_STOCK` o `minimum_state` con política; `shortfall:desc` en bajo stock. Un `sort` explícito
(`display_name`, `internal_code` o `created_at`) hace que conduzca Commercial Relationship.

## Resumen frente a listados

El resumen cuenta con los datos de cada propietario: `adopted_products` (CR: productos `ACTIVE` con control de
inventario, solo a nivel de empresa) y, en Inventory, productos con saldo positivo, con saldo registrado en cero,
con política y bajo mínimo. Un producto **sin registro de saldo** no cuenta en ningún indicador, y no existe
"productos sin existencias" (sería una resta entre servicios). Los indicadores de Inventory pueden incluir
productos inactivos o sin control de inventario que conservan saldo, que los listados no muestran por defecto.

## Configuración

| Variable | Uso | Valor por defecto |
|---|---|---|
| `SIO_AUTH_ISSUER`, `SIO_AUTH_JWKS_URL`, `SIO_AUTH_AUDIENCE` | Validación de tokens | — |
| `OPERATIONAL_CONTEXT_SERVICE_BASE_URL`, `COMMERCIAL_RELATIONSHIP_SERVICE_BASE_URL`, `PRODUCT_CATALOG_SERVICE_BASE_URL`, `INVENTORY_SERVICE_BASE_URL` | Dependencias (con `/api/v1`) | — |
| `KEYCLOAK_TOKEN_URL`, `PIQS_CLIENT_ID`, `PIQS_CLIENT_SECRET` | Identidad técnica | `product-inventory-query-service` |
| `PIQS_CURSOR_SECRET`, `PIQS_CURSOR_SECRET_PREVIOUS` | Firma del cursor (≥ 32 bytes; el anterior durante la rotación) | — |
| `PIQS_CURSOR_TTL_SECONDS` | Vigencia del cursor | `900` |
| `PIQS_DEPENDENCY_TIMEOUT_SECONDS`, `PIQS_REQUEST_BUDGET_SECONDS`, `PIQS_WORK_TIME_SECONDS` | 3 s por dependencia, 8 s por solicitud, 5 s de búsqueda | `3`, `8`, `5` |
| `PIQS_MAX_BATCHES_PER_REQUEST`, `PIQS_BATCH_MIN`, `PIQS_BATCH_FACTOR`, `PIQS_BATCH_MAX` | Límite de trabajo y tamaño de lote | `5`, `20`, `2`, `40` |
| `PIQS_MAX_PARALLEL_CALLS`, `PIQS_REFERENCE_CACHE_SECONDS` | Concurrencia por solicitud y vida de la caché de unidades | `8`, `300` |
| `SIO_DOCS_ENABLED` | `/docs` y `/openapi.json` públicos | `false` |

Los secretos van solo por entorno (`infrastructure/.env`, nunca versionado). `/health/live` no depende de nada;
`/health/ready` valida la configuración y el JWKS, no las dependencias: si una cae, cada consulta responde `503`.

## Ejecución

```bash
docker compose --file infrastructure/services/product-inventory-query-service.yaml --env-file infrastructure/.env up -d
```

El cliente técnico y los permisos están en la plantilla del realm; aplicarlos al Keycloak persistente requiere
autorización (FR-022-112).

## Pruebas

```bash
cd services/product-inventory-query-service
.venv/bin/pytest                                   # unitarias, contrato, API, oráculo, ejemplos y salud (dobles)
PRODUCT_INVENTORY_QUERY_EXAMPLES_WRITE=1 .venv/bin/pytest tests/examples   # regenerar docs/ejemplo/
```

Integración, seguridad y rendimiento con servicios reales **solo** en la pila aislada `sio-it-*`
(`validation/isolated-stack/README.md`), con `SIO_TEST_TARGET=isolated` y `validation/isolation_guard.py`:

```bash
.venv/bin/pytest -m integration -o addopts="" tests/integration
.venv/bin/pytest -m performance -o addopts="" tests/performance
```

## Limitaciones conocidas

- Sin valoración económica ni `quantities_by_base_unit` (D-022-12 y D-022-10; specs futuras).
- Datos que cambian entre páginas (nombre, estado o saldo) pueden mover un producto de posición; se acepta y
  `resolved_at` lo documenta (FR-022-67).
- Sin limitación de tasa en la ruta pública de imágenes de Product Catalog.
