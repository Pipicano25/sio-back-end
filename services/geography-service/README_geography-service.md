# Geography Service

Microservicio de SIO encargado de administrar catálogos geográficos globales.

Actualmente el primer recurso implementado es `global_countries`.

Tecnologías principales: FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, Docker / Docker Compose, `libs/sio-auth` y Keycloak.

> `geography-service` no implementa lógica propia de JWT, JWKS, Keycloak ni resolución de permisos. Toda la seguridad transversal se delega a `sio-auth`.

## Seguridad

Todas las rutas son privadas por defecto:

```python
auth = SIOAuth.from_env()

auth.protect(
    app,
    public_paths={
        "/health/live",
        "/health/ready",
    },
)
```

Las únicas rutas públicas de negocio son:

```text
GET /health/live
GET /health/ready
```

Cuando `SIO_DOCS_ENABLED=true`, también se habilitan `/docs` y `/openapi.json`.

La autenticación ocurre una sola vez por request. `sio-auth` valida el Access Token y conserva los claims en el contexto de la solicitud.

Para conocer al usuario autenticado se usa:

```python
from sio_auth import CurrentSubject
```

`CurrentSubject` entrega el `sub` del Access Token ya validado y se utiliza para auditoría en `created_by` y `updated_by`.

## Permisos

Formato general:

```text
perm:{servicio}:{recurso}:{accion}
```

Permisos actuales:

| Operación | Método | Ruta | Permiso |
|---|---|---|---|
| Listar países | GET | `/global-countries` | `perm:geography:global_countries:read` |
| Consultar país | GET | `/global-countries/{country_id}` | `perm:geography:global_countries:read` |
| Crear país | POST | `/global-countries` | `perm:geography:global_countries:create` |
| Actualizar país | PUT | `/global-countries/{country_id}` | `perm:geography:global_countries:update` |
| Eliminar país | DELETE | `/global-countries/{country_id}` | `perm:geography:global_countries:delete` |

`sio-auth` también resuelve wildcards como:

```text
perm:geography:global_countries:all
perm:geography:all:read
perm:geography:all:all
perm:all:all:all
```

Los grupos de Keycloak no se hardcodean en el microservicio. Si, por ejemplo, solo `admin.test` y `supervisor.test` deben eliminar países, esa asignación se hace en Keycloak otorgando a esos grupos `perm:geography:global_countries:delete` o un wildcard equivalente.

## Variables de entorno

Archivo local:

```text
services/geography-service/.env
```

Ejemplo:

```env
SIO_DOCS_ENABLED=true

# Base del proyecto compose geography-service; credenciales en infrastructure/.env
DATABASE_URL=postgresql+psycopg://geography_user:change-this-geography-database-password@localhost:5442/geography

SIO_AUTH_ISSUER=http://localhost:8081/realms/sio
SIO_AUTH_JWKS_URL=http://localhost:8081/realms/sio/protocol/openid-connect/certs
SIO_AUTH_AUDIENCE=sio-api
```

El `.env` no debe subirse a Git. Debe existir un `.env.example` sin secretos.

En producción:

```env
SIO_DOCS_ENABLED=false
```

Con esto FastAPI no publica `/docs` ni `/openapi.json`.

## Keycloak

Realm:

```text
sio
```

Issuer:

```text
http://localhost:8081/realms/sio
```

OpenID Configuration:

```text
http://localhost:8081/realms/sio/.well-known/openid-configuration
```

JWKS:

```text
http://localhost:8081/realms/sio/protocol/openid-connect/certs
```

Audiencia esperada:

```text
sio-api
```

Los permisos llegan en:

```text
resource_access.sio-api.roles
```

## Instalación local

Desde `SIO/services/geography-service`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Si cambió `libs/sio-auth`:

```powershell
python -m pip install -e ..\..\libs\sio-auth
```

Verificar API pública:

```powershell
python -c "from sio_auth import SIOAuth, CurrentClaims, CurrentSubject; print('OK')"
```

Ejecutar localmente:

```powershell
python -m uvicorn geography_service.main:app --reload --port 8000 --env-file .env
```

Swagger:

```text
http://localhost:8000/docs
```

## Docker

Validar Compose:

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env config
```

Construir y levantar (requiere el proyecto `sio` levantado; aplicación en `http://localhost:8102`):

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env up --build -d
```

Estado:

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env ps
```

Logs:

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env logs -f geography-service
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env logs -f geography-db
```

Detener sin borrar datos:

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env down
```

No usar `docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env down -v` salvo que realmente se quiera eliminar el volumen y los datos.

## PostgreSQL desde fuera de Docker

Desde el host:

```text
Host:       localhost
Port:       5442
Database:   geography
Username:   geography_user
Password:   GEOGRAPHY_DB_PASSWORD de infrastructure/.env
```

Puede utilizarse con DBeaver, DataGrip, pgAdmin o psql.

Dentro de Docker, el microservicio se conecta a:

```text
Host: geography-db
Port: 5432
```

No usa `localhost:5442`.

En producción PostgreSQL no debe exponerse directamente a Internet; usar red privada, VPN, bastion o túnel seguro.

## Health checks

Liveness:

```text
GET /health/live
```

Respuesta normal:

```json
{
  "status": "ok"
}
```

Readiness:

```text
GET /health/ready
```

Comprueba PostgreSQL mediante `SELECT 1`.

Con BD disponible: `200 OK`.

Con BD no disponible: `503 Service Unavailable`.

