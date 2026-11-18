# Permisos en el frontend de SIO

Cómo debe leer el frontend los permisos del usuario para mostrar u ocultar módulos, menús y acciones. Esto es
**solo presentación**: la autorización real la hace cada microservicio con `sio-auth` en cada solicitud
(Constitución, Principio V). Ocultar un botón nunca sustituye esa comprobación.

## Grupos y perfiles

Hay cinco grupos de Keycloak (spec 026): dos perfiles (`superadmin`, `admin`) y tres áreas (`Compras`, `Ventas`,
`Inventario`). Un usuario puede estar en **varios** grupos y recibe la **suma** de sus permisos; un operario típico
está en las tres áreas. El grupo da los permisos; la membresía en Operational Context dice en qué empresas se
aplican.

| Grupo | Quién | Qué puede |
| --- | --- | --- |
| `superadmin` | Dueño del software y quienes él indique | Todo, en todas las empresas sin ser miembro; crear empresas; eliminar y desactivar datos globales |
| `admin` | Gerente, dueño o encargado de una empresa | Todo en sus empresas (incluida la rentabilidad y los usuarios de la empresa); crear y modificar datos globales, sin eliminarlos ni desactivarlos |
| `Compras` | Personal de compras | Compras en sus empresas, proveedores y lo que necesita consultar; crear y modificar personas y organizaciones |
| `Ventas` | Personal de ventas | Ventas en sus empresas (sin rentabilidad), crear clientes y lo que necesita consultar; crear y modificar personas y organizaciones |
| `Inventario` | Personal de bodega | Ajustes, conteos y consultas de existencias en sus empresas |

Las tres áreas juntas equivalen al antiguo grupo `empleado`. Los grupos del usuario llegan en el claim `groups` de
`userinfo` (por ejemplo `["/Compras", "/Ventas", "/Inventario"]`); sirven para mostrar el perfil, no para decidir
permisos.

## Dónde están los permisos

En el **Access Token** que emite Keycloak para el cliente `sio-web`, en un único lugar:

```json
{
  "aud": ["sio-api", "..."],
  "resource_access": {
    "sio-api": { "roles": ["perm:inventory:balances:read", "perm:geography:all:read", "..."] }
  }
}
```

- Son los client roles **efectivos** de `sio-api`: los de los grupos del usuario más los asignados directamente
  (los incluye el client scope estándar `roles`, mapper `client roles`). No hay otro claim con permisos; no usar
  `realm_access`, `groups` ni el ID Token.
- Solo cuentan los roles con formato `perm:{servicio}:{recurso}:{accion}`. Los demás (`superadmin`, `admin`)
  son el **perfil** del grupo (las áreas no traen rol sin prefijo): sirven para mostrar el rol del usuario, no para decidir permisos.
  Un `perm:` mal formado (con más o menos de cuatro partes) se ignora.
- El frontend lee el payload del Access Token (base64url) solo para la interfaz; no necesita verificar la firma,
  porque no toma decisiones de seguridad. La fuente del token es la respuesta de Keycloak, nunca un valor editable.

## Cómo evaluar un permiso

Igual que `SioGrant.allows` en `libs/sio-auth/src/sio_auth/models.py`: un permiso del token cubre al exigido si
cada parte coincide o vale `all`.

```ts
const concede = (grant: string, servicio: string, recurso: string, accion: string) => {
  const p = grant.split(":");
  return p.length === 4 && p[0] === "perm"
    && [servicio, "all"].includes(p[1]) && [recurso, "all"].includes(p[2]) && [accion, "all"].includes(p[3]);
};
const puede = (roles: string[], s: string, r: string, a: string) => roles.some((g) => concede(g, s, r, a));
```

| Permiso en el token | Cubre |
| --- | --- |
| `perm:all:all:all` | Todo, en todas las empresas (grupo `superadmin`) |
| `perm:sales:all:all` | Todo en Sales, incluida la rentabilidad (grupo `admin`) |
| `perm:product-catalog:all:update` | Modificar cualquier recurso de Product Catalog, pero no `delete` ni `deactivate` (grupo `admin`) |
| `perm:sales:all:create` | Crear en cualquier recurso de Sales (grupo `Ventas`) |

