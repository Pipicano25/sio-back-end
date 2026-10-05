# party-identity-service

Microservicio FastAPI de SIO, fuente de verdad de la **identidad global** de personas naturales y
organizaciones: responde **quién es** una persona u organización, independientemente del rol que
tenga para cada empresa (cliente, proveedor, fabricante, asesor…), y guarda la información
**compartida** que los demás servicios consultan sin copiarla: contactos, sector económico y
representantes legales.

- Spec, plan y contratos:
  - Fase A: [`specs/003-party-identity-core/`](../../specs/003-party-identity-core/) (gate `PARTY-IDENTITY-CORE READY`).
  - Fase B: [`specs/006-party-identity-complementary/`](../../specs/006-party-identity-complementary/) (gate `PARTY-IDENTITY COMPLETE`).
- API REST `v1` bajo `/api/v1`, protegida con `sio-auth` (Keycloak).
- Ejercicios de uso validados y guía de permisos: [`docs/ejemplo/`](docs/ejemplo/README.md).

## Entidades propias

| Entidad | Tabla | Estados |
| --- | --- | --- |
| Regla de identificación | `identification_type_rules` | Activa / histórica (`is_active`, `valid_to`); nunca se elimina |
| Persona | `person_identities` | `status` (uso): `ACTIVE`/`INACTIVE` · `verification_status`: `UNVERIFIED`/`VERIFIED`/`SUSPENDED` |
| Organización | `organization_identities` | `status` (uso): `ACTIVE`/`INACTIVE` · `registration_status`: estado legal informativo |
| Perfil de contacto de persona | `person_contact_profiles` | Versión vigente / cerrada (`is_active`, `valid_from`, `valid_to`) |
| Perfil de contacto de organización | `organization_contact_profiles` | Versión vigente / cerrada |
| Persona de contacto | `organization_contact_persons` | `ACTIVE`/`INACTIVE` (`is_active`); principal único |
| Sector económico | `global_business_sectors` | `ACTIVE`/`INACTIVE`; jerárquico (CIIU Rev. 5 A.C., `CIIU_REV5_AC`) |
| Sector de una organización | `organization_business_sectors` | Vigente / cerrada; principal único; no se reactiva |
| Representante legal | `organization_legal_representatives` | Vigente / cerrada; un `PRIMARY` vigente como máximo; no se reactiva |

Terminología: **`status` es el estado de uso** (controla si la identidad aparece por defecto en las
listas y si los consumidores aceptan nuevas referencias). `verification_status` y
`registration_status` son independientes y no controlan el uso.

Reglas principales de la Fase A:

- País + tipo + número de identificación es único (también frente a identidades inactivas).
- El número y el tipo se normalizan (sin espacios exteriores, en mayúsculas) y se validan contra las
  reglas activas de la sigla: basta con cumplir una. Si no hay regla para la sigla se aplican solo
  validaciones base (obligatorio, máximo 40, unicidad).
- Una regla con edades exige `birth_date` y valida la edad (zona operativa `America/Bogota`).
- Las modificaciones llevan la `version` leída (`409` si está desactualizada). Solo se consulta
  Geography y se revalida el número si cambia el país, el tipo o el número; un `PUT` sin cambios
  responde `200` sin incrementar la versión.
- No hay eliminación física: personas y organizaciones se inactivan (`/deactivate`) y reactivan
  (`/reactivate`); las reglas se retiran (`/deactivate`) o se versionan (`/versions`).
- El número de identificación y la fecha de nacimiento se enmascaran en logs y mensajes de error
  (`******0001`); solo las consultas autorizadas devuelven el valor completo.

Reglas principales de la Fase B:

- **Perfiles versionados:** un cambio nunca sobrescribe: cierra la versión vigente (`valid_to`) y crea
  otra en la misma transacción, con bloqueo de la identidad. `version` crece de forma continua por
  persona u organización. Una solicitud idéntica responde `200` sin crear versión. `:close` cierra sin
  reemplazo: sin perfil previo → `404 CONTACT_PROFILE_NOT_FOUND`; ya cerrado → `409
  CONTACT_PROFILE_ALREADY_CLOSED`.
- **Confirmación desde una empresa:** cada versión guarda `confirmed_by_company_id` y
  `confirmed_by_user_id` (el `ApplicationUser` de Operational Context). El usuario debe tener
  **membresía `ACTIVE`** en la empresa; Party Identity la comprueba con su cliente técnico y nunca
  acepta `confirmed_by_user_id` en el cuerpo. `created_by`/`updated_by` siguen siendo el `sub`.
