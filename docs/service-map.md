# SIO — Mapas de dominio por microservicio

Cada microservicio conserva su mapa en:

`services/<microservicio>/docs/domain-map.md`

Estos archivos son una referencia rápida. La fuente detallada del modelo continúa siendo `docs/SIO Database.md` (o la ubicación oficial que defina el repositorio).

## Servicios incluidos
- `services/audit-service/docs/domain-map.md`
- `services/commercial-relationship-service/docs/domain-map.md`
- `services/geography-service/docs/domain-map.md`
- `services/inventory-service/docs/domain-map.md`
- `services/operational-context-service/docs/domain-map.md`
- `services/party-identity-service/docs/domain-map.md`
- `services/payment-reference-service/docs/domain-map.md`
- `services/product-catalog-service/docs/domain-map.md`
- `services/purchase-service/docs/domain-map.md`
- `services/sales-service/docs/domain-map.md`
- `services/workflow-service/docs/domain-map.md`

## Nota
El modelo actual también documenta un `Finance Service`, pero no se incluyó porque no aparece entre las carpetas proporcionadas y corresponde a un alcance posterior al MVP actual.

## Registro de servicios (D8)

### product-catalog-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Catálogo global compartido de productos (16 entidades; ver su `domain-map.md`) |
| Ruta | `services/product-catalog-service/` |
| Puerto | `8103` (proyecto `infrastructure/services/`); interno `8000` |
| Base de datos | PostgreSQL propia `product_catalog` (`5444`); pruebas `55438` (perfil `test`) |
| Depende de | Keycloak (clase B); Party Identity Service (clase C, `GET /api/v1/organization-identities/{id}`; su URL base incluye `/api/v1`) |
| Es consumido por | Commercial Relationship Service (en uso, con su `client_credentials`: `products/batch-lookup`, `products/{id}/first-use` —también con presentación—, `presentations/batch-lookup` y `GET products/{id}` para la unidad base) |
| Referencias externas | `manufacturer_organization_id` → Party Identity Service |
| Eventos | Ninguno |
| Autenticación | Token del usuario propagado a Party Identity; los consumidores usan `client_credentials` |
| Spec | `specs/002-product-catalog-service/` |

### party-identity-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Identidad global de personas y organizaciones, reglas de identificación, contactos, sectores económicos y representantes legales (9 entidades; ver su `domain-map.md`) |
| Ruta | `services/party-identity-service/` |
| Puerto | `8101` (proyecto `infrastructure/services/`); interno `8000` |
| Base de datos | PostgreSQL propia `party_identity` (`5441`); pruebas `55436` (perfil `test`) |
| Depende de | Keycloak (clase B: validación de tokens y `client_credentials`); Geography Service (clase C, `GET global-countries/{id}`, `GET global-countries?iso3_code=`, `GET global-administrative-divisions/{id}`, `GET global-cities/{id}`); Operational Context Service (clase C, `GET /api/v1/operational-access` vía técnica, solo al confirmar perfiles de contacto) |
| Es consumido por | Product Catalog Service, Operational Context Service y Commercial Relationship Service (en uso: personas, organizaciones y `organization-contact-persons/{id}` con el token del usuario); Sales y Purchase (futuros) — contratos `identity-lookup-provider.md` (003) y `contact-lookup-provider.md` (006) |
| Referencias externas | `country_id`, `identification_country_id` → Geography Service; `country_id`, `administrative_division_id`, `city_id` (perfiles de contacto) → Geography Service; `confirmed_by_company_id` → Company y `confirmed_by_user_id` → ApplicationUser (Operational Context) |
| Eventos | Ninguno |
| Autenticación | Token del usuario propagado a Geography; `client_credentials` del cliente `party-identity-service` para el `seed` (modo Geography) y para Operational Context (`platform:lookup`, `application_users:read`; renovación una vez ante `401`); los consumidores propagan el token de su usuario o usan su propio `client_credentials` con el permiso específico de cada recurso |
| Nota | Dependencia en ambos sentidos con Operational Context sin recursión (C-07): ninguna lectura de Party Identity llama a Operational Context y `operational-access` no llama a Party Identity |
| Spec | `specs/003-party-identity-core/`, `specs/006-party-identity-complementary/` |

### operational-context-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Contexto operativo: empresas, sucursales, usuarios operativos (membresías), asignaciones a sucursales y asesores, con aislamiento por empresa (5 entidades; ver su `domain-map.md`) |
| Ruta | `services/operational-context-service/` |
| Puerto | `8104` (proyecto `infrastructure/services/`); interno `8000` |
| Base de datos | PostgreSQL propia `operational_context` (`5440`); pruebas `55440` (perfil `test`) |
| Depende de | Keycloak (clase B: validación de tokens; Admin API de solo lectura con cliente técnico propio para verificar cuentas y leer permisos efectivos); Party Identity Service (clase C, `GET /api/v1/organization-identities/{id}` y `GET /api/v1/person-identities/{id}`); Geography Service (clase C, `GET global-countries/{id}`, `GET global-administrative-divisions/{id}`, `GET global-cities/{id}`) |
| Es consumido por | Party Identity (en uso: `operational-access` vía técnica para confirmar perfiles de contacto); Commercial Relationship (en uso: `operational-access` vía propia, `me/operational-context` y `companies/{id}` con el token del usuario); Audit (en uso: `operational-access` vía propia con el token del usuario, solo para la consulta de eventos de empresa); Inventory, Purchase y Sales (futuros) — contratos `operational-context-provider.md` (004) y `operational-access-provider.md` (005) |
| Referencias externas | `organization_identity_id` → Party Identity; `person_identity_id` (usuarios operativos y asesores) → Party Identity; `keycloak_user_id` (`sub`) → Keycloak; `country_id`, `administrative_division_id`, `city_id` → Geography |
| Eventos | Ninguno |
| Autenticación | Token del usuario propagado a Party Identity y Geography; `client_credentials` del cliente `operational-context-service` (`view-users`, `query-clients`) hacia la Admin API de Keycloak; los consumidores propagan el token de su usuario o usan su propio `client_credentials` con `perm:operational-context:platform:lookup` |
| Spec | `specs/004-operational-context-core/`, `specs/005-operational-context-users/` |

