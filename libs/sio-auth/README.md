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

### Respuesta sin permiso (`403`)

Si el token no trae un permiso compatible, la dependencia responde `403` con un
`detail` descriptivo que **nunca** nombra el permiso, el rol ni la regla exigidos
(revelarlos facilita enumerar los permisos del sistema):

> Su usuario no tiene permiso para realizar esta operación. Si necesita acceso,
> solicítelo al administrador del sistema indicando el trace_id de esta respuesta.

El texto está en `sio_auth.FORBIDDEN_DETAIL`. El permiso exigido se registra solo
en el log del servidor, en el logger `sio_auth` (`sio_auth.LOGGER_NAME`), nivel
`WARNING`, con el sujeto, el método y la ruta; el registro lleva además el atributo
`sio_required_permission` (`sio_auth.DENIED_PERMISSION_ATTRIBUTE`) para que las
pruebas lo lean sin depender del cuerpo de la respuesta. Los servicios que agregan
`trace_id` a sus logs deben incluir el logger `sio_auth`.

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

## Pruebas reales contra Keycloak

`tests/validar_token_env.py` obtiene un token real de `admin.test` y lo valida con
`sio-auth`. No se ejecuta con la suite ordinaria (no sigue el patrón `test_*.py`):

```bash
pytest tests/validar_token_env.py
```

| Variable | Uso | Dónde se define |
| --- | --- | --- |
| `KEYCLOAK_TEST_USER_PASSWORD` | Contraseña de los usuarios de prueba (secreto, sin valor por defecto) | Variable de entorno o `infrastructure/.env` |
| `KEYCLOAK_PUBLIC_URL` | URL pública de Keycloak (por defecto `http://localhost:8081`) | Variable de entorno o `infrastructure/.env` |
| `KEYCLOAK_REALM` | Realm (por defecto `sio`) | Variable de entorno o `infrastructure/.env` |

La variable de entorno tiene prioridad sobre `infrastructure/.env`. `infrastructure/.env` no se
versiona; `infrastructure/.env.example` documenta las variables con valores ficticios. Sin
contraseña, las pruebas se omiten. Ningún valor secreto se escribe en el código.

## Sesiones y permisos en tokens (pila aislada)

Pruebas activas contra Keycloak y Geography de la pila aislada `sio-it-*`; se omiten sin `SIO_TEST_TARGET=isolated`:

| Módulo | Comprueba |
| --- | --- |
| `tests/integration/test_permisos_en_tokens.py` | `resource_access.sio-api.roles` con los client roles efectivos al iniciar sesión y al renovar; altas y bajas reflejadas en la siguiente renovación (usuario temporal) |
| `tests/integration/test_renovacion_y_logout.py` | Renovación, rotación (reutilización y concurrencia rechazadas), refresh inválido, logout, sin tokens offline y clientes técnicos sin Refresh Token |
| `tests/integration/test_expiracion_de_sesion.py` | Access Token expirado (`401`), Refresh Token vencido por inactividad y vida máxima de la sesión (cliente temporal con tiempos cortos) |

```bash
SIO_TEST_TARGET=isolated .venv/bin/pytest tests/integration
```

Necesita en la pila Keycloak y Geography con su migración aplicada. Guía cURL manual: `infrastructure/README.md`.

Cómo debe usar el frontend estos permisos: `docs/frontend-permissions.md`.
