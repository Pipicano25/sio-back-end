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
| Puerto | `8003` (entorno del servicio), `8103` (entorno integrado `infrastructure/`); interno `8000` |
| Base de datos | PostgreSQL propia `product_catalog` (servicio: `55437`, pruebas: `55438`, integrado: `5444`) |
| Depende de | Keycloak (clase B); Party Identity Service (clase C, `GET /api/v1/organization-identities/{id}`; su URL base incluye `/api/v1`) |
| Es consumido por | Commercial Relationship Service (`batch-lookup`, `first-use`) |
| Referencias externas | `manufacturer_organization_id` → Party Identity Service |
| Eventos | Ninguno |
| Autenticación | Token del usuario propagado a Party Identity; los consumidores usan `client_credentials` |
| Spec | `specs/002-product-catalog-service/` |

### party-identity-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Identidad global de personas y organizaciones y reglas de identificación (Fase A: 3 entidades; ver su `domain-map.md`) |
| Ruta | `services/party-identity-service/` |
| Puerto | `8002` (entorno del servicio), `8101` (entorno integrado `infrastructure/`); interno `8000` |
| Base de datos | PostgreSQL propia `sio_party_identity` (servicio: `55435`, pruebas: `55436`); integrado `party_identity` (`5441`) |
| Depende de | Keycloak (clase B); Geography Service (clase C, `GET global-countries/{id}` y `GET global-countries?iso3_code=`) |
| Es consumido por | Product Catalog Service y Operational Context Service (en uso); Commercial Relationship (futuro) — contrato `identity-lookup-provider.md` |
| Referencias externas | `country_id`, `identification_country_id` → Geography Service |
| Eventos | Ninguno |
| Autenticación | Token del usuario propagado a Geography; `client_credentials` del cliente `party-identity-service` solo para el `seed` (modo Geography); los consumidores propagan el token de su usuario o usan su propio `client_credentials` |
| Spec | `specs/003-party-identity-core/` |

### operational-context-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Contexto operativo: empresas, sucursales, usuarios operativos (membresías), asignaciones a sucursales y asesores, con aislamiento por empresa (5 entidades; ver su `domain-map.md`) |
| Ruta | `services/operational-context-service/` |
| Puerto | `8004` (entorno del servicio), `8104` (entorno integrado `infrastructure/`); interno `8000` |
| Base de datos | PostgreSQL propia `sio_operational_context` (servicio: `55439`, pruebas: `55440`); integrado `operational_context` (`5440`) |
| Depende de | Keycloak (clase B: validación de tokens; Admin API de solo lectura con cliente técnico propio para verificar cuentas y leer permisos efectivos); Party Identity Service (clase C, `GET /api/v1/organization-identities/{id}` y `GET /api/v1/person-identities/{id}`); Geography Service (clase C, `GET global-countries/{id}`, `GET global-administrative-divisions/{id}`, `GET global-cities/{id}`) |
| Es consumido por | Commercial Relationship, Inventory, Purchase, Sales y Audit (futuros) — contratos `operational-context-provider.md` (004) y `operational-access-provider.md` (005) |
| Referencias externas | `organization_identity_id` → Party Identity; `person_identity_id` (usuarios operativos y asesores) → Party Identity; `keycloak_user_id` (`sub`) → Keycloak; `country_id`, `administrative_division_id`, `city_id` → Geography |
| Eventos | Ninguno |
| Autenticación | Token del usuario propagado a Party Identity y Geography; `client_credentials` del cliente `operational-context-service` (`view-users`, `query-clients`) hacia la Admin API de Keycloak; los consumidores propagan el token de su usuario o usan su propio `client_credentials` con `perm:operational-context:platform:lookup` |
| Spec | `specs/004-operational-context-core/`, `specs/005-operational-context-users/` |
