# geography-service

Catálogo geográfico compartido de SIO para **países**, **divisiones administrativas** y **ciudades**.

`geography-service` es un microservicio FastAPI independiente, con su propio `Dockerfile`, su propia base PostgreSQL (`geography-db`) y seguridad centralizada mediante la librería compartida `libs/sio-auth`.

El servicio no tiene alcance por empresa y no debe duplicar lógica de autenticación, JWT, JWKS, Keycloak ni resolución de permisos.

Como referencias de diseño del monorepo pueden existir:

- `docs/service-map.md`
- `docs/spec-driven-development-plan.md`
- `specs/002-geography-service-catalog/`

> Si algún documento histórico contradice el código actual, las migraciones vigentes, este README o la configuración desplegada, se debe revisar y alinear la documentación antes de continuar.

---

# Arquitectura interna

La estructura actual sigue una separación explícita por capas:

```text
services/geography-service/
├── alembic/
├── data/
│   ├── raw/
│   │   └── geonames/
│   └── south_america/
├── src/
│   └── geography_service/
│       ├── api/
│       │   ├── filters/
│       │   ├── schemas/
│       │   ├── global_administrative_divisions.py
│       │   ├── global_cities.py
│       │   ├── global_countries.py
│       │   ├── health.py
│       │   ├── openapi.py
│       │   └── pagination.py
│       ├── application/
│       │   ├── exceptions.py
│       │   ├── global_administrative_division_service.py
│       │   ├── global_city_service.py
│       │   ├── global_country_service.py
│       │   ├── pagination.py
│       │   └── ports.py
│       ├── domain/
│       │   ├── global_administrative_division.py
│       │   ├── global_city.py
│       │   └── global_country.py
│       ├── infrastructure/
│       │   ├── database.py
│       │   ├── global_administrative_division_repository.py
│       │   ├── global_city_repository.py
│       │   ├── global_country_repository.py
│       │   └── models.py
│       ├── seed/
│       │   ├── __init__.py
│       │   ├── __main__.py
│       │   ├── constants.py
│       │   ├── loader.py
│       │   └── preparer.py
│       ├── config.py
│       └── main.py
├── tests/
│   ├── unit/
│   ├── contract/
│   └── health/
├── .env.example
├── alembic.ini
├── Dockerfile
└── pyproject.toml
```

## Responsabilidad de cada capa

### `domain/`

Contiene entidades y tipos de dominio puros. No debe depender de FastAPI, SQLAlchemy, PostgreSQL ni `sio-auth`.

### `application/`

Contiene servicios de aplicación, contratos (`Protocol`), excepciones y estructuras compartidas como `PageResult`.

### `infrastructure/`

Contiene detalles de persistencia: SQLAlchemy, sesiones, modelos y repositorios concretos.

### `api/`

Contiene routers FastAPI, schemas Pydantic, filtros HTTP, paginación y configuración OpenAPI.

### `seed/`

Contiene el proceso de preparación y carga idempotente de datos iniciales.

> La implementación actual usa repositorios separados por recurso. No existe una única obligación de usar un archivo `repositories.py` monolítico.

---

# Requisitos

- Python `>= 3.12`.
- Docker + Docker Compose para entorno containerizado.
- PostgreSQL 17 para desarrollo y testing.
- `libs/sio-auth` presente en el monorepo.
- Keycloak para autenticación real en desarrollo/manual.

Actualmente se ha trabajado también con Python 3.13.

---

# Instalación local

Desde:

```text
services/geography-service
```

crear y activar el entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Actualizar `pip`:

```powershell
python -m pip install --upgrade pip
```

Instalar el servicio en modo editable con dependencias de pruebas:

```powershell
python -m pip install -e ".[test]"
```

Si solamente necesitas el servicio sin extras de testing:

```powershell
python -m pip install -e .
```

Verificar import:

```powershell
python -c "import geography_service; print('geography_service OK')"
```

---

# Variables de entorno

Ejemplo de `.env` local:

```env
SIO_DOCS_ENABLED=true

# Base del proyecto compose geography-service; credenciales en infrastructure/.env
DATABASE_URL=postgresql+psycopg://geography_user:change-this-geography-database-password@localhost:5442/geography

SIO_AUTH_ISSUER=http://localhost:8081/realms/sio
SIO_AUTH_JWKS_URL=http://localhost:8081/realms/sio/protocol/openid-connect/certs
SIO_AUTH_AUDIENCE=sio-api

GEOGRAPHY_TEST_DATABASE_URL=postgresql+psycopg://sio_geography_test:sio_geography_test_dev_change_me@localhost:55433/sio_geography_test
```

La aplicación usa actualmente variables `SIO_AUTH_*`. Documentación antigua que mencione `KEYCLOAK_ISSUER`, `KEYCLOAK_JWKS_URL` u otros nombres debe considerarse desactualizada hasta que el código indique lo contrario.

---

# Keycloak y sio-auth

En desarrollo se usa actualmente:

```text
Keycloak: http://localhost:8081
Realm: sio
Issuer: http://localhost:8081/realms/sio
JWKS: http://localhost:8081/realms/sio/protocol/openid-connect/certs
Audience: sio-api
```

## Importante al ejecutar dentro de Docker

El claim `iss` del token debe continuar coincidiendo exactamente con:

```text
http://localhost:8081/realms/sio
```

Por eso el issuer no debe cambiarse a `host.docker.internal`.

Cuando el contenedor necesita llegar físicamente al JWKS que corre en el host, puede utilizar:

```text
http://host.docker.internal:8081/realms/sio/protocol/openid-connect/certs
```

manteniendo el issuer original.

---

# Seguridad

La seguridad está centralizada en:

```text
libs/sio-auth
```

El microservicio no debe implementar:

- `jwt.decode()` propio.
- Validación de firmas propia.
- Resolución propia de JWKS.
- Middleware propio de autenticación.
- Reglas hardcodeadas por usuario o grupo.

El patrón actual es:

```python
from sio_auth import SIOAuth

auth = SIOAuth.from_env()
auth.protect(
    app,
    public_paths={
        "/health/live",
        "/health/ready",
    },
)
```

Y por endpoint:

```python
auth.permission(
    "geography",
    "global_countries",
    "read",
)
```

Formato de permisos:

```text
perm:{servicio}:{recurso}:{accion}
```

Los permisos llegan desde:

```text
resource_access.sio-api.roles
```

## Rutas públicas

Funcionalmente solo son públicas:

```text
GET /health/live
GET /health/ready
```

Cuando `SIO_DOCS_ENABLED=true`, se habilitan para documentación:

```text
/docs
/openapi.json
```

El resto permanece protegido.

---

# Auditoría

Las entidades persistentes usan:

```text
created_by
updated_by
created_at
updated_at
```

Para solicitudes de API:

```text
CurrentSubject
    ↓
JWT.sub
```

En creación:

```text
created_by = actor_id
updated_by = actor_id
```

En actualización:

```text
created_by = valor original
updated_by = actor_id actual
```

El cliente no debe controlar estos campos desde el body.

Para el seed geográfico se utiliza un actor técnico explícito:

```text
system:geography-seed
```

---

# PostgreSQL local

El contenedor `sio-geography-db` (proyecto compose `geography-service`) expone PostgreSQL únicamente por loopback:

```text
Host: localhost
Port: 5442
Database: geography
User: geography_user
Password: GEOGRAPHY_DB_PASSWORD de infrastructure/.env
```

Esto permite conectarse desde:

- DBeaver
- DataGrip
- pgAdmin

Dentro de Docker, `geography-service` debe conectarse usando el hostname del servicio:

```text
geography-db:5432
```

En producción no se debe exponer PostgreSQL directamente a Internet.

---

# Docker

## Build context

El servicio depende de `libs/sio-auth`, por lo cual el build debe tener contexto en la raíz del monorepo.

Patrón utilizado:

```dockerfile
COPY libs/sio-auth /app/libs/sio-auth
COPY services/geography-service /app/services/geography-service
```

## Levantar todo

Desde `services/geography-service` (requiere el proyecto `sio` levantado: red `sio-network` y Keycloak).
El único proyecto compose del servicio es `geography-service`, definido en
`infrastructure/services/geography-service.yaml`; la aplicación queda en `http://localhost:8102`:

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env up -d --build
```

## Reconstruir solo geography-service

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env up -d --build geography-service
```

Este es el comando recomendado cuando solo cambias código Python del servicio.

## Reiniciar sin reconstruir

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env restart
```

## Estado

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env ps -a
```

## Logs

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env logs -f geography-service
```

Últimas 200 líneas:

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env logs geography-service --tail 200
```

---

# Ejecutar localmente sin Docker

Con `.venv` activo y PostgreSQL disponible:

```powershell
python -m uvicorn geography_service.main:app --reload --port 8000 --env-file .env
```

Disponible en:

```text
http://localhost:8000
```

Swagger, si está habilitado:

```text
http://localhost:8000/docs
```

---

# Health checks

## Liveness

```http
GET /health/live
```

Respuesta esperada:

```json
{
  "status": "ok"
}
```

Debe indicar que el proceso está vivo.

## Readiness

```http
GET /health/ready
```

Comprueba conexión real a PostgreSQL.

Si PostgreSQL está disponible:

```text
200 OK
```

Si no está disponible:

```text
503 Service Unavailable
```

## Base de datos no disponible

Cambio transversal 2026-10-05 (feature 009, Constitución 2.4.0, Principio X):

- La conexión a PostgreSQL tiene un tiempo de espera de 5 s y el pool descarta las conexiones rotas
  antes de usarlas (`pool_pre_ping`).
- Si la base no está disponible, `/health/live` sigue en `200`, `/health/ready` responde `503` y los
  endpoints que usan la base responden `503` con el formato actual del servicio:

```json
{"detail": "La base de datos del servicio no está disponible temporalmente. Intente de nuevo más tarde."}
```

- Solo la pérdida o indisponibilidad de la conexión produce ese `503` (conexión rechazada o perdida,
  tiempo agotado, SQLSTATE `08xxx`, `57P01`, `57P02`, `57P03`). Un *deadlock*, un fallo de
  serialización, una sentencia cancelada o un bloqueo no disponible siguen respondiendo `500`.
- Cuando la base vuelve, el servicio se recupera solo, sin reiniciarse.
- En Docker, `sio-geography-db` tiene `healthcheck` y `restart: unless-stopped`, y la aplicación arranca
  cuando la base está sana (`infrastructure/services/geography-service.yaml`).

El resto de la línea base AS-IS no cambia (sin `code`, `trace_id` ni RFC 9457).

---

# Swagger / OpenAPI

Controlado por:

```env
SIO_DOCS_ENABLED=true
```

En desarrollo:

```text
http://localhost:8000/docs
```

Swagger expone esquema HTTP Bearer para pegar un Access Token real de Keycloak.

Swagger no valida JWT por sí mismo: solamente envía:

```text
Authorization: Bearer <token>
```

La validación continúa siendo responsabilidad exclusiva de `sio-auth`.

En producción se recomienda:

```env
SIO_DOCS_ENABLED=false
```

---

# Recursos HTTP

## Countries

Base:

```text
/global-countries
```

Operaciones:

```text
GET    /global-countries
GET    /global-countries/{country_id}
POST   /global-countries
PUT    /global-countries/{country_id}
DELETE /global-countries/{country_id}
```

Permisos:

```text
perm:geography:global_countries:read
perm:geography:global_countries:create
perm:geography:global_countries:update
perm:geography:global_countries:delete
```

## Administrative Divisions

Base:

```text
/global-administrative-divisions
```

Operaciones:

```text
GET    /global-administrative-divisions
GET    /global-administrative-divisions/{division_id}
POST   /global-administrative-divisions
PUT    /global-administrative-divisions/{division_id}
DELETE /global-administrative-divisions/{division_id}
```

Permisos:

```text
perm:geography:global_administrative_divisions:read
perm:geography:global_administrative_divisions:create
perm:geography:global_administrative_divisions:update
perm:geography:global_administrative_divisions:delete
```

## Cities

Base:

```text
/global-cities
```

Operaciones:

```text
GET    /global-cities
GET    /global-cities/{city_id}
POST   /global-cities
PUT    /global-cities/{city_id}
DELETE /global-cities/{city_id}
```

Permisos:

```text
perm:geography:global_cities:read
perm:geography:global_cities:create
perm:geography:global_cities:update
perm:geography:global_cities:delete
```

Los grupos o usuarios no deben hardcodearse en el microservicio. Las asignaciones se resuelven en Keycloak.

---

# Paginación

Los tres endpoints de listado soportan:

```text
page
page_size
```

Valores actuales:

```text
page >= 1
1 <= page_size <= 100
```

Ejemplo:

```http
GET /global-countries?page=3&page_size=5
```

Respuesta:

```json
{
  "items": [],
  "page": 3,
  "page_size": 5,
  "total_records": 47,
  "total_pages": 10
}
```

Si se solicita una página posterior a la última, se devuelve normalmente:

```json
{
  "items": [],
  "page": 50,
  "page_size": 5,
  "total_records": 47,
  "total_pages": 10
}
```

No se considera `404`.

---

# Búsqueda y filtros

La búsqueda sencilla usa PostgreSQL `ILIKE` y puede combinarse con paginación y filtros exactos.

## Countries

Parámetros disponibles:

```text
page
page_size
search
iso2_code
iso3_code
status
```

`search` busca parcialmente en:

```text
name
iso2_code
iso3_code
```

Ejemplos:

```http
GET /global-countries?search=col&page=1&page_size=5
```

```http
GET /global-countries?iso2_code=CO
```

```http
GET /global-countries?status=ACTIVE
```

## Administrative Divisions

Parámetros disponibles:

```text
page
page_size
search
country_id
parent_division_id
division_type
status
```

`search` busca parcialmente en:

```text
name
code
```

Ejemplos:

```http
GET /global-administrative-divisions?country_id=<UUID_COLOMBIA>
```

```http
GET /global-administrative-divisions?country_id=<UUID_COLOMBIA>&search=ant
```

```http
GET /global-administrative-divisions?country_id=<UUID_COLOMBIA>&division_type=DEPARTMENT&status=ACTIVE
```

## Cities

Parámetros disponibles:

```text
page
page_size
search
country_id
administrative_division_id
code
status
```

`search` busca parcialmente en:

```text
name
code
```

Ejemplos:

```http
GET /global-cities?country_id=<UUID_COLOMBIA>
```

```http
GET /global-cities?administrative_division_id=<UUID_ANTIOQUIA>
```

```http
GET /global-cities?country_id=<UUID_COLOMBIA>&search=med&page=1&page_size=5
```

## Semántica del conteo

`total_records` representa los registros que cumplen los filtros, no el total absoluto de la tabla.

Ejemplo:

```text
20.000 ciudades totales
85 ciudades coinciden con country_id + search
```

la respuesta debe mostrar:

```text
total_records = 85
```

---

# Modelo funcional

Relaciones principales:

```text
global_countries
      │
      ├── 1:N ──> global_administrative_divisions
      │                  │
      │                  └── parent_division_id
      │                      autorreferencia jerárquica
      │
      └── 1:N ──> global_cities
                         │
                         └── administrative_division_id
```

Reglas importantes:

- Una división administrativa debe pertenecer a un país existente.
- Si una división tiene `parent_division_id`, el padre debe existir.
- El padre debe pertenecer al mismo país.
- Una división no puede apuntarse a sí misma como padre.
- Si una ciudad tiene `administrative_division_id`, esa división debe existir.
- La división de la ciudad debe pertenecer al mismo `country_id`.
- Latitud debe estar entre `-90` y `90`.
- Longitud debe estar entre `-180` y `180`.
- Los estados actuales son `ACTIVE` e `INACTIVE`.

