# sales-service

Microservicio de **ventas** de SIO (`specs/015-sales-core/`, con los cambios de `specs/020-mvp-commercial-rules/` y
`specs/021-automatic-purchase-pricing/`): registra ventas en borrador con el precio
que resuelve Commercial Relationship, consulta existencias, confirma descontando el inventario de la
sucursal con su costo FIFO y su número oficial, y anula revirtiendo exactamente la salida.

## Responsabilidad y entidades

| Tabla | Rol |
| --- | --- |
| `sales` | Cabecera: cliente, sucursal, fecha de negocio (la del día en que se confirma), solo contado (`CASH`, `due_date = operation_date`), moneda (la `default_currency` de la empresa), totales, número, estado `DRAFT`/`CONFIRMED`/`CANCELLED`, `inventory_operation_id`, `has_unknown_cost` |
| `sale_details` | Líneas (1–100): producto empresarial, presentación (obligatoria, spec 019), precio resuelto (`unit_price`, `price_list_id`, `price_list_item_id`, `price_list_requested`), cantidad, descuento, impuesto, snapshots, costo FIFO (`unit_cost_snapshot` por unidad base, `cost_total`, `cost_known`) y margen |
| `sale_sequences` | Numeración por empresa o sucursal; a lo sumo una activa por empresa, sucursal y tipo |
| `sale_sequence_counters` | Contador independiente por período (`''` continuo, `YYYY`, `YYYYMM`) |
| `sale_operations` | Confirmación o anulación distribuida (`PENDING`/`SUCCEEDED`/`FAILED`), clave de idempotencia, `inventory_operation_id`, usuario operativo que la inició y motivo (inmutables; `error_details` solo errores) |
| `audit_outbox` | Transactional Outbox de `sio-audit` |

Snapshots (nombre e identificación del cliente, código y nombre del producto, presentación, unidad,
factor): **excepción documentada al Principio III** (DS-02). Son provisionales en el borrador y se
refrescan y **congelan al confirmar**; después no cambian. El precio, el costo y el margen de una venta
confirmada no se recalculan nunca (RN-04).

## Reglas de la venta

- **Precio** (R-07): siempre lo resuelve Commercial Relationship (`applicable-prices/resolve`); no hay
  precio manual (`422 UNIT_PRICE_NOT_ALLOWED`). Toda línea indica su presentación, también la de factor 1
  para vender la unidad base (spec 019; sin ella, `422`). Se usa solo el precio explícito de esa
  presentación en la lista pedida o en la predeterminada, tal cual y sin conversiones entre presentaciones;
  `price_list_requested` guarda la intención. Sin precio vigente la línea se rechaza (`409 PRICE_NOT_IN_LIST`
  o `PRICE_NOT_AVAILABLE`). No hay precio del producto ni respaldo (`COMPANY_PRODUCT_SALE_PRICE` solo
  aparece en ventas anteriores a la spec 019).
  Si Commercial Relationship dice que la lista pedida no es aplicable, Sales consulta la lista:
  inexistente → `422 PRICE_LIST_NOT_FOUND`; existe → `409 PRICE_LIST_NOT_APPLICABLE`.
- **Solo contado** (DP-01): no se acepta condición de pago ni fecha; `operation_date` es la fecha del
  día en la zona horaria de la sucursal y se fija al confirmar.
- **Medio de pago** (spec 020, FR-020-09): `payment_method_id` obligatorio, un único método `ACTIVE` de
  Payment Reference (`PAYMENT_METHOD_NOT_FOUND` `422`, `PAYMENT_METHOD_INACTIVE` `409`), con copia de su
  código y nombre que se refresca y congela al confirmar. Es **declarativo**: no registra ni comprueba pagos.
- **Sin descuentos** (spec 020, FR-020-13): `discount_amount` se conserva por compatibilidad y solo admite
  `0` (`422 DISCOUNT_NOT_ALLOWED`); la base lo garantiza (`ck_sale_details_no_discount`).
- **Sin impuesto adicional** (spec 021, provisional): `tax_amount` solo admite `0` (`422 TAX_NOT_ALLOWED`, también
  al confirmar); la base lo garantiza (`ck_sale_details_no_tax`). El precio de la lista es el **importe final** que
  paga el cliente. **No es una solución fiscal** (R-12): no hay facturación electrónica ni discriminación de IVA.
