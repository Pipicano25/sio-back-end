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
| Es consumido por | Commercial Relationship Service (en uso, con su `client_credentials`: `products/batch-lookup`, `products/{id}/first-use` —también con presentación—, `presentations/batch-lookup` y `GET products/{id}` para la unidad base); Purchase (en uso: `presentations/{id}`, `products/{id}` y `units-of-measure/{id}` con su `client_credentials`, feature 014) |
| Referencias externas | `manufacturer_organization_id` → Party Identity Service |
| Eventos | Ninguno de mensajería (sin RabbitMQ); auditoría por Transactional Outbox de sus 63 operaciones de escritura (eventos de plataforma; acciones en `specs/016-existing-services-audit/contracts/audit-actions.md`) |
| Autenticación | Token del usuario propagado a Party Identity; los consumidores usan `client_credentials`; `client_credentials` del cliente `product-catalog-service` solo para entregar su auditoría (`perm:audit:audit-events:create`) |
| Spec | `specs/002-product-catalog-service/`, `specs/016-existing-services-audit/` (auditoría) |

### party-identity-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Identidad global de personas y organizaciones, reglas de identificación, contactos, sectores económicos y representantes legales (9 entidades; ver su `domain-map.md`) |
| Ruta | `services/party-identity-service/` |
| Puerto | `8101` (proyecto `infrastructure/services/`); interno `8000` |
| Base de datos | PostgreSQL propia `party_identity` (`5441`); pruebas `55436` (perfil `test`) |
| Depende de | Keycloak (clase B: validación de tokens y `client_credentials`); Geography Service (clase C, `GET global-countries/{id}`, `GET global-countries?iso3_code=`, `GET global-administrative-divisions/{id}`, `GET global-cities/{id}`); Operational Context Service (clase C, `GET /api/v1/operational-access` vía técnica, solo al confirmar perfiles de contacto) |
| Es consumido por | Product Catalog Service, Operational Context Service y Commercial Relationship Service (en uso: personas, organizaciones y `organization-contact-persons/{id}` con el token del usuario); Purchase (en uso: `organization-identities/{id}` con su `client_credentials`, identificación garantizada por la ampliación documental de la 014); Sales (en uso: `person-identities/{id}` y `organization-identities/{id}` con su `client_credentials`, identificación de personas garantizada por la ampliación documental de la 015) — contratos `identity-lookup-provider.md` (003) y `contact-lookup-provider.md` (006) |
| Referencias externas | `country_id`, `identification_country_id` → Geography Service; `country_id`, `administrative_division_id`, `city_id` (perfiles de contacto) → Geography Service; `confirmed_by_company_id` → Company y `confirmed_by_user_id` → ApplicationUser (Operational Context) |
| Eventos | Ninguno de mensajería (sin RabbitMQ); auditoría por Transactional Outbox de sus 32 operaciones de escritura (eventos de plataforma, datos personales solo como marcador; acciones en `specs/016-existing-services-audit/contracts/audit-actions.md`) |
| Autenticación | Token del usuario propagado a Geography; `client_credentials` del cliente `party-identity-service` para el `seed` (modo Geography) y para Operational Context (`platform:lookup`, `application_users:read`; renovación una vez ante `401`); los consumidores propagan el token de su usuario o usan su propio `client_credentials` con el permiso específico de cada recurso; el mismo cliente entrega su auditoría (`perm:audit:audit-events:create`) |
| Nota | Dependencia en ambos sentidos con Operational Context sin recursión (C-07): ninguna lectura de Party Identity llama a Operational Context y `operational-access` no llama a Party Identity |
| Spec | `specs/003-party-identity-core/`, `specs/006-party-identity-complementary/`, `specs/016-existing-services-audit/` (auditoría) |