- **Geografía estricta** en las direcciones: país → división → ciudad, existentes, `ACTIVE` y
  coherentes; solo se consulta Geography si cambió algún nivel.
- **Principales únicos** (contacto, sector, representante `PRIMARY`): se cambian solo con
  `:set-primary`, que es atómico; `is_primary` no se cambia con `PUT`; crear otro principal → `409`.
- **Vigencias** `[valid_from, valid_to)`: cerrar antes de que inicie deja `valid_to = valid_from`
  (nunca estuvo vigente). Sectores de organización y representantes cerrados no se reactivan.
- **Sin cascadas:** inactivar una identidad o un sector no cierra sus relaciones; solo impide nuevas.
  Un sector con hijos `ACTIVE` no se inactiva.
- **Datos sensibles:** correo, teléfono, dirección, código postal y referencia documental se
  enmascaran en logs y errores; se leen solo con el permiso específico del recurso.

## Dependencias

| Clase | Dependencia | Uso |
| --- | --- | --- |
| A | PostgreSQL 17 propio | Base `sio_party_identity` (desarrollo) y base de pruebas aislada |
| B | Keycloak | Validación de tokens (`sio-auth`); token técnico `client_credentials` del cliente `party-identity-service` para el `seed` (modo Geography) y para consultar Operational Context |
| C | Geography Service | Validar el país de identidades y reglas (`GET {GEOGRAPHY_SERVICE_BASE_URL}/global-countries/{id}`); validar país, división y ciudad de las direcciones de los perfiles; resolver `COL` en el `seed`. Se propaga el token del usuario. |
| C | Operational Context Service | Confirmación de perfiles: `GET {OPERATIONAL_CONTEXT_SERVICE_BASE_URL}/operational-access?company_id=…&keycloak_user_id=…` (vía técnica, con el cliente técnico; permisos `platform:lookup` y `application_users:read`). Ante el primer `401` se renueva el token y se repite una sola vez. |

Dependencia en ambos sentidos con Operational Context, **sin recursión**: Operational Context consulta
identidades; Party Identity consulta `operational-access` solo al confirmar un perfil. Ninguna lectura
de Party Identity llama a Operational Context.

### Integraciones e independencia local

Un único contrato por dependencia y el mismo comportamiento en todos los entornos (FR-044, FR-101): no
existen modos ni variables que cambien la lógica por entorno.

| Operación | Producción e integración | Pruebas | Desarrollo local sin la dependencia (opcional) |
| --- | --- | --- | --- |
| Arranque, `/health/*`, consultas | Sin dependencias externas | Igual | Igual |
| Altas y cambios de país/tipo/número | Geography real | Doble inyectado desde `tests/conftest.py` | Mock HTTP externo vía `GEOGRAPHY_SERVICE_BASE_URL` |
| Versión nueva de perfil | Geography (dirección) y Operational Context (membresía) reales | Dobles inyectados | Mocks HTTP externos vía las URL base |

- Referencia inexistente o inválida → `422` con su código (`COUNTRY_NOT_FOUND`, `CITY_NOT_FOUND`,
  `GEOGRAPHY_INCOHERENT`, `COMPANY_NOT_FOUND`, `CONFIRMATION_MEMBERSHIP_INVALID`…).
- Dependencia no disponible → `503 PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE` con la extensión
  `dependency` (`geography`, `operational-context` o `keycloak`); la causa real queda en el log.
- Sin las variables del cliente técnico el servicio arranca y las lecturas funcionan; la confirmación
  de perfiles responde `503` con `dependency: keycloak`.
- Nunca se copian tablas ni datos de otros servicios.

## Configuración

Copie `.env.example` a `.env`. Variables:

| Variable | Uso | Ejemplo |
| --- | --- | --- |
| `SIO_DOCS_ENABLED` | Publica `/docs` y `/openapi.json` | `true` |
| `DATABASE_URL` | Base del proyecto compose (credenciales en `infrastructure/.env`) | `postgresql+psycopg://…@127.0.0.1:5441/party_identity` |
| `PARTY_IDENTITY_TEST_DATABASE_URL` | Base de pruebas (perfil `test`) | puerto `55436` |
| `SIO_AUTH_ISSUER`, `SIO_AUTH_JWKS_URL`, `SIO_AUTH_AUDIENCE` | `sio-auth` | `http://localhost:8081/realms/sio`, …, `sio-api` |
| `GEOGRAPHY_SERVICE_BASE_URL` | URL de Geography **incluido su prefijo de ruta** (hoy sin `/api/v1`) | `http://localhost:8102` |
| `GEOGRAPHY_TIMEOUT_SECONDS` | Tiempo de espera de Geography | `5` |
| `OPERATIONAL_CONTEXT_SERVICE_BASE_URL` | URL de Operational Context **con** `/api/v1` | `http://localhost:8104/api/v1` |
| `OPERATIONAL_CONTEXT_TIMEOUT_SECONDS` | Tiempo de espera de Operational Context | `5` |
| `PARTY_IDENTITY_SEED_COUNTRY_ID` | País explícito del `seed` de reglas (vacío = modo Geography) | UUID de Colombia en su Geography |
| `KEYCLOAK_TOKEN_URL`, `KEYCLOAK_TIMEOUT_SECONDS` | Token técnico (`seed` y Operational Context) | `…/protocol/openid-connect/token`, `5` |
| `PARTY_IDENTITY_CLIENT_ID`, `PARTY_IDENTITY_CLIENT_SECRET` | Cliente técnico `party-identity-service` (`client_credentials`) | secreto real solo en `.env`, nunca en el repositorio |

Si el puerto `55436` de la base de pruebas no está disponible en Windows (rango reservado por
Hyper-V/WinNAT), defina otro en su `infrastructure/.env` local, por ejemplo
`PARTY_IDENTITY_TEST_DB_PORT=56436`, y ajuste `PARTY_IDENTITY_TEST_DATABASE_URL` (ver `docs/port-map.md`).

## Arranque local

```bash
cd services/party-identity-service
docker compose --file ../../infrastructure/services/party-identity-service.yaml --env-file ../../infrastructure/.env up -d party-identity-db                       # sio-party-identity-db
python -m venv .venv && .venv/Scripts/pip install -e ".[test]"
alembic upgrade head
python -m party_identity_service.seed load --country-id <uuid>   # ver "Datos iniciales"
python -m party_identity_service.seed load-business-sectors      # catálogo CIIU (ver "Datos iniciales")
uvicorn party_identity_service.main:app --port 8002
```

Con contenedor: `docker compose --file ../../infrastructure/services/party-identity-service.yaml --env-file ../../infrastructure/.env up -d --build`
(aplicación `sio-party-identity-service` en `http://localhost:8101`). Es el mismo proyecto compose
`party-identity-service` que levanta `infrastructure/scripts/rebuild-all.sh`: requiere el proyecto `sio`
arriba (red `sio-network` y Keycloak). `uvicorn` fuera de Docker usa el puerto local `8002` y la
misma base del proyecto (`DATABASE_URL` del `.env`).

## Migraciones

`alembic upgrade head`. Las migraciones `0001`–`0010` son históricas y no se editan. `0011` añade
`status` a personas y organizaciones; `0012` convierte `created_by`/`updated_by` a texto
(`VARCHAR(255)`, el `sub` de Keycloak). El `downgrade` de `0012` falla de forma explícita si hay
identidades de auditoría que no son UUID (por ejemplo `system:party-identity-seed`).

Fase B: `0013` (sectores), `0014` (perfiles de contacto), `0015` (personas de contacto), `0016`
(sectores de organización) y `0017` (representantes legales). Solo añaden tablas; su `downgrade` las
elimina y deja intacta la Fase A.

## Datos iniciales

`python -m party_identity_service.seed load` carga, de forma idempotente, las 8 reglas de
identificación de Colombia (`RC`, `TI` moderna y antigua, `CC` moderna y antigua, `CE`, `NIT` de
persona y de organización). Actor de auditoría: `system:party-identity-seed`. Si ya existe una
regla activa con la misma llave (tipo de parte + país + tipo de identificación) se omite.

El `id` de Colombia **no está fijo en el código** (no es el mismo en todos los entornos). Dos modos:

