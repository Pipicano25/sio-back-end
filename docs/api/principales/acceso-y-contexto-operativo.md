# 6.1 Acceso y contexto operativo

[← API principales](README.md) · [← Índice](../index.md)

Todo lo que el frontend debe hacer entre la pantalla de login y la primera operación de negocio: autenticar al usuario en Keycloak, saber quién es, en qué empresas tiene membresía, en qué sucursales puede operar y fijar la empresa y la sucursal con las que trabajará.

Servicios implicados: Keycloak (realm `siodev`, cliente público `sio-web`) y [Operational Context](../servicios/operational-context.md). Guías de apoyo: [Autenticación](../guias/autenticacion.md), [Permisos](../guias/permisos.md), [Primeros pasos](../guias/primeros-pasos.md).

| # | Funcionalidad | Operación | Ficha |
|---|---|---|---|
| 1 | Iniciar sesión | `GET …/protocol/openid-connect/auth` + `POST …/protocol/openid-connect/token` (Keycloak) | [Autenticación §4](../guias/autenticacion.md#4-inicio-de-sesión-authorization-code--pkce-s256) |
| 2 | Renovar la sesión | `POST …/protocol/openid-connect/token` con `grant_type=refresh_token` | [Autenticación §9](../guias/autenticacion.md#9-renovar-tokens-rotación-obligatoria) |
| 3 | Cerrar sesión | `GET`/`POST …/protocol/openid-connect/logout` | [Autenticación §11](../guias/autenticacion.md#11-cerrar-sesión) |
| 4 | Identificar al usuario y sus permisos | Lectura del Access Token (sin llamada) | [Autenticación §7](../guias/autenticacion.md#7-qué-contiene-el-access-token-y-qué-permisos-se-utilizan) |
| 5 | Conocer membresías, empresas y sucursales con acceso efectivo | `GET /api/v1/me/operational-context` | [OC 32](../servicios/operational-context.md#32-get-meoperational-context) |
| 6 | Comprobar un acceso concreto antes de actuar | `GET /api/v1/operational-access` | [OC 33](../servicios/operational-context.md#33-get-operational-access) |

Las operaciones 1 a 3 son de Keycloak, no de los microservicios; se incluyen porque sin ellas no hay token. Las operaciones 5 y 6 son las únicas API de SIO que el frontend necesita en este módulo. La selección de empresa y sucursal (funcionalidad 7, más abajo) no tiene API: es una decisión del frontend que se materializa en los identificadores que envía después.

---

## 1. Iniciar sesión

**¿Qué puede hacer el usuario?** Entrar a SIO con su usuario y contraseña de Keycloak y obtener los tokens que autorizan todas las llamadas.

**¿Qué API debe consumir el frontend?** Authorization Code con PKCE S256 contra el realm `siodev`:

| Paso | Método y URL |
|---|---|
| Redirigir al login | `GET https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/auth?client_id=sio-web&response_type=code&scope=openid&redirect_uri=…&code_challenge=…&code_challenge_method=S256&state=…` |
| Canjear el código | `POST https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token` con `grant_type=authorization_code`, `client_id=sio-web`, `code`, `redirect_uri`, `code_verifier` (formulario `application/x-www-form-urlencoded`) |

No requiere permiso: es la operación que los otorga. El cliente `sio-web` es público (sin secreto). El grant `password` no debe usarse en el frontend.

**¿Qué necesita antes?** Que la `redirect_uri` del frontend esté registrada en `sio-web`. La plantilla del realm la toma de la variable de entorno `SIO_WEB_REDIRECT_URI` del despliegue de Keycloak; su valor en Render desde este repositorio (ver [Autenticación §3.2](../guias/autenticacion.md#32-redirect-uris-y-web-origins)).

**¿Cómo sabe que funcionó?** El token endpoint responde `200` con `access_token`, `refresh_token`, `expires_in` y `refresh_expires_in`. El `access_token` se guarda en memoria y se envía como `Authorization: Bearer` en cada llamada. Errores: `400 invalid_grant` (código vencido o `code_verifier` incorrecto), `400 invalid_request` con `redirect_uri` no autorizada.

## 2. Renovar la sesión

**¿Qué puede hacer el usuario?** Seguir trabajando sin volver a escribir la contraseña mientras el Refresh Token siga vigente.

**¿Qué API debe consumir el frontend?** `POST https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/token` con `grant_type=refresh_token`, `client_id=sio-web` y `refresh_token`.

**¿Qué necesita antes?** El `refresh_token` más reciente. La rotación es obligatoria: cada renovación entrega un `refresh_token` nuevo y el anterior deja de servir.

**¿Cómo sabe que funcionó?** `200` con un nuevo par de tokens; el frontend reemplaza **ambos**. `400 invalid_grant` significa que la sesión caducó o se reutilizó un Refresh Token antiguo: hay que volver a iniciar sesión. Estrategia recomendada: renovar cuando falten pocos segundos para `expires_in` o al recibir `401` de una API, reintentando la llamada una sola vez ([Primeros pasos §4](../guias/primeros-pasos.md#4-flujo-de-integración-recomendado)).

## 3. Cerrar sesión

**¿Qué puede hacer el usuario?** Terminar su sesión en Keycloak y en el frontend.

**¿Qué API debe consumir el frontend?** `GET https://fastapi-postgrest-online-keycloak.onrender.com/realms/siodev/protocol/openid-connect/logout?client_id=sio-web&id_token_hint=<ID_TOKEN>&post_logout_redirect_uri=<URL>` (redirección del navegador) o `POST` al mismo endpoint con `client_id=sio-web&refresh_token=<REFRESH_TOKEN>` (sin redirección).

**¿Qué necesita antes?** El `id_token` o el `refresh_token` vigentes y una `post_logout_redirect_uri` autorizada en `sio-web` (la plantilla usa la misma variable `SIO_WEB_REDIRECT_URI`; su valor en Render).

**¿Cómo sabe que funcionó?** Keycloak redirige a la URL indicada (`GET`) o responde `204` (`POST`). El frontend borra tokens y estado local en cualquier caso, incluso si la llamada falla.

## 4. Identificar al usuario y sus permisos

**¿Qué puede hacer el usuario?** Ver su nombre en la interfaz y acceder solo a los módulos que su rol permite.

**¿Qué API debe consumir el frontend?** Ninguna: la información va dentro del Access Token (JWT). Campos útiles: `sub` (identificador del usuario en Keycloak, el `keycloak_user_id` de Operational Context), `preferred_username`, `name`, `email`, y `resource_access["sio-api"].roles` con los permisos `perm:{servicio}:{recurso}:{accion}`.

**¿Qué necesita antes?** Un Access Token válido (funcionalidad 1 o 2).

**¿Cómo sabe que funcionó?** El token decodifica correctamente y `aud` incluye `sio-api`. Los permisos se usan para **mostrar u ocultar** opciones; la autorización real la decide cada API, que responde `403` cuando el permiso falta y `404` cuando falta la membresía ([Permisos](../guias/permisos.md)).

## 5. Conocer membresías, empresas y sucursales con acceso efectivo

**¿Qué puede hacer el usuario?** Ver las empresas a las que pertenece y, en cada una, las sucursales en las que puede operar ahora mismo.

**¿Qué API debe consumir el frontend?**

| | |
|---|---|
| Método y URL | `GET https://sio-operational-context-dev.onrender.com/api/v1/me/operational-context` |
| Permiso | `perm:operational-context:application_users:read` |
| Parámetros | Ninguno (el usuario se toma del token) |
| Alcance | Propio: siempre devuelve el contexto del usuario autenticado |

**¿Qué necesita antes?** Solo el Access Token. Es la **primera llamada** tras el login.

**¿Cómo sabe que funcionó?** `200` con `MeOperationalContextResponse`:

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

Cómo leerla (reglas verificadas en el código de Operational Context, `domain/access.py`):

- `memberships[]` trae **una entrada por empresa** en la que el usuario tiene membresía, activa o inactiva. Un usuario puede tener varias; no asumas una sola.
- Una empresa es operable cuando `status` (membresía) y `company_status` son `ACTIVE`.
- Una sucursal es operable cuando `allowed` es `true`. Si es `false`, `reason` indica la primera condición que falla, en este orden: `USER_MEMBERSHIP_INACTIVE`, `COMPANY_INACTIVE`, `BRANCH_INACTIVE`, `BRANCH_NOT_ASSIGNED`, `USER_BRANCH_INACTIVE`.
- `memberships: []` significa que el usuario está autenticado pero no pertenece a ninguna empresa: no debe llamar a las API de empresa (responderían `404`).
- Los nombres de empresa y sucursal **no vienen** en esta respuesta: se consultan con `GET …/companies/{company_id}` (OC 5) y `GET …/companies/{company_id}/branches` (OC 9) o `GET …/branches/{branch_id}` (OC 11), descritos en [Administración empresarial](administracion-empresarial.md). La razón social está en Party Identity (`organization_identity_id` de la empresa).

Errores: `401` token inválido o vencido; `403` el token no tiene `perm:operational-context:application_users:read`.

## 6. Comprobar un acceso concreto antes de actuar

**¿Qué puede hacer el usuario?** Saber, antes de abrir una pantalla, si podrá ejecutar una acción en una empresa o sucursal (por ejemplo, crear ventas en la sucursal elegida), con la causa exacta si no puede.

**¿Qué API debe consumir el frontend?**

| | |
|---|---|
| Método y URL | `GET https://sio-operational-context-dev.onrender.com/api/v1/operational-access` |
| Permiso | `perm:operational-context:application_users:read` |
| Parámetros de consulta | `company_id` (UUID), `branch_id` (UUID, opcional), `permission` (`perm:…`, opcional) |

```bash
curl -sS 'https://sio-operational-context-dev.onrender.com/api/v1/operational-access?company_id=550e8400-e29b-41d4-a716-446655440000&branch_id=7c9e6679-7425-40de-944b-e07fc1f90ae7&permission=perm:sales:sales:create' \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**¿Qué necesita antes?** Los identificadores de la funcionalidad 5. El parámetro `keycloak_user_id` evalúa a otro usuario y exige `perm:operational-context:platform:lookup`; no es para el frontend.

**¿Cómo sabe que funcionó?** Siempre `200`: `allowed: true` con `reason: null`, o `allowed: false` con `reason` del catálogo anterior más `PERMISSION_DENIED` y `USER_NOT_MEMBER` (también cuando la empresa o la sucursal no existen: la vía propia no distingue ambos casos). Es opcional: las API de negocio aplican las mismas reglas y responden `403 BRANCH_ACCESS_DENIED` u `OPERATIONAL_ACCESS_DENIED` si se llama sin comprobar.

## 7. Seleccionar empresa y sucursal de trabajo

**¿Qué puede hacer el usuario?** Elegir con qué empresa y sucursal opera durante la sesión y cambiarlas cuando quiera.

**¿Qué API debe consumir el frontend?** Ninguna. No existe un recurso "contexto seleccionado" en el backend ni cabeceras de contexto: la empresa elegida viaja en la ruta (`/companies/{company_id}/…`) y la sucursal en el cuerpo o en la consulta (`branch_id`) de cada operación posterior. Cambiar de empresa es usar otro `company_id`.

**¿Qué necesita antes?** La respuesta de la funcionalidad 5 filtrada: membresías con `status: ACTIVE` y `company_status: ACTIVE`; sucursales con `allowed: true`. Si una sola empresa y una sola sucursal cumplen, selecciónalas sin preguntar; si hay varias, pide al usuario que elija y recuerda la elección en la sesión del navegador (no en el código).

**¿Cómo sabe que funcionó?** Las operaciones de negocio responden `2xx`. Un `404 NOT_FOUND` en recursos de empresa indica que el `company_id` no está en el alcance del usuario; un `403 BRANCH_ACCESS_DENIED` (Sales, Purchase, Inventory) indica que la sucursal no está asignada o está inactiva: vuelve a leer el contexto operativo, porque pudo cambiar desde el login.

## Dependencias con otros módulos

- [Administración empresarial](administracion-empresarial.md) crea las empresas, sucursales, membresías y asignaciones que este módulo consulta; sin ellas, `memberships` llega vacío.
- Todos los demás módulos empiezan con el `company_id` y el `branch_id` elegidos aquí ([company_id](../parametros/company-id.md), [branch_id](../parametros/branch-id.md)).
