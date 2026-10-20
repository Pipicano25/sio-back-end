# Autenticación de SIO con Keycloak

[← Volver al índice de las API](../index.md) · [Primeros pasos](primeros-pasos.md) · [Permisos de usuario](permisos.md) · [Errores](errores.md) · [Operational Context](../servicios/operational-context.md)

> **Entorno de esta guía:** `siodev`, servicios publicados en Render. Explica cómo una aplicación cliente obtiene una sesión de usuario, llama a las API de SIO, renueva la sesión y cierra sesión, y qué comprueban exactamente las API al recibir el token. **No incluye contraseñas, tokens ni secretos reales.**

## 1. Resumen para desarrolladores

SIO usa **Keycloak** como proveedor de identidad (OpenID Connect) y **tokens Bearer** para acceder a las API FastAPI.

1. El usuario entra en su aplicación web.
2. La aplicación lo envía a Keycloak mediante **Authorization Code + PKCE S256**.
3. Keycloak autentica al usuario y devuelve un *authorization code* a la URL de retorno autorizada.
4. El cliente canjea ese código por un **Access Token** y un **Refresh Token**.
5. La aplicación invoca las API enviando `Authorization: Bearer <ACCESS_TOKEN>`.
6. Cuando el Access Token está por expirar, el cliente renueva **una sola vez** y sustituye los tokens anteriores por los nuevos.

**Importante:** poder acceder a una URL de Render no concede acceso a un recurso protegido. La API valida el token, el permiso y, cuando corresponda, la membresía en la empresa o sucursal.

## 2. Datos de conexión

| Campo | Valor | ¿Para qué sirve? | Verificación |
|---|---|---|---|
| Servidor Keycloak | `https://fastapi-postgrest-online-keycloak.onrender.com` | Servidor de autenticación público | Verificado en vivo el 2026-10-19 (`/.well-known/openid-configuration`) |
| Realm | `siodev` | Ámbito de usuarios, roles y clientes de esta instalación | Verificado en vivo |
| Issuer (`iss` del token) | `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev` | Emisor que comprueban las API | Verificado en vivo |
| Client ID web | `sio-web` | Identificador público de cliente (no es una contraseña) | Plantilla del realm (`infrastructure/keycloak/realm-template/sio-realm.template.json`) |
| Audience de las API (`aud`) | `sio-api` | Audiencia que exige `libs/sio-auth` en todos los servicios | Código de `libs/sio-auth` (valor predeterminado) y plantilla del realm |
| Tipo de cliente | Público | **No** utiliza `client_secret` en el navegador | Plantilla del realm |
| Flujo web | Authorization Code + PKCE S256 | Autenticación interactiva; PKCE obligatorio (`pkce.code.challenge.method = S256`) | Plantilla del realm |
| Algoritmo de firma aceptado | `RS256` | Único algoritmo que aceptan las API; no es configurable | Código de `libs/sio-auth` |

### Endpoints de Keycloak (verificados en vivo)

| Método | Finalidad | URL completa |
|---|---|---|
| `GET` | Descubrir la configuración OpenID Connect | `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/.well-known/openid-configuration` |
| `GET` | Iniciar autorización / mostrar login | `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/auth` |
| `POST` | Canjear código o renovar tokens | `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token` |
| `GET` / `POST` | Cerrar sesión (*end session*) | `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/logout` |
| `GET` | Consultar información básica del usuario | `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/userinfo` |
| `GET` | Consultar las claves públicas (JWKS) | `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/certs` |
| `GET` | Gestionar la cuenta del usuario | `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/account` |

El JWKS publicado contiene una clave de firma `RS256` (`use: sig`) y una clave de cifrado `RSA-OAEP` (`use: enc`). Las API solo usan la de firma.

### Ejemplos cURL por endpoint

Cada endpoint tiene un ejemplo cURL en la sección donde se explica su uso. Los que son de solo lectura se comprobaron en vivo el 2026-10-20; los que necesitan una sesión usan marcadores (`CODIGO_TEMPORAL`, `$ACCESS_TOKEN`, `$REFRESH_TOKEN`) que debes sustituir por los valores reales de tu sesión y nunca escribir en la documentación ni en el código.

