# sio-auth

Librería compartida de autenticación y autorización por permisos para los
microservicios FastAPI de SIO.

## Responsabilidad

`sio-auth` hace únicamente estas tareas:

- protege todas las rutas HTTP por defecto;
- permite declarar rutas públicas explícitas por path exacto;
- valida Access Tokens de Keycloak con RS256 y JWKS;
- valida `iss`, `aud`, `exp`, `sub` y `kid`;
- guarda los claims autenticados en `request.state` durante esa request;
- obtiene dinámicamente los client roles desde `resource_access.<audience>.roles`;
- interpreta como permisos únicamente los roles con formato
  `perm:{servicio}:{recurso}:{accion}`;
- interpreta `all` como wildcard al evaluar un permiso.

La librería **no contiene catálogos ni listas estáticas de grupos, roles,
permisos, servicios, recursos o acciones**. Esos valores pertenecen a Keycloak
y a cada microservicio.

## Configuración

```bash
SIO_AUTH_ISSUER=http://keycloak:8080/realms/sio
SIO_AUTH_AUDIENCE=sio-api

# Opcionales
SIO_AUTH_HTTP_TIMEOUT_SECONDS=5
SIO_AUTH_JWKS_CACHE_TTL_SECONDS=300
```

Si `SIO_AUTH_JWKS_URL` no se define, se deriva del issuer como:

```text
{issuer}/protocol/openid-connect/certs
```

El algoritmo aceptado es RS256 y no es configurable.

## Proteger un microservicio

```python
from fastapi import FastAPI
from sio_auth import SIOAuth

app = FastAPI()
auth = SIOAuth.from_env()

auth.protect(
    app,
    public_paths={
        "/health/live",
        "/health/ready",
    },
)
```

Cualquier otra ruta exige automáticamente un Bearer Access Token válido.

## Exigir un permiso

El permiso requerido por un endpoint se declara en el propio microservicio:

```python
@app.post(
    "/resource",
    dependencies=[auth.permission("service", "resource", "action")],
)
def operation():
    ...
```

`sio-auth` compara ese permiso con los roles que realmente llegaron en el JWT.
No consulta una lista local de permisos conocidos.

Un grant recibido desde Keycloak puede contener `all` en cualquiera de sus tres
segmentos. La interpretación del wildcard ocurre solamente dentro de
`sio-auth`.

## Acceder a los claims

```python
from sio_auth import CurrentClaims

@app.get("/me")
def me(claims: CurrentClaims):
    return {
        "sub": claims.subject,
        "username": claims.preferred_username,
    }
```

La dependencia no vuelve a validar el JWT. Lee los claims que el middleware ya
guardó para esa request.

`TokenClaims.roles` contiene los client roles recibidos desde Keycloak y
`TokenClaims.permissions` contiene únicamente los roles `perm:...` que pudieron
interpretarse correctamente. Ninguno de los dos se completa desde una lista
local.

## Evaluar roles obtenidos por otra vía

Cuando un servicio necesita saber si **otro usuario** (no el de la solicitud)
tendría un permiso, por ejemplo con sus roles efectivos leídos de Keycloak,
usa la función pública `evaluate_permission`:

```python
from sio_auth import SioPermission, evaluate_permission

roles = ["perm:inventory:all:all", "otro-rol"]  # roles efectivos del usuario objetivo
required = SioPermission("inventory", "movements", "create")

evaluate_permission(roles, required)  # True
```

- Es una función pura: no consulta Keycloak ni tiene efectos.
- Aplica exactamente el mismo algoritmo que `auth.permission`: ignora los roles
  sin prefijo `perm:` o mal formados y admite `all` en cualquier segmento
  (incluido `perm:all:all:all`).
- No sustituye a `auth.permission`: la autorización de cada endpoint se sigue
  declarando con `auth.permission(...)` sobre el token de la solicitud.

## Versiones

| Versión | Cambio |
| --- | --- |
| `0.3.0` | Nueva función pública `evaluate_permission(roles, required)` (compatible). |
| `0.2.0` | Versión previa. |