Con la base no disponible por pérdida de conexión, los endpoints de negocio responden
`503 {"detail": …}` en lugar de `500`, y el servicio se recupera solo cuando la base vuelve (feature 009;
ver "Base de datos no disponible" en `README.md`).

## Swagger y Access Token

Abrir:

```text
http://localhost:8000/docs
```

Presionar `Authorize` y pegar únicamente el Access Token. Swagger agrega `Bearer` automáticamente.

Comportamiento esperado:

```text
Sin token válido       -> 401 Unauthorized
Token válido sin rol   -> 403 Forbidden
Token válido + permiso -> endpoint ejecutado
```

Swagger no valida el JWT; lo hace `sio-auth`.

## global_countries

Modelo:

```text
id            UUID PK
iso2_code     CHAR(2) UNIQUE NOT NULL
iso3_code     CHAR(3) UNIQUE NOT NULL
name          VARCHAR(120) NOT NULL
phone_prefix  VARCHAR(10) NULL
status        VARCHAR(20) NOT NULL
version       INTEGER NOT NULL DEFAULT 1
created_by    VARCHAR(255) NOT NULL
updated_by    VARCHAR(255) NOT NULL
created_at    TIMESTAMPTZ NOT NULL
updated_at    TIMESTAMPTZ NOT NULL
```

Estados permitidos:

```text
ACTIVE
INACTIVE
```

`created_by` y `updated_by` se obtienen de `CurrentSubject`; el cliente no los envía.

### Crear

```text
POST /global-countries
```

Permiso:

```text
perm:geography:global_countries:create
```

Body:

```json
{
  "iso2_code": "CO",
  "iso3_code": "COL",
  "name": "Colombia",
  "phone_prefix": "+57",
  "status": "ACTIVE"
}
```

Respuesta esperada: `201 Created`.

### Consultar

```text
GET /global-countries
GET /global-countries/{country_id}
```

Permiso:

```text
perm:geography:global_countries:read
```

`country_id` es el UUID contenido en el campo `id`.

### Actualizar

```text
PUT /global-countries/{country_id}
```

Permiso:

```text
perm:geography:global_countries:update
```

Ejemplo:

```json
{
  "iso2_code": "CO",
  "iso3_code": "COL",
  "name": "República de Colombia",
  "phone_prefix": "+57",
  "status": "ACTIVE",
  "version": 1
}
```

`version` implementa concurrencia optimista. Si el registro fue modificado y la versión enviada ya no coincide con la BD, se devuelve `409 Conflict`.

### Eliminar

```text
DELETE /global-countries/{country_id}
```

Permiso:

```text
perm:geography:global_countries:delete
```

Actualmente realiza borrado físico y responde `204 No Content`.

## Migraciones con Alembic

Consultar revisión actual:

```powershell
python -m alembic current
```

Crear migración:

```powershell
python -m alembic revision --autogenerate -m "descripcion del cambio"
```

Revisar siempre el archivo generado en `alembic/versions/` antes de aplicarlo.

Aplicar:

```powershell
python -m alembic upgrade head
```

Historial:

```powershell
python -m alembic history
```

Revertir una revisión:

```powershell
python -m alembic downgrade -1
```

Las credenciales no deben escribirse en `alembic.ini`.

## Estructura principal

```text
geography-service/
├── .env
├── .env.example
├── Dockerfile
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
└── src/
    └── geography_service/
        ├── main.py
        ├── config.py
        ├── api/
        │   ├── health.py
        │   ├── openapi.py
        │   ├── global_countries.py
        │   └── schemas/
        │       └── global_country.py
        ├── application/
        │   ├── exceptions.py
        │   ├── ports.py
        │   └── global_country_service.py
        ├── domain/
        │   └── global_country.py
        └── infrastructure/
            ├── database.py
            ├── models.py
            └── global_country_repository.py
```

## Puertos de desarrollo

| Componente | URL / Puerto |
|---|---|
| Geography Service (contenedor `sio-geography-service`) | `http://localhost:8102` |
| Geography Service con `uvicorn` local | `http://localhost:8000` |
| Swagger (`uvicorn` local) | `http://localhost:8000/docs` |
| PostgreSQL desde host | `localhost:5442` |
| PostgreSQL de pruebas (perfil `test`) | `localhost:55433` |
| Keycloak | `http://localhost:8081` |
| Realm SIO | `http://localhost:8081/realms/sio` |

## Solución de problemas

`SIO_AUTH_ISSUER es obligatorio`: ejecutar Uvicorn con `--env-file .env`.

`No fue posible obtener las claves de firma de Keycloak`: comprobar OpenID Configuration y JWKS en el puerto 8081.

`401 Unauthorized`: falta el token, expiró o no supera las validaciones de `sio-auth`.

`403 Forbidden`: el token es válido pero no tiene el permiso requerido.

`409 Conflict` al actualizar: consultar nuevamente el registro y usar la versión actual.

Alembic indica que `DATABASE_URL` es obligatoria: comprobar `.env` y `load_dotenv(override=False)` en `alembic/env.py`.

DBeaver no conecta: comprobar `docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env ps` y usar `localhost:5442`, no `geography-db:5432`.

## Producción

Antes de desplegar:

```env
SIO_DOCS_ENABLED=false
```

No exponer PostgreSQL directamente a Internet.

No almacenar secretos en Git ni en la imagen Docker.

Revisar migraciones antes de aplicarlas.

Gestionar grupos y permisos desde Keycloak, nunca mediante listas hardcodeadas en el microservicio.

Las nuevas rutas quedan privadas por defecto mediante `SIOAuth.protect()`.
