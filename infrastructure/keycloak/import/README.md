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

> Keycloak **no sustituye de forma confiable variables de entorno custom**
> dentro del JSON de import nativo (`--import-realm`). Por eso la plantilla
> con `${VAR}` NO es el archivo que Keycloak lee directamente: primero se
> renderiza a `sio-realm.json` (sin placeholders) usando
> `../scripts/render-realm.sh`, y ese archivo generado es el que se monta
> en el contenedor. `sio-realm.json` no se versiona en git (está en
> `.gitignore`) porque contiene el valor real de
> `KEYCLOAK_TEST_USER_PASSWORD`.

## Variables de entorno usadas

- `${KEYCLOAK_REALM}`: nombre del realm importado.
- `${SIO_WEB_ORIGIN}`: URL base del frontend.
- `${SIO_WEB_REDIRECT_URI}`: URI de redirección para el cliente web.
- `${KEYCLOAK_TEST_USER_PASSWORD}`: contraseña común para los usuarios de prueba.

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