### operational-context-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Contexto operativo: empresas, sucursales, usuarios operativos (membresías), asignaciones a sucursales y asesores, con aislamiento por empresa (5 entidades; ver su `domain-map.md`) |
| Ruta | `services/operational-context-service/` |
| Puerto | `8104` (proyecto `infrastructure/services/`); interno `8000` |
| Base de datos | PostgreSQL propia `operational_context` (`5440`); pruebas `55440` (perfil `test`) |
| Depende de | Keycloak (clase B: validación de tokens; Admin API de solo lectura con cliente técnico propio para verificar cuentas y leer permisos efectivos); Party Identity Service (clase C, `GET /api/v1/organization-identities/{id}` y `GET /api/v1/person-identities/{id}`); Geography Service (clase C, `GET global-countries/{id}`, `GET global-administrative-divisions/{id}`, `GET global-cities/{id}`) |
| Es consumido por | Party Identity (en uso: `operational-access` vía técnica para confirmar perfiles de contacto); Commercial Relationship (en uso: `operational-access` vía propia, `me/operational-context` y `companies/{id}` con el token del usuario); Audit (en uso: `operational-access` vía propia con el token del usuario, solo para la consulta de eventos de empresa); Inventory (en uso: `branches/{id}`, `application-users/{id}` y `companies/{id}` con su `client_credentials` y `platform:lookup`, y `operational-access` vía propia con el token del usuario, por `company_id` y —ajustes y conteos, feature 013— por `branch_id`); Purchase (en uso: `companies/{id}`, `branches/{id}` y `application-users/{id}` con su `client_credentials` y `platform:lookup`, y `operational-access` vía propia con el token del usuario por `branch_id` y `company_id`, feature 014); Sales (en uso: igual que Purchase, feature 015; la zona horaria de la sucursal fija la fecha de negocio) — contratos `operational-context-provider.md` (004) y `operational-access-provider.md` (005) |
| Referencias externas | `organization_identity_id` → Party Identity; `person_identity_id` (usuarios operativos y asesores) → Party Identity; `keycloak_user_id` (`sub`) → Keycloak; `country_id`, `administrative_division_id`, `city_id` → Geography |
| Eventos | Ninguno de mensajería (sin RabbitMQ); auditoría por Transactional Outbox de sus 18 operaciones de escritura (eventos de empresa, datos de contacto solo como marcador; acciones en `specs/016-existing-services-audit/contracts/audit-actions.md`) |
| Autenticación | Token del usuario propagado a Party Identity y Geography; `client_credentials` del cliente `operational-context-service` (`view-users`, `query-clients`) hacia la Admin API de Keycloak; los consumidores propagan el token de su usuario o usan su propio `client_credentials` con `perm:operational-context:platform:lookup`; el mismo cliente entrega su auditoría (`perm:audit:audit-events:create`) |
| Spec | `specs/004-operational-context-core/`, `specs/005-operational-context-users/`, `specs/016-existing-services-audit/` (auditoría) |

### payment-reference-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Catálogos globales de tipos de condición de pago y métodos de pago (2 entidades; ver su `domain-map.md`) |
| Ruta | `services/payment-reference-service/` |
| Puerto | `8105` (proyecto `infrastructure/services/`); interno `8000` |
| Base de datos | PostgreSQL propia `payment_reference` (`5443`); pruebas `55441` (perfil `test`) |
| Depende de | Keycloak (clase B: validación de tokens) |
| Es consumido por | Commercial Relationship (en uso: `GET global-payment-condition-types/{id}` con su `client_credentials`, feature 010); Purchase (en uso, igual, feature 014); Sales no lo consume en el MVP (solo contado, DP-01 de la 015) — `payment-condition-type-provider.md` (008) |
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
| Es consumido por | Inventory (en uso: `company-products/batch-lookup` con su `client_credentials` y `platform:lookup`, feature 012); Purchase (en uso: proveedores, condiciones de pago, productos y presentaciones por lotes y productos de proveedor con su `client_credentials` y `platform:lookup`, feature 014); Sales (en uso: clientes, productos y presentaciones por lotes, `applicable-prices/resolve` y `price-lists/{id}` con su `client_credentials` y `platform:lookup`, feature 015) — `commercial-relationship-provider.md` (007 y su ampliación en la 010: presentaciones por lotes, productos de proveedor, condiciones de pago, listas, precios y precio aplicable) |
| Referencias externas | `company_id` → Operational Context; `global_product_id`, `global_product_presentation_id`, `purchase_unit_id` → Product Catalog; `person_identity_id`, `organization_identity_id`, `preferred_contact_person_id` → Party Identity; `payment_condition_type_id` → Payment Reference |
| Eventos | Ninguno de mensajería (sin RabbitMQ); auditoría por Transactional Outbox de sus 35 operaciones de escritura (eventos de empresa; acciones en `specs/016-existing-services-audit/contracts/audit-actions.md`) |
| Autenticación | Token del usuario propagado a Operational Context y Party Identity; `client_credentials` del cliente `commercial-relationship-service` hacia Product Catalog (`products:read`, `first-use:register`) y Payment Reference (`global_payment_condition_types:read`); consumidores con su `client_credentials` y `platform:lookup`; el mismo cliente entrega su auditoría (`perm:audit:audit-events:create`) |
| Spec | `specs/007-commercial-relationship-core/`, `specs/010-commercial-relationship-commercial-product/`, `specs/016-existing-services-audit/` (auditoría) |

