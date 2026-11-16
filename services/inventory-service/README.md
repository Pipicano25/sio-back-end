# inventory-service

Microservicio de inventario de SIO. **Fase A: motor central** (`specs/012-inventory-core/`) y **Fase
B: gestión complementaria** (`specs/013-inventory-complementary/`). Es la única fuente de verdad de
cuánto hay de cada producto empresarial en cada sucursal, cómo se llegó a ese saldo y cuánto vale
(valoración FIFO).

## Responsabilidad y entidades propias

| Tabla | Qué guarda |
| --- | --- |
| `inventory_balances` | Saldo vigente por empresa, sucursal y producto (en unidad base), con `inventory_value`, `average_unit_cost` y `has_unknown_cost`. Nunca negativo; nunca se elimina. `version` = número de movimientos aplicados |
| `inventory_movements` | Kardex **inmutable**: cada cambio de saldo con saldo anterior, cantidad, saldo nuevo, `balance_sequence` (correlativo por saldo, sin huecos), `unit_cost`, `movement_value` y `cost_known`, documento y línea de origen, usuario operativo y flujo |
| `inventory_operations` | Una fila por operación aplicada o reverso (también ajustes y finalizaciones de conteo): clave de idempotencia, cliente o usuario que la usó, huella `request_hash` y enlace al reverso. Inmutable |
| `inventory_adjustments` | Ajuste aplicado (positivo o negativo) con motivo, costo y valor; inmutable (013) |
| `inventory_counts`, `inventory_count_details` | Conteos físicos `DRAFT → IN_PROGRESS → COMPLETED/CANCELLED` y sus productos contados (013) |
| `company_inventory_policies`, `inventory_policies` | Política de la empresa (solo `FIFO`) y niveles de reposición por producto y sucursal; solo configuración (013) |
| `inventory_cost_layers`, `inventory_cost_consumptions` | Capas FIFO y los consumos, restituciones y retiros que explican el costo de cada movimiento; los consumos son inmutables (013) |
| `audit_outbox` | Outbox de auditoría de `libs/sio-audit` |

Fuera de alcance: promedio ponderado, lotes y vencimientos, aprobación de ajustes (Workflow) y
compras automáticas.

## Dependencias

| Servicio | Uso | Identidad |
| --- | --- | --- |
| Keycloak (B) | Validación de tokens (`sio-auth`) y token `client_credentials` propio | Cliente `inventory-service` |
| Operational Context (C) | Operaciones: sucursal (`branches/{id}`), usuario operativo (`application-users/{id}`) y moneda (`companies/{id}`, solo si se crean capas). Consultas y políticas: `operational-access?company_id=`. Ajustes y conteos: `operational-access?branch_id=` (membresía y asignación a la sucursal) | Técnica con `platform:lookup` / token del usuario |
| Commercial Relationship (C) | Productos por lote (`company-products/batch-lookup`): de la empresa, `ACTIVE` y con `inventory_control_enabled` | Técnica con `platform:lookup` |
| Audit | Eventos por `inventory-audit-outbox-worker` (sin llamada síncrona; Audit caído no bloquea) | Cliente `inventory-service` con `perm:audit:audit-events:create` |

Cualquier dependencia no disponible responde `503` con `dependency` (`operational-context`,
`commercial-relationship`, `database`) **sin aplicar nada**. Contratos:
`specs/012-inventory-core/contracts/` y los cambios de `specs/013-inventory-complementary/contracts/`.

## Reglas principales

- **Solo cuentas de servicio aplican entradas, salidas y reversos** (Purchase, Sales y el cliente de
  pruebas `inventory-test-operator`); un usuario humano recibe `403` aunque tenga el permiso.
- **Solo usuarios humanos registran ajustes, operan conteos y configuran políticas**; una cuenta de
  servicio recibe `403` aunque tenga el permiso. Ajustes y conteos exigen además asignación `ACTIVE`
  a la sucursal (`403 BRANCH_ACCESS_DENIED`); el usuario operativo lo informa Operational Context.
- **Todo o nada**: una operación de 1 a 100 líneas (hasta 1 000 al completar un conteo) se aplica
  completa o no se aplica.