| Endpoint | ¿Para qué lo usa el frontend? | ¿Desde dónde se llama? | Ejemplo |
|---|---|---|---|
| `GET …/.well-known/openid-configuration` | Descubrir todas las URL y capacidades del realm | Biblioteca OIDC al arrancar, o a mano para diagnosticar | Esta sección |
| `GET …/protocol/openid-connect/certs` | Obtener las claves públicas con las que las API verifican la firma del token | Las API (no el frontend); a mano para diagnosticar | Esta sección |
| `GET …/protocol/openid-connect/auth` | Mostrar el formulario de login y devolver un `code` | Navegador (redirección); cURL solo para comprobar que responde | §4.1 |
| `POST …/protocol/openid-connect/token` (`authorization_code`) | Canjear el `code` por Access, Refresh e ID Token | Frontend, una vez por login | §4.2 |
| `POST …/protocol/openid-connect/token` (`refresh_token`) | Renovar los tokens antes de que venzan | Frontend, cada ~4–5 minutos de uso | §9.1 |
| `POST …/protocol/openid-connect/token` (`password`) | Obtener tokens con usuario y contraseña, solo para scripts de desarrollo | Terminal o pruebas automatizadas; **nunca** el frontend | §10 |
| `GET …/protocol/openid-connect/userinfo` | Comprobar que un Access Token es válido y leer la identidad básica | Opcional, diagnóstico | §7.1 |
| `POST …/protocol/openid-connect/logout` | Revocar la sesión sin salir de la página | Frontend (alternativa) | §11 |
| `GET …/protocol/openid-connect/logout` | Cerrar la sesión SSO y volver al frontend | Navegador (redirección) | §11 |
| `GET …/account` | Consola de cuenta de Keycloak (cambiar contraseña, ver sesiones) | Navegador, solo si se quiere enlazar | No aplica a cURL |
| `GET https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` | Primera llamada a una API de SIO con el token | Frontend, justo después del login | §6.2 |

**Descubrimiento.** Devuelve el documento OpenID Connect del realm; sirve para configurar la biblioteca OIDC con una sola URL y para confirmar que el realm existe y responde:

```bash
curl -sS 'https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/.well-known/openid-configuration'
```

Respuesta `200` (fragmento observado en vivo):

```json
{
  "issuer": "https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev",
  "authorization_endpoint": "https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/auth",
  "token_endpoint": "https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token",
  "userinfo_endpoint": "https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/userinfo",
  "end_session_endpoint": "https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/logout",
  "jwks_uri": "https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/certs",
  "grant_types_supported": ["authorization_code", "client_credentials", "implicit", "password", "refresh_token"],
  "code_challenge_methods_supported": ["plain", "S256"]
}
```

`grant_types_supported` describe lo que el **realm** admite en general; lo que admite el cliente `sio-web` lo decide su configuración (sección 3). Un `404` aquí significa que la URL del servidor o el nombre del realm están mal escritos.

**Claves públicas (JWKS).** No la llama el frontend: la usan las 12 API para verificar la firma `RS256` del Access Token. Sirve para diagnosticar un `401` por firma inválida (por ejemplo, un token emitido por otro realm):

```bash
curl -sS 'https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/certs'
```

Respuesta `200` (fragmento observado; se omiten los valores largos de `n`, `e` y `x5c`):

```json
{
  "keys": [
    {"kid": "W8Hgh_USfds4O5ZRD7Qn0v8dPWeIj18m-IWSecfa2Fo", "kty": "RSA", "alg": "RS256", "use": "sig"},
    {"kid": "TRKSstM9eWKyFRRlFJ3ZST9SO98vwaTrmDWCdV95FgY", "kty": "RSA", "alg": "RSA-OAEP", "use": "enc"}
  ]
}
```

El `kid` de la clave `sig` debe coincidir con el `kid` de la cabecera del Access Token. Si Keycloak rota la clave, las API la recargan desde esta URL.

**Recomendación:** si usas una biblioteca OIDC, configúrala con el *issuer* o el documento de descubrimiento en lugar de construir a mano todas las URL.

## 3. Clientes del realm

| Cliente | Tipo | Uso | Quién lo usa |
|---|---|---|---|
| `sio-web` | Público (sin secreto), Standard Flow, PKCE S256, sin Implicit Flow, sin Service Account | Login de usuarios desde el navegador | **Frontend** |
| `sio-api` | Bearer-only (no inicia sesiones) | Representa a las API. Es la **audiencia** (`aud`) de los tokens y el contenedor de los *client roles* `perm:*` | Las 12 API, al validar tokens |
| `party-identity-service`, `operational-context-service`, `commercial-relationship-service`, `product-catalog-service`, `inventory-service`, `purchase-service`, `sales-service`, `product-inventory-query-service`, `sio-data-importer`, `audit-test-emitter`, `inventory-test-operator` | Confidenciales con `client_credentials` | Identidades técnicas entre servicios y de pruebas | **Solo backend. Nunca desde el frontend.** |

El cliente `sio-web` incluye un *protocol mapper* de audiencia que añade `sio-api` al claim `aud` del Access Token. Sin ese claim las API responden `401`.

Scopes por defecto de `sio-web`: `web-origins`, `acr`, `roles`, `profile`, `basic`, `email`. Scopes opcionales: `address`, `phone`, `organization`, `microprofile-jwt`. **`offline_access` no está disponible** para `sio-web`: no solicite tokens sin conexión.

### 3.1. ¿Qué debe configurar el frontend?

