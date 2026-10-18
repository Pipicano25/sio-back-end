# business-reporting-service

Microservicio de **solo lectura** de SIO (spec 023, fase 1). Genera reportes **bajo demanda** en JSON y CSV a partir
de las agregaciones que calculan sus servicios propietarios. No tiene base de datos, colas, workers, tareas
programadas ni almacenamiento de reportes: en reposo solo responde su healthcheck (cada 60 s).

| Endpoint | Qué entrega | Permiso del reporte | Permiso del propietario |
|---|---|---|---|
| `GET /api/v1/companies/{c}/reports/top-selling-products` | Ranking por cantidad en unidad base (por defecto) o importe | `perm:business-reporting:top_selling_products:read` | `perm:sales:sales:read` |
| `GET /api/v1/companies/{c}/reports/sales-by-branch` | Ventas y total por sucursal, con participación | `perm:business-reporting:sales_by_branch:read` | `perm:sales:sales:read` |
| `GET /api/v1/companies/{c}/reports/purchases` | Compras recibidas, pendientes y anuladas con totales | `perm:business-reporting:purchases:read` | `perm:purchase:purchases:read` |
| `GET /api/v1/companies/{c}/branches/{b}/reports/stock-evolution` | Existencia inicial, movimientos y existencia final por producto | `perm:business-reporting:stock_evolution:read` | `perm:inventory:stock_evolution:read` |
| `GET /api/v1/companies/{c}/branches/{b}/reports/top-selling-products` | Ranking de una sucursal | `perm:business-reporting:top_selling_products:read` | `perm:sales:sales:read` |
| `GET /api/v1/companies/{c}/branches/{b}/reports/sales-by-branch` | Ventas de una sucursal (también en cero), sin participación | `perm:business-reporting:sales_by_branch:read` | `perm:sales:sales:read` |
| `GET /api/v1/companies/{c}/branches/{b}/reports/purchases` | Compras de una sucursal con sus totales | `perm:business-reporting:purchases:read` | `perm:purchase:purchases:read` |

Las rutas por sucursal reutilizan el mismo caso de uso que la ruta de empresa con un único `branch_id`, exigen la
sucursal en la ruta (la principal, con su UUID; `404` si no es de la empresa) y rechazan `branch_id` por consulta
(`422`). En la ruta de empresa de ventas por sucursal, `share_percentage` es el total de la sucursal sobre la suma de
**las sucursales de la respuesta** (con `branch_id`, solo las filtradas).

| `GET /api/v1/companies/{c}/reports/stock-evolution` | Existencias consolidadas por producto de la empresa (o de `branch_id`), con `branch_count` | `perm:business-reporting:stock_evolution:read` | `perm:inventory:stock_evolution:read` |

La consolidación la calcula Inventory en SQL (INV-R1C, una consulta por página); cada fila es un producto (nunca se
suman productos distintos), los días van en la zona horaria de la empresa y no hay costos. Sin `branch_id` incluye
también las sucursales inactivas, que pueden conservar existencias. En total, **ocho** endpoints de reportes.

Todos aceptan `date_from` y `date_to` (fechas de negocio, incluidas, hasta 366 días, sin fechas futuras) y
`format=json|csv`. Contrato: `specs/023-business-reporting-service/contracts/`. Ejemplos validados:
[`docs/ejemplo/`](docs/ejemplo/README.md). El margen bruto es de la **fase 2** de la spec 023 (pendiente).

## Qué es y qué no es

- **Agrega el propietario, no este servicio.** Sales (SAL-R1, SAL-R2), Purchase (PUR-R1) e Inventory (INV-R1)
  calculan las sumas en SQL sobre índices existentes; aquí solo se verifica el acceso, se completan nombres y
  unidades por lote (una llamada por página y tipo) y se da formato. No se descargan documentos para agruparlos.
- **Reglas de negocio** (decisiones aprobadas): solo ventas `CONFIRMED` (las anuladas se excluyen por su estado
  actual); el período es la `operation_date` de ventas y compras; las compras se clasifican en `RECEIVED`,
  `PENDING_RECEIPT` y `CANCELLED`, y las anuladas nunca suman en `effective_total`; las cantidades van en la unidad
  base de cada producto y nunca se suman entre productos (`mixed_base_units` lo advierte); los importes nunca se
  suman entre monedas.
- **Sin costos ni márgenes** en esta fase. La evolución de existencias solo tiene cantidades.

## Seguridad