| Modo | Cómo | Necesita |
| --- | --- | --- |
| País explícito (independiente) | `load --country-id <uuid>` o `PARTY_IDENTITY_SEED_COUNTRY_ID=<uuid>` (el parámetro prevalece) | Solo la base. No consulta Geography ni Keycloak |
| Geography (por defecto) | `load` sin país | Geography en ejecución y el cliente `party-identity-service` (`KEYCLOAK_TOKEN_URL`, `PARTY_IDENTITY_CLIENT_ID`, `PARTY_IDENTITY_CLIENT_SECRET`) con el permiso `perm:geography:global_countries:read` |

Si falla (Geography caído, `COL` inexistente o ambiguo, credenciales ausentes) termina con código
distinto de cero y **no escribe nada**. En el entorno integrado:
`docker compose --file ../../infrastructure/services/party-identity-service.yaml --env-file ../../infrastructure/.env exec party-identity-service python -m party_identity_service.seed load`.

Las migraciones históricas `0003`–`0010` también insertan reglas con un `id` de Colombia fijo; si en
su entorno Colombia tiene otro `id`, el `seed` crea las reglas correctas y lista las anteriores como
advertencia (no se eliminan).

**Catálogo de sectores (Fase B):** `python -m party_identity_service.seed load-business-sectors`
carga la CIIU Rev. 5 A.C. completa (`CIIU_REV5_AC`: 22 secciones, 87 divisiones, 266 grupos y 544
clases) desde el snapshot oficial del DANE versionado en `src/party_identity_service/seed/data/ciiu_rev5_ac/`
(fuente, edición, fecha y SHA-256 en su `SOURCE.md`). Verifica el checksum, no usa Internet ni
Keycloak, es idempotente (conserva los UUID; solo actualiza nombre o padre si cambian) y carga en una
sola transacción. En el entorno integrado:

```bash
docker compose --file ../../infrastructure/services/party-identity-service.yaml --env-file ../../infrastructure/.env   exec party-identity-service python -m party_identity_service.seed load-business-sectors
```

Para actualizar el snapshot cuando el DANE publique otra versión: `pip install -e ".[tools]"` y
`python scripts/ciiu/convert_dane_ciiu.py` (detalle en `SOURCE.md`).

## Pruebas

```bash
docker compose --file ../../infrastructure/services/party-identity-service.yaml --env-file ../../infrastructure/.env --profile test up -d party-identity-test-db
pytest                                   # toda la suite, sin Geography, Operational Context ni Keycloak reales
pytest tests/examples                    # ejercicios de docs/ejemplo/
PARTY_IDENTITY_EXAMPLES_WRITE=1 pytest tests/examples   # regenerar docs/ejemplo/
pytest -m integration                    # opcionales contra servicios reales (ver abajo)
```

- `tests/unit`: reglas, edad, enmascaramiento, servicios con dobles, geografía estricta, adaptadores
  HTTP (Geography, Operational Context, token técnico) con `httpx.MockTransport`.
- `tests/contract`: migraciones desde cero, restricciones, repositorios, concurrencia (incluidas 20
  solicitudes simultáneas sobre perfiles y principales), `seed` y mínimo privilegio del realm
  (`test_realm_least_privilege.py`, con la instantánea `data/realm_reads_before.json`).
- `tests/api`: rutas, errores RFC 9457, `401`/`403` por operación, contratos Provider, no recursión
  con Operational Context, OpenAPI.
- `tests/health`, `tests/examples`.

Geography y Operational Context se sustituyen por dobles inyectados (solo en `tests/`) y `sio-auth`
usa un JWKS local con tokens RS256 firmados en la prueba.

**Pruebas de integración (`-m integration`):** `tests/integration/test_phase_b_integration.py` usa
Keycloak, Geography y Operational Context reales. Requiere el realm regenerado desde la plantilla, las
variables del cliente técnico y los datos que indica su docstring.

## Disponibilidad de la base

Regla de la Constitución 2.4.0 (Principio X), feature 009:

- La conexión a PostgreSQL tiene un tiempo de espera de 5 s y el pool descarta las conexiones rotas
  antes de usarlas (`pool_pre_ping`).
- Si la base no está disponible: `/health/live` sigue en `200`, `/health/ready` responde `503` y los
  endpoints que usan la base responden `503` `PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE` con `dependency:
  "database"`, `trace_id` y sin detalles internos (la causa queda en el log).