### audit-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Registro oficial e inmutable de las acciones importantes de SIO (`AuditEvent`; ver su `domain-map.md`): registro por cuentas de servicio y consulta por empresa o de plataforma |
| Ruta | `services/audit-service/`; librería compartida `libs/sio-audit/` (contrato del evento, redacción, outbox y `audit-outbox-worker`) |
| Puerto | `8110` (proyecto `infrastructure/services/`); interno `8000` |
| Base de datos | PostgreSQL propia `audit` (`5449`); pruebas `55451` (perfil `test`) |
| Depende de | Keycloak (B: validación de tokens); Operational Context (C: `operational-access` vía propia, solo para consultar eventos de empresa). El registro de eventos no depende de ningún otro servicio |
| Es consumido por | Servicios emisores mediante `POST /api/v1/audit-events` y `/audit-events/batch` con su `audit-outbox-worker` (en uso: Inventory, feature 012; Purchase, feature 014; Sales, feature 015; cliente de pruebas `audit-test-emitter`); también en uso por Party Identity, Product Catalog, Operational Context y Commercial Relationship, feature 016 |
| Referencias externas | `company_id`, `branch_id`, `application_user_id` → Operational Context; `keycloak_user_id` → Keycloak; `entity_id` → entidad del servicio emisor (todas `UUID REF` sin validar al registrar, DS-03) |
| Eventos | Ninguno de mensajería (sin RabbitMQ): la entrega es HTTP con Transactional Outbox en cada emisor |
| Autenticación | Emisores: `client_credentials` propio con `perm:audit:audit-events:create` (solo cuentas de servicio); consulta: token del usuario con `perm:audit:audit-events:read` (empresa, propagado a Operational Context) o `perm:audit:platform-events:read` (plataforma) |
| Spec | `specs/011-audit-core/` |

