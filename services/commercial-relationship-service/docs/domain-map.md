# Commercial Relationship Service — Domain Map

## Responsabilidad
Administrar la relación privada de cada empresa con productos, clientes, proveedores y precios comerciales.

## Entidades propietarias
### MVP / núcleo
- `CompanyProduct` — **implementada (Fase A)**
- `CompanyCustomer` — **implementada (Fase A)**
- `CompanySupplier` — **implementada (Fase A)**
- `CompanyProductPresentation` — **implementada (Fase B)**
- `SupplierProduct` — **implementada (Fase B)**
- `SupplierPaymentCondition` — **implementada (Fase B)**; el roadmap (bloque 10) la incluye en el MVP (C-03 de la 010)
- `PriceList` — **implementada (Fase B)**
- `PriceListItem` — **implementada (Fase B)**

### Evolución / Post-MVP
- `CustomerSegment`
- `SupplierCommercialCondition`
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

## Fase B — producto comercial (implementada)

Spec: `specs/010-commercial-relationship-commercial-product/`.

| Entidad | Tabla | Estados | Referencias internas (FK compuestas con `company_id`) | Referencias externas (`UUID REF`, sin FK física) |
| --- | --- | --- | --- | --- |
| `CompanyProductPresentation` | `company_product_presentations` | `ACTIVE`, `INACTIVE` | `CompanyProduct` | `global_product_presentation_id` → Product Catalog |
| `SupplierProduct` | `supplier_products` | `ACTIVE`, `INACTIVE` | `CompanySupplier`, `CompanyProduct`, `CompanyProductPresentation` (opcional, del mismo producto) | `purchase_unit_id` → Product Catalog (unidad base) |
| `SupplierPaymentCondition` | `supplier_payment_conditions` | `ACTIVE`, `INACTIVE` | `CompanySupplier` | `payment_condition_type_id` → Payment Reference |
| `PriceList` | `price_lists` | `ACTIVE`, `INACTIVE` | — | — |
| `PriceListItem` | `price_list_items` | `ACTIVE`, `INACTIVE` | `PriceList`, `CompanyProduct`, `CompanyProductPresentation` (opcional) | — |

- **Reglas clave**: predeterminadas únicas entre las `ACTIVE` con cambio atómico (presentación de compra y
  de venta por producto, preferido por producto, condición por proveedor y moneda, lista por empresa y
  moneda); productos de proveedor únicos por proveedor + producto + presentación entre las `ACTIVE`;
  precios sin vigencias solapadas (exclusión `btree_gist`), inmutables en vigencia y con `change-price`;
  precio aplicable con respaldo en `sale_price` solo sin lista explícita.
- **Contrato Provider ampliado**: `specs/010-commercial-relationship-commercial-product/contracts/commercial-relationship-provider.md`
  (por UUID de las cinco entidades, lotes de presentaciones y precio aplicable por lotes).
- **Contratos consumidos nuevos**: `presentations/batch-lookup`, `products/{id}` y `first-use` con
  presentación (Product Catalog); `global-payment-condition-types/{id}` (Payment Reference), ambos con la
  identidad técnica.

## Dependencias registradas por Product Catalog

Registradas por `specs/002-product-catalog-service` (C-18):

- **Elegibilidad de productos (FR-074 de Product Catalog)** — *atendida en la Fase A*: solo se
  adopta un producto `ACTIVE` y completo, validado con `POST /api/v1/products/batch-lookup`. La
  elegibilidad de presentaciones (`POST /api/v1/presentations/batch-lookup`) — *atendida en la Fase B*
  (010): solo se adopta una presentación `ACTIVE`, elegible y del mismo producto global, con su primer uso.
- **Primer uso (FR-080, `specs/002-product-catalog-service/contracts/first-use.md`)** — *atendida en
  la Fase A*: `POST /api/v1/products/{id}/first-use` se invoca de forma síncrona **antes** de guardar
  cada adopción; si falla, la adopción se rechaza.
- **Keycloak** — *atendida en la Fase A*: el cliente `commercial-relationship-service` de la
  plantilla del realm tiene cuenta de servicio, el scope `service_account` (claim `client_id`) y los
  roles `perm:product-catalog:first-use:register` y `perm:product-catalog:products:read`.
  `perm:product-catalog:units-of-measure:read` no fue necesario en la Fase B: la unidad base se lee del
  producto con `products:read` (C-09 de la 010).
- **Unidades (OP-01)** — *atendida en la Fase B*: en el MVP no hay conversión entre unidades;
  `SupplierProduct.purchase_unit_id` debe ser la unidad base del producto (validada en Product Catalog) y
  las cantidades se expresan en esa unidad o mediante una presentación.

## Auditoría

Emisor de Audit desde la feature 016: Eventos de empresa (`company_id`). Tabla `audit_outbox` (Outbox, D26) y
contenedor `commercial-relationship-audit-outbox-worker` con el cliente `commercial-relationship-service`. Acciones en
`specs/016-existing-services-audit/contracts/audit-actions.md`.

## Ubicación
`services/commercial-relationship-service/docs/domain-map.md`
