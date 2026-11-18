# Importación del realm de Keycloak

Este archivo documenta el contenido y el propósito de `sio-realm.json`, la configuración de importación usada por Keycloak cuando se inicia el servidor.

## Propósito

`keycloak/realm-template/sio-realm.template.json` (plantilla versionada en git) define un
realm de desarrollo para SIO con:

- Realm y metadatos básicos.
- Configuración de seguridad y políticas de contraseña.
- Clientes OpenID Connect para frontend y API.
- Roles de cliente y grupos predefinidos.
- Usuarios de prueba asociados a grupos y credenciales.

> `compose.yaml` monta la **plantilla** como `/opt/keycloak/data/import/sio-realm.json` y Keycloak
> (`--import-realm`) sustituye los `${VAR}` con las variables de entorno del contenedor (verificado al
> reconstruir Keycloak el 2026-10-05). `../scripts/render-realm.sh` genera aparte una copia resuelta
> en `sio-realm.json` solo para validarla; ese archivo no se versiona (está en `.gitignore`) porque
> contiene contraseñas y secretos reales.
>
> Los usuarios de prueba y las cuentas de servicio tienen `id` fijo en la plantilla: su `sub` no
> cambia al reconstruir Keycloak, de modo que siguen siendo válidas las referencias que guardan otros
> servicios (membresías de Operational Context, auditoría `created_by`/`first_used_by`).

## Variables de entorno usadas

- `${KEYCLOAK_REALM}`: nombre del realm importado.
- `${SIO_WEB_ORIGIN}`: URL base del frontend.
- `${SIO_WEB_REDIRECT_URI}`: URI de redirección para el cliente web.
- `${SIO_WEB_DIRECT_ACCESS_GRANTS_ENABLED:false}`: grant `password` de `sio-web`. Sin la variable queda en
  `false` (producción); `compose.yaml` y la pila aislada la definen en `true` para las herramientas de desarrollo y
  las pruebas.
- `${KEYCLOAK_TEST_USER_PASSWORD}`: contraseña común para los usuarios de prueba.
- `${PARTY_IDENTITY_CLIENT_SECRET}`, `${OPERATIONAL_CONTEXT_CLIENT_SECRET}`,
  `${COMMERCIAL_RELATIONSHIP_CLIENT_SECRET}`: secretos de los clientes técnicos (solo en `.env`).
- `${AUDIT_TEST_EMITTER_CLIENT_SECRET}`: secreto del cliente de pruebas `audit-test-emitter`
  (solo `perm:audit:audit-events:create`; lo usan las pruebas de integración de audit-service y de
  `libs/sio-audit`). Solo en `.env`.

Permisos de auditoría (feature 011): `perm:audit:audit-events:create`, `perm:audit:audit-events:read`
y `perm:audit:platform-events:read` en `sio-api`. Desde la spec 026, `superadmin` los obtiene por `perm:all:all:all` y `admin` recibe
explícitamente solo `perm:audit:audit-events:read`; `empleado` no tiene permisos de Audit. Consultar auditoría de una empresa exige además
`perm:operational-context:application_users:read` y membresía `ACTIVE`.
- `${INVENTORY_SERVICE_CLIENT_SECRET}`: secreto del cliente técnico `inventory-service` (lectura
  técnica en Operational Context y Commercial Relationship con `platform:lookup`, y
  `perm:audit:audit-events:create` para su `audit-outbox-worker`). Solo en `.env`.
- `${INVENTORY_TEST_OPERATOR_CLIENT_SECRET}`: secreto del cliente de pruebas `inventory-test-operator`
  (los cinco permisos `perm:inventory:*` de la 012 y las cinco lecturas de la 013; lo usan las
  pruebas de integración de inventory-service).
  Solo en `.env`.
- `${PURCHASE_SERVICE_CLIENT_SECRET}`: secreto del cliente técnico `purchase-service` (feature 014,
  R-02): lectura técnica en Operational Context (`companies`, `branches`, `application_users`),
  Commercial Relationship (proveedores, condiciones de pago, productos, presentaciones y productos de
  proveedor), Product Catalog (`products`, `units-of-measure`), Party Identity
  (`organization_identities`) y Payment Reference (`global_payment_condition_types`), con
  `platform:lookup` en Operational Context y Commercial Relationship; `perm:inventory:entries:create`,
  `perm:inventory:movements:read` y `perm:inventory:platform:lookup` en Inventory; y
  `perm:audit:audit-events:create` para su `audit-outbox-worker`. Nunca escribe compras: las rutas de
  purchase-service exigen usuarios humanos. Los grupos no cambian (`empleado` tiene el CRUD
  de compras y `admin` tiene `perm:purchase:all:all`). Solo en `.env`.
