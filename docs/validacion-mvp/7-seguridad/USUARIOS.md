# Usuarios y permisos — Ejercicio 7 — Seguridad entre empresas y permisos

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

✅ = el usuario tiene el permiso (o los permisos) de la llamada según la plantilla del realm · ❌ = recibe `403`. Tener el permiso no basta en las rutas de empresa: fuera de sus empresas el usuario recibe `404` (aislamiento).

| Paso | Id | Método y ruta | Permiso requerido | Usuario del recorrido | admin | compras | ventas | supervisor | consulta | reportes | inventario |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-aislamiento-en-operational-context.md) | `I-01.empresa` | `GET /companies/<EMPRESA_A>` | `perm:operational-context:companies:read` | `reportes.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-aislamiento-en-operational-context.md) | `I-01.sucursales` | `GET /companies/<EMPRESA_A>/branches` | `perm:operational-context:branches:read` | `reportes.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-aislamiento-en-operational-context.md) | `I-01.usuarios` | `GET /companies/<EMPRESA_A>/application-users` | `perm:operational-context:application_users:read` | `reportes.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-aislamiento-en-commercial-relationship.md) | `I-02.clientes` | `GET /companies/<EMPRESA_A>/company-customers` | `perm:commercial-relationship:company_customers:read` | `reportes.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [02](02-aislamiento-en-commercial-relationship.md) | `I-02.proveedores` | `GET /companies/<EMPRESA_A>/company-suppliers` | `perm:commercial-relationship:company_suppliers:read` | `reportes.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [02](02-aislamiento-en-commercial-relationship.md) | `I-02.productos` | `GET /companies/<EMPRESA_A>/company-products` | `perm:commercial-relationship:company_products:read` | `reportes.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [02](02-aislamiento-en-commercial-relationship.md) | `I-02.listas` | `GET /companies/<EMPRESA_A>/price-lists` | `perm:commercial-relationship:price_lists:read` | `reportes.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [03](03-aislamiento-en-purchase.md) | `I-03.compras` | `GET /companies/<EMPRESA_A>/purchases` | `perm:purchase:purchases:read` | `reportes.test` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| [03](03-aislamiento-en-purchase.md) | `I-03.compra` | `GET /companies/<EMPRESA_A>/purchases/<COMPRA_1>` | `perm:purchase:purchases:read` | `reportes.test` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| [04](04-aislamiento-en-sales.md) | `I-04.ventas` | `GET /companies/<EMPRESA_A>/sales` | `perm:sales:sales:read` | `reportes.test` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [04](04-aislamiento-en-sales.md) | `I-04.venta` | `GET /companies/<EMPRESA_A>/sales/<VENTA_2>` | `perm:sales:sales:read` | `reportes.test` | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [05](05-aislamiento-en-inventory.md) | `I-05.saldos` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances` | `perm:inventory:balances:read` | `inventario.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [05](05-aislamiento-en-inventory.md) | `I-05.kardex` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/kardex/<PRODUCTO_EMPRESA_A>` | `perm:inventory:movements:read` | `inventario.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [05](05-aislamiento-en-inventory.md) | `I-05.valoracion` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/valuation` | `perm:inventory:valuation:read` | `inventario.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [05](05-aislamiento-en-inventory.md) | `I-05.ajuste` | `POST /companies/<EMPRESA_A>/inventory-adjustments` | `perm:inventory:adjustments:create` | `inventario.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [06](06-aislamiento-en-audit.md) | `I-06.eventos` | `GET /companies/<EMPRESA_B>/audit-events` | `perm:audit:audit-events:read` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-aislamiento-en-audit.md) | `I-06.historial` | `GET /companies/<EMPRESA_B>/entity-history/Company/<EMPRESA_B>` | `perm:audit:audit-events:read` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [07](07-permisos-el-vendedor-no-compra.md) | `S-01` | `POST /companies/<EMPRESA_A>/purchases` | `perm:purchase:purchases:create` | `ventas.test` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [08](08-permisos-el-comprador-no-vende.md) | `S-02` | `POST /companies/<EMPRESA_A>/sales` | `perm:sales:sales:create` | `compras.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [09](09-permisos-consulta-no-escribe.md) | `S-03.compra` | `POST /companies/<EMPRESA_A>/purchases` | `perm:purchase:purchases:create` | `consulta.test` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [09](09-permisos-consulta-no-escribe.md) | `S-03.venta` | `POST /companies/<EMPRESA_A>/sales` | `perm:sales:sales:create` | `consulta.test` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [10](10-permisos-la-cuenta-de-servicio-de-sales-no-vende.md) | `S-04.crear` | `POST /companies/<EMPRESA_A>/sales` | `perm:sales:sales:create` | `service-account-sales-service` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [10](10-permisos-la-cuenta-de-servicio-de-sales-no-vende.md) | `S-04.confirmar` | `POST /companies/<EMPRESA_A>/sales/<VENTA_4>/confirmation` | `perm:sales:sales:update` | `service-account-sales-service` | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| [11](11-permisos-la-cuenta-de-servicio-de-purchase-no-compra.md) | `S-05.crear` | `POST /companies/<EMPRESA_A>/purchases` | `perm:purchase:purchases:create` | `service-account-purchase-service` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [11](11-permisos-la-cuenta-de-servicio-de-purchase-no-compra.md) | `S-05.confirmar` | `POST /companies/<EMPRESA_A>/purchases/<COMPRA_1>/confirmation` | `perm:purchase:purchases:update` | `service-account-purchase-service` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.party-identity.lectura` | `GET /person-identities` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.party-identity.escritura` | `POST /person-identities` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.geography.lectura` | `GET /global-countries` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.geography.escritura` | `POST /global-countries` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.product-catalog.lectura` | `GET /products` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.product-catalog.escritura` | `POST /categories` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.operational-context.lectura` | `GET /companies` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.operational-context.escritura` | `POST /companies` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.payment-reference.lectura` | `GET /global-payment-methods` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.payment-reference.escritura` | `POST /global-payment-methods` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.commercial-relationship.lectura` | `GET /companies/<EMPRESA_A>/company-products` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.commercial-relationship.escritura` | `POST /companies/<EMPRESA_A>/company-customers` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.purchase.lectura` | `GET /companies/<EMPRESA_A>/purchases` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.purchase.escritura` | `POST /companies/<EMPRESA_A>/purchases` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.sales.lectura` | `GET /companies/<EMPRESA_A>/sales` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.sales.escritura` | `POST /companies/<EMPRESA_A>/sales` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.inventory.lectura` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.inventory.escritura` | `POST /companies/<EMPRESA_A>/inventory-adjustments` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.audit.lectura` | `GET /companies/<EMPRESA_A>/audit-events` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.sin-token.audit.escritura` | `POST /audit-events` | — | `sin-token` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.party-identity.lectura` | `GET /person-identities` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.party-identity.escritura` | `POST /person-identities` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.geography.lectura` | `GET /global-countries` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.geography.escritura` | `POST /global-countries` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.product-catalog.lectura` | `GET /products` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.product-catalog.escritura` | `POST /categories` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.operational-context.lectura` | `GET /companies` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.operational-context.escritura` | `POST /companies` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.payment-reference.lectura` | `GET /global-payment-methods` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.payment-reference.escritura` | `POST /global-payment-methods` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.commercial-relationship.lectura` | `GET /companies/<EMPRESA_A>/company-products` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.commercial-relationship.escritura` | `POST /companies/<EMPRESA_A>/company-customers` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.purchase.lectura` | `GET /companies/<EMPRESA_A>/purchases` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.purchase.escritura` | `POST /companies/<EMPRESA_A>/purchases` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.sales.lectura` | `GET /companies/<EMPRESA_A>/sales` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.sales.escritura` | `POST /companies/<EMPRESA_A>/sales` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.inventory.lectura` | `GET /companies/<EMPRESA_A>/branches/<SUCURSAL_A1>/balances` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.inventory.escritura` | `POST /companies/<EMPRESA_A>/inventory-adjustments` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.audit.lectura` | `GET /companies/<EMPRESA_A>/audit-events` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [12](12-sin-token-y-con-token-invalido.md) | `S-06.token-invalido.audit.escritura` | `POST /audit-events` | — | `token-invalido` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
