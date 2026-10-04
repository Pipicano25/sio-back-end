# Commercial Relationship Service — Domain Map

## Responsabilidad
Administrar la relación privada de cada empresa con productos, clientes, proveedores y precios comerciales.

## Entidades propietarias
### MVP / núcleo
- `CompanyProduct` — **implementada (Fase A)**
- `CompanyCustomer` — **implementada (Fase A)**
- `CompanySupplier` — **implementada (Fase A)**
- `SupplierProduct` — Fase B
- `CompanyProductPresentation` — Fase B
- `PriceList` — Fase B
- `PriceListItem` — Fase B

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

## Fase A — núcleo (implementada)

Spec: `specs/007-commercial-relationship-core/`.

| Entidad           | Tabla               | Estados                          | Referencias externas (`UUID REF`, sin FK física)                                                   |
| ----------------- | ------------------- | -------------------------------- | -------------------------------------------------------------------------------------------------- |
| `CompanyProduct`  | `company_products`  | `ACTIVE`, `INACTIVE`             | `company_id` → Operational Context; `global_product_id` → Product Catalog                          |
| `CompanyCustomer` | `company_customers` | `ACTIVE`, `INACTIVE`             | `company_id`; `person_identity_id` u `organization_identity_id`, `preferred_contact_person_id` → Party Identity |
| `CompanySupplier` | `company_suppliers` | `ACTIVE`, `INACTIVE`, `BLOCKED`  | `company_id`; `organization_identity_id`, `preferred_contact_person_id` → Party Identity           |

- **Contrato Provider expuesto**: `specs/007-commercial-relationship-core/contracts/commercial-relationship-provider.md`
  (`GET /api/v1/company-products/{id}`, `POST /api/v1/company-products/batch-lookup`,
  `GET /api/v1/company-customers/{id}` y `GET /api/v1/company-suppliers/{id}`, con la exención técnica `perm:commercial-relationship:platform:lookup` solo para identidades técnicas).
  Consumidores previstos: Purchase, Sales e Inventory.
- **Contratos consumidos**: acceso operativo, empresas del usuario y empresa (Operational Context), consulta por lotes y
  primer uso de productos (Product Catalog), personas, organizaciones y personas de contacto (Party
  Identity).
- **Resumen de empresas** (`GET /api/v1/company-summaries`, FR-046): empresas con membresía `ACTIVE`
  del usuario y conteos por estado; la razón social se lee en cada solicitud y no se guarda.
- **Eventos**: ninguno (ni publica ni consume).

## Dependencias registradas por Product Catalog

Registradas por `specs/002-product-catalog-service` (C-18):

- **Elegibilidad de productos (FR-074 de Product Catalog)** — *atendida en la Fase A*: solo se
  adopta un producto `ACTIVE` y completo, validado con `POST /api/v1/products/batch-lookup`. La
  elegibilidad de presentaciones (`POST /api/v1/presentations/batch-lookup`) queda para la Fase B,
  con `CompanyProductPresentation`.
- **Primer uso (FR-080, `specs/002-product-catalog-service/contracts/first-use.md`)** — *atendida en
  la Fase A*: `POST /api/v1/products/{id}/first-use` se invoca de forma síncrona **antes** de guardar
  cada adopción; si falla, la adopción se rechaza.
- **Keycloak** — *atendida en la Fase A*: el cliente `commercial-relationship-service` de la
  plantilla del realm tiene cuenta de servicio, el scope `service_account` (claim `client_id`) y los
  roles `perm:product-catalog:first-use:register` y `perm:product-catalog:products:read`.
  `perm:product-catalog:units-of-measure:read` queda para la Fase B (C-05).
- **Unidades (OP-01)** — *pendiente, Fase B*: en el MVP no hay conversión entre unidades;
  `SupplierProduct.purchase_unit_id` debe ser la unidad base del producto o la compra debe
  expresarse con una presentación.

## Ubicación
`services/commercial-relationship-service/docs/domain-map.md`
