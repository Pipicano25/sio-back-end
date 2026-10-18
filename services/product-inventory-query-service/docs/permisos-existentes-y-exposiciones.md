# Permisos existentes que exponen información económica fuera de este servicio

**Origen:** spec 022, tarea T059 (A-10, D-022-2). **Fecha de revisión:** 2026-10-17.
**Fuente:** `infrastructure/keycloak/realm-template/sio-realm.template.json` y los esquemas de respuesta de cada servicio.

`product-inventory-query-service` nunca entrega costos, costo promedio, costo FIFO, márgenes, porcentajes de
ganancia ni valoración económica: la valoración quedó fuera del alcance de la spec 022 (decisión del usuario del
2026-10-17) y queda para una spec futura. Sin embargo,
algunos grupos **ya tienen** permisos sobre las API originales con los que pueden ver esa información directamente,
sin pasar por este servicio. Este documento solo los registra: **no se cambió ningún permiso**. Cada acción
propuesta requiere una autorización aparte y su propia evaluación de impacto.

## Hallazgos

| # | Grupo | Permiso existente | Qué expone | Dónde |
|---|---|---|---|---|
| 1 | `inventario` | `perm:inventory:balances:read` | `average_unit_cost` e `inventory_value` de cada saldo | `GET …/balances`, `…/balances/{id}`, `POST …/balances/lookup` de Inventory |
| 2 | `inventario` | `perm:inventory:valuation:read` | Valoración por producto, capas FIFO con costo unitario y consumos de costo | `GET …/valuation`, `…/valuation/{id}/layers`, `…/cost-consumptions` de Inventory |
| 3 | `inventario` | `perm:inventory:movements:read` | `unit_cost` y `movement_value` de cada movimiento del kardex | `GET …/kardex/{id}` e `inventory-operations` de Inventory |
| 4 | `inventario` | `perm:inventory:adjustments:read`, `perm:inventory:counts:read` | Costo unitario y valor de ajustes y conteos | Rutas de ajustes y conteos de Inventory |
| 5 | `compras`, `reportes`, `consulta` | `perm:purchase:purchases:read`, `perm:purchase:purchase_details:read` | Importes y costos de compra por línea | API de Purchase |
| 6 | `ventas`, `compras`, `reportes`, `consulta` | `perm:commercial-relationship:price_list_items:read`, `price_lists:read` | Precios de venta de las listas | API de Commercial Relationship (es información comercial, no de costo) |
| 7 | `ventas`, `compras`, `reportes`, `consulta` | `perm:commercial-relationship:product_pricing_policies:read` | Ningún endpoint vigente usa ese recurso: las políticas de ganancia de la spec 021 usan `pricing_policies`, que esos grupos **no** tienen | Plantilla del realm (permiso sin uso) |
| 8 | Grupos con `perm:product-catalog:all:read` (`ventas`, `inventario`, `compras`) | Lectura del catálogo | Contenido de los activos por la ruta protegida `…/assets/{id}/content` | API de Product Catalog (catálogo global, sin datos de empresa) |

`supervisores` (`perm:all:all:read`) y `administradores` (`perm:all:all:all`) ven todo por diseño.

## Consecuencias para la spec 022

- **D-022-1 resuelto:** `ventas` ve existencias solo con `perm:product-inventory-query:stock:read` y nunca recibe
  `perm:inventory:balances:read`, así que no gana acceso al hallazgo 1.
- **D-022-2:** nadie ve la valoración en este servicio, pero `inventario` **sí** la ve en Inventory por los
  hallazgos 1 a 4. La decisión aprobada fue no modificar automáticamente los permisos actuales de Inventory, ni la
  valoración existente de Inventory.

## Permisos de la spec 022 que quedan sin uso

| Permiso | Dónde está | Situación |
|---|---|---|
| `perm:product-inventory-query:inventory_valuation:read` | Rol de cliente de la plantilla, sin grupo, usuario ni cuenta asignados | Ningún endpoint lo evalúa; reservado para una spec futura de valoración |
| `perm:inventory:valuation:read` | **Retirado** del cliente técnico `product-inventory-query-service` (autorizado el 2026-10-18) | El servicio no pide valoración a INV-3; el grupo `inventario` y los demás roles de Inventory lo conservan |

## Acciones propuestas (requieren autorización)

1. Decidir si `inventario` debe conservar `balances:read`, `valuation:read`, `movements:read` y las lecturas de
   ajustes y conteos sobre la API de Inventory, o si sus consultas operativas pasan a este servicio. Retirarlos
   puede afectar pantallas y ejercicios actuales de Inventory.
2. Evaluar si Inventory debería ofrecer una vista de saldos **sin costo** para perfiles operativos, en una spec
   propia.
3. Evaluar si `compras`, `reportes` y `consulta` deben ver los costos de compra por línea en Purchase.
4. Retirar `perm:commercial-relationship:product_pricing_policies:read` de la plantilla si se confirma que no tiene
   uso (hallazgo 7).
5. Decidir si se conserva el rol sin asignar `perm:product-inventory-query:inventory_valuation:read` hasta la spec
   de valoración. (El retiro de `perm:inventory:valuation:read` del cliente técnico ya se aplicó en la plantilla.)

Ninguna de estas acciones forma parte de la spec 022.
