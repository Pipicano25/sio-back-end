# Commercial Relationship Service — Domain Map

## Responsabilidad
Administrar la relación privada de cada empresa con productos, clientes, proveedores y precios comerciales.

## Entidades propietarias
### MVP / núcleo
- `CompanyProduct`
- `CompanyCustomer`
- `CompanySupplier`
- `SupplierProduct`
- `CompanyProductPresentation`
- `PriceList`
- `PriceListItem`

### Evolución / Post-MVP
- `CustomerSegment`
- `SupplierCommercialCondition`
- `SupplierPaymentCondition`
- `ProductPricingPolicy`
- `CustomerCreditProfile`
- `CustomerPaymentCondition`
- `SupplierEvaluation`

## Referencias externas principales
- `global_product_id`, presentaciones y unidades → Product Catalog Service
- identidades de personas/organizaciones → Party Identity Service
- `company_id` → Operational Context Service
- condiciones de pago → Payment Reference Service

## Dependencias pendientes

Registradas por `specs/002-product-catalog-service` (C-18); deben incorporarse a la futura Spec de
este servicio:

- **Elegibilidad (FR-074 de Product Catalog)**: solo se adopta un producto `ACTIVE` y completo, y
  una presentación `ACTIVE` de un producto elegible. Validar con
  `POST /api/v1/products/batch-lookup` y `POST /api/v1/presentations/batch-lookup`.
- **Primer uso (FR-080, `specs/002-product-catalog-service/contracts/first-use.md`)**: invocar
  `POST /api/v1/products/{id}/first-use` **antes** de confirmar cada adopción y **rechazar** la
  adopción si la llamada falla. No confirmar sin marca ni diferir la notificación.
- **Keycloak**: el cliente de este servicio en
  `infrastructure/keycloak/realm-template/sio-realm.template.json` requiere cuenta de servicio
  (`serviceAccountsEnabled: true`) con el rol `perm:product-catalog:first-use:register` y los roles
  de lectura `perm:product-catalog:products:read` y `perm:product-catalog:units-of-measure:read`.
- **Unidades (OP-01)**: en el MVP no hay conversión entre unidades; `SupplierProduct.purchase_unit_id`
  debe ser la unidad base del producto o la compra debe expresarse con una presentación.

## Ubicación
`services/commercial-relationship-service/docs/domain-map.md`
