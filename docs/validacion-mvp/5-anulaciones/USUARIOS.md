# Usuarios y permisos — Ejercicio 5 — Anulaciones y reversos

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

✅ = el usuario tiene el permiso (o los permisos) de la llamada según la plantilla del realm · ❌ = recibe `403`. Tener el permiso no basta en las rutas de empresa: fuera de sus empresas el usuario recibe `404` (aislamiento).

| Paso | Id | Método y ruta | Permiso requerido | Usuario del recorrido | admin | compras | ventas | supervisor | consulta | reportes | inventario |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-anular-borradores-y-documentos-confirmados.md) | `A-01.P4` | `POST /companies/<EMPRESA_A>/purchases/<COMPRA_4>/cancellation` | `perm:purchase:purchases:delete` | `compras.test` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [01](01-anular-borradores-y-documentos-confirmados.md) | `A-01.V6` | `POST /companies/<EMPRESA_A>/sales/<VENTA_6>/cancellation` | `perm:sales:sales:delete` | `ventas.test` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| [01](01-anular-borradores-y-documentos-confirmados.md) | `A-01.V3` | `POST /companies/<EMPRESA_A>/sales/<VENTA_3>/cancellation` | `perm:sales:sales:delete` | `ventas.test` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| [01](01-anular-borradores-y-documentos-confirmados.md) | `A-01.P3` | `POST /companies/<EMPRESA_A>/purchases/<COMPRA_3>/cancellation` | `perm:purchase:purchases:delete` | `compras.test` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [01](01-anular-borradores-y-documentos-confirmados.md) | `A-01.operaciones_V3` | `GET /companies/<EMPRESA_A>/sales/<VENTA_3>/operations` | `perm:sales:sale_operations:read` | `ventas.test` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [01](01-anular-borradores-y-documentos-confirmados.md) | `A-01.operaciones_P3` | `GET /companies/<EMPRESA_A>/purchases/<COMPRA_3>/operations` | `perm:purchase:purchase_operations:read` | `compras.test` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| [02](02-rechazo-al-anular-una-compra-consumida.md) | `A-02.P1` | `POST /companies/<EMPRESA_A>/purchases/<COMPRA_1>/cancellation` | `perm:purchase:purchases:delete` | `compras.test` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [03](03-consultar-el-inventario-final.md) | `A-03.saldo_a` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_A>` | `perm:inventory:balances:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [03](03-consultar-el-inventario-final.md) | `A-03.saldo_b` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_B>` | `perm:inventory:balances:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [03](03-consultar-el-inventario-final.md) | `A-03.kardex_a` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_A>` | `perm:inventory:movements:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [03](03-consultar-el-inventario-final.md) | `A-03.kardex_b` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_B>` | `perm:inventory:movements:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [03](03-consultar-el-inventario-final.md) | `A-03.capas_a` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_A>/layers` | `perm:inventory:valuation:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [03](03-consultar-el-inventario-final.md) | `A-03.capas_b` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_B>/layers` | `perm:inventory:valuation:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [03](03-consultar-el-inventario-final.md) | `A-03.valoracion` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation` | `perm:inventory:valuation:read` | `supervisor.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