- **Saldo nunca negativo**: una salida, un ajuste negativo o un conteo sin saldo suficiente se rechaza
  con `409 INSUFFICIENT_STOCK` y `shortages`.
- **Valoración FIFO en la misma transacción**: las entradas y los ajustes positivos crean capas; las
  salidas y los ajustes negativos las consumen de la más antigua a la más reciente. La suma de las
  capas abiertas es siempre el saldo y su valor el del saldo; si no, la transacción se revierte.
- **Costo obligatorio** (cambio incompatible aprobado, 013): toda entrada trae `unit_cost`
  (`422 UNIT_COST_REQUIRED`). Un ajuste positivo o un sobrante toma el costo de la capa más reciente o
  el informado; sin capas, o si la más reciente no tiene costo conocido, el costo es obligatorio.
  Ninguna cantidad nueva entra sin costo.
- **Capa de apertura** (migración `0002`): cada saldo de la Fase A recibió una capa `OPENING` por su
  cantidad exacta con el costo de su última entrada con costo; sin costo histórico, `0` con
  `cost_known = false` ("sin costo"), que se propaga a consumos, movimientos (`cost_known`) y saldos
  (`has_unknown_cost`) y nunca se deduce de `unit_cost = 0`.
- **Reversos valorizados**: el de una salida restituye cada consumo a su misma capa con el mismo costo;
  el de una entrada exige su capa completa (`409 ENTRY_LAYER_CONSUMED` si se consumió en todo o en
  parte; una entrada de la Fase A se retira de la apertura). Una salida de la Fase A (sin consumos)
  no se revierte: `409 OUTPUT_NOT_VALUED`. Ningún reverso cambia el costo histórico de otras salidas.
- **Concurrencia y orden de bloqueos**: conteo (si aplica) → saldos `SELECT … FOR UPDATE` en orden de
  `company_product_id` → capas por producto, `received_at`, `id`. `balance_sequence = version + 1` se
  asigna con la fila bloqueada, sin `SEQUENCE`. `lock_timeout` agotado → `503 database` reintentable.
- **Idempotencia**: la clave (`operation_key`, `adjustment_key`, `completion_key`) es única y queda
  ligada al cliente o al usuario que la usó; misma solicitud → `200` con el resultado original **sin
  consultar dependencias**; cualquier diferencia → `409 OPERATION_KEY_CONFLICT`.
- **Inmutabilidad en la base**: triggers rechazan cambios a movimientos, operaciones, ajustes y
  consumos, la eliminación de saldos y capas, y los cambios a detalles de conteos finalizados.
- **Control de versión**: conteos y políticas exigen la `version` vigente (`409 VERSION_CONFLICT`).
- **Auditoría** en `audit_outbox`, en la misma transacción: entradas, salidas y reversos (con costo,
  valor y `cost_known` por línea), `CREATE_INVENTORY_ADJUSTMENT`, `START_`, `CANCEL_` y
  `COMPLETE_INVENTORY_COUNT` (resumen), `SET_COMPANY_INVENTORY_POLICY` y `CREATE_`, `UPDATE_` y
  `DEACTIVATE_INVENTORY_POLICY`. Los rechazos solo quedan en el log.

## Lecturas para el servicio de consultas (spec 022)

Solo lectura sobre `inventory_balances` e `inventory_policies`, sin migraciones ni cambios en las
escrituras; se filtran por la empresa de la ruta y nunca devuelven costos unitarios, costo promedio ni FIFO.

- **INV-1** `POST /companies/{c}/branches/{b}/inventory-policies/lookup` (`product-policies:read`): la
  política activa de 1 a 100 productos, o `null`.
- **INV-2** `POST /companies/{c}/inventory-product-sets` (`balances:read` y `product-policies:read`):
  productos con `stock_state = IN_STOCK` (suma de las sucursales `> 0`) y/o `minimum_state` (al menos una
  sucursal; un par sin saldo cuenta con 0), en orden `company_product_id` con `after` y `limit`; con
  `unit = PAIRS` (solo `BELOW_MINIMUM`), pares por faltante descendente. Sin conteos.