- **Precios automáticos** (spec 021): el precio de una lista con políticas lo actualiza Commercial Relationship con
  cada recepción de compra. Sales no cambia: vende con el precio vigente al resolverlo, aunque haya
  actualizaciones pendientes, y conserva `409 PRICES_CHANGED` si cambió antes de confirmar. El margen sigue siendo
  (subtotal − descuento) − costo FIFO de Inventory; no es el recargo de la política.
- **Costo y margen** (R-10): el costo FIFO lo informa Inventory en la salida y se copia sin convertir
  ni recalcular. Margen = (subtotal − descuento) − costo; porcentaje nulo si el neto es 0 o si no cabe en
  `NUMERIC(7,4)`; con costo desconocido (`cost_known = false`) los márgenes quedan nulos y la cabecera
  marca `has_unknown_cost`. El log `sales.margin.percentage_outcome` registra el motivo por línea.
- **Rentabilidad** (DS-12): costo, `cost_known`, márgenes y `has_unknown_cost` solo aparecen con
  `perm:sales:sales:read-profitability` (grupos `supervisores` y `administradores`); sin él se omiten
  de todas las respuestas. Los eventos de auditoría nunca los incluyen.

## Flujo de confirmación (research.md R-04, R-05)

1. Acceso: usuario humano con `perm:sales:sales:update`, membresía y asignación `ACTIVE` a la sucursal.
2. `Idempotency-Key` obligatoria, ligada a venta, tipo y `sub`. Con una operación en curso → `409
   OPERATION_IN_PROGRESS` antes que cualquier otro conflicto.
3. En paralelo y fuera de transacción: referencias y **nueva resolución del precio** (si cambió precio,
   lista o ítem → `409 PRICES_CHANGED` sin efectos), usuario operativo y saldos de la sucursal (consulta
   previa informativa: faltante → `409 INSUFFICIENT_STOCK`; si Inventory no responde se omite).
4. T1: `operation_date` y `due_date` del día, snapshots congelados, operación `CONFIRM` `PENDING`; su
   `id` es la clave enviada a Inventory. Un reintento o el conciliador conservan esa fecha.
5. `POST /inventory-outputs`: cantidades en unidad base (`quantity × factor`), **sin costo**.
6. T2: costo y margen por línea, número del período, `CONFIRMED`, `SUCCEEDED`, auditoría. Saldo
   insuficiente en Inventory (la barrera real) → `409 INSUFFICIENT_STOCK` y la venta sigue en borrador.
   Si Inventory no responde, la operación queda `PENDING` (`503` con `operation_id`).
7. Si la salida se aplicó pero la numeración ya no es posible, se **compensa**: reverso de la salida
   con clave derivada y el usuario que inició la confirmación; si el reverso falla, la operación queda
   `PENDING` con `error_code = COMPENSATION_PENDING`, visible y reintentada por el conciliador.

Anular: borrador → local; confirmada → reverso de exactamente `inventory_operation_id` (Inventory
restituye cantidad y costo).

## Procesos

| Proceso | Comando | Notas |
| --- | --- | --- |
| API | `uvicorn sales_service.main:app` | Puerto interno `8000` (host `8108`) |
| Worker de auditoría | `python -m sio_audit.worker` | Entrega `audit_outbox` a Audit con el cliente `sales-service` |
| Conciliador | `python -m sales_service.reconciler` (`--once`, `--check`) | Cada `SALES_RECONCILER_INTERVAL_SECONDS` toma operaciones `PENDING` más antiguas que `SALES_RECONCILER_THRESHOLD_SECONDS`, consulta Inventory por clave y las completa (con el costo de la salida) o cierra; nunca vuelve a aplicar |

Identidad de los procesos internos (D1, D22): el conciliador registra `updated_by =
system:sales-reconciler`.

El healthcheck del conciliador (`python -m sales_service.reconciler --check`) tiene `timeout: 20s`
(D-04): arranca un intérprete nuevo e importa el motor de operaciones antes de comprobar la base, y
en un entorno local cargado esa importación tarda de 6 a 10 s; con 5 s el contenedor quedaba
`unhealthy` aunque el proceso funcionaba (`--check` devolvía 0).

## Dependencias

