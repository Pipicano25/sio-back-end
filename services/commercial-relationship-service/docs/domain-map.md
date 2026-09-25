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

## Ubicación
`services/commercial-relationship-service/docs/domain-map.md`