- **INV-3** `POST /companies/{c}/inventory-summary` (`balances:read` y `product-policies:read`): por
  sucursal y consolidado, productos con saldo positivo, con saldo registrado en cero (nunca los que no
  tienen registro), con política activa y bajo mínimo, en una sola consulta agregada y sin límite de
  productos. No filtra por estado comercial. `inventory_value` solo con `include_valuation` y
  `perm:inventory:valuation:read`.

## Vistas de contrato (spec 025, D27)

La migración `0003` publica el esquema `contract` con vistas de solo lectura para que otros servicios lean sin
llamar por HTTP. Las escrituras (entradas, salidas, ajustes, reversiones) siguen siendo solo por esta API. Quién lee
qué vista está en [`contract/grants.yaml`](contract/grants.yaml); los roles los crea
`infrastructure/scripts/contract-readers/provision.py`.

| Vista | Columnas | Reemplaza | Consumidores |
|---|---|---|---|
| `v1_balances` | `company_id`, `branch_id`, `company_product_id`, `quantity`, `balance_sequence` | `POST /companies/{c}/branches/{b}/balances/lookup` | Sales, PIQ |
| `v1_operations_by_key` | `company_id`, `operation_key`, `operation_id`, `operation_type`, `status`, `branch_id`, `reverses_operation_id`, `reversed_by_operation_id`, `created_at` | cabecera de `GET /companies/{c}/inventory-operations/by-key/{key}` | Sales, Purchase |
| `v1_operation_movements` | `operation_id`, `company_id`, `line_index`, `movement_id`, `origin_detail_id`, `company_product_id`, `movement_type`, `quantity`, `unit_cost`, `movement_value`, `cost_known`, `reversed_movement_id` | `movements` de la misma respuesta `by-key` | Sales, Purchase |

Reglas:

- **Saldos**: una fila por saldo registrado; `balance_sequence` es la `version` del saldo, como en el API. Un
  producto sin saldo **no tiene fila**: el API responde `quantity = "0.0000"` y `balance_sequence = 0`, y el
  consumidor debe hacer lo mismo. Un saldo que volvió a cero sí tiene fila.
- **Operación por clave**: se filtra siempre por `company_id` y `operation_key` (sin fila → el `404` de hoy, también
  para la clave de otra empresa). Todas las operaciones están confirmadas (tabla de solo inserción).
  `reversed_by_operation_id` es la operación que la revierte; `status` se deriva de ella (`REVERSED` o `APPLIED`) y
  no existe en el API.
- **Movimientos**: se leen con `WHERE operation_id = :id AND company_id = :c ORDER BY line_index`, el mismo orden en
  que el API los lista. `quantity` y `unit_cost` son `NUMERIC(18,4)` y `movement_value` `NUMERIC(18,2)`: su texto es
  el mismo que el del API (`"5.0000"`, `"15.00"`); `unit_cost`, `movement_value` y `cost_known` son nulos en
  movimientos anteriores a la valoración. Sales solo los lee en operaciones `OUTPUT`; Purchase solo usa la cabecera
  (`operation_id`, `operation_type`, `reverses_operation_id`).
- Se publican dos vistas (cabecera y movimientos) en vez de una fila por movimiento para que una operación sea
  exactamente una fila y la cabecera no cambie si se agregan columnas de movimiento.
- `v1_inventory_policies` (PIQ) llega en una fase posterior.

Cambios: compatibles con `CREATE OR REPLACE VIEW` (columnas nuevas al final); incompatibles, con una vista `v2_`.
`tests/contract_views/` prueba la paridad con `by-key` (entrada, salida, ajuste y reversiones de entrada y de salida)
y con `balances/lookup`, que los roles lectores de Sales y Purchase solo leen sus vistas, y el `downgrade`/`upgrade`
de `0003`.

## Permisos