- `${SALES_SERVICE_CLIENT_SECRET}`: secreto del cliente técnico `sales-service` (feature 015, R-02):
  lectura técnica en Operational Context (`companies`, `branches`, `application_users`), Commercial
  Relationship (`company_customers`, `company_products`, `company_product_presentations`,
  `price_lists`, `price_list_items`), Product Catalog (`products`, `units-of-measure`) y Party Identity
  (`person_identities`, `organization_identities`), con `platform:lookup` en Operational Context y
  Commercial Relationship; `perm:inventory:outputs:create`, `perm:inventory:balances:read`,
  `perm:inventory:movements:read` y `perm:inventory:platform:lookup` en Inventory; y
  `perm:audit:audit-events:create` para su `audit-outbox-worker`. Nunca escribe ventas. Solo en `.env`.
- `${PRODUCT_CATALOG_SERVICE_CLIENT_SECRET}`: secreto del cliente técnico `product-catalog-service`
  (feature 016, C-02): solo `perm:audit:audit-events:create`, para su `audit-outbox-worker`. Solo en `.env`.
- `${SIO_DATA_IMPORTER_CLIENT_SECRET}`: secreto del cliente técnico `sio-data-importer`
  (`client_credentials`), con el que `tools/data-migration/ia-tools/cargar_gold.py` carga los datos de una
  empresa (`--rol cliente:sio-data-importer`; token con `python services/get_token.py --cliente
  sio-data-importer`).
  - **Permisos de lectura:** `perm:geography:all:read`, `perm:party-identity:organization_identities:read`,
    `perm:operational-context:companies:read`, `perm:operational-context:branches:read` y
    `perm:product-catalog:all:read`.
  - **Permisos de creación:** `perm:party-identity:organization_identities:create` y
    `perm:product-catalog:{packaging-types,brands,attribute-definitions,categories,products}:create`.
  - **Actualización:** `perm:product-catalog:products:update` (presentaciones, identificadores, categorías y
    valores de atributo de un producto) y `perm:product-catalog:categories:update` (asociar atributos a categorías).
  - **Sin** `delete`, `deactivate`, `platform:administer` ni roles de realm.
  - **No puede crear** empresas ni sedes (requieren `platform:administer`) ni datos de empresa en Commercial
    Relationship (requieren membresía `ACTIVE`); eso lo hace una identidad administrativa.

  Solo en `.env`.

Auditoría de servicios existentes (feature 016, C-01/C-02): `party-identity-service` y
`operational-context-service` tienen el scope por defecto `service_account` (su token emite
`client_id`, que Audit usa como `source_service`); `operational-context-service` tiene además la
audiencia `sio-api`. Las cuentas de servicio de Party Identity, Operational Context, Commercial
Relationship y Product Catalog tienen `perm:audit:audit-events:create`, sin otros cambios de roles.
Usuarios y grupos no cambian. Cambiar esta configuración exige reconstruir Keycloak.

Rentabilidad de ventas (feature 015, C-08): el rol `perm:sales:sales:read-profitability` permite ver costo y
margen de las ventas y no abre ninguna ruta. El grupo `empleado` tiene `perm:sales:all:create`, `read`,
`update` y `delete` explícitos (no `perm:sales:all:all`, que por comodín de acción incluiría la
rentabilidad); `admin` la obtiene por `perm:sales:all:all` y `superadmin` por `perm:all:all:all`. Cambiar esta matriz exige reconstruir Keycloak.

Permisos de inventario (feature 012): `perm:inventory:entries:create`, `perm:inventory:outputs:create`
(solo cuentas de servicio: Purchase, Sales y el cliente de pruebas), `perm:inventory:balances:read`,
`perm:inventory:movements:read` y `perm:inventory:platform:lookup` (lectura técnica sin membresía) en
`sio-api`. Los grupos `admin` y `empleado` reciben `perm:inventory:balances:read` y
`perm:inventory:movements:read` explícitos y `superadmin` por comodín. Ningún grupo salvo `superadmin`
(por `perm:all:all:all`) tiene `entries:create`, `outputs:create` ni `platform:lookup`.

Permisos de inventario (feature 013): `perm:inventory:adjustments:create`,
`perm:inventory:counts:create`, `perm:inventory:company-policies:update` y
`perm:inventory:product-policies:update` (solo usuarios humanos; una cuenta de servicio recibe `403`
aunque tenga el permiso; ajustes y conteos exigen además asignación `ACTIVE` a la sucursal) y las
lecturas `perm:inventory:adjustments:read`, `perm:inventory:counts:read`,
`perm:inventory:company-policies:read`, `perm:inventory:product-policies:read` y
`perm:inventory:valuation:read`. Los grupos `admin` y `empleado` reciben ajustes, conteos y las cinco lecturas;
las políticas solo las configuran `superadmin` y `admin`.
`inventory-test-operator` recibe las cinco lecturas.

## Secciones principales

### Realm

- `realm`: identifica el realm.
- `displayName`: nombre visible en la consola.
- `enabled`: habilita el realm.
- `sslRequired`: `external` significa que solo requiere SSL en conexiones externas.
- Opciones de registro y login controlan el comportamiento de usuario.

### Seguridad

