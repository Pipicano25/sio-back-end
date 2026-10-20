# ¿De dónde sale cada parámetro?

[← Índice](../index.md)

Guías reutilizables de los identificadores que piden las API de SIO. Cada una indica qué representa el valor, su tipo, qué servicio lo entrega, la URL completa de Render, el método, los parámetros y el permiso de la consulta, un ejemplo de solicitud y de respuesta, el campo exacto del que se copia y cómo usarlo después. Las fichas de servicio enlazan aquí en lugar de repetir la explicación.

| Parámetro | Qué es | Lo entrega | Guía |
|---|---|---|---|
| `company_id` | Empresa cliente de SIO | Operational Context | [company-id.md](company-id.md) |
| `branch_id` | Sucursal de la empresa | Operational Context | [branch-id.md](branch-id.md) |
| `company_customer_id` | Cliente de la empresa | Commercial Relationship | [customer-id.md](customer-id.md) |
| `company_supplier_id` | Proveedor de la empresa | Commercial Relationship | [supplier-id.md](supplier-id.md) |
| `company_product_id` | Producto adoptado por la empresa | Commercial Relationship | [company-product-id.md](company-product-id.md) |
| `company_product_presentation_id` | Presentación empresarial del producto (unidad de venta o compra) | Commercial Relationship | [company-product-presentation-id.md](company-product-presentation-id.md) |
| `global_product_id` | Producto del catálogo global | Product Catalog | [global-product-id.md](global-product-id.md) |
| `payment_method_id` | Método global de pago | Payment Reference | [payment-method-id.md](payment-method-id.md) |
| `person_identity_id` | Identidad de una persona | Party Identity | [person-identity-id.md](person-identity-id.md) |
| `organization_identity_id` | Identidad de una organización | Party Identity | [organization-identity-id.md](organization-identity-id.md) |
| `application_user_id` | Membresía de un usuario en una empresa | Operational Context | [application-user-id.md](application-user-id.md) |
| `price_list_id` | Lista de precios de la empresa | Commercial Relationship | [price-list-id.md](price-list-id.md) |
| `policy_id` | Política de porcentaje de ganancia de una lista | Commercial Relationship | [pricing-policy-id.md](pricing-policy-id.md) |
| `global_product_presentation_id` | Presentación del catálogo global | Product Catalog | [global-product-presentation-id.md](global-product-presentation-id.md) |
| `sale_id` | Venta de la empresa | Sales | [sale-id.md](sale-id.md) |
| `purchase_id` | Compra de la empresa | Purchase | [purchase-id.md](purchase-id.md) |
| `country_id`, `administrative_division_id`, `city_id` | Jerarquía geográfica global | Geography | [country-id.md](country-id.md) |

## Cadena habitual para una venta

1. [`company_id`](company-id.md) y [`branch_id`](branch-id.md) desde `/me/operational-context`.
2. [`company_customer_id`](customer-id.md) buscando en los clientes de la empresa.
3. [`company_product_id`](company-product-id.md) y su [`company_product_presentation_id`](company-product-presentation-id.md) desde los productos empresariales (o desde Product Inventory Query, que los devuelve juntos con precio y existencias).
4. [`price_list_id`](price-list-id.md) de la lista que el vendedor elige entre los precios vigentes de la presentación.
5. [`payment_method_id`](payment-method-id.md) desde Payment Reference.
6. El [`sale_id`](sale-id.md) lo devuelve Sales al crear el borrador.

Para una compra, sustituye el cliente por [`company_supplier_id`](supplier-id.md), omite la lista de precios (el costo lo escribe el comprador) y conserva el [`purchase_id`](purchase-id.md) que devuelve Purchase.

## Cadena habitual para configurar una empresa

1. [`country_id`, `administrative_division_id` y `city_id`](country-id.md) desde Geography.
2. [`organization_identity_id`](organization-identity-id.md) de la empresa y [`person_identity_id`](person-identity-id.md) de cada usuario, desde Party Identity.
3. [`company_id`](company-id.md) y [`branch_id`](branch-id.md) al crearlos en Operational Context.
4. [`application_user_id`](application-user-id.md) al asociar cada usuario a la empresa; con él se asignan las sucursales.

## Cadena habitual para precios

1. [`price_list_id`](price-list-id.md) al crear o consultar la lista de la empresa.
2. [`policy_id`](pricing-policy-id.md) al crear la política de ganancia de esa lista y asociarle presentaciones.
3. [`global_product_presentation_id`](global-product-presentation-id.md) → [`company_product_presentation_id`](company-product-presentation-id.md) para adoptar las presentaciones que tendrán precio.

## Reglas comunes

- Usa los identificadores tal como los entrega el backend. No los escribas fijos en el código ni los deduzcas de otros campos.
- Todos son UUID en texto. El servidor los genera al crear el recurso; el valor está en el campo `id` de la respuesta `201`.
- Un identificador de empresa (cliente, proveedor, producto empresarial, presentación) solo es válido dentro de su `company_id`. Enviarlo en otra empresa produce `404` o `409 REFERENCES_NOT_ELIGIBLE`.
- Los identificadores globales (producto global, método de pago, identidades) no dependen de la empresa.
- Otros identificadores menos frecuentes (`price_list_item_id`, `supplier_payment_condition_id`, `customer_payment_condition_id`, `user_branch_id`, `detail_id`, `inventory_operation_id`, `count_id`, …) se explican dentro de la ficha del servicio que los genera.