| Permiso | Uso | Quién |
| --- | --- | --- |
| `perm:inventory:entries:create` | Entradas de compra y sus reversos | Cuentas de servicio (Purchase, `inventory-test-operator`) |
| `perm:inventory:outputs:create` | Salidas de venta y sus reversos | Cuentas de servicio (Sales, `inventory-test-operator`) |
| `perm:inventory:balances:read` / `movements:read` | Saldos, stock, kardex y operaciones | `inventario`; `administradores` y `supervisores` (comodín) |
| `perm:inventory:adjustments:create` / `counts:create` | Ajustes y conteos | Usuarios humanos: `inventario` y comodín |
| `perm:inventory:company-policies:update` / `product-policies:update` | Políticas | Usuarios humanos: `administradores` y `supervisores` (comodín) |
| `perm:inventory:adjustments:read`, `counts:read`, `company-policies:read`, `product-policies:read`, `valuation:read` | Lecturas de 013 | `inventario`, comodín e `inventory-test-operator` |
| `perm:inventory:platform:lookup` | Lectura técnica sin membresía | Solo cuentas de servicio consumidoras |

Consultar exige además membresía `ACTIVE` en la empresa (y `perm:operational-context:application_users:read`,
que pide Operational Context); no exige asignación a la sucursal. Ejercicios y matriz de permisos:
[`docs/ejemplo/`](docs/ejemplo/README.md).

## Configuración

Variables en [`.env.example`](.env.example) (copiar a `.env`, que no se versiona). Sin modos de
entorno: las pruebas inyectan dobles por DI. La Fase B no agrega variables ni secretos.

## Arranque

Entorno integrado (desde la raíz del repositorio; el proyecto `sio` y sus dependencias levantados):

```bash
docker compose -p inventory-service -f infrastructure/services/inventory-service.yaml --env-file infrastructure/.env up -d --build
docker exec sio-inventory-service alembic upgrade head
curl -s localhost:8109/health/ready
```

`alembic upgrade head` desde la `0001` crea las capas de apertura y verifica que coincidan con los
saldos; si no coinciden, la migración falla y la base queda en la `0001`.

El contenedor `inventory-audit-outbox-worker` usa la misma imagen y base (`python -m sio_audit.worker`);
si arranca antes de la migración registra un error y se recupera solo en el ciclo siguiente.

Entorno independiente (desde `services/inventory-service/`):

```bash
docker compose --file ../../infrastructure/services/inventory-service.yaml --env-file ../../infrastructure/.env --profile test up -d inventory-test-db
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[test]" -e ../../libs/sio-auth -e ../../libs/sio-audit
alembic upgrade head
```

## Pruebas

```bash
pytest                                       # unitarias, contrato, API, concurrencia, propiedades, ejemplos
pytest -m performance -o addopts=""          # 1 000 000 de movimientos, 100 000 capas, conteo de 500 productos
pytest -m integration -o addopts=""          # Keycloak, OC, CR, Audit y base reales
INVENTORY_EXAMPLES_WRITE=1 pytest tests/examples   # regenera docs/ejemplo/
```

Las pruebas de integración leen `KEYCLOAK_TEST_USER_PASSWORD` e `INVENTORY_TEST_OPERATOR_CLIENT_SECRET`
del entorno o de `infrastructure/.env`, crean datos ficticios con los servicios reales y detienen y
vuelven a iniciar temporalmente Operational Context, Commercial Relationship, Audit y la base.

## Datos iniciales y entorno

No hay datos iniciales (`seed`): los saldos nacen de las entradas y las capas de apertura de la
migración `0002` son una transformación de los saldos existentes. El servicio sigue la práctica
vigente del repositorio de un único proyecto Compose en `infrastructure/services/`; la reconciliación
del Principio IV ("`docker-compose.yml` propio") está pendiente por separado (G1).

## Evolución de existencias para reportes (spec 023)

Solo lectura, para `business-reporting-service`: `GET /api/v1/companies/{c}/branches/{b}/stock-evolution`
(INV-R1). Permiso **propio** `perm:inventory:stock_evolution:read` (DR-11), que no abre el kardex ni la valoración.
Por producto, en unidad base: saldo inicial (último movimiento antes de `from`), entradas, salidas, reversos,
ajustes y saldo final de `[from, to)`; nunca costos ni valores. Sin índices nuevos ni migraciones.

`GET /api/v1/companies/{c}/stock-evolution` (INV-R1C): la misma consulta, consolidada **por producto** sobre las
sucursales de `branch_id` (repetible, obligatorio, ≤ 100), con `branch_count`. Mismo permiso.