| Parámetro | Ejemplo | Dónde obtenerlo o configurarlo |
|---|---|---|
| `url` / `issuer` | `https://fastapi-postgrest-online-keycloak.onrender.com` | Tabla anterior; es un valor público |
| `realm` | `siodev` | Tabla anterior |
| `clientId` | `sio-web` | Cliente de Keycloak habilitado para la aplicación |
| `redirect_uri` | `https://mi-frontend.example.com/auth/callback` | **La define el desarrollador del frontend**; debe registrarse como *Valid Redirect URI* en `sio-web` |
| Origen de la aplicación | `https://mi-frontend.example.com` | Dirección donde se publicará la aplicación; debe registrarse como *Web Origin* en `sio-web` |
| URL de retorno tras el logout | `https://mi-frontend.example.com/` | Debe registrarse como *Valid Post Logout Redirect URI* en `sio-web` |
| `scope` | `openid profile email` | Solicitud OIDC habitual; los permisos llegan por el client scope `roles` |
| `access_token` | `eyJ...` | Lo entrega el **token endpoint** tras el login; es sensible y no debe incluirse en documentación ni logs |
| `refresh_token` | `eyJ...` | Lo entrega el token endpoint; se usa únicamente para renovar la sesión |
| `company_id` | UUID | **No** viene en el token. Se obtiene de [Operational Context](../parametros/company-id.md) después de iniciar sesión |
| `branch_id` | UUID | Se obtiene de [Operational Context](../parametros/branch-id.md) después de iniciar sesión |

> El dominio `mi-frontend.example.com` es **ficticio**. El equipo integrador debe comunicar su URL de retorno y su origen para registrarlos en Keycloak.

### 3.2. Redirect URIs y Web Origins

La plantilla del realm toma estos valores de variables de entorno (`SIO_WEB_REDIRECT_URI`, `SIO_WEB_ORIGIN`). En el entorno local valen `http://localhost:3000/*` y `http://localhost:3000`.

La plantilla del realm del repositorio define estos tres campos a partir de variables de entorno del despliegue de Keycloak: `redirectUris` y `post.logout.redirect.uris` toman `SIO_WEB_REDIRECT_URI`, y `webOrigins` y `rootUrl` toman `SIO_WEB_ORIGIN`. 

## 4. Inicio de sesión: Authorization Code + PKCE S256

Es el único flujo permitido para el frontend. **No envíes el usuario y la contraseña directamente desde tu aplicación al token endpoint usando `grant_type=password`** (ver la sección 10). Los flujos *implicit* e *hybrid* están deshabilitados en `sio-web`.

Secuencia:

1. El frontend genera un `code_verifier` aleatorio (43 a 128 caracteres) y su `code_challenge = BASE64URL(SHA256(code_verifier))`.
2. Redirige al usuario al endpoint de autorización.
3. El usuario se autentica en la pantalla de Keycloak.
4. Keycloak redirige a la `redirect_uri` con `code` y `state`.
5. El frontend intercambia el `code` por tokens en el token endpoint, enviando el `code_verifier`.
6. El frontend guarda los tokens **en memoria** y usa el `access_token` en cada llamada a las API.

### 4.1. Solicitud de autorización

El navegador abre la URL del *authorization endpoint* con los parámetros de la tabla (ejemplo ilustrativo; el *code challenge* y el estado se generan para cada intento). Este endpoint devuelve una página HTML de login y termina en una redirección, así que no se consume desde código; el cURL siguiente muestra la URL completa y sirve para comprobar qué responde Keycloak a los parámetros del frontend:

```bash
curl -sS -o /dev/null -w '%{http_code} %{content_type}\n' \
  'https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/auth?client_id=sio-web&response_type=code&scope=openid%20profile%20email&redirect_uri=https%3A%2F%2Fmi-frontend.example.com%2Fauth%2Fcallback&state=f3c1a2b4c5d6e7f8&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&code_challenge_method=S256'
```

| Parámetro | Obligatorio | Función | Origen |
|---|---|---|---|
| `client_id` | Sí | Identifica la aplicación cliente | `sio-web` |
| `response_type` | Sí | Solicita un código de autorización | Valor fijo: `code` |
| `redirect_uri` | Sí | Dirección a la que Keycloak devuelve el navegador | URL de retorno propia del frontend, registrada en Keycloak |
| `scope` | Habitual | Solicita identidad OpenID Connect | `openid`, opcionalmente `profile` y `email` |
| `state` | Sí, recomendado | Protege y vincula la solicitud con su respuesta | Valor impredecible generado por el cliente y verificado al volver |
| `code_challenge` | Sí (PKCE obligatorio) | Resumen derivado del `code_verifier` | Lo genera la biblioteca OIDC |
| `code_challenge_method` | Sí | Algoritmo PKCE | `S256` |

Tras autenticarse, Keycloak redirige a la aplicación con parámetros parecidos a estos:

```text
https://mi-frontend.example.com/auth/callback?code=CODIGO_TEMPORAL&state=f3c1a2b4c5d6e7f8
```

