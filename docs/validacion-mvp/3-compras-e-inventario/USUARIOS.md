# Usuarios y permisos — Ejercicio 3 — Compras e inventario: secuencias, compras de contado, confirmación, recepción física (entradas), saldos, kardex y capas

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

✅ = el usuario tiene el permiso (o los permisos) de la llamada según la plantilla del realm · ❌ = recibe `403`. Tener el permiso no basta en las rutas de empresa: fuera de sus empresas el usuario recibe `404` (aislamiento).

| Paso | Id | Método y ruta | Permiso requerido | Usuario del recorrido | admin | admin | operario |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-crear-las-secuencias-de-numeracion.md) | `C-13.compras` | `POST /companies/<EMPRESA_A>/purchase-sequences` | `perm:purchase:purchase_sequences:create` | `admin.sio` | ✅ | ✅ | ✅ |
| [01](01-crear-las-secuencias-de-numeracion.md) | `C-13.ventas` | `POST /companies/<EMPRESA_A>/sale-sequences` | `perm:sales:sale_sequences:create` | `admin.sio` | ✅ | ✅ | ✅ |
| [02](02-registrar-las-compras.md) | `P-01.P1` | `POST /companies/<EMPRESA_A>/purchases` | `perm:purchase:purchases:create` + `perm:purchase:purchase_details:create` | `operario.dao` | ✅ | ✅ | ✅ |
| [02](02-registrar-las-compras.md) | `P-01.P2` | `POST /companies/<EMPRESA_A>/purchases` | `perm:purchase:purchases:create` + `perm:purchase:purchase_details:create` | `operario.dao` | ✅ | ✅ | ✅ |
| [02](02-registrar-las-compras.md) | `P-01.P3` | `POST /companies/<EMPRESA_A>/purchases` | `perm:purchase:purchases:create` + `perm:purchase:purchase_details:create` | `operario.dao` | ✅ | ✅ | ✅ |
| [02](02-registrar-las-compras.md) | `P-01.P4` | `POST /companies/<EMPRESA_A>/purchases` | `perm:purchase:purchases:create` + `perm:purchase:purchase_details:create` | `operario.dao` | ✅ | ✅ | ✅ |
| [02](02-registrar-las-compras.md) | `P-01.credito` | `POST /companies/<EMPRESA_A>/purchases` | `perm:purchase:purchases:create` | `operario.dao` | ✅ | ✅ | ✅ |
| [03](03-confirmar-las-compras.md) | `P-02.P1` | `POST /companies/<EMPRESA_A>/purchases/<COMPRA_1>/confirmation` | `perm:purchase:purchases:update` | `operario.dao` | ✅ | ✅ | ✅ |
| [03](03-confirmar-las-compras.md) | `P-02.P2` | `POST /companies/<EMPRESA_A>/purchases/<COMPRA_2>/confirmation` | `perm:purchase:purchases:update` | `operario.dao` | ✅ | ✅ | ✅ |
| [03](03-confirmar-las-compras.md) | `P-02.P3` | `POST /companies/<EMPRESA_A>/purchases/<COMPRA_3>/confirmation` | `perm:purchase:purchases:update` | `operario.dao` | ✅ | ✅ | ✅ |
| [04](04-confirmar-la-recepcion-fisica-de-las-compras.md) | `P-02R.P1` | `POST /companies/<EMPRESA_A>/purchases/<COMPRA_1>/receipt` | `perm:purchase:purchases:update` | `operario.dao` | ✅ | ✅ | ✅ |
| [04](04-confirmar-la-recepcion-fisica-de-las-compras.md) | `P-02R.P2` | `POST /companies/<EMPRESA_A>/purchases/<COMPRA_2>/receipt` | `perm:purchase:purchases:update` | `operario.dao` | ✅ | ✅ | ✅ |
| [04](04-confirmar-la-recepcion-fisica-de-las-compras.md) | `P-02R.P3` | `POST /companies/<EMPRESA_A>/purchases/<COMPRA_3>/receipt` | `perm:purchase:purchases:update` | `operario.dao` | ✅ | ✅ | ✅ |
| [05](05-consultar-el-inventario-tras-las-compras.md) | `P-03.precio_automatico` | `GET /companies/<EMPRESA_A>/price-list-items` | `perm:commercial-relationship:price_list_items:read` | `admin.sio` | ✅ | ✅ | ✅ |
| [05](05-consultar-el-inventario-tras-las-compras.md) | `P-03.saldo_a` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_A>` | `perm:inventory:balances:read` | `admin.sio` | ✅ | ✅ | ✅ |
| [05](05-consultar-el-inventario-tras-las-compras.md) | `P-03.saldo_b` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances/<PRODUCTO_EMPRESA_B>` | `perm:inventory:balances:read` | `admin.sio` | ✅ | ✅ | ✅ |
| [05](05-consultar-el-inventario-tras-las-compras.md) | `P-03.kardex_a` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_A>` | `perm:inventory:movements:read` | `admin.sio` | ✅ | ✅ | ✅ |
| [05](05-consultar-el-inventario-tras-las-compras.md) | `P-03.capas_a` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_A>/layers` | `perm:inventory:valuation:read` | `admin.sio` | ✅ | ✅ | ✅ |
| [05](05-consultar-el-inventario-tras-las-compras.md) | `P-03.capas_b` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation/<PRODUCTO_EMPRESA_B>/layers` | `perm:inventory:valuation:read` | `admin.sio` | ✅ | ✅ | ✅ |
