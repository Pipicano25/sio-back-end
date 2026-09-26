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
- `manufacturer_organization_id` → Party Identity Service (`OrganizationIdentity`). Solo se valida
  la existencia, y solo al asignar o cambiar el fabricante; se propaga el token del usuario.

## Contratos entrantes
- Consultas por lotes (`/api/v1/products/batch-lookup`, `/api/v1/presentations/batch-lookup`,
  `/api/v1/units-of-measure/batch-lookup`) para validar existencia, estado y elegibilidad.
- Registro síncrono del primer uso (`/api/v1/products/{id}/first-use`): lo invoca el servicio que
  adopta (Commercial Relationship) **antes** de confirmar la adopción. Ver
  `specs/002-product-catalog-service/contracts/first-use.md`.

## Eventos
Ninguno: no publica ni consume eventos en esta versión (DS-11).

No almacena precios privados, costos empresariales, proveedores ni stock.

## Ubicación
`services/product-catalog-service/docs/domain-map.md`