La aplicación comprueba `state` y canjea el código utilizando el `code_verifier` original. Un código es de corta duración y solo puede utilizarse una vez.

**Qué responde el cURL anterior:**

| Resultado | Significado |
|---|---|
| `200 text/html` | Keycloak aceptó los parámetros y devolvió el formulario de login: la `redirect_uri` está registrada en `sio-web` |
| `400 text/html` | Keycloak rechazó la solicitud (la página dice, por ejemplo, `Invalid parameter: redirect_uri` o falta `code_challenge`). Observado en vivo el 2026-10-20 con la `redirect_uri` de ejemplo, que no está registrada |

Sustituye `redirect_uri` por la URL exacta de tu frontend para saber si ya está autorizada sin tener que abrir el navegador.

### 4.2. Canje del código por tokens

`POST` al *token endpoint* con un formulario `application/x-www-form-urlencoded`. Es la llamada que hace el frontend (o la biblioteca OIDC) al volver a `/auth/callback`; sirve para reproducir a mano un canje y ver la respuesta completa. El `code` caduca en segundos y solo vale una vez, y el `code_verifier` debe ser el mismo que generó el `code_challenge` de §4.1:

```bash
curl -sS -X POST 'https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=authorization_code' \
  --data-urlencode 'client_id=sio-web' \
  --data-urlencode 'code=CODIGO_TEMPORAL' \
  --data-urlencode 'redirect_uri=https://mi-frontend.example.com/auth/callback' \
  --data-urlencode 'code_verifier=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'
```

Ejemplo desde consola

```bash
curl -sS -X POST \
  'https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=password' \
  --data-urlencode 'client_id=sio-web' \
  --data-urlencode 'username=NombreUsuario' \
  --data-urlencode 'password=ContraseñaUsuario' \
  --data-urlencode 'scope=openid' | jq
```

**Campos de formulario** (no JSON):

| Campo | Obligatorio | Ejemplo | Origen |
|---|---|---|---|
| `grant_type` | Sí | `authorization_code` | Valor fijo |
| `client_id` | Sí | `sio-web` | Configuración pública del frontend |
| `code` | Sí | `CODIGO_TEMPORAL` | Parámetro `code` recibido en la URL de retorno |
| `redirect_uri` | Sí | La misma URL de retorno usada al autorizar | Configuración del frontend |
| `code_verifier` | Sí | Valor secreto temporal generado antes de iniciar el flujo | Lo genera la biblioteca OIDC; **no** es un `client_secret` |

No se envía `client_secret`: `sio-web` es público.

**Respuesta `200 OK`** (formato estándar de Keycloak; valores ilustrativos, no son tokens utilizables):

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
| `access_token` | string (JWT RS256) | Enviar a las API como `Authorization: Bearer …` |
| `expires_in` | integer (segundos) | Programar la renovación antes de que venza (30 a 60 s de margen). Valor documentado: 300 |
| `refresh_token` | string (JWT) | Solo para renovar. Nunca enviarlo a las API |
| `refresh_expires_in` | integer (segundos) | Si vence, hay que volver a iniciar sesión. También aplican los límites de sesión de la sección 9 |
| `id_token` | string (JWT) | Identidad para la interfaz y para el cierre de sesión (`id_token_hint`). **No** sustituye al Access Token |
| `token_type` | string | Siempre `Bearer` |
| `session_state` | string (UUID) | Identificador de sesión SSO; informativo |
| `scope` | string | Scopes concedidos |

**Errores del token endpoint** (formato estándar OAuth 2.0 de Keycloak):

| HTTP | `error` | Causa habitual |
|---|---|---|
| 400 | `invalid_grant` | `code` ya usado o vencido, `code_verifier` incorrecto, `redirect_uri` distinta de la usada en el login, refresh token vencido o ya rotado |
| 400 | `invalid_request` | Falta un parámetro obligatorio (por ejemplo `code_verifier`) |
| 400 | `unauthorized_client` | El cliente no tiene habilitado ese `grant_type` |
| 401 | `invalid_client` | `client_id` inexistente o se envió un secreto a un cliente público |

```json
{
  "error": "invalid_grant",
  "error_description": "Code not valid"
}
```

> **Consejo:** utiliza una biblioteca probada como `keycloak-js` para generar y validar los elementos del flujo PKCE. No implementes criptografía de PKCE ni almacenamiento de sesión manualmente si puedes evitarlo.

## 5. Integración con una biblioteca OIDC

El frontend no debe implementar a mano el flujo de §4. Cualquier biblioteca OpenID Connect para navegador (por ejemplo `keycloak-js`, que publica el propio Keycloak) lo resuelve con tres datos públicos: la URL del servidor, el realm `siodev` y el `client_id` `sio-web`. Al configurarla, comprueba que:

- usa **Authorization Code + PKCE `S256`** (es obligatorio en `sio-web`);
- inicia sesión con redirección al login de Keycloak y vuelve a una URL de retorno registrada (§3.2);
- renueva el Access Token antes de que venza (vida de 300 s; renovar con 30–60 s de margen) y **sustituye siempre** el Refresh Token por el nuevo (§9);
- expone el Access Token vigente para adjuntarlo como `Authorization: Bearer` en cada llamada a las API (§6);
- cierra sesión con el *end session endpoint* (§11).

Una aplicación con **varias pestañas** debe coordinar la renovación entre ellas (§9.2). Los tokens se guardan en memoria; no en `localStorage` ni en cookies accesibles por script (§14).

## 6. Consumir una API de SIO con el Access Token

### 6.2. Primera consulta recomendada: contexto operativo

**Método y URL:** `GET https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context`

| Encabezado | Obligatorio | Ejemplo | Origen |
|---|---|---|---|
| `Authorization` | Sí | `Bearer eyJ...` | Access Token devuelto por Keycloak; nunca el Refresh Token |
| `Accept` | Opcional | `application/json` | Lo define la aplicación |

**Permiso exigido:** `perm:operational-context:application_users:read` (declarado en el router del servicio). Lo incluyen todos los grupos de prueba del realm salvo que se haya modificado la asignación.

**Parámetros de ruta:** ninguno. **Parámetros de consulta:** ninguno. **Body:** no lleva.

**Ejemplo cURL**, usando un token previamente obtenido y almacenado solo en la sesión de terminal:

```bash
curl --request GET \
  'https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context' \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  --header 'Accept: application/json'
```