## Módulos, menús y acciones

- **Permiso por elemento**: cada módulo, opción de menú o botón usa el mismo permiso que declara el endpoint que
  invoca (está en el contrato OpenAPI y en `docs/ejemplo/` de cada servicio). No inventar permisos de interfaz.
- **Módulo**: se muestra si el usuario tiene al menos uno de los permisos de sus pantallas.
- **Acción**: el botón se muestra (o habilita) solo con el permiso de su endpoint; p. ej. "Nueva venta" con
  `perm:sales:sales:create`.
- **Respuestas del servidor**: un `403` significa que el permiso cambió o no alcanza; se informa con el
  `trace_id` y se recalcula la interfaz. Un `404` de empresa o sucursal significa que no hay membresía (no se
  distingue de "no existe", a propósito).

## Empresas y sucursales

El token **no** contiene empresas ni sucursales: tener `perm:sales:sales:create` no da acceso a cualquier empresa.
El alcance lo define Operational Context:

- `GET /api/v1/me/operational-context`: membresías `ACTIVE` del usuario y sus sucursales con acceso efectivo.
  Con esto se arma el selector de empresa y sucursal.
- `GET /api/v1/operational-access?company_id=…&branch_id=…&permission=…`: comprobación puntual (`allowed`).

Ambas exigen `perm:operational-context:application_users:read`. Cada microservicio vuelve a comprobar la membresía
en cada operación; el frontend nunca envía una empresa que no esté en `me/operational-context`.

## Cambios de permisos y renovación

- Un alta o baja de permiso en Keycloak aparece en el **siguiente** Access Token, tanto en un nuevo login como en
  una renovación con `grant_type=refresh_token`, sin volver a pedir credenciales.
- Un Access Token ya emitido conserva sus permisos hasta su `exp` (hoy 300 s). Es la ventana máxima de propagación.
- Tras **cada** renovación, el frontend vuelve a leer `resource_access.sio-api.roles` y recalcula la interfaz.
- Verificado en la pila aislada por `libs/sio-auth/tests/integration/test_permisos_en_tokens.py`.

## Sesión y renovación

- Login con Authorization Code + PKCE S256 (cliente `sio-web`); el grant `password` no existe en producción.
- **Rotación:** cada renovación devuelve un Refresh Token nuevo y el anterior queda inválido (`invalid_grant`). El
  frontend reemplaza siempre el par completo.
- **Una sola renovación en vuelo, obligatoria:** reutilizar un Refresh Token ya usado **cierra la sesión** (Keycloak
  invalida también el vigente). Dos renovaciones simultáneas con el mismo token cuentan como reutilización: una
  gana, pero su token nuevo tampoco sirve y el usuario debe volver a iniciar sesión. Con varias pestañas, una sola
  renueva y comparte el resultado (p. ej. `BroadcastChannel` o un `SharedWorker`); `keycloak-js` ya encola las
  llamadas a `updateToken` de una misma página. Verificado en
  `libs/sio-auth/tests/integration/test_renovacion_y_logout.py`.
- Renovar un poco antes del `exp` del Access Token (p. ej. 30 a 60 s) y, ante un `401` con
  `"El token de acceso ha expirado"`, renovar una vez y reintentar la petición una vez.
- Sin renovar en 30 min, o pasadas 10 h desde el login, la renovación responde `invalid_grant`: volver al login.
- Logout por `end_session` de Keycloak: el Refresh Token deja de servir; el Access Token emitido vale hasta su `exp`.
- No hay tokens offline (`offline_access` no está disponible en `sio-web`).

## Lo que el frontend no debe hacer

- Guardar los permisos (ni los tokens) en `localStorage`; se derivan del Access Token vigente, en memoria.
- Cachear la lista de permisos más allá de la vida del Access Token.
- Decidir el acceso a datos por el perfil o el grupo (`admin`, `/Ventas`) en lugar de por `perm:*`.
- Asumir que la ausencia de un botón protege una operación.