1. `sio-auth` valida el token (RS256, JWKS) y el permiso del reporte (`403` sin revelar el permiso).
2. Operational Context verifica, **con el token del usuario**, la membresía `ACTIVE` y las sucursales antes de
   cualquier otra llamada: sin membresía, empresa inexistente o sucursal de otra empresa → `404`.
3. Sales, Purchase, Inventory, Commercial Relationship y Product Catalog se consultan **también con el token del
   usuario** (D5, DR-07): cada propietario aplica su membresía y su permiso de lectura. Si responde `403`, el
   reporte responde el mismo `403` genérico. El servicio **no tiene cliente técnico** ni secretos propios.
4. `reportes` lee la evolución de existencias con `perm:inventory:stock_evolution:read`, que **no** abre el kardex,
   los costos ni las capas (DR-11).
5. Toda fila de otra empresa o sucursal fuera del alcance es un incidente de integridad (`503`, sin datos). Los
   logs no contienen tokens.

## CSV: garantías reales

- UTF-8 con BOM (`bom=false` lo omite), mismos filtros, permisos y datos que el JSON; protección contra fórmulas
  (`'` delante del texto que empieza por `=`, `+`, `-`, `@`, tabulación o retorno de carro; los números no se
  alteran). Sin archivos temporales: se transmite página a página (memoria de una página).
- **Antes del primer byte** se leen la primera página y el total de filas: todo error previo (permisos,
  validación, dependencia, más de 50.000 filas) es una respuesta RFC 9457, nunca un CSV.
- **Un CSV completo siempre termina con la fila `TOTAL FILAS,<n>`**, escrita solo si todas las páginas se leyeron.
  Es la prueba de completitud que no depende del cliente.
- **Error a mitad de la transmisión**: sin filas de totales ni `TOTAL FILAS`; última línea
  `#ERROR: reporte incompleto, trace_id=<id>`; la conexión se cierra sin el bloque final `chunked`
  (comprobado con un Uvicorn real: `httpx` informa `RemoteProtocolError`; `curl`, transferencia incompleta). Que
  un navegador marque la descarga como fallida depende del navegador: **no** se garantiza.

## Configuración

| Variable | Uso | Por defecto |
|---|---|---|
| `SIO_AUTH_ISSUER`, `SIO_AUTH_JWKS_URL`, `SIO_AUTH_AUDIENCE` | Validación de tokens | — |
| `OPERATIONAL_CONTEXT_SERVICE_BASE_URL`, `SALES_SERVICE_BASE_URL`, `PURCHASE_SERVICE_BASE_URL`, `INVENTORY_SERVICE_BASE_URL`, `COMMERCIAL_RELATIONSHIP_SERVICE_BASE_URL`, `PRODUCT_CATALOG_SERVICE_BASE_URL` | Dependencias (con `/api/v1`) | — |
| `BRS_DEPENDENCY_TIMEOUT_SECONDS`, `BRS_JSON_BUDGET_SECONDS`, `BRS_CSV_BUDGET_SECONDS` | 5 s por llamada; 10 s por JSON; 120 s por CSV | `5`, `10`, `120` |
| `BRS_MAX_PARALLEL_CALLS` | Llamadas simultáneas por solicitud | `4` |
| `BRS_MAX_PERIOD_DAYS`, `BRS_CSV_MAX_ROWS` | Límites (DR-09) | `366`, `50000` |
| `BRS_DEFAULT_TIMEZONE` | Zona si la empresa no informa una | `America/Bogota` |
| `SIO_DOCS_ENABLED` | `/docs` y `/openapi.json` públicos | `false` |

`/health/live` no depende de nada; `/health/ready` solo del JWKS. Sin dependencias de arranque: si un propietario
cae, cada reporte responde `503`.

## Ejecución

```bash
docker compose --file infrastructure/services/business-reporting-service.yaml --env-file infrastructure/.env up -d
```

Los permisos `perm:business-reporting:*` y `perm:inventory:stock_evolution:read` están en la plantilla del realm;
aplicarlos al Keycloak persistente requiere autorización. Los propietarios deben tener las ampliaciones de la
spec 023.

## Pruebas

```bash
cd services/business-reporting-service
.venv/bin/pytest                                   # unitarias, contrato, API, CSV (con Uvicorn local), ejemplos y salud
BUSINESS_REPORTING_EXAMPLES_WRITE=1 .venv/bin/pytest tests/examples   # regenerar docs/ejemplo/
SIO_TEST_TARGET=isolated .venv/bin/pytest -m integration -o addopts="" tests/integration   # solo en la pila sio-it
```