---

# Migraciones Alembic

## Aplicar migraciones

Con `.env` disponible:

```powershell
python -m alembic upgrade head
```

## Ver revisión actual

```powershell
python -m alembic current
```

## Crear migración automática

Después de modificar modelos SQLAlchemy:

```powershell
python -m alembic revision --autogenerate -m "descripcion del cambio"
```

Siempre revisar el archivo generado antes de ejecutar `upgrade head`.

No guardar credenciales directamente en `alembic.ini`.

`alembic/env.py` carga `.env` y toma `DATABASE_URL` desde `Settings`.

---

# Seed de Sudamérica

El servicio dispone de un proceso para precargar datos geográficos de Sudamérica y evitar altas manuales masivas.

## Alcance actual

Países soberanos incluidos:

```text
Argentina
Bolivia
Brasil
Chile
Colombia
Ecuador
Guyana
Paraguay
Perú
Surinam
Uruguay
Venezuela
```

Actualmente la preparación usa:

- Países.
- Divisiones administrativas de primer nivel (`ADM1`).
- Catálogo amplio de ciudades/localidades basado en `cities500`.

## Fuente

El proceso usa snapshots de GeoNames:

```text
countryInfo.txt
admin1CodesASCII.txt
cities500.zip
```

Directorio esperado:

```text
data/raw/geonames/
```

Los datos normalizados se generan en:

```text
data/south_america/
├── countries.csv
├── administrative_divisions.csv
└── cities.csv
```

GeoNames distribuye sus datos bajo licencia CC BY 4.0. El proyecto debe conservar la atribución correspondiente cuando distribuya o reutilice estos datasets.

## Descargar archivos

Desde:

```text
services/geography-service
```

crear carpeta:

```powershell
New-Item -ItemType Directory -Force -Path data\raw\geonames
```

Descargar:

```powershell
Invoke-WebRequest `
  -Uri "https://download.geonames.org/export/dump/countryInfo.txt" `
  -OutFile ".\data\raw\geonames\countryInfo.txt"

Invoke-WebRequest `
  -Uri "https://download.geonames.org/export/dump/admin1CodesASCII.txt" `
  -OutFile ".\data\raw\geonames\admin1CodesASCII.txt"

Invoke-WebRequest `
  -Uri "https://download.geonames.org/export/dump/cities500.zip" `
  -OutFile ".\data\raw\geonames\cities500.zip"
```

No es necesario descomprimir `cities500.zip`.

## Preparar snapshot SIO

Con `.venv` activo y el proyecto instalado en editable:

```powershell
python -m geography_service.seed prepare
```

Esto genera los CSV normalizados.

## Cargar datos

Con PostgreSQL disponible y `DATABASE_URL` correctamente configurada:

```powershell
python -m geography_service.seed load
```

Orden interno:

```text
countries
   ↓
administrative_divisions
   ↓
cities
```

## Idempotencia

El seed está diseñado para poder ejecutarse nuevamente sin duplicar registros.

El loader intenta reutilizar registros existentes y utiliza UUID deterministas para datos del snapshot.

Actor técnico:

```text
system:geography-seed
```

## Ejecutar dentro del contenedor

Si el código de seed ya está dentro de la imagen:

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env exec geography-service python -m geography_service.seed load
```

---

# Testing

La suite se divide en:

```text
tests/
├── unit/
├── contract/
└── health/
```

## Unit tests

Prueban servicios de aplicación mediante repositorios falsos en memoria.

Actualmente existen pruebas para:

- `GlobalCountryService`
- `GlobalAdministrativeDivisionService`
- `GlobalCityService`

No requieren PostgreSQL, Docker ni Keycloak.

Ejecutar:

```powershell
python -m pytest tests/unit -v
```

## Contract / persistence tests

Las pruebas de persistencia usan **PostgreSQL real de testing**, no SQLite.

Esto es importante porque se validan:

- UUID PostgreSQL.
- `TIMESTAMPTZ`.
- `NUMERIC`.
- Foreign keys.
- `CHECK` constraints.
- `ON DELETE RESTRICT`.
- Auditoría.
- Concurrencia optimista.

Base de testing:

```text
Host: localhost
Port: 55433
Database: sio_geography_test
```

Levantarla:

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env --profile test up -d geography-test-db
```

