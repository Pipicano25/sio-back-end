# Product Catalog Service — Domain Map

## Responsabilidad
Administrar la definición global y reutilizable de productos y sus clasificaciones.

## Entidades propietarias
- `GlobalCategory`
- `GlobalUnitOfMeasure`
- `GlobalProduct`
- `ProductAttributeDefinition`
- `GlobalBrand`
- `GlobalProductCategory`
- `GlobalPackagingType`
- `GlobalProductPresentation`
- `GlobalProductIdentifier`
- `GlobalProductGroupType`
- `GlobalProductGroup`
- `GlobalProductGroupAssignment`
- `ProductAttributeOption`
- `GlobalCategoryAttribute`
- `GlobalProductAttributeValue`
- `ProductAsset`

## Referencias externas principales
- `manufacturer_organization_id` → Party Identity Service

No almacena precios privados, costos empresariales, proveedores ni stock.

## Ubicación
`services/product-catalog-service/docs/domain-map.md`
