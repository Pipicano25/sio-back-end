# purchase-service

Microservicio de **compras** de SIO (`specs/014-purchase-core/`): registra compras en borrador, las
confirma ingresando la mercancía en Inventory con su costo y su número oficial, las anula revirtiendo
exactamente su entrada, administra la numeración por período y registra los hitos logísticos.

## Responsabilidad y entidades

| Tabla | Rol |
| --- | --- |
| `purchases` | Cabecera: proveedor, sucursal, fecha de negocio, condición de pago (`CASH`/`CREDIT`/`FINANCING`), `due_date`, moneda (la `default_currency` de la empresa), totales, número, estado `DRAFT`/`CONFIRMED`/`CANCELLED`, `inventory_operation_id` |
| `purchase_details` | Líneas (1–100): producto empresarial, presentación opcional, producto de proveedor opcional, cantidad y costo en la unidad de compra, descuento, impuesto, snapshots |
| `purchase_sequences` | Numeración por empresa o sucursal; a lo sumo una activa por empresa, sucursal y tipo |
| `purchase_sequence_counters` | Contador independiente por período (`''` continuo, `YYYY`, `YYYYMM`) |
| `purchase_operations` | Confirmación o anulación distribuida (`PENDING`/`SUCCEEDED`/`FAILED`), clave de idempotencia, `inventory_operation_id`, usuario operativo que la inició y motivo (inmutables; `error_details` solo errores) |
| `purchase_lifecycle_events` | Hitos inmutables `ORDERED → SUPPLIER_DISPATCHED → ARRIVED → RECEIVED → AVAILABLE_FOR_SALE` |
| `audit_outbox` | Transactional Outbox de `sio-audit` |

Snapshots (nombre e identificación del proveedor, código y nombre del producto, presentación, unidad,
factor, lead time esperado, condición de pago): **excepción documentada al Principio III** (DS-02).
Son provisionales en el borrador y se refrescan y **congelan al confirmar**; después no cambian.

## Flujo de confirmación (research.md R-04, R-05)

1. Acceso: usuario humano con `perm:purchase:purchases:update`, membresía y asignación `ACTIVE` a la
   sucursal de la compra.
2. `Idempotency-Key` obligatoria, ligada a compra, tipo y `sub`. La misma clave devuelve el resultado
   de la primera solicitud (o la reanuda si quedó `PENDING`); otra compra, otro tipo u otra identidad →
   `409 IDEMPOTENCY_KEY_CONFLICT`.
3. Validación completa de referencias fuera de transacción (regla `422` inexistente / `409` no apta).
4. T1: snapshots congelados, operación `CONFIRM` `PENDING`; su `id` es la clave enviada a Inventory.
5. `POST /inventory-entries`: cantidad en unidad base (`quantity × factor`) y costo por unidad base
   `ROUND_HALF_UP((subtotal − descuento) / cantidad_base, 4)`, **sin impuestos**.
6. T2: número del período (contador asignado en la misma transacción), `CONFIRMED`, `SUCCEEDED`,
   auditoría. Un rechazo definitivo deja la operación `FAILED` y la compra en borrador sin consumir
   número. Si Inventory no responde, la operación queda `PENDING` (`503` con `operation_id`).
7. Si Inventory aplicó la entrada pero la numeración ya no es posible (secuencia desactivada, agotada o
   número repetido), se **compensa**: reverso con clave derivada, como usuario operativo el que inició la
   confirmación (`application_user_id` de la operación, inmutable), y operación `FAILED`; si el reverso no
   puede aplicarse, la operación queda `PENDING` con `error_code = COMPENSATION_PENDING`, visible en
   `GET /purchase-operations/{id}`, y el conciliador lo reintenta.

Anular: borrador → local; confirmada → reverso de exactamente `inventory_operation_id`;
`ENTRY_LAYER_CONSUMED` → `409 INVENTORY_ALREADY_CONSUMED` y la compra sigue `CONFIRMED`.

## Procesos

| Proceso | Comando | Notas |
| --- | --- | --- |
| API | `uvicorn purchase_service.main:app` | Puerto interno `8000` (host `8107`) |
| Worker de auditoría | `python -m sio_audit.worker` | Entrega `audit_outbox` a Audit con el cliente `purchase-service` |
| Conciliador | `python -m purchase_service.reconciler` (`--once`, `--check`) | Cada `PURCHASE_RECONCILER_INTERVAL_SECONDS` toma operaciones `PENDING` más antiguas que `PURCHASE_RECONCILER_THRESHOLD_SECONDS`, consulta Inventory por clave y las completa o cierra; nunca vuelve a aplicar |

Identidad de los procesos internos (D1, D22): el conciliador registra `updated_by =
system:purchase-reconciler`.

## Dependencias

Ver `specs/014-purchase-core/contracts/dependencies.md`. Un único adaptador real por dependencia, sin
modos de entorno; las pruebas inyectan dobles por DI. Identidad técnica: cliente `purchase-service`
(`client_credentials`, secreto `PURCHASE_SERVICE_CLIENT_SECRET` solo en `infrastructure/.env`).
`operational-access` siempre con el token del usuario.

## Configuración

Variables en `.env.example` (copiar a `.env`; nunca versionar secretos). Payment Reference se configura
**sin** `/api/v1`.

## Base de datos

```bash
docker compose --file ../../infrastructure/services/purchase-service.yaml --env-file ../../infrastructure/.env up -d purchase-db
alembic upgrade head            # en el contenedor: docker exec sio-purchase-service alembic upgrade head
```

Migración `0001`: tablas, restricciones nombradas, índices únicos parciales (número por empresa, una
secuencia activa por alcance, una operación `PENDING` por compra) y triggers de inmutabilidad y ciclo
de vida. Sin datos iniciales (las secuencias las crea el administrador).

## Pruebas

```bash
docker compose --file ../../infrastructure/services/purchase-service.yaml --env-file ../../infrastructure/.env --profile test up -d purchase-test-db
.venv/Scripts/python.exe -m pytest                     # unitarias, contrato, API, ejemplos
.venv/Scripts/python.exe -m pytest -m integration      # servicios reales (detiene y reinicia contenedores)
.venv/Scripts/python.exe -m pytest -m performance      # SC-001, SC-002, SC-005
```

No ejecutar en paralelo suites que usen la misma base de pruebas.

## Permisos

`perm:purchase:{purchases,purchase_details,purchase_lifecycle_events,purchase_sequences,purchase_operations}:{create,read,update,delete}`.
Todas las rutas exigen usuario humano; escribir compras, líneas e hitos y confirmar o anular exige
además asignación a la sucursal. Ver `docs/ejemplo/usuarios-y-permisos.md`.

## Ejemplos

`docs/ejemplo/` (Principio XXII): ejercicios generados y verificados por `tests/examples`.

## Fuera de alcance

Publicación a Finance (la compra conserva `due_date` y la condición para una integración futura),
multimoneda, recepción parcial, devoluciones, aprobaciones.

## Entorno

Proyecto Compose único `infrastructure/services/purchase-service.yaml` (proyecto `purchase-service`):
`purchase-db`, `purchase-test-db` (perfil `test`), `purchase-service`, `purchase-audit-outbox-worker`,
`purchase-reconciler`.