### inventory-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Inventario (Fases A y B): saldo por empresa, sucursal y producto empresarial, kardex inmutable, entradas de compra, salidas de venta y sus reversos (solo cuentas de servicio), ajustes y conteos físicos (solo usuarios asignados a la sucursal), políticas de inventario y valoración FIFO con capas y consumos (ver su `domain-map.md`) |
| Ruta | `services/inventory-service/` |
| Puerto | `8109` (proyecto `infrastructure/services/`); interno `8000`; contenedor adicional `inventory-audit-outbox-worker` (misma imagen) |
| Base de datos | PostgreSQL propia `inventory` (`5448`); pruebas `55449` (perfil `test`) |
| Depende de | Keycloak (B: validación de tokens y `client_credentials` propio); Operational Context (C: `branches/{id}`, `application-users/{id}` y `companies/{id}` —moneda de las capas— con identidad técnica y `platform:lookup` al aplicar operaciones; `operational-access?company_id=` vía propia con el token del usuario en las consultas y políticas, y `operational-access?branch_id=` en ajustes y conteos); Commercial Relationship (C: `company-products/batch-lookup` con identidad técnica y `platform:lookup`); Audit (eventos por `audit-outbox-worker`, sin llamada síncrona) |
| Es consumido por | Purchase (en uso: entradas con costo, su reverso y conciliación `by-key` con su `client_credentials`, feature 014) y Sales (en uso: salidas con su costo FIFO, sus reversos, `balances/lookup` y conciliación `by-key` con su `client_credentials`, feature 015) — `inventory-provider.md` (012) con `inventory-provider-delta.md` (013); cliente de pruebas `inventory-test-operator` |
| Referencias externas | `company_id`, `branch_id`, `application_user_id` → Operational Context; `company_product_id` → Commercial Relationship; `origin_id`, `origin_detail_id` → documento de Purchase o Sales (sin validar) |
| Eventos | Ninguno de mensajería (sin RabbitMQ); auditoría por Transactional Outbox (`APPLY_INVENTORY_ENTRY`, `APPLY_INVENTORY_OUTPUT`, `REVERSE_INVENTORY_ENTRY`, `REVERSE_INVENTORY_OUTPUT`, `CREATE_INVENTORY_ADJUSTMENT`, `START_`/`CANCEL_`/`COMPLETE_INVENTORY_COUNT`, `SET_COMPANY_INVENTORY_POLICY`, `CREATE_`/`UPDATE_`/`DEACTIVATE_INVENTORY_POLICY`) |
| Autenticación | Consumidores: `client_credentials` propio con `perm:inventory:entries:create` / `perm:inventory:outputs:create` (solo cuentas de servicio) y, para leer sin membresía, `perm:inventory:balances:read`/`movements:read` + `perm:inventory:platform:lookup`; usuarios: su token con el permiso de lectura y membresía `ACTIVE`; ajustes y conteos, usuario humano con el permiso y asignación `ACTIVE` a la sucursal; políticas, usuario humano con el permiso (comodín); Inventory usa el cliente `inventory-service` hacia Operational Context, Commercial Relationship y Audit |
| Spec | `specs/012-inventory-core/`, `specs/013-inventory-complementary/` |

### purchase-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Compras: borrador con líneas validadas, confirmación distribuida e idempotente que ingresa la mercancía en Inventory (unidad base, costo sin impuestos) y asigna el número oficial con contador por período, anulación con reverso exacto, secuencias de numeración, hitos logísticos y conciliador de operaciones pendientes (5 entidades más `purchase_sequence_counters`; ver su `domain-map.md`) |
| Ruta | `services/purchase-service/` |
| Puerto | `8107` (proyecto `infrastructure/services/`); interno `8000`; contenedores adicionales `purchase-audit-outbox-worker` y `purchase-reconciler` (misma imagen) |
| Base de datos | PostgreSQL propia `purchase` (`5446`); pruebas `55445` (perfil `test`) |
| Depende de | Keycloak (B: validación de tokens y `client_credentials` propio); Operational Context (C: `companies/{id}`, `branches/{id}`, `application-users/{id}` con identidad técnica y `platform:lookup`; `operational-access` vía propia con el token del usuario por `branch_id` en escrituras y por `company_id` en lecturas y secuencias); Commercial Relationship (C: proveedores, condiciones de pago, productos y presentaciones por lotes y productos de proveedor con identidad técnica y `platform:lookup`); Product Catalog (C: `presentations/{id}`, `products/{id}`, `units-of-measure/{id}`); Party Identity (C: `organization-identities/{id}`, identificación garantizada por la ampliación documental de la 014); Payment Reference (C: `global-payment-condition-types/{id}`, URL sin `/api/v1`); Inventory (C: `inventory-entries`, su reverso y `inventory-operations/by-key`); Audit (eventos por `audit-outbox-worker`, sin llamada síncrona) |
| Es consumido por | Ninguno en esta fase (Finance, futuro, fuera de alcance de la 014) |
| Referencias externas | `company_id`, `branch_id`, `created_by_user_id`, `cancelled_by_user_id`, `recorded_by_user_id` → Operational Context; `company_supplier_id`, `supplier_payment_condition_id`, `company_product_id`, `company_product_presentation_id`, `supplier_product_id` → Commercial Relationship; `inventory_operation_id` → Inventory (todas `UUID REF` sin FK física) |
| Eventos | Ninguno de mensajería (sin RabbitMQ); auditoría por Transactional Outbox (`CREATE_`/`UPDATE_PURCHASE`, `ADD_`/`UPDATE_`/`DELETE_PURCHASE_DETAIL`, `CONFIRM_PURCHASE`, `CANCEL_PURCHASE`, `RECORD_PURCHASE_LIFECYCLE_EVENT`, `CREATE_`/`UPDATE_`/`DEACTIVATE_`/`REACTIVATE_PURCHASE_SEQUENCE`) |
| Autenticación | Solo usuarios humanos (una cuenta de servicio recibe `403`): permiso `perm:purchase:{recurso}:{accion}`, membresía `ACTIVE` y, para escribir, asignación `ACTIVE` a la sucursal; Purchase usa el cliente `purchase-service` hacia sus dependencias, Inventory y Audit |
| Spec | `specs/014-purchase-core/` |