### payment-reference-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Catálogos globales de tipos de condición de pago y métodos de pago (2 entidades; ver su `domain-map.md`) |
| Ruta | `services/payment-reference-service/` |
| Puerto | `8105` (proyecto `infrastructure/services/`); interno `8000` |
| Base de datos | PostgreSQL propia `payment_reference` (`5443`); pruebas `55441` (perfil `test`) |
| Depende de | Keycloak (clase B: validación de tokens) |
| Es consumido por | Commercial Relationship (en uso: `GET global-payment-condition-types/{id}` con su `client_credentials`, feature 010); Purchase y Sales (futuros) — `payment-condition-type-provider.md` (008) |
| Referencias externas | Ninguna |
| Eventos | Ninguno |
| Autenticación | Bearer token; permisos `perm:payment-reference:{recurso}:{accion}`; los consumidores usan su propio tiempo de espera finito |
| Spec | `specs/008-payment-reference-condition-type-contract/` (corrección acotada con línea base AS-IS y backlog de brechas) |

### commercial-relationship-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Relación comercial privada de cada empresa: productos adoptados y sus presentaciones, clientes, proveedores, productos de proveedor, condiciones de pago y listas de precios (8 entidades: 3 de la Fase A y 5 de la Fase B; ver su `domain-map.md`) |
| Ruta | `services/commercial-relationship-service/` |
| Puerto | `8106` (proyecto `infrastructure/services/`); interno `8000` |
| Base de datos | PostgreSQL propia `commercial_relationship` (`5445`); pruebas `55443` (perfil `test`) |
| Depende de | Keycloak (B: tokens y `client_credentials` propio); Operational Context (C: `operational-access` vía propia, `me/operational-context`, `companies/{id}`); Product Catalog (C: `products/batch-lookup`, `products/{id}/first-use`, `presentations/batch-lookup`, `products/{id}`); Party Identity (C: `person-identities/{id}`, `organization-identities/{id}`, `organization-contact-persons/{id}`); Payment Reference (C: `global-payment-condition-types/{id}`, URL sin `/api/v1` por GAP-PR-14) |
| Es consumido por | Inventory, Purchase, Sales (futuros) — `commercial-relationship-provider.md` (007 y su ampliación en la 010: presentaciones por lotes, productos de proveedor, condiciones de pago, listas, precios y precio aplicable) |
| Referencias externas | `company_id` → Operational Context; `global_product_id`, `global_product_presentation_id`, `purchase_unit_id` → Product Catalog; `person_identity_id`, `organization_identity_id`, `preferred_contact_person_id` → Party Identity; `payment_condition_type_id` → Payment Reference |
| Eventos | Ninguno |
| Autenticación | Token del usuario propagado a Operational Context y Party Identity; `client_credentials` del cliente `commercial-relationship-service` hacia Product Catalog (`products:read`, `first-use:register`) y Payment Reference (`global_payment_condition_types:read`); consumidores con su `client_credentials` y `platform:lookup` |
| Spec | `specs/007-commercial-relationship-core/`, `specs/010-commercial-relationship-commercial-product/` |

### audit-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Registro oficial e inmutable de las acciones importantes de SIO (`AuditEvent`; ver su `domain-map.md`): registro por cuentas de servicio y consulta por empresa o de plataforma |
| Ruta | `services/audit-service/`; librería compartida `libs/sio-audit/` (contrato del evento, redacción, outbox y `audit-outbox-worker`) |
| Puerto | `8110` (proyecto `infrastructure/services/`); interno `8000` |
| Base de datos | PostgreSQL propia `audit` (`5449`); pruebas `55451` (perfil `test`) |
| Depende de | Keycloak (B: validación de tokens); Operational Context (C: `operational-access` vía propia, solo para consultar eventos de empresa). El registro de eventos no depende de ningún otro servicio |
| Es consumido por | Servicios emisores mediante `POST /api/v1/audit-events` y `/audit-events/batch` con su `audit-outbox-worker` (en uso: ninguno; cliente de pruebas `audit-test-emitter`). Inventory, Purchase y Sales lo adoptan desde su Spec; Party Identity, Product Catalog, Operational Context y Commercial Relationship, en la feature transversal "Auditoría de servicios existentes" (aún **no auditados**) |
| Referencias externas | `company_id`, `branch_id`, `application_user_id` → Operational Context; `keycloak_user_id` → Keycloak; `entity_id` → entidad del servicio emisor (todas `UUID REF` sin validar al registrar, DS-03) |
| Eventos | Ninguno de mensajería (sin RabbitMQ): la entrega es HTTP con Transactional Outbox en cada emisor |
| Autenticación | Emisores: `client_credentials` propio con `perm:audit:audit-events:create` (solo cuentas de servicio); consulta: token del usuario con `perm:audit:audit-events:read` (empresa, propagado a Operational Context) o `perm:audit:platform-events:read` (plataforma) |
| Spec | `specs/011-audit-core/` |
