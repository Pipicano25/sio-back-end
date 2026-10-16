# purchase-service

Microservicio de **compras** de SIO (`specs/014-purchase-core/`, con los cambios de
`specs/020-mvp-commercial-rules/`): registra compras de contado en borrador, las confirma con su número
oficial (sin mover inventario), ingresa la mercancía en Inventory con su costo cuando se confirma su
**recepción física completa**, las anula (localmente si no se recibieron; revirtiendo exactamente su
entrada si se recibieron), administra la numeración por período y registra los hitos logísticos.

## Reglas de la spec 020

- **Recepción** (`POST /companies/{c}/purchases/{id}/receipt`, `{version, full_receipt_confirmed: true}`,
  `Idempotency-Key`, permiso `purchases:update`): única operación que aplica la entrada en Inventory; solo
  completa (sin parciales ni diferencias); `receipt_status` = `PENDING`/`RECEIVED`, `received_at`,
  `received_by_user_id`. Una segunda recepción → `409 PURCHASE_ALREADY_RECEIVED`.
- **Solo contado**: condición de tipo `CREDIT`/`FINANCING` → `409 PAYMENT_CONDITION_NOT_AVAILABLE`;
  `ck_purchases_cash_only`.
- **Medio de pago** declarado (`payment_method_id`, uno activo de Payment Reference; no registra pagos).
- **Presentación obligatoria** en toda línea (la de factor 1 para la unidad) y **costos > 0**
  (`UNIT_COST_NOT_POSITIVE`, `NET_COST_NOT_POSITIVE`, `BASE_UNIT_COST_NOT_POSITIVE`).
- Hitos `RECEIVED`/`AVAILABLE_FOR_SALE` solo en compras recibidas (`409 PURCHASE_NOT_RECEIVED`).
- **Cargue inicial**: compras normales identificadas con `observations` (no se filtra ni se audita); aparecen
  en los reportes como compras normales.

## Reglas de la spec 021

`specs/021-automatic-purchase-pricing/` (precios automáticos por recepción):

- **Impuesto por tasa:** la línea ya no recibe `tax_amount` (un campo desconocido da `422`). Purchase lo calcula con
  `ROUND_HALF_UP((subtotal − descuento) × tasa / 100, 2)`, con la tasa de compra del producto en Commercial
  Relationship (`tax_percentage_source = PRODUCT_DEFAULT`) o la de la factura (`LINE_OVERRIDE`, permiso
  `perm:purchase:purchase_line_taxes:override`, auditada como `OVERRIDE_PURCHASE_LINE_TAX`). Sin tasa la línea
  tiene la advertencia `PURCHASE_TAX_NOT_CONFIGURED` y la compra no se confirma (`409`); si la tasa del producto
  cambió desde que se guardó la línea, `409 PURCHASE_TAX_CHANGED`.
- **Una presentación por compra:** `409 DUPLICATE_PRESENTATION_IN_PURCHASE` al crear, agregar o editar líneas y al
  confirmar (`uq_purchase_details_purchase_presentation`).
- **Hechos de costo:** en la T2 de la recepción se actualiza `purchase_presentation_cost_series` y se escribe una fila
  de `purchase_price_update_outbox` por línea (contrato v1, secuencia contigua por presentación). La anulación no
  los modifica (M-1). El costo que recibe Inventory no cambia (sin impuestos; FIFO intacto).
- **Entrega:** el proceso `purchase-price-update-worker` los entrega a Commercial Relationship por HTTP (excepción
  EXC-001 a D6, solo esta spec). La recepción nunca depende de esa entrega.

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
| `purchase_presentation_cost_series` | Spec 021: última recepción por empresa y presentación (secuencia y hechos de costo) |
| `purchase_price_update_outbox` | Spec 021: solicitudes de actualización de precio pendientes de entregar a Commercial Relationship |

Snapshots (nombre e identificación del proveedor, código y nombre del producto, presentación, unidad,
factor, lead time esperado, condición de pago): **excepción documentada al Principio III** (DS-02).
Son provisionales en el borrador y se refrescan y **congelan al confirmar**; después no cambian.

## Flujo de confirmación y recepción (research.md R-04, R-05; spec 020)

1. Acceso: usuario humano con `perm:purchase:purchases:update`, membresía y asignación `ACTIVE` a la
   sucursal de la compra. `Idempotency-Key` obligatoria, ligada a compra, tipo y `sub`.
2. **Confirmación** (local, una transacción): validación completa de referencias, número del período,
   `CONFIRMED`, operación `CONFIRM` `SUCCEEDED` y auditoría. Sin Inventory: la compra queda pendiente de
   recepción. Un error de numeración responde `409` sin efectos (no hay compensación).