**Respuesta `200`** (estructura tomada del modelo Pydantic `MeOperationalContextResponse`; identificadores ilustrativos):

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
        }
      ]
    }
  ]
}
```

| Campo | Tipo | Significado |
|---|---|---|
| `keycloak_user_id` | string | El `sub` del token |
| `memberships[]` | array | Una entrada por empresa en la que el usuario tiene membresía |
| `memberships[].application_user_id` | UUID | Usuario de aplicación dentro de esa empresa |
| `memberships[].company_id` | UUID | **Valor de `company_id`** para el resto de las API |
| `memberships[].company_status`, `memberships[].status` | `"ACTIVE"` \| `"INACTIVE"` | Estado de la empresa y de la membresía |
| `memberships[].branches[].branch_id` | UUID | **Valor de `branch_id`** |
| `memberships[].branches[].allowed` | boolean | Si el usuario puede operar en esa sucursal ahora |
| `memberships[].branches[].reason` | string \| null | Causa estable cuando `allowed` es `false` |

Un usuario autenticado sin membresías recibe `memberships: []`. Esta respuesta permite elegir la empresa y la sucursal activas; el detalle completo está en la ficha de [Operational Context](../servicios/operational-context.md).

**Siguiente paso:** [obtener la empresa](../parametros/company-id.md), [obtener la sucursal](../parametros/branch-id.md) y consultar el [catálogo de servicios](../index.md).

## 7. Qué contiene el Access Token y qué permisos se utilizan

Payload decodificado de un Access Token de `sio-web` (**ejemplo ilustrativo**; los identificadores no son reales):

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

| Claim | Uso en SIO | Quién lo entrega |
|---|---|---|
| `iss` | Debe ser exactamente el issuer configurado en cada API | Keycloak |
| `aud` | Debe incluir `sio-api` | Keycloak (mapper de audiencia de `sio-web`) |
| `sub` | Identificador estable del usuario (`keycloak_user_id`). Es la clave con la que Operational Context asocia membresías y sucursales | Keycloak |
| `exp` | Vencimiento. No hay tolerancia de reloj: un token vencido por un segundo es rechazado | Keycloak |
| `resource_access["sio-api"].roles` | Roles de negocio (`administrador`, `supervisor`, `compras`, `ventas`, `inventario`, `reportes`, `consulta`) y permisos `perm:*`. **Solo los que empiezan por `perm:` conceden acceso a operaciones** | Keycloak (client scope `roles`) |
| `preferred_username`, `email` | Informativos; algunos servicios los registran en auditoría | Keycloak |

Los permisos tienen la forma `perm:{servicio}:{recurso}:{accion}` y admiten el comodín `all` en cualquier segmento. Por ejemplo, `perm:sales:sales:create` permite solicitar la creación de ventas **si las demás validaciones del endpoint también se cumplen**. Los roles simples, como `ventas`, representan perfiles, no permisos suficientes por sí solos. Un `perm:` con un número de segmentos distinto de cuatro se ignora.

El frontend puede leer `resource_access["sio-api"].roles` para mostrar u ocultar opciones, pero **la autorización definitiva la hace cada API**. No use `realm_access`, `groups` ni el ID Token para decidir permisos.

**Atención:** el Access Token **no contiene la lista de empresas y sucursales** del usuario. Ese contexto se consulta en Operational Context. Para ampliar, visita [Permisos](permisos.md).

## 8. Qué comprueban las API al recibir el token

Las 12 API usan la misma librería (`libs/sio-auth`) como middleware global. Comportamiento verificado en el código:

1. **Rutas públicas** (sin token): `/health/live`, `/health/ready` y, cuando la documentación está habilitada, `/docs` y `/openapi.json`. El 2026-10-19 los 12 servicios en Render servían `/openapi.json` sin token. Todo lo demás exige token.
2. **Cabecera**: debe ser exactamente `Authorization: Bearer <token>` (dos partes; el esquema no distingue mayúsculas). Sin cabecera o mal formada: `401`.
3. **Encabezado JWT**: `alg` debe ser `RS256` y debe existir `kid`. La clave se busca en el JWKS del issuer (caché de 300 s).
4. **Claims obligatorios**: `exp`, `iss`, `aud`, `sub`. `iss` igual al configurado; `aud` debe contener `sio-api`.
5. **Permisos**: se extraen de `resource_access["sio-api"].roles` y cada operación exige un permiso concreto. Sin permiso: `403`.
6. **Alcance de datos**: además del permiso, los servicios con datos de empresa comprueban la membresía del `sub` en la empresa o sucursal de la ruta. Fuera de alcance responden `404`, igual que si el recurso no existiera.

### 8.1. Respuestas `401`

Mensajes posibles en `detail` (texto exacto del código de `libs/sio-auth`):

- «Se requiere un token de acceso Bearer»
- «El token de acceso está mal formado»
- «El token de acceso utiliza un algoritmo no permitido»
- «El encabezado del token de acceso no contiene kid»
- «El token de acceso ha expirado»
- «El issuer del token de acceso es inválido»
- «La audiencia del token de acceso es inválida»
- «Al token de acceso le falta el claim obligatorio: {claim}»
- «El token de acceso es inválido»

Toda respuesta `401` incluye `WWW-Authenticate: Bearer`. El cuerpo tiene dos formas según el servicio:

Forma básica (la emite la librería; es la que devuelven **Geography** y **Payment Reference**):

```json
{
  "detail": "El token de acceso ha expirado"
}
```

Forma Problem Details (`application/problem+json`, con `code` y `trace_id`; la emiten los otros diez servicios a través de su middleware de trazabilidad; ejemplo de Operational Context):

```json
{
  "type": "https://sio/errors/operational-context/unauthenticated",
  "title": "No autenticado",
  "status": 401,
  "detail": "El token de acceso ha expirado",
  "instance": "/api/v1/me/operational-context",
  "code": "OPERATIONAL_CONTEXT.UNAUTHENTICATED",
  "trace_id": "9f8e7d6c5b4a39281716151413121110"
}
```

El detalle por servicio está en [Errores](errores.md).

### 8.2. Respuestas `403`

Cuando el token es válido pero no cubre el permiso de la operación, la librería responde `403` con este `detail` fijo, que **nunca revela el permiso exigido**:

```json
{
  "detail": "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, solicítelo al administrador del sistema indicando el trace_id de esta respuesta."
}
```

El permiso exigido queda registrado solo en el log del servidor junto con el `trace_id` (cabecera `X-Trace-Id` en los servicios que la emiten). El frontend debe mostrar ese identificador al usuario para que soporte pueda diagnosticar. No reintente un `403`.

## 9. Renovar tokens: rotación obligatoria

La configuración del realm (plantilla del repositorio) establece:

| Regla | Valor documentado | Consecuencia |
|---|---|---|
| Vida del Access Token | `300` segundos | Renovar antes de que expire (por ejemplo, con 30–60 s de margen) |
| Sesión inactiva | `1800` segundos (30 min) | Si transcurre el límite sin renovar, habrá que volver a iniciar sesión |
| Duración máxima de sesión | `36000` segundos (10 h) | La sesión no puede renovarse indefinidamente |
| Rotación | Activada (`revokeRefreshToken=true`) | Cada renovación sustituye el Refresh Token anterior |
| Reutilización permitida | `0` (`refreshTokenMaxReuse=0`) | Reutilizar un Refresh Token anterior invalida toda la sesión, incluido el Refresh Token vigente |
| `offline_access` | No habilitado en `sio-web` | No solicitar tokens offline para el frontend |


### 9.1. Endpoint de renovación

`POST` al mismo *token endpoint* de §4.2, con `grant_type=refresh_token`. Es la llamada que el frontend repite en segundo plano antes de que venza el Access Token (300 s). El Refresh Token va en el cuerpo del formulario, nunca en la cabecera `Authorization`:

```bash
curl -sS -X POST 'https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=refresh_token' \
  --data-urlencode 'client_id=sio-web' \
  --data-urlencode "refresh_token=$REFRESH_TOKEN"