- `bruteForceProtected`: protección contra fuerza bruta habilitada.
- `passwordPolicy`: obliga contraseña con 12 caracteres, mayúscula, minúscula y dígitos.
- Sesiones y tokens:
  - `accessTokenLifespan`: 300 segundos.
  - `ssoSessionIdleTimeout`: 1800 segundos.
  - `ssoSessionMaxLifespan`: 36000 segundos.
  - `offlineSessionIdleTimeout`: 2592000 segundos.

### Clientes

Se definen dos clientes OpenID Connect:

#### `sio-api`

- `clientId`: `sio-api`
- `publicClient`: `false`
- `bearerOnly`: `true`
- `standardFlowEnabled`: `false`
- `implicitFlowEnabled`: `false`
- `directAccessGrantsEnabled`: `false`
- `serviceAccountsEnabled`: `false`

Este cliente representa el backend y solo admite tokens de acceso.

#### `sio-web`

- `clientId`: `sio-web`
- `publicClient`: `true`
- `standardFlowEnabled`: `true`
- `directAccessGrantsEnabled`: `${SIO_WEB_DIRECT_ACCESS_GRANTS_ENABLED:false}` (solo desarrollo y pruebas)
- `defaultClientScopes`: `web-origins`, `acr`, `roles`, `profile`, `basic`, `email`
- `optionalClientScopes`: `address`, `phone`, `organization`, `microprofile-jwt` (sin `offline_access`)
- `redirectUris`: incluye `${SIO_WEB_REDIRECT_URI}`
- `webOrigins`: incluye `${SIO_WEB_ORIGIN}`
- `attributes.pkce.code.challenge.method`: `S256`
- `frontchannelLogout`: `true`
- `fullScopeAllowed`: `true`

Este cliente es el frontend React y usa PKCE para seguridad.

##### Protocol mapper

- El mapper `sio-api-audience` agrega la audiencia `sio-api` al token de acceso.
- Está configurado para incluir el claim en el access token y en el token de introspección.

### Roles del cliente

El archivo define roles del cliente `sio-api`:

- roles de permiso `perm:{servicio}:{recurso}:{accion}`, los únicos que conceden acceso;
- roles de perfil `superadmin`, `admin` y `empleado`, que solo identifican el perfil del usuario.

La matriz completa de cada grupo está en `docs/api/guias/permisos.md`.

### Grupos

Tres grupos predefinidos (spec 026). El grupo dice qué puede hacer el usuario; su membresía en
Operational Context dice en qué empresas:

- `superadmin` → perfil `superadmin` y `perm:all:all:all`: todo, en todas las empresas.
- `admin` → perfil `admin`: todo en sus empresas y crear y modificar datos globales, sin eliminarlos ni
  desactivarlos ni permisos de plataforma.
- `empleado` → perfil `empleado`: ventas, compras, ajustes y conteos de inventario; crear, leer y
  modificar personas, organizaciones y sus contactos en Party Identity; lecturas del resto. Sin
  rentabilidad, sin escritura en Operational Context ni en datos globales.

### Usuarios de prueba

Se crean usuarios de prueba con los mismos permisos de grupo correspondientes:

- `admin.sio` → grupo `/superadmin`
- `admin.dao` → grupo `/admin`
- `operario.dao` → grupo `/empleado`

Reemplazan a los usuarios genéricos anteriores (`admin.test`, `supervisor.test`, `ventas.test`, `compras.test`,
`inventario.test`, `reportes.test` y `consulta.test`) y conservan los `id` de `admin.test`, `supervisor.test` y
`ventas.test`. Un realm ya importado no cambia al reimportar la plantilla; ver la guía de migración de grupos.

Todos los usuarios:

- están habilitados (`enabled: true`)
- tienen `emailVerified: true`
- usan credenciales de tipo `password`
- comparten la contraseña `${KEYCLOAK_TEST_USER_PASSWORD}`
- tienen permisos estándar de cuenta (`manage-account`, `manage-account-links`, `view-profile`)

## Uso

1. Asegúrate de tener `infrastructure/.env` con las variables necesarias
   (`cp .env.example .env` si no existe).
2. Renderiza el realm real a partir de la plantilla:
   ```bash
   cd infrastructure
   ./scripts/render-realm.sh
   ```
3. Inicia la infraestructura de Keycloak. El realm se importa
   automáticamente desde el `sio-realm.json` ya renderizado.
4. Si luego cambias `KEYCLOAK_REALM`, `SIO_WEB_ORIGIN`,
   `SIO_WEB_REDIRECT_URI` o `KEYCLOAK_TEST_USER_PASSWORD` en `.env`,
   vuelve a correr `render-realm.sh` y luego
   `docker compose up -d --force-recreate keycloak`.

## Notas

- Este JSON es para un entorno de desarrollo/local.
- No debe usarse tal cual en producción sin ajustar contraseñas, usuarios y políticas.
- El realm no incluye datos productivos, empresas ni sucursales.
