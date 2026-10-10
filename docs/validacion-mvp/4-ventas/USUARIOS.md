# Usuarios y permisos — Ejercicio 4 — Ventas con los tres mecanismos de precio, rechazos, costo FIFO y margen

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

✅ = el usuario tiene el permiso (o los permisos) de la llamada según la plantilla del realm · ❌ = recibe `403`. Tener el permiso no basta en las rutas de empresa: fuera de sus empresas el usuario recibe `404` (aislamiento).

| Paso | Id | Método y ruta | Permiso requerido | Usuario del recorrido | admin | compras | ventas | supervisor | consulta | reportes | inventario |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-registrar-las-ventas.md) | `V-01.V1` | `POST /companies/<EMPRESA_A>/sales` | `perm:sales:sales:create` + `perm:sales:sale_details:create` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [01](01-registrar-las-ventas.md) | `V-01.V2` | `POST /companies/<EMPRESA_A>/sales` | `perm:sales:sales:create` + `perm:sales:sale_details:create` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [01](01-registrar-las-ventas.md) | `V-01.V3` | `POST /companies/<EMPRESA_A>/sales` | `perm:sales:sales:create` + `perm:sales:sale_details:create` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [01](01-registrar-las-ventas.md) | `V-01.V4` | `POST /companies/<EMPRESA_A>/sales` | `perm:sales:sales:create` + `perm:sales:sale_details:create` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [01](01-registrar-las-ventas.md) | `V-01.V5` | `POST /companies/<EMPRESA_A>/sales` | `perm:sales:sales:create` + `perm:sales:sale_details:create` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [01](01-registrar-las-ventas.md) | `V-01.V6` | `POST /companies/<EMPRESA_A>/sales` | `perm:sales:sales:create` + `perm:sales:sale_details:create` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [01](01-registrar-las-ventas.md) | `V-01.V7` | `POST /companies/<EMPRESA_A>/sales` | `perm:sales:sales:create` + `perm:sales:sale_details:create` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [02](02-consultar-la-disponibilidad.md) | `V-02.V2` | `GET /companies/<EMPRESA_A>/sales/<VENTA_2>/availability` | `perm:sales:sales:read` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [02](02-consultar-la-disponibilidad.md) | `V-02.V4` | `GET /companies/<EMPRESA_A>/sales/<VENTA_4>/availability` | `perm:sales:sales:read` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [03](03-confirmar-las-ventas.md) | `V-03.V1` | `POST /companies/<EMPRESA_A>/sales/<VENTA_1>/confirmation` | `perm:sales:sales:update` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [03](03-confirmar-las-ventas.md) | `V-03.V2` | `POST /companies/<EMPRESA_A>/sales/<VENTA_2>/confirmation` | `perm:sales:sales:update` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [03](03-confirmar-las-ventas.md) | `V-03.V3` | `POST /companies/<EMPRESA_A>/sales/<VENTA_3>/confirmation` | `perm:sales:sales:update` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [04](04-rechazo-por-existencias-insuficientes.md) | `V-04.V4` | `POST /companies/<EMPRESA_A>/sales/<VENTA_4>/confirmation` | `perm:sales:sales:update` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [05](05-rechazo-por-precio-cambiado.md) | `V-05.cambio` | `POST /price-list-items/<ITEM_GENERAL>/change-price` | `perm:commercial-relationship:price_list_items:update` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [05](05-rechazo-por-precio-cambiado.md) | `V-05.V5` | `POST /companies/<EMPRESA_A>/sales/<VENTA_5>/confirmation` | `perm:sales:sales:update` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [06](06-rechazo-por-producto-inactivo.md) | `V-05b.inactivar` | `POST /company-products/<PRODUCTO_EMPRESA_B>/deactivate` | `perm:commercial-relationship:company_products:delete` | `admin.test` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [06](06-rechazo-por-producto-inactivo.md) | `V-05b.V7` | `POST /companies/<EMPRESA_A>/sales/<VENTA_7>/confirmation` | `perm:sales:sales:update` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [06](06-rechazo-por-producto-inactivo.md) | `V-05b.reactivar` | `POST /company-products/<PRODUCTO_EMPRESA_B>/reactivate` | `perm:commercial-relationship:company_products:update` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [07](07-costo-y-margen-segun-el-permiso.md) | `V-06.vendedor` | `GET /companies/<EMPRESA_A>/sales/<VENTA_2>` | `perm:sales:sales:read` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [07](07-costo-y-margen-segun-el-permiso.md) | `V-06.supervisor` | `GET /companies/<EMPRESA_A>/sales/<VENTA_2>` | `perm:sales:sales:read` + `perm:sales:sales:read-profitability` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [08](08-consultar-el-inventario-tras-las-ventas.md) | `V-07.saldo_a` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_A>` | `perm:inventory:balances:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [08](08-consultar-el-inventario-tras-las-ventas.md) | `V-07.saldo_b` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_B>` | `perm:inventory:balances:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [08](08-consultar-el-inventario-tras-las-ventas.md) | `V-07.kardex_a` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_A>` | `perm:inventory:movements:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [08](08-consultar-el-inventario-tras-las-ventas.md) | `V-07.kardex_b` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_B>` | `perm:inventory:movements:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [08](08-consultar-el-inventario-tras-las-ventas.md) | `V-07.capas_a` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_A>/layers` | `perm:inventory:valuation:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [08](08-consultar-el-inventario-tras-las-ventas.md) | `V-07.capas_b` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_B>/layers` | `perm:inventory:valuation:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [08](08-consultar-el-inventario-tras-las-ventas.md) | `V-07.consumos_v1` | `GET /companies/<EMPRESA_A>/inventory-movements/<MOVIMIENTO_V1>/cost-consumptions` | `perm:inventory:valuation:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [08](08-consultar-el-inventario-tras-las-ventas.md) | `V-07.consumos_v2` | `GET /companies/<EMPRESA_A>/inventory-movements/<MOVIMIENTO_V2>/cost-consumptions` | `perm:inventory:valuation:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [08](08-consultar-el-inventario-tras-las-ventas.md) | `V-07.consumos_v3` | `GET /companies/<EMPRESA_A>/inventory-movements/<MOVIMIENTO_V3>/cost-consumptions` | `perm:inventory:valuation:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