```

**Respuesta `200 OK`** (mismo formato que en 4.2; incluye un **nuevo** `refresh_token`):

```json
{
  "access_token": "NUEVO_ACCESS_TOKEN",
  "refresh_token": "NUEVO_REFRESH_TOKEN",
  "token_type": "Bearer",
  "expires_in": 300,
  "refresh_expires_in": 1800
}
```

**Respuesta ante un Refresh Token inválido o de otra sesión** (`400`, observado en vivo el 2026-10-20):

```json
{
  "error": "invalid_grant",
  "error_description": "Invalid refresh token"
}
```

**Respuesta ante reutilización de un Refresh Token ya consumido** (texto observado en el realm de desarrollo local con la misma política):

```json
{
  "error": "invalid_grant",
  "error_description": "Maximum allowed refresh token reuse exceeded"
}
```

### 9.2. Regla fundamental

**Después de cada renovación, reemplaza tanto el `access_token` como el `refresh_token`. Nunca vuelvas a utilizar el Refresh Token anterior.**

- Centraliza la renovación en un único punto del cliente y **serializa** las renovaciones. Dos pestañas o dos peticiones concurrentes que renueven con el mismo token cierran la sesión. `keycloak-js` agrupa renovaciones dentro de una misma página, pero **no garantiza coordinación entre varias pestañas**; una aplicación multi-pestaña debe usar un único coordinador (por ejemplo `BroadcastChannel` o un `SharedWorker`) sin exponer tokens innecesariamente.
- Ante `invalid_grant` o una sesión ya no renovable, lleva al usuario al login. No reintentes con el mismo Refresh Token.
- Después de cada renovación, recalcula los permisos representados en la interfaz: pueden haber cambiado.
- Estrategia recomendada ante las API: si una llamada devuelve `401`, renovar una vez y reintentar una vez. Si vuelve a fallar, cerrar sesión localmente y redirigir al login.

## 10. Cerrar sesión

**Redirección del navegador** (cierra la sesión SSO y vuelve al frontend). El navegador abre el *end session endpoint* con `client_id`, `id_token_hint` (el ID Token de la sesión) y `post_logout_redirect_uri`; la biblioteca OIDC construye esta URL al cerrar sesión. El cURL muestra la URL completa y permite comprobar la respuesta sin abrir el navegador:

```bash
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' \
  "https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/logout?client_id=sio-web&id_token_hint=$ID_TOKEN&post_logout_redirect_uri=https%3A%2F%2Fmi-frontend.example.com%2F"
```
ejemplo desde consolda

```bash
curl -sS -X POST \
  'https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'grant_type=refresh_token' \
  --data-urlencode 'client_id=sio-web' \
  --data-urlencode 'refresh_token=TU_REFRESH_TOKEN' | jq
```

| Resultado | Significado |
|---|---|
| `302` y `redirect_url` igual a la `post_logout_redirect_uri` | Sesión cerrada; Keycloak devuelve al frontend |
| `400` | `post_logout_redirect_uri` no autorizada en *Valid Post Logout Redirect URIs* de `sio-web` o `id_token_hint` inválido. Observado en vivo el 2026-10-20 con la URL de ejemplo, que no está registrada |

`sio-web` tiene *front-channel logout* habilitado.

**Alternativa sin redirección** (`POST` al mismo endpoint con `client_id` y `refresh_token` en el formulario). Útil para cerrar la sesión desde un script o para un botón de «salir» que no quiera abandonar la página. Revoca el Refresh Token y la sesión SSO en Keycloak:

```bash
curl -sS -X POST 'https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/logout' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'client_id=sio-web' \
  --data-urlencode "refresh_token=$REFRESH_TOKEN" \
  -o /dev/null -w '%{http_code}\n'
