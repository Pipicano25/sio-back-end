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
- `${KEYCLOAK_TEST_USER_PASSWORD}`: contraseña común para los usuarios de prueba.
- `${PARTY_IDENTITY_CLIENT_SECRET}`, `${OPERATIONAL_CONTEXT_CLIENT_SECRET}`,
  `${COMMERCIAL_RELATIONSHIP_CLIENT_SECRET}`: secretos de los clientes técnicos (solo en `.env`).
- `${AUDIT_TEST_EMITTER_CLIENT_SECRET}`: secreto del cliente de pruebas `audit-test-emitter`
  (solo `perm:audit:audit-events:create`; lo usan las pruebas de integración de audit-service y de
  `libs/sio-audit`). Solo en `.env`.

Permisos de auditoría (feature 011): `perm:audit:audit-events:create`, `perm:audit:audit-events:read`
y `perm:audit:platform-events:read` en `sio-api`. Ningún grupo los recibe explícitamente:
`administradores` y `supervisores` los obtienen por comodín (DS-18); otro grupo se habilita
asignándolos en la plantilla. Consultar auditoría de una empresa exige además
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
  purchase-service exigen usuarios humanos. Los grupos no cambian (`compras` ya tiene
  `perm:purchase:all:all`). Solo en `.env`.

Permisos de inventario (feature 012): `perm:inventory:entries:create`, `perm:inventory:outputs:create`
(solo cuentas de servicio: Purchase, Sales y el cliente de pruebas), `perm:inventory:balances:read`,
`perm:inventory:movements:read` y `perm:inventory:platform:lookup` (lectura técnica sin membresía) en
`sio-api`. El grupo `inventario` recibe `perm:inventory:balances:read`,
`perm:inventory:movements:read` y `perm:commercial-relationship:company_products:read`;
`administradores` y `supervisores` consultan por comodín. Ningún grupo puede aplicar operaciones.

Permisos de inventario (feature 013): `perm:inventory:adjustments:create`,
`perm:inventory:counts:create`, `perm:inventory:company-policies:update` y
`perm:inventory:product-policies:update` (solo usuarios humanos; una cuenta de servicio recibe `403`
aunque tenga el permiso; ajustes y conteos exigen además asignación `ACTIVE` a la sucursal) y las
lecturas `perm:inventory:adjustments:read`, `perm:inventory:counts:read`,
`perm:inventory:company-policies:read`, `perm:inventory:product-policies:read` y
`perm:inventory:valuation:read`. El grupo `inventario` recibe ajustes, conteos y las cinco lecturas;
las políticas solo las configuran `administradores` y `supervisores` por comodín.
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

- `administrador`
- `supervisor`
- `compras`
- `ventas`
- `inventario`
- `reportes`
- `consulta`

Estos roles se usan para controlar el acceso a recursos y operaciones del backend.

### Grupos

Los grupos predefinidos se asignan a roles de `sio-api`:

- `administradores` → `administrador`
- `supervisores` → `supervisor`
- `compras` → `compras`
- `ventas` → `ventas`
- `inventario` → `inventario`
- `reportes` → `reportes`
- `consulta` → `consulta`

### Usuarios de prueba

Se crean usuarios de prueba con los mismos permisos de grupo correspondientes:

- `admin.test` → grupo `/administradores`
- `supervisor.test` → grupo `/supervisores`
- `compras.test` → grupo `/compras`
- `ventas.test` → grupo `/ventas`
- `inventario.test` → grupo `/inventario`
- `reportes.test` → grupo `/reportes`
- `consulta.test` → grupo `/consulta`

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
