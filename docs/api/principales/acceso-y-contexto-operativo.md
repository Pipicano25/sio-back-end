# 6.1 Acceso y contexto operativo

[← API principales](README.md) · [← Índice](../index.md)

Todo lo que el frontend debe hacer entre la pantalla de login y la primera operación de negocio: autenticar al usuario en Keycloak con su usuario y contraseña, mantener la sesión, saber en qué empresas tiene membresía y en qué sucursales puede operar, y fijar la empresa y la sucursal con las que trabajará.

Servicios implicados: Keycloak (realm `siodev`, cliente público `sio-web`) y [Operational Context](../servicios/operational-context.md). Guías de apoyo: [Autenticación](../guias/autenticacion.md), [Permisos](../guias/permisos.md), [Primeros pasos](../guias/primeros-pasos.md), [Errores](../guias/errores.md).

| # | API | Método y URL | Permiso | Referencia técnica |
|---|---|---|---|---|
| 1 | Iniciar sesión (usuario y contraseña) | `POST https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token` | Ninguno | [Autenticación](../guias/autenticacion.md) |
| 2 | Renovar la sesión | `POST https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token` | Ninguno | [Autenticación §9](../guias/autenticacion.md#9-renovar-tokens-rotación-obligatoria) |
| 3 | Cerrar sesión | `POST https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/logout` | Ninguno | [Autenticación §10](../guias/autenticacion.md#10-cerrar-sesión) |
| 4 | Identificar al usuario y sus permisos | Sin llamada: lectura del Access Token | Ninguno | [Autenticación §7](../guias/autenticacion.md#7-qué-contiene-el-access-token-y-qué-permisos-se-utilizan) |
| 5 | Consultar las empresas y sucursales del usuario | `GET https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` | `perm:operational-context:application_users:read` | [OC 32](../servicios/operational-context.md#32-get-meoperational-context) |
| 6 | Comprobar un acceso concreto antes de actuar | `GET https://sio-operational-context-dev.onrender.com/api/v1/operational-access` | `perm:operational-context:application_users:read` | [OC 33](../servicios/operational-context.md#33-get-operational-access) |
| 7 | Seleccionar empresa y sucursal de trabajo | Sin llamada: decisión del frontend | Ninguno | [company_id](../parametros/company-id.md) · [branch_id](../parametros/branch-id.md) |

Las API 1 a 3 son de Keycloak y reciben formularios `application/x-www-form-urlencoded`, no JSON. Las API 5 y 6 son las únicas de SIO en este módulo; ambas responden errores en formato Problem Details (`application/problem+json`) salvo el `401`, que llega como `{"detail": "…"}`.

Convenciones de los ejemplos: `TU_ACCESS_TOKEN` y `TU_REFRESH_TOKEN` son marcadores que el frontend sustituye por los tokens de su sesión; `ventas.demo` y `ClaveDemo2026` son credenciales ficticias; los UUID son ficticios.

---

## 1. Iniciar sesión (usuario y contraseña)

**Método:** `POST`
**URL:** `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token`
**Permiso requerido:** ninguno. Es la operación que entrega los permisos.

### ¿Qué hace esta API?

Autentica al usuario con su nombre de usuario y contraseña de Keycloak y devuelve los tokens que autorizan todas las llamadas a SIO: el `access_token`, que se envía a cada API en la cabecera `Authorization`, el `refresh_token`, que sirve solo para renovar la sesión (API 2), y el `id_token`, con la identidad del usuario. Es lo primero que hace el frontend cuando el usuario envía el formulario de login. El cliente `sio-web` es público: no existe `client_secret` y nunca debe enviarse uno. El cuerpo es un formulario `application/x-www-form-urlencoded`, no JSON.

> **Nota.** Este mecanismo (*Direct Access Grants*, `grant_type=password`) funciona porque está habilitado hoy en el cliente `sio-web` del realm `siodev` (comprobado en vivo el 2026-10-20) y depende de que permanezca así. No es el flujo recomendado para aplicaciones web públicas, porque la contraseña pasa por la aplicación; la alternativa estándar está descrita en la [guía de autenticación](../guias/autenticacion.md).

Antes necesita: un usuario del realm `siodev` con su contraseña (los entrega el administrador) y una membresía en al menos una empresa para poder operar después (API 5).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=password' \
  --data-urlencode 'client_id=sio-web' \
  --data-urlencode 'username=ventas.demo' \
  --data-urlencode 'password=ClaveDemo2026' \
  --data-urlencode 'scope=openid'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:**

| Nombre | Obligatorio | Valor |
|---|---|---|
| `Content-Type` | Sí | `application/x-www-form-urlencoded` |

**Cuerpo de la solicitud:** formulario `application/x-www-form-urlencoded`, no JSON.

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `grant_type` | string | Sí | Tipo de concesión: usuario y contraseña directos | `password` | Valor fijo |
| `client_id` | string | Sí | Cliente público del frontend | `sio-web` | Valor fijo |
| `username` | string | Sí | Nombre de usuario en el realm `siodev`; también se acepta el correo electrónico | `ventas.demo` | Formulario de login |
| `password` | string | Sí | Contraseña del usuario | `ClaveDemo2026` | Formulario de login; nunca se guarda ni se registra en logs |
| `scope` | string | No | `openid` hace que la respuesta incluya también el `id_token` | `openid` | Valor fijo |

No se envía `client_secret`.

### Respuesta exitosa

`200 OK` (formato estándar de Keycloak; los tokens del ejemplo no son utilizables):

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJXOEhnaC4uLiJ9.eyJleHAiOjE3OTI0NTYwMDB9.firma",
  "expires_in": 300,
  "refresh_expires_in": 1800,
  "refresh_token": "eyJhbGciOiJIUzUxMiIsInR5cCIgOiAiSldUIn0.eyJleHAiOjE3OTI0NTc1MDB9.firma",
  "token_type": "Bearer",
  "id_token": "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIzZjJhIn0.firma",
  "not-before-policy": 0,
  "session_state": "6b0c5a1e-2f4d-4c8e-9a1b-0d2e3f4a5b6c",
  "scope": "openid profile email"
}
```

| Campo | Tipo | Uso en el frontend |
|---|---|---|
| `access_token` | string (JWT RS256) | Se guarda en memoria y se envía a todas las API de SIO como `Authorization: Bearer …` |
| `expires_in` | integer (segundos) | Vida del Access Token (300 en la plantilla del realm). Renovar con 30–60 s de margen (API 2) |
| `refresh_token` | string (JWT) | Solo para renovar (API 2) y cerrar sesión (API 3). Nunca se envía a las API de SIO |
| `refresh_expires_in` | integer (segundos) | Tiempo de inactividad permitido antes de tener que iniciar sesión de nuevo (1 800 en la plantilla) |
| `id_token` | string (JWT) | Identidad del usuario para la interfaz. No sustituye al Access Token |
| `token_type` | string | Siempre `Bearer` |
| `not-before-policy` | integer | Informativo; `0` salvo que el administrador revoque sesiones |
| `session_state` | string (UUID) | Identificador de la sesión en Keycloak; informativo |
| `scope` | string | Scopes concedidos |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `400` | `invalid_grant` (`Invalid user credentials`) | Usuario o contraseña incorrectos, o usuario bloqueado 60 s tras dos intentos fallidos seguidos (en ese caso Keycloak responde lo mismo aunque la contraseña sea correcta). Comprobado en vivo | Mostrar «usuario o contraseña incorrectos» y permitir corregir; no registrar las credenciales |
| `400` | `invalid_grant` (`Account disabled`) | El usuario está deshabilitado en Keycloak | Indicar que contacte al administrador |
| `400` | `invalid_grant` (`Account is not fully set up`) | El usuario tiene acciones pendientes en Keycloak (por ejemplo, cambiar la contraseña) | Indicar que contacte al administrador para completarlas |
| `400` | `invalid_request` | Falta un campo obligatorio del formulario (`username`, `password`) | Corregir la solicitud |
| `400` | `unauthorized_client` (`Client not allowed for direct access grants`) | *Direct Access Grants* se deshabilitó en `sio-web`: este inicio de sesión ya no está disponible | Avisar al administrador; el frontend no puede resolverlo |
| `401` | `invalid_client` | `client_id` inexistente o se envió un secreto a un cliente público | Enviar solo `client_id=sio-web` |

```json
{
  "error": "invalid_grant",
  "error_description": "Invalid user credentials"
}
```

## 2. Renovar la sesión

**Método:** `POST`
**URL:** `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token`
**Permiso requerido:** ninguno.

### ¿Qué hace esta API?

Entrega un Access Token nuevo sin pedir la contraseña, a cambio del Refresh Token vigente. El frontend la llama en segundo plano antes de que venza el Access Token (300 s) o cuando una API responde `401`. La rotación es obligatoria: cada renovación devuelve también un Refresh Token nuevo y el anterior queda invalidado; reutilizarlo cierra toda la sesión. Las renovaciones deben hacerse desde un único punto del cliente y de una en una, incluso con varias pestañas abiertas.

Antes necesita: el `refresh_token` más reciente (API 1 o la última renovación).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=refresh_token' \
  --data-urlencode 'client_id=sio-web' \
  --data-urlencode 'refresh_token=TU_REFRESH_TOKEN'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:**

| Nombre | Obligatorio | Valor |
|---|---|---|
| `Content-Type` | Sí | `application/x-www-form-urlencoded` |

**Cuerpo de la solicitud:** formulario `application/x-www-form-urlencoded`, no JSON.

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `grant_type` | string | Sí | Tipo de concesión | `refresh_token` | Valor fijo |
| `client_id` | string | Sí | Cliente público | `sio-web` | Valor fijo |
| `refresh_token` | string | Sí | Refresh Token vigente; va en el formulario, nunca en `Authorization` | `TU_REFRESH_TOKEN` | Respuesta de la API 1 o de la última renovación |

### Respuesta exitosa

`200 OK`, mismo formato que la API 1, con un Access Token y un Refresh Token **nuevos**:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJXOEhnaC4uLiJ9.eyJleHAiOjE3OTI0NTYzMDB9.firma",
  "expires_in": 300,
  "refresh_expires_in": 1800,
  "refresh_token": "eyJhbGciOiJIUzUxMiIsInR5cCIgOiAiSldUIn0.eyJleHAiOjE3OTI0NTc4MDB9.firma",
  "token_type": "Bearer",
  "id_token": "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIzZjJhIn0.firma",
  "not-before-policy": 0,
  "session_state": "6b0c5a1e-2f4d-4c8e-9a1b-0d2e3f4a5b6c",
  "scope": "openid profile email"
}
```

| Campo | Tipo | Uso en el frontend |
|---|---|---|
| `access_token` | string (JWT) | Reemplaza al anterior en memoria |
| `refresh_token` | string (JWT) | Reemplaza al anterior; el viejo ya no sirve |
| `expires_in`, `refresh_expires_in` | integer (segundos) | Reprogramar la siguiente renovación |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `400` | `invalid_grant` (`Invalid refresh token`) | Refresh Token inválido, vencido por inactividad (1 800 s), sesión que superó su duración máxima (36 000 s) o sesión cerrada | Borrar los tokens locales y volver a la API 1 |
| `400` | `invalid_grant` (`Maximum allowed refresh token reuse exceeded`) | Se reutilizó un Refresh Token ya rotado, normalmente por dos renovaciones simultáneas | Borrar los tokens locales y volver a la API 1; serializar las renovaciones |
| `400` | `unauthorized_client` | El cliente no admite `refresh_token` | No aplica a `sio-web`; revisar `client_id` |

```json
{
  "error": "invalid_grant",
  "error_description": "Invalid refresh token"
}
```

## 3. Cerrar sesión

**Método:** `POST`
**URL:** `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/logout`
**Permiso requerido:** ninguno.

### ¿Qué hace esta API?

Termina la sesión del usuario en Keycloak: revoca el Refresh Token y la sesión asociada, de modo que ya no se pueden renovar tokens. Es la llamada del botón «Salir». Después de llamarla, el frontend borra los tokens y el estado local; debe hacerlo también si la llamada falla. Los Access Tokens ya emitidos siguen siendo válidos para las API hasta su vencimiento (máximo 5 minutos), porque las API validan la firma y no consultan la sesión en Keycloak.

Antes necesita: el `refresh_token` vigente (API 1 o la última renovación).

### ¿Cómo se realiza la solicitud?

```bash
curl -X POST \
  'https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/logout' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'client_id=sio-web' \
  --data-urlencode 'refresh_token=TU_REFRESH_TOKEN'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:**

| Nombre | Obligatorio | Valor |
|---|---|---|
| `Content-Type` | Sí | `application/x-www-form-urlencoded` |

**Cuerpo de la solicitud:** formulario `application/x-www-form-urlencoded`, no JSON.

| Nombre | Tipo | Obligatorio | Descripción | Ejemplo | Origen |
|---|---|---|---|---|---|
| `client_id` | string | Sí | Cliente público | `sio-web` | Valor fijo |
| `refresh_token` | string | Sí | Refresh Token vigente de la sesión que se cierra | `TU_REFRESH_TOKEN` | Respuesta de la API 1 o 2 |

### Respuesta exitosa

`204 No Content`. Esta operación no devuelve cuerpo.

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `400` | `invalid_grant` (`Invalid refresh token`) | El Refresh Token ya no es válido: la sesión ya estaba cerrada o vencida. Comprobado en vivo | Nada más: borrar los tokens locales y volver al login |
| `400` | `invalid_request` | Falta `refresh_token` o `client_id` | Corregir la solicitud |

```json
{
  "error": "invalid_grant",
  "error_description": "Invalid refresh token"
}
```

## 4. Identificar al usuario y sus permisos

**Método:** sin llamada. Se decodifica el Access Token en el frontend.
**URL:** no aplica.
**Permiso requerido:** ninguno.

### ¿Qué hace esta API?

Permite mostrar el nombre del usuario y habilitar u ocultar módulos de la interfaz según sus permisos, sin ninguna petición de red: la información viene dentro del Access Token (JWT firmado con RS256). Se usa justo después de la API 1 o 2. Los permisos leídos del token sirven solo para la interfaz; la autorización definitiva la decide cada API, que responde `403` cuando falta el permiso y `404` cuando falta la membresía en la empresa.

Antes necesita: un Access Token válido.

### ¿Cómo se realiza la solicitud?

No hay solicitud. El frontend decodifica el segundo segmento del JWT (Base64URL) sin verificar la firma, porque la firma la verifican las API. El cURL siguiente muestra ese contenido desde la terminal:

```bash
echo "TU_ACCESS_TOKEN" | cut -d '.' -f 2 | tr '_-' '/+' | base64 -d 2>/dev/null | python3 -m json.tool
```

### Parámetros de la solicitud

No requiere parámetros de ruta. No requiere parámetros de consulta. No requiere Body.

### Respuesta exitosa

Contenido decodificado del Access Token (ejemplo ilustrativo; identificadores no reales):

```json
{
  "exp": 1792456300,
  "iat": 1792456000,
  "jti": "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
  "iss": "https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev",
  "aud": ["sio-api", "account"],
  "sub": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "typ": "Bearer",
  "azp": "sio-web",
  "session_state": "6b0c5a1e-2f4d-4c8e-9a1b-0d2e3f4a5b6c",
  "acr": "1",
  "scope": "openid profile email",
  "resource_access": {
    "sio-api": {
      "roles": [
        "ventas",
        "perm:sales:all:create",
        "perm:sales:all:read",
        "perm:sales:all:update",
        "perm:operational-context:application_users:read",
        "perm:geography:all:read",
        "perm:product-catalog:all:read"
      ]
    },
    "account": {
      "roles": ["manage-account", "manage-account-links", "view-profile"]
    }
  },
  "email_verified": true,
  "name": "Nombre Apellido",
  "preferred_username": "ventas.test",
  "given_name": "Nombre",
  "family_name": "Apellido",
  "email": "ventas.test@ejemplo.test"
}
```

| Campo | Tipo | Uso en el frontend |
|---|---|---|
| `sub` | string (UUID) | Identificador estable del usuario en Keycloak; es el `keycloak_user_id` que devuelve la API 5 |
| `preferred_username`, `name`, `email` | string | Mostrar quién inició sesión |
| `resource_access["sio-api"].roles` | array de string | Roles de perfil (`administrador`, `supervisor`, `compras`, `ventas`, `inventario`, `reportes`, `consulta`) y permisos `perm:{servicio}:{recurso}:{accion}`. Solo los que empiezan por `perm:` conceden acceso; admiten el comodín `all` en cualquier segmento (por ejemplo `perm:all:all:all`) |
| `aud` | array de string | Debe incluir `sio-api`; si no, todas las API responden `401` |
| `exp` | integer (epoch segundos) | Vencimiento; sin tolerancia de reloj en las API |

### Posibles errores

No hay errores de esta operación. Un token mal formado o sin `resource_access["sio-api"]` indica que no fue emitido por `sio-web` en el realm `siodev`: volver a la API 1.

## 5. Consultar las empresas y sucursales del usuario

**Método:** `GET`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context`
**Permiso requerido:** `perm:operational-context:application_users:read`

### ¿Qué hace esta API?

Devuelve las empresas en las que el usuario autenticado tiene membresía y, para cada una, las sucursales que tiene asignadas, indicando cuáles puede usar ahora mismo (`allowed`) y, si no, por qué. Es la **primera llamada a SIO** después del login y la fuente del `company_id` y el `branch_id` que necesitan todas las demás API. El usuario se identifica por el token; no se envía ningún parámetro. Devuelve también membresías y asignaciones inactivas, para que la interfaz pueda explicarlo. Los nombres de empresa y sucursal no vienen en esta respuesta: se obtienen en [Administración empresarial](administracion-empresarial.md) con `GET …/companies/{company_id}` y `GET …/companies/{company_id}/branches`.

Antes necesita: solo el Access Token (API 1 o 2).

### ¿Cómo se realiza la solicitud?

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:** no requiere parámetros de consulta.

**Encabezados:**

| Nombre | Obligatorio | Valor | Origen |
|---|---|---|---|
| `Authorization` | Sí | `Bearer TU_ACCESS_TOKEN` | Access Token de la API 1 o 2; nunca el Refresh Token |
| `Accept` | No | `application/json` | Lo define la aplicación |

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`MeOperationalContextResponse`):

```json
{
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "memberships": [
    {
      "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      "company_id": "550e8400-e29b-41d4-a716-446655440000",
      "company_status": "ACTIVE",
      "status": "ACTIVE",
      "branches": [
        {
          "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
          "user_branch_status": "ACTIVE",
          "branch_status": "ACTIVE",
          "allowed": true,
          "reason": null
        },
        {
          "branch_id": "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
          "user_branch_status": "INACTIVE",
          "branch_status": "ACTIVE",
          "allowed": false,
          "reason": "USER_BRANCH_INACTIVE"
        }
      ]
    }
  ]
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `keycloak_user_id` | string (UUID) | El `sub` del token |
| `memberships[]` | array | Una entrada por empresa en la que el usuario tiene membresía (activa o inactiva). Puede tener varias; `[]` significa que el usuario no pertenece a ninguna empresa y no debe llamar a las API de empresa |
| `memberships[].application_user_id` | UUID | Identificador de la membresía (usuario dentro de la empresa) |
| `memberships[].company_id` | UUID | Empresa; es el `company_id` de las rutas `/companies/{company_id}/…` |
| `memberships[].company_status` | `ACTIVE` \| `INACTIVE` | Estado de la empresa |
| `memberships[].status` | `ACTIVE` \| `INACTIVE` | Estado de la membresía. La empresa es operable solo si `status` y `company_status` son `ACTIVE` |
| `branches[]` | array | Sucursales asignadas al usuario en esa empresa; `[]` si no tiene ninguna asignada |
| `branches[].branch_id` | UUID | Sucursal; es el `branch_id` que se envía en ventas, compras e inventario |
| `branches[].user_branch_status` | `ACTIVE` \| `INACTIVE` | Estado de la asignación usuario–sucursal |
| `branches[].branch_status` | `ACTIVE` \| `INACTIVE` | Estado de la sucursal |
| `branches[].allowed` | boolean | `true` si el usuario puede operar en esa sucursal ahora mismo |
| `branches[].reason` | string \| null | `null` si `allowed` es `true`; si no, la primera condición que falla, en este orden: `USER_MEMBERSHIP_INACTIVE`, `COMPANY_INACTIVE`, `BRANCH_INACTIVE`, `USER_BRANCH_INACTIVE` |

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "Se requiere un token de acceso Bearer"}` u otro `detail` (token vencido, firma, `iss` o `aud` incorrectos) | Falta el Access Token o no es válido | Renovar una vez (API 2) y reintentar; si falla, volver al login |
| `403` | `OPERATIONAL_CONTEXT.FORBIDDEN` | El token no incluye `perm:operational-context:application_users:read` | Mostrar que faltan permisos y el `trace_id`; no reintentar |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | Base de datos del servicio no disponible | Reintentar más tarde |

Ejemplo de `403` (Problem Details):

```json
{
  "type": "https://sio/errors/operational-context/forbidden",
  "title": "Acceso denegado",
  "status": 403,
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta.",
  "instance": "/api/v1/me/operational-context",
  "code": "OPERATIONAL_CONTEXT.FORBIDDEN",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

## 6. Comprobar un acceso concreto antes de actuar

**Método:** `GET`
**URL:** `https://sio-operational-context-dev.onrender.com/api/v1/operational-access`
**Permiso requerido:** `perm:operational-context:application_users:read`

### ¿Qué hace esta API?

Responde si el usuario autenticado puede operar en una empresa **o** en una sucursal, opcionalmente con un permiso concreto, y si no puede, la causa exacta. Es opcional: las API de negocio aplican las mismas reglas por sí mismas. Resulta útil para decidir qué mostrar al cambiar de empresa o sucursal, o para explicar al usuario por qué una acción no está disponible antes de que la intente. Una denegación nunca es un `403`: siempre responde `200` con `allowed: false`.

Regla verificada en el código: se envía **exactamente uno** de `company_id` o `branch_id`. Con `branch_id`, la empresa se deduce de la sucursal. Enviar los dos, o ninguno, responde `422`.

Antes necesita: el `company_id` o el `branch_id` de la API 5 y, si se quiere evaluar un permiso, su nombre exacto `perm:{servicio}:{recurso}:{accion}`.

### ¿Cómo se realiza la solicitud?

Comprobar una sucursal y un permiso:

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/operational-access?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&permission=perm:sales:sales:create' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

Comprobar solo la empresa:

```bash
curl -X GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/operational-access?company_id=550e8400-e29b-41d4-a716-446655440000' \
  -H 'Authorization: Bearer TU_ACCESS_TOKEN' \
  -H 'Accept: application/json'
```

### Parámetros de la solicitud

**Parámetros de ruta:** no requiere parámetros de ruta.

**Parámetros de consulta:**

| Nombre | Tipo | Obligatorio | Descripción | Valores admitidos y ejemplo | Cómo se agrega a la URL | Origen |
|---|---|---|---|---|---|---|
| `company_id` | UUID | Uno de los dos | Empresa a evaluar. No se combina con `branch_id` | UUID; p. ej. `550e8400-e29b-41d4-a716-446655440000` | `?company_id=550e8400-e29b-41d4-a716-446655440000` | `memberships[].company_id` de la API 5 |
| `branch_id` | UUID | Uno de los dos | Sucursal a evaluar; la empresa se deduce de ella. No se combina con `company_id` | UUID; p. ej. `7c9e6679-7425-40de-944b-e07fc1f90ae7` | `&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7` | `branches[].branch_id` de la API 5 |
| `permission` | string (≤ 255) | No | Permiso concreto a evaluar junto con el acceso, en formato `perm:{servicio}:{recurso}:{accion}`, sin el comodín `all`. Si se omite, no se evalúa ningún permiso | Texto libre (≤ 255 caracteres); p. ej. `perm:sales:sales:create` | `&permission=perm:sales:sales:create` | Permiso de la operación que se va a ejecutar (ver cada módulo) |
| `keycloak_user_id` | string (≤ 255) | No | Evalúa a **otro** usuario. Exige `perm:operational-context:platform:lookup`; no es para el frontend | Identificador `sub` de Keycloak (texto); p. ej. `3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c` | `&keycloak_user_id=3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c` | No usar |

Los parámetros de consulta se agregan al final de la URL: el primero después de `?` y los siguientes unidos con `&`; se envían solo los que se necesiten, en cualquier orden, y los valores con espacios, tildes o símbolos deben codificarse (por ejemplo `Pérez` → `P%C3%A9rez`). URL armada del ejemplo anterior: `https://sio-operational-context-dev.onrender.com/api/v1/operational-access?branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&permission=perm:sales:sales:create`

**Encabezados:**

| Nombre | Obligatorio | Valor | Origen |
|---|---|---|---|
| `Authorization` | Sí | `Bearer TU_ACCESS_TOKEN` | Access Token de la API 1 o 2 |
| `Accept` | No | `application/json` | Lo define la aplicación |

**Cuerpo de la solicitud:** no requiere Body.

### Respuesta exitosa

`200 OK` (`OperationalAccessResponse`), tanto si el acceso está permitido como si no. Acceso permitido:

```json
{
  "allowed": true,
  "reason": null,
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "company_id": "550e8400-e29b-41d4-a716-446655440000",
  "branch_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "application_user_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  "permission": "perm:sales:sales:create"
}
```

Acceso denegado (el usuario no es miembro de la empresa o la sucursal no existe):

```json
{
  "allowed": false,
  "reason": "USER_NOT_MEMBER",
  "keycloak_user_id": "3f2a9c1e-7b4d-4e8a-9c6f-1d2e3f4a5b6c",
  "company_id": null,
  "branch_id": "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
  "application_user_id": null,
  "permission": "perm:sales:sales:create"
}
```

| Campo | Tipo | Significado para el frontend |
|---|---|---|
| `allowed` | boolean | `true`: puede operar (y tiene el `permission`, si se envió) |
| `reason` | string \| null | `null` si `allowed` es `true`. Si no, la primera condición que falla, en este orden: `USER_NOT_MEMBER`, `USER_MEMBERSHIP_INACTIVE`, `COMPANY_INACTIVE`, `BRANCH_INACTIVE`, `BRANCH_NOT_ASSIGNED`, `USER_BRANCH_INACTIVE`, `PERMISSION_DENIED` |
| `keycloak_user_id` | string | Usuario evaluado (el del token) |
| `company_id` | UUID \| null | Empresa evaluada. Con `branch_id` en la solicitud, es la empresa de esa sucursal; `null` cuando `reason` es `USER_NOT_MEMBER` y se envió `branch_id` |
| `branch_id` | UUID \| null | Sucursal evaluada; `null` si solo se envió `company_id` |
| `application_user_id` | UUID \| null | Membresía del usuario en la empresa; `null` si no es miembro |
| `permission` | string \| null | El permiso enviado, o `null` si no se envió |

`USER_NOT_MEMBER` se devuelve también cuando la empresa o la sucursal no existen: por diseño esta API no revela si un identificador ajeno existe.

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `401` | `{"detail": "…"}` | Falta el Access Token o no es válido | Renovar una vez y reintentar; si falla, volver al login |
| `403` | `OPERATIONAL_CONTEXT.FORBIDDEN` | El token no incluye `perm:operational-context:application_users:read`, o se envió `keycloak_user_id` sin `perm:operational-context:platform:lookup` | Quitar `keycloak_user_id`; si persiste, mostrar que faltan permisos |
| `422` | `OPERATIONAL_CONTEXT.VALIDATION_ERROR` | Se enviaron `company_id` y `branch_id` a la vez, o ninguno; `permission` con formato distinto de `perm:a:b:c` o con `all`; un UUID mal formado | Corregir la solicitud; no es una denegación de acceso |
| `503` | `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` | Base de datos del servicio no disponible | Reintentar más tarde |

Ejemplo de `422` al enviar `company_id` y `branch_id` juntos:

```json
{
  "type": "https://sio/errors/operational-context/validation-error",
  "title": "Solicitud inválida",
  "status": 422,
  "detail": "Indique exactamente uno de branch_id o company_id.",
  "instance": "/api/v1/operational-access",
  "code": "OPERATIONAL_CONTEXT.VALIDATION_ERROR",
  "trace_id": "9f8e7d6c5b4a39281716151413121110",
  "errors": [
    {
      "field": "branch_id",
      "message": "Indique exactamente uno de branch_id o company_id.",
      "code": "VALIDATION_ERROR"
    }
  ]
}
```

## 7. Seleccionar empresa y sucursal de trabajo

**Método:** sin llamada. Es una decisión del frontend.
**URL:** no aplica.
**Permiso requerido:** ninguno.

### ¿Qué hace esta API?

Fija con qué empresa y sucursal trabajará el usuario durante la sesión. No existe en el backend un recurso «contexto seleccionado» ni cabeceras de contexto: la empresa elegida viaja en la ruta de cada operación posterior (`/companies/{company_id}/…`) y la sucursal en el cuerpo o en la consulta (`branch_id`). Cambiar de empresa o de sucursal es simplemente usar otro identificador en las siguientes llamadas.

Antes necesita: la respuesta de la API 5.

### ¿Cómo se realiza la solicitud?

No hay solicitud. Reglas para elegir, con la respuesta de la API 5:

1. Empresas elegibles: `memberships[]` con `status: "ACTIVE"` y `company_status: "ACTIVE"`.
2. Sucursales elegibles de la empresa elegida: `branches[]` con `allowed: true`.
3. Si hay una sola empresa y una sola sucursal elegibles, seleccionarlas sin preguntar. Si hay varias, pedir al usuario que elija y recordar la elección en la sesión del navegador.
4. Si no hay ninguna empresa elegible, mostrar que el usuario no tiene acceso a ninguna empresa y no llamar a las API de empresa (responderían `404`).

### Parámetros de la solicitud

No requiere parámetros de ruta. No requiere parámetros de consulta. No requiere Body.

### Respuesta exitosa

No aplica. La selección se confirma cuando las operaciones de negocio con ese `company_id` y `branch_id` responden `2xx`.

### Posibles errores

| HTTP | Código | Motivo | Qué debe hacer el frontend |
|---|---|---|---|
| `404` en rutas `/companies/{company_id}/…` | `{SERVICIO}.NOT_FOUND` | El `company_id` no está en el alcance del usuario (sin membresía activa) | Volver a leer la API 5: el contexto pudo cambiar desde el login |
| `403` en Sales, Purchase e Inventory | `BRANCH_ACCESS_DENIED` u `OPERATIONAL_ACCESS_DENIED` | La sucursal no está asignada al usuario o está inactiva | Volver a leer la API 5 y elegir otra sucursal |

## Dependencias con otros módulos

- [Administración empresarial](administracion-empresarial.md) crea las empresas, sucursales, membresías y asignaciones que este módulo consulta; sin ellas, `memberships` llega vacío. Crear una empresa no crea membresías ni sucursales: la primera membresía la registra un administrador.
- Todos los demás módulos empiezan con el `company_id` y el `branch_id` elegidos aquí ([company_id](../parametros/company-id.md), [branch_id](../parametros/branch-id.md)).