### sales-service

| Campo | Valor |
| --- | --- |
| Responsabilidad | Ventas: borrador con precio resuelto por Commercial Relationship (sin precio manual), consulta de existencias, confirmación distribuida e idempotente que verifica precio y existencias, descuenta Inventory (unidad base, sin costo), guarda el costo FIFO informado y el margen, fija la fecha del día y asigna el número con contador por período; anulación con reverso exacto; solo contado; secuencias y conciliador (4 entidades más `sale_sequence_counters`; ver su `domain-map.md`) |
| Ruta | `services/sales-service/` |
| Puerto | `8108` (proyecto `infrastructure/services/`); interno `8000`; contenedores adicionales `sales-audit-outbox-worker` y `sales-reconciler` (misma imagen) |
| Base de datos | PostgreSQL propia `sales` (`5447`); pruebas `55447` (perfil `test`) |
| Depende de | Keycloak (B: validación de tokens y `client_credentials` propio); Operational Context (C: `companies/{id}`, `branches/{id}`, `application-users/{id}` con identidad técnica y `platform:lookup`; `operational-access` vía propia con el token del usuario por `branch_id` en escrituras y por `company_id` en lecturas y secuencias); Commercial Relationship (C: `company-customers/{id}`, productos y presentaciones por lotes, `applicable-prices/resolve` y `price-lists/{id}` con identidad técnica y `platform:lookup`); Product Catalog (C: `presentations/{id}`, `products/{id}`, `units-of-measure/{id}`); Party Identity (C: `person-identities/{id}` y `organization-identities/{id}`, identificación garantizada por las ampliaciones documentales de la 014 y la 015); Inventory (C: `inventory-outputs`, su reverso, `balances/lookup` e `inventory-operations/by-key`); Audit (eventos por `audit-outbox-worker`, sin llamada síncrona). Sin Payment Reference |
| Es consumido por | Ninguno en esta fase (Finance y Reporting, futuros, fuera de alcance de la 015) |
| Referencias externas | `company_id`, `branch_id`, `created_by_user_id`, `cancelled_by_user_id` → Operational Context; `company_customer_id`, `customer_payment_condition_id` (siempre nulo en el MVP), `company_product_id`, `company_product_presentation_id`, `price_list_id`, `price_list_item_id` → Commercial Relationship; `inventory_operation_id` → Inventory (todas `UUID REF` sin FK física) |
| Eventos | Ninguno de mensajería (sin RabbitMQ); auditoría por Transactional Outbox, sin costo ni margen (`CREATE_`/`UPDATE_SALE`, `ADD_`/`UPDATE_`/`DELETE_SALE_DETAIL`, `CONFIRM_SALE`, `CANCEL_SALE`, `CREATE_`/`UPDATE_`/`DEACTIVATE_`/`REACTIVATE_SALE_SEQUENCE`) |
| Autenticación | Solo usuarios humanos (una cuenta de servicio recibe `403`): permiso `perm:sales:{recurso}:{accion}`, membresía `ACTIVE` y, para escribir, asignación `ACTIVE` a la sucursal; costo y margen solo con `perm:sales:sales:read-profitability` (grupos `supervisores` y `administradores`); Sales usa el cliente `sales-service` hacia sus dependencias, Inventory y Audit |
| Spec | `specs/015-sales-core/` |