Ejecutar pruebas de persistencia:

```powershell
python -m pytest tests/contract -v
```

Ejecutar todo:

```powershell
python -m pytest -v
```

## Base de datos no disponible

`tests/unit/test_database_unavailable_classification.py` (sin base) y `tests/api/test_database_unavailable.py`
(base de pruebas) verifican el `503`, la salud y la recuperación sin reiniciar.

Validación contra el entorno integrado (detiene `sio-geography-db` temporalmente; solo lecturas con
`admin.test` y `KEYCLOAK_TEST_USER_PASSWORD` del entorno o de `infrastructure/.env`):

```powershell
python -m pytest -m integration -o addopts="" tests/integration/test_database_outage_recovery.py
```

Cubre una caída prolongada (`docker stop`) y una caída inesperada de PostgreSQL (reinicio por Docker),
contra `http://localhost:8102` (`GEOGRAPHY_INTEGRATION_BASE_URL`). Si se interrumpe con la base
detenida: `docker start sio-geography-db`.

## Protección de la base de testing

`GEOGRAPHY_TEST_DATABASE_URL` debe apuntar a una base cuyo nombre contenga `test`.

La suite está diseñada para rechazar configuraciones que puedan apuntar accidentalmente a la base de desarrollo.

## Seguridad HTTP automatizada pendiente

Todavía falta completar la fase de tests HTTP con:

```text
TestClient
+ sio-auth activo
+ 401
+ 403
+ permisos
+ CurrentSubject
+ PostgreSQL de testing
```

No se debe deshabilitar `auth.protect()` ni `auth.permission()` para implementar esos tests.

La intención acordada es sustituir únicamente dependencias externas como Keycloak/JWKS mediante una estrategia de testing compatible con `sio-auth`, manteniendo activa la seguridad de la librería.

---

# Errores HTTP esperados

Convención actual:

```text
200  lectura y actualización exitosa
201  creación
204  eliminación
401  no autenticado
403  autenticado sin permiso
404  recurso inexistente
409  conflicto de integridad o concurrencia
422  request inválido
503  dependencia no disponible
```

No se deben exponer directamente errores internos de SQLAlchemy o PostgreSQL.

---

# Troubleshooting

## `ModuleNotFoundError: No module named 'geography_service'`

Activar `.venv` e instalar editable:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

Verificar:

```powershell
python -c "import geography_service; print('OK')"
```

## `DATABASE_URL es obligatoria`

Los comandos Python normales no cargan `.env` automáticamente.

Para Uvicorn:

```powershell
python -m uvicorn geography_service.main:app --reload --port 8000 --env-file .env
```

Alembic y el CLI de seed cargan su configuración mediante el mecanismo definido en el proyecto.

---

# Flujo de trabajo habitual

Para desarrollo diario:

```powershell
cd services/geography-service
.\.venv\Scripts\Activate.ps1

docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env up -d geography-db
python -m alembic upgrade head
python -m uvicorn geography_service.main:app --reload --port 8000 --env-file .env
```

Para trabajar completamente con Docker:

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env up -d --build
```

Después de cambiar solo código del servicio:

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env up -d --build geography-service
```

Para testing:

```powershell
docker compose --file ../../infrastructure/services/geography-service.yaml --env-file ../../infrastructure/.env --profile test up -d geography-test-db
python -m pytest -v
```

Para preparar/cargar Sudamérica:

```powershell
python -m geography_service.seed prepare
python -m geography_service.seed load
```