Ver `specs/015-sales-core/contracts/dependencies.md`. Spec 020: Payment Reference
(`GET /global-payment-methods/{id}`, `PAYMENT_REFERENCE_SERVICE_BASE_URL` **sin** `/api/v1`, permiso técnico
`perm:payment-reference:global_payment_methods:read`). Un único adaptador real por dependencia, sin
modos de entorno; las pruebas inyectan dobles por DI. Identidad técnica: cliente `sales-service`
(`client_credentials`, secreto `SALES_SERVICE_CLIENT_SECRET` solo en `infrastructure/.env`), renovado en
segundo plano antes de expirar. `operational-access` siempre con el token del usuario.

## Configuración

Variables en `.env.example` (copiar a `.env`; nunca versionar secretos). Sin Payment Reference: el MVP
solo vende de contado.

## Base de datos

```bash
docker compose --file ../../infrastructure/services/sales-service.yaml --env-file ../../infrastructure/.env up -d sales-db
alembic upgrade head            # en el contenedor: docker exec sio-sales-service alembic upgrade head
```

Migración `0003` (spec 021): `ck_sale_details_no_tax` (`tax_amount = 0`); se detiene sin cambios si alguna línea
tiene impuesto.

Migración `0002` (spec 020): medio de pago (columnas, `ck_sales_payment_method_*`), ventas sin descuento y
trigger de inmutabilidad reemplazado; se detiene sin cambios si hay descuentos o ventas fuera de `DRAFT`.

Migración `0001`: tablas, restricciones nombradas (incluida `ck_sales_cash_only`), índices únicos
parciales (número por empresa, una secuencia activa por alcance, una operación `PENDING` por venta) y
triggers de inmutabilidad y ciclo de vida. Sin datos iniciales (las secuencias las crea el administrador).

## Pruebas

```bash
docker compose --file ../../infrastructure/services/sales-service.yaml --env-file ../../infrastructure/.env --profile test up -d sales-test-db
.venv/Scripts/python.exe -m pytest                     # unitarias, contrato, API, ejemplos
SIO_TEST_TARGET=isolated .venv/Scripts/python.exe -m pytest -m integration   # solo la pila aislada sio-it-*
.venv/Scripts/python.exe -m pytest -m performance      # SC-001, SC-002, SC-003, SC-005
```

Las pruebas de integración escriben en servicios reales: **solo** se ejecutan contra la pila aislada `sio-it-*` con `SIO_TEST_TARGET=isolated` y las URL de esa pila. La barrera `validation/isolation_guard.py` hace fallar la sesión antes de la primera solicitud si algún destino no es un contenedor con `sio.integration.isolated=true` (incidente del 2026-10-16); `localhost` no basta.

No ejecutar en paralelo suites que usen la misma base de pruebas.

## Permisos

`perm:sales:{sales,sale_details,sale_sequences,sale_operations}:{create,read,update,delete}` y
`perm:sales:sales:read-profitability`. Todas las rutas exigen usuario humano; escribir ventas y líneas,
confirmar y anular exige además asignación a la sucursal. Ver `docs/ejemplo/usuarios-y-permisos.md`.

## Ejemplos

`docs/ejemplo/` (Principio XXII): ejercicios generados y verificados por `tests/examples`.

## Fuera de alcance

Crédito, financiación y perfil crediticio del cliente (POST-MVP), publicación a Finance (la venta
conserva `due_date`), multimoneda, precio manual, descuentos y políticas de descuento (spec 020), pagos
registrados, pagos divididos, cartera, promociones, reservas de existencias, devoluciones y
notas crédito.

## Entorno

Proyecto Compose único `infrastructure/services/sales-service.yaml` (proyecto `sales-service`):
`sales-db`, `sales-test-db` (perfil `test`), `sales-service`, `sales-audit-outbox-worker`,
`sales-reconciler`.

## Agregaciones para reportes (spec 023)

Solo lectura, para `business-reporting-service` (que las llama con el token del usuario): `GET
/api/v1/companies/{c}/sales-aggregates/by-product` (SAL-R1) y `…/by-branch` (SAL-R2). Permiso
`perm:sales:sales:read` y membresía; solo ventas `CONFIRMED` con `operation_date` en el período (máximo 366 días);
cantidades en unidad base con el factor guardado en la línea; importes por moneda; sin costos ni márgenes. Se
calculan con `GROUP BY` sobre `ix_sales_company_date` y `uq_sale_details_line_number`, sin migraciones.
