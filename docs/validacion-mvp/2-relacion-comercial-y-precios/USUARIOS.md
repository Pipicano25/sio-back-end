# Usuarios y permisos — Ejercicio 2 — Relación comercial y precios: proveedor, cliente, productos, adopción, presentaciones y listas

[← Orden del ejercicio](ORDEN.md) · [Usuarios y permisos (general)](../usuarios-y-permisos.md)

✅ = el usuario tiene el permiso (o los permisos) de la llamada según la plantilla del realm · ❌ = recibe `403`. Tener el permiso no basta en las rutas de empresa: fuera de sus empresas el usuario recibe `404` (aislamiento).

| Paso | Id | Método y ruta | Permiso requerido | Usuario del recorrido | admin | compras | ventas | supervisor | consulta | reportes | inventario |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [01](01-consultar-los-datos-de-referencia.md) | `C-00.5` | `GET /units-of-measure` | `perm:product-catalog:units-of-measure:read` | `admin.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [01](01-consultar-los-datos-de-referencia.md) | `C-00.6` | `GET /global-payment-condition-types` | `perm:payment-reference:global_payment_condition_types:read` | `admin.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [01](01-consultar-los-datos-de-referencia.md) | `C-00.7` | `GET /global-payment-methods` | `perm:payment-reference:global_payment_methods:read` | `admin.test` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [02](02-seleccionar-el-proveedor-y-su-condicion-de-pago.md) | `C-08.proveedor` | `POST /companies/<EMPRESA_A>/company-suppliers` | `perm:commercial-relationship:company_suppliers:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [02](02-seleccionar-el-proveedor-y-su-condicion-de-pago.md) | `C-08.condicion` | `POST /companies/<EMPRESA_A>/supplier-payment-conditions` | `perm:commercial-relationship:supplier_payment_conditions:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [03](03-incorporar-el-cliente.md) | `C-09.cliente` | `POST /companies/<EMPRESA_A>/company-customers` | `perm:commercial-relationship:company_customers:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [04](04-crear-los-productos-globales.md) | `C-10.categoria` | `POST /categories` | `perm:product-catalog:categories:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [04](04-crear-los-productos-globales.md) | `C-10.producto_a` | `POST /products` | `perm:product-catalog:products:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [04](04-crear-los-productos-globales.md) | `C-10.categoria_a` | `POST /products/<PRODUCTO_A>/categories` | `perm:product-catalog:products:update` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [04](04-crear-los-productos-globales.md) | `C-10.base_a` | `POST /products/<PRODUCTO_A>/presentations` | `perm:product-catalog:products:update` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [04](04-crear-los-productos-globales.md) | `C-10.caja_a` | `POST /products/<PRODUCTO_A>/presentations` | `perm:product-catalog:products:update` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [04](04-crear-los-productos-globales.md) | `C-10.producto_b` | `POST /products` | `perm:product-catalog:products:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [04](04-crear-los-productos-globales.md) | `C-10.categoria_b` | `POST /products/<PRODUCTO_B>/categories` | `perm:product-catalog:products:update` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [04](04-crear-los-productos-globales.md) | `C-10.base_b` | `POST /products/<PRODUCTO_B>/presentations` | `perm:product-catalog:products:update` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [05](05-adoptar-productos-y-presentacion.md) | `C-11.producto_a` | `POST /companies/<EMPRESA_A>/company-products` | `perm:commercial-relationship:company_products:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [05](05-adoptar-productos-y-presentacion.md) | `C-11.producto_b` | `POST /companies/<EMPRESA_A>/company-products` | `perm:commercial-relationship:company_products:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [05](05-adoptar-productos-y-presentacion.md) | `C-11.base_a` | `POST /companies/<EMPRESA_A>/company-product-presentations` | `perm:commercial-relationship:company_product_presentations:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [05](05-adoptar-productos-y-presentacion.md) | `C-11.base_b` | `POST /companies/<EMPRESA_A>/company-product-presentations` | `perm:commercial-relationship:company_product_presentations:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [05](05-adoptar-productos-y-presentacion.md) | `C-11.caja_a` | `POST /companies/<EMPRESA_A>/company-product-presentations` | `perm:commercial-relationship:company_product_presentations:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-crear-las-listas-de-precios.md) | `C-12.lista_general` | `POST /companies/<EMPRESA_A>/price-lists` | `perm:commercial-relationship:price_lists:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-crear-las-listas-de-precios.md) | `C-12.lista_mayorista` | `POST /companies/<EMPRESA_A>/price-lists` | `perm:commercial-relationship:price_lists:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-crear-las-listas-de-precios.md) | `C-12.item_general` | `POST /companies/<EMPRESA_A>/price-list-items` | `perm:commercial-relationship:price_list_items:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-crear-las-listas-de-precios.md) | `C-12.item_b` | `POST /companies/<EMPRESA_A>/price-list-items` | `perm:commercial-relationship:price_list_items:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| [06](06-crear-las-listas-de-precios.md) | `C-12.item_mayorista` | `POST /companies/<EMPRESA_A>/price-list-items` | `perm:commercial-relationship:price_list_items:create` | `admin.test` | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