```

Respuesta `204 No Content`. Si el Refresh Token ya no es válido (sesión vencida, token rotado o inventado), Keycloak responde `400` con `{"error": "invalid_grant", "error_description": "Invalid refresh token"}` (observado en vivo el 2026-10-20); en ese caso la sesión ya no existe y basta con borrar los tokens locales. La variante `GET …/logout` con `id_token_hint` y `post_logout_redirect_uri` es solo para el navegador: responde con una redirección, no con un cuerpo utilizable desde cURL. Después, borre los tokens de memoria. Los Access Tokens ya emitidos siguen siendo válidos para las API hasta su vencimiento (máximo 5 min), porque las API validan la firma y no consultan la sesión en Keycloak.

## 12. Errores habituales y qué hacer

| Situación | Dónde sucede | Respuesta habitual | Acción para el frontend |
|---|---|---|---|
| Falta `Authorization` en una API protegida | Microservicio FastAPI | `401` «Se requiere un token de acceso Bearer» | Iniciar sesión y enviar Access Token |
| Token expirado, inválido o con emisor o audiencia incorrectos | Microservicio FastAPI | `401` con el `detail` correspondiente (sección 8.1) | Renovar una vez si procede; si no es posible, ir al login |
| Token válido, sin permiso funcional | Microservicio FastAPI | `403` con `detail` fijo (sección 8.2) | Mostrar falta de permisos y el `trace_id`; no repetir la acción |
| Empresa o sucursal no accesible | API de negocio / Operational Context | `404` | Revisar el contexto activo mediante `me/operational-context` |
| URL de retorno no autorizada | Keycloak | `Invalid parameter: redirect_uri` | Registrar la Redirect URI exacta del frontend en `sio-web` |
| Refresh Token anterior reutilizado o renovaciones simultáneas | Keycloak | `400` `invalid_grant` «Maximum allowed refresh token reuse exceeded» | Cerrar el estado local de sesión y volver a autenticar |
| Sesión vencida por inactividad o duración máxima | Keycloak | `400` `invalid_grant` | Volver al login |
| Usuario o contraseña incorrectos | Keycloak | Error en el formulario de login | Permitir corrección sin registrar credenciales en logs |

Los detalles de errores y JSON de cada operación se documentan en [Errores](errores.md) y en la ficha de cada microservicio.

## 13. Seguridad y buenas prácticas

- Utiliza siempre **HTTPS** para Keycloak y para las API públicas de Render.
- Use solo `sio-web` con Authorization Code + PKCE S256. No use `client_credentials`, `grant_type=password` ni ningún secreto de cliente técnico en el navegador.
- **Nunca** coloques contraseñas, Refresh Tokens, `client_secret` de clientes técnicos ni credenciales de Neon en archivos públicos del frontend.
- Mantén los tokens en memoria cuando sea viable; evita `localStorage` para Access Tokens, Refresh Tokens y permisos derivados de ellos.
- No envíes tokens mediante parámetros de URL ni los imprimas en consola, capturas, analíticas o logs.
- Nunca envíes el `refresh_token` ni el `id_token` a las API de SIO. Solo el `access_token`.
- No asumas acceso por tener un rol de perfil (`ventas`, `supervisor`): comprueba `perm:*` y deja la decisión final al backend.
- No inventes `company_id` ni `branch_id`: consulta los valores permitidos en Operational Context.
- Trata `401` como «renovar y reintentar una vez» y `403` como «sin permiso: mostrar mensaje y `trace_id`».
- Cada operación sensible (`WRITE`, `HIGH_RISK`) debe confirmarse con el usuario antes de enviarse; las API no piden confirmación.
- Los ejemplos de esta guía usan dominios, identificadores y credenciales ficticios.

## 14. Lista de verificación de integración

- [ ] El frontend conoce URL de Keycloak, realm `siodev` y el `client_id` `sio-web`.
- [ ] Su URL de retorno, su origen y su URL de post-logout están registrados en `sio-web`.
- [ ] El login usa **Authorization Code + PKCE S256**.
- [ ] Las API reciben `Authorization: Bearer <ACCESS_TOKEN>`.
- [ ] El Access Token incluye la audiencia `sio-api`.
- [ ] El frontend consulta `GET /api/v1/me/operational-context` para obtener empresas y sucursales reales.
- [ ] Los permisos se leen desde `resource_access["sio-api"].roles` y se recalculan después de renovar.
- [ ] Se reemplaza el Refresh Token en cada renovación y no se renueva simultáneamente con el mismo token.
- [ ] Ante `403` se muestra el `trace_id` de la cabecera `X-Trace-Id` o del cuerpo.
- [ ] El logout termina la sesión y limpia el estado local del frontend.

## 15. Información pendiente de verificar

| Punto | Estado |
|---|---|
| *Valid Redirect URIs*, *Web Origins* y *Valid Post Logout Redirect URIs* del cliente `sio-web` en Render |  (la plantilla los toma de `SIO_WEB_REDIRECT_URI` y `SIO_WEB_ORIGIN`) |
| Duración real de Access Token, Refresh Token y sesión en el realm `siodev` de Render |  (la plantilla indica 300 s, 1 800 s y 36 000 s) |
| Grant `password` habilitado o no en `sio-web` de Render |  (depende de `SIO_WEB_DIRECT_ACCESS_GRANTS_ENABLED`; el script de despliegue lo activa si la variable falta) |
| Existencia de los usuarios de prueba y sus membresías en Render |  |
| Que el issuer configurado en las 12 API de Render (`SIO_AUTH_ISSUER`) sea exactamente `https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev` |  directamente; se infiere de que las API usan el mismo realm |

---

**Referencias del propio repositorio:** `libs/sio-auth/` (validación de tokens y permisos), `infrastructure/keycloak/realm-template/sio-realm.template.json` (clientes, grupos, usuarios de prueba, tiempos de sesión), `infrastructure/README.md` (sesiones y tokens de `sio-web`, validación manual con cURL), `docs/frontend-permissions.md` (uso de permisos en la interfaz) y los contratos OpenAPI de los microservicios.