3. **Recepción**: T1 operación `RECEIVE` `PENDING` (su `id` es la clave enviada a Inventory);
   `POST /inventory-entries` con cantidad en unidad base (`quantity × factor`) y costo por unidad base
   `ROUND_HALF_UP((subtotal − descuento) / cantidad_base, 4)`, **sin impuestos**; T2 `received_at`,
   `received_by_user_id`, `inventory_operation_id`, `SUCCEEDED`, auditoría `RECEIVE_PURCHASE`. Si Inventory
   no responde, la operación queda `PENDING` (`503` con `operation_id`) para el reintento o el conciliador.

Anular: borrador o confirmada sin recibir → local; recibida → reverso de exactamente
`inventory_operation_id`; `ENTRY_LAYER_CONSUMED` → `409 INVENTORY_ALREADY_CONSUMED` y la compra sigue
`CONFIRMED`.

## Procesos

| Proceso | Comando | Notas |
| --- | --- | --- |
| API | `uvicorn purchase_service.main:app` | Puerto interno `8000` (host `8107`) |
| Worker de auditoría | `python -m sio_audit.worker` | Entrega `audit_outbox` a Audit con el cliente `purchase-service` |
| Conciliador | `python -m purchase_service.reconciler` (`--once`, `--check`) | Cada `PURCHASE_RECONCILER_INTERVAL_SECONDS` toma operaciones `PENDING` (recepciones y anulaciones de compras recibidas) más antiguas que `PURCHASE_RECONCILER_THRESHOLD_SECONDS`, consulta Inventory por clave y las completa o cierra (`OPERATION_NOT_APPLIED`); nunca vuelve a aplicar |

| Entrega de precios (spec 021) | `python -m purchase_service.price_update_worker` (`--once`, `--check`) | Entrega `purchase_price_update_outbox` a `POST /companies/{c}/automatic-price-update-requests` de Commercial Relationship con el cliente `purchase-service`, en orden de secuencia por presentación; espera creciente ante fallos; un `409` no se reintenta automáticamente. Variables `PURCHASE_PRICE_WORKER_*` |

Identidad de los procesos internos (D1, D22): el conciliador registra `updated_by =
system:purchase-reconciler`.

## Dependencias

Ver `specs/014-purchase-core/contracts/dependencies.md`. Un único adaptador real por dependencia, sin
modos de entorno; las pruebas inyectan dobles por DI. Identidad técnica: cliente `purchase-service`
(`client_credentials`, secreto `PURCHASE_SERVICE_CLIENT_SECRET` solo en `infrastructure/.env`).
`operational-access` siempre con el token del usuario.

Spec 021: la tasa de compra se lee del `batch-lookup` de productos de Commercial Relationship (clase C, ya existente)
y el worker de entrega llama a la ruta técnica de precios de Commercial Relationship (clase C) con el token
`client_credentials` de Keycloak (clase B). No hay dependencias de clase D.

## Configuración

Variables en `.env.example` (copiar a `.env`; nunca versionar secretos). Payment Reference se configura
**sin** `/api/v1`.

## Base de datos

```bash
docker compose --file ../../infrastructure/services/purchase-service.yaml --env-file ../../infrastructure/.env up -d purchase-db
alembic upgrade head            # en el contenedor: docker exec sio-purchase-service alembic upgrade head
```

Migración `0003` (spec 021): `tax_percentage` y `tax_percentage_source` en las líneas, la restricción única de
presentación por compra (con guarda: se detiene si ya hay duplicados), la serie de costos y el outbox de precios.

Migración `0002` (spec 020): recepción, solo contado, medio de pago, presentación y costo > 0, con guardas
que la detienen sin cambios ante datos incompatibles.

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

`perm:purchase:{purchases,purchase_details,purchase_lifecycle_events,purchase_sequences,purchase_operations}:{create,read,update,delete}`
y, desde la spec 021, `perm:purchase:purchase_line_taxes:override` (solo administradores y supervisores).
Todas las rutas exigen usuario humano; escribir compras, líneas e hitos y confirmar o anular exige
además asignación a la sucursal. Ver `docs/ejemplo/usuarios-y-permisos.md`.

## Ejemplos

`docs/ejemplo/` (Principio XXII): ejercicios generados y verificados por `tests/examples`.

## Fuera de alcance

Publicación a Finance (la compra conserva `due_date` y la condición para una integración futura),
multimoneda, recepción parcial o por línea, crédito y financiación (spec 020), pagos registrados y cuentas
por pagar, devoluciones, aprobaciones.

## Entorno

Proyecto Compose único `infrastructure/services/purchase-service.yaml` (proyecto `purchase-service`):
`purchase-db`, `purchase-test-db` (perfil `test`), `purchase-service`, `purchase-audit-outbox-worker`,
`purchase-reconciler` y `purchase-price-update-worker` (spec 021).

**Limitación (R-12):** el impuesto de compra forma parte del costo real que usa la actualización automática de
precios; Sales no agrega impuesto a la venta (provisional, **no es una solución fiscal**).