- Solo la pérdida o indisponibilidad de la conexión produce ese `503` (conexión rechazada o perdida,
  tiempo agotado, SQLSTATE `08xxx`, `57P01`, `57P02`, `57P03`). Un *deadlock*, un fallo de
  serialización, una sentencia cancelada o un bloqueo no disponible conservan su respuesta
  (`500 PARTY_IDENTITY.INTERNAL_ERROR`); integridad, validación y versión conservan `409`/`422`.
- Cuando la base vuelve, el servicio se recupera solo, sin reiniciarse.
- En Docker la base `sio-party-identity-db` tiene `healthcheck` y `restart: unless-stopped`, y la aplicación
  arranca cuando la base está sana (`infrastructure/services/party-identity-service.yaml`).

Validación en el entorno integrado (detiene la base temporalmente; solo lecturas con `admin.test` y
`KEYCLOAK_TEST_USER_PASSWORD` del entorno o de `infrastructure/.env`):

```bash
pytest -m integration -o addopts="" tests/integration/test_database_outage_recovery.py
```

Cubre una caída prolongada (`docker stop`) y una caída inesperada de PostgreSQL (reinicio por Docker),
contra `http://localhost:8101` (`PARTY_IDENTITY_INTEGRATION_BASE_URL`). Si se interrumpe con la
base detenida: `docker start sio-party-identity-db`.

## Consumo de la API

- Prefijo `/api/v1`; errores `application/problem+json` con `code` (`PARTY_IDENTITY.<CAUSA>`) y
  `trace_id`; cabecera `X-Trace-Id` en toda respuesta (se respeta `traceparent`). Los `503` incluyen
  `dependency`.
- Contratos: Fase A en [`specs/003-party-identity-core/contracts/`](../../specs/003-party-identity-core/contracts/);
  Fase B en [`specs/006-party-identity-complementary/contracts/`](../../specs/006-party-identity-complementary/contracts/)
  (`rest-api.md`, `errors.md`).
- **Consumidores de identidades** (Product Catalog, Operational Context, Commercial Relationship):
  `GET /api/v1/organization-identities/{id}` o `GET /api/v1/person-identities/{id}` según
  [`identity-lookup-provider.md`](../../specs/003-party-identity-core/contracts/identity-lookup-provider.md).
  Su `PARTY_IDENTITY_SERVICE_BASE_URL` **debe incluir `/api/v1`**. `200` devuelve `status`:
  `INACTIVE` significa que existe pero no debería aceptarse en referencias nuevas.
- **Consumidores de contactos, sectores y representantes** (Commercial Relationship, Sales, Purchase,
  Operational Context): persona de contacto por `id`, perfil vigente, sectores y representantes
  vigentes según
  [`contact-lookup-provider.md`](../../specs/006-party-identity-complementary/contracts/contact-lookup-provider.md),
  con el permiso específico de cada recurso. Guardan solo los UUID; no copian los datos.

## Permisos

`perm:party-identity:{recurso}:{accion}` con recursos `identification_type_rules`,
`person_identities`, `organization_identities`, `person_contact_profiles`,
`organization_contact_profiles`, `organization_contact_persons`, `global_business_sectors`,
`organization_business_sectors` y `organization_legal_representatives`:

| Operación | Acción |
| --- | --- |
| Consultar | `read` |
| Crear; nueva versión de regla; nueva versión de perfil; `:set-primary` de representante | `create` |
| Modificar; reactivar; `:set-primary` de contacto y de sector | `update` |
| Inactivar identidad, contacto o sector; retirar regla; cerrar perfil, asignación o representante | `delete` |

Los recursos de contacto y representantes legales son **sensibles**: leer una persona u organización
no concede leerlos.

| Usuario de prueba | En Party Identity |
| --- | --- |
| `admin.test` | Todo |
| `supervisor.test` | Todo menos `delete` |
| `compras.test`, `ventas.test` | Leer identidades, reglas, contactos y sectores; **no** representantes legales |
| `reportes.test`, `consulta.test` | Leer identidades, reglas y sectores; **no** contactos ni representantes legales |
| `inventario.test` | Sin acceso |

Para **confirmar** un perfil además se necesita membresía `ACTIVE` en la empresa (sin permisos de
Operational Context). Detalle y ejemplos en
[`docs/ejemplo/usuarios-y-permisos.md`](docs/ejemplo/usuarios-y-permisos.md); matriz del realm en
[`realm-permissions.md`](../../specs/006-party-identity-complementary/realm-permissions.md).
