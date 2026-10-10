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
| `PARTY_IDENTITY_SEED_COUNTRY_ID` | UUID de Colombia en el Geography del entorno: **obligatorio para la migración `0020`**; en el `seed` de reglas activa el modo país explícito (vacío = modo Geography) | UUID de Colombia en su Geography (`GET /global-countries?iso3_code=COL`) |
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
PARTY_IDENTITY_SEED_COUNTRY_ID=<uuid> alembic upgrade head     # ver "Migraciones"
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

**`0020` — país de las reglas colombianas históricas (G-017-01).** `0006` y `0010` insertan las 8
reglas colombianas con el `id` de Colombia fijo `cf160c2d-…`, que no existe en un Geography cargado
desde su `seed`. `0020` cambia su `country_id` por el `id` de Colombia **de este entorno**, que recibe
en `PARTY_IDENTITY_SEED_COUNTRY_ID` (sin la variable falla sin escribir nada; no hace llamadas HTTP):

```bash
PARTY_IDENTITY_SEED_COUNTRY_ID=<uuid de COL en Geography> alembic upgrade head
docker compose --file ../../infrastructure/services/party-identity-service.yaml --env-file ../../infrastructure/.env \
  exec -e PARTY_IDENTITY_SEED_COUNTRY_ID=<uuid> party-identity-service alembic upgrade head
```

- Solo toca las 8 reglas por su `id` fijo y solo si aún apuntan al UUID histórico (donde Colombia
  conserva ese `id`, no cambia nada). Las 8 quedan activas; las copias activas equivalentes que el
  `seed` haya creado con el país real se retiran (`is_active = false`, `valid_to`). No borra filas.
- Falla sin escribir si otra regla usa el UUID histórico, si la copia equivalente no la creó el
  `seed` o si difiere en patrón, sigla o edades.
- El estado anterior queda en `identification_type_rule_country_corrections`; el `downgrade`
  restaura exactamente `country_id`, `is_active`, `valid_to`, `version`, `updated_by` y `updated_at`.
- `infrastructure/scripts/rebuild-all.sh` lee el `id` de Colombia de `geography-db` y lo pasa a esta
  migración; en modo completo carga los datos de Geography antes de migrar Party Identity.

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

Las 8 reglas que insertan las migraciones históricas (con el país corregido por `0020`) cuentan como
existentes: tras una instalación limpia el `seed` las omite y quedan exactamente 8 reglas colombianas
activas. Si alguna sigue activa con otro país (`0020` pendiente o un `id` de Colombia distinto del
resuelto), el `seed` termina con error **sin escribir**, en vez de crear copias equivalentes. Otras
reglas activas equivalentes asociadas a otro país se listan como advertencia (no se eliminan).

**Validador de integridad** (repetible; solo lectura): `country_id` de todas las reglas ⊆ países de
Geography, una consulta `GET /global-countries/{id}` por país distinto, con el cliente técnico.
Código `0` sin referencias huérfanas, `1` con huérfanas, `2` si no se pudo validar:

```bash
docker compose --file ../../infrastructure/services/party-identity-service.yaml --env-file ../../infrastructure/.env exec party-identity-service python -m party_identity_service.integrity country-references
```

La misma comprobación, por las API de ambos servicios, está en
`tests/integration/test_geography_country_references.py` (`pytest -m integration`).

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
  (`test_realm_least_privilege.py`, con la instantánea `data/realm_reads_before.json`). Migración `0020` y `seed`
  sin duplicados: `test_colombia_rule_country_migration.py`. Las pruebas migran su base con
  `PARTY_IDENTITY_SEED_COUNTRY_ID` = el país ficticio del doble de Geography (`tests/conftest.py`).
- `tests/api`: rutas, errores RFC 9457, `401`/`403` por operación, contratos Provider, no recursión
  con Operational Context, OpenAPI.
- `tests/health`, `tests/examples`.

Geography y Operational Context se sustituyen por dobles inyectados (solo en `tests/`) y `sio-auth`
usa un JWKS local con tokens RS256 firmados en la prueba.

**Pruebas de integración (`-m integration`):** `tests/integration/test_phase_b_integration.py` usa
Keycloak, Geography y Operational Context reales. Requiere el realm regenerado desde la plantilla, las
variables del cliente técnico y los datos que indica su docstring.
`tests/integration/test_geography_country_references.py` (G-017-01) valida con Party Identity y
Geography reales que el país de todas las reglas exista en Geography (0 huérfanas), que haya
exactamente las 8 reglas colombianas activas de las migraciones, y que la API rechace un país
inexistente (`422 COUNTRY_NOT_FOUND`) y no cambie el país en `PUT` (`422 IMMUTABLE_FIELD`).

## Auditoría (feature 016)

Eventos de plataforma (`company_id` nulo). 32 operaciones de escritura auditadas.

Cada escritura de la API registra **un** evento de auditoría en la tabla `audit_outbox` de este
servicio, en la misma transacción que el cambio (si el cambio se revierte, el evento no existe), y el
proceso `party-identity-audit-outbox-worker` (misma imagen y base; `python -m sio_audit.worker`) lo entrega a
Audit con el cliente técnico `party-identity-service` (`perm:audit:audit-events:create`; `source_service =
party-identity-service`). Detalle por operación en
[`specs/016-existing-services-audit/contracts/audit-actions.md`](../../specs/016-existing-services-audit/contracts/audit-actions.md).

- Solo eventos `SUCCESS`: un rechazo sin efecto (`401`, `403`, `404`, `409`, `422`, `503`) no registra
  nada; una escritura que no cambia ningún campo tampoco (DS-02, DS-05).
- Valores: en la creación, los campos de la entidad; en la edición, solo los campos que cambiaron (antes y
  después); sin `id`, `version` ni columnas `created_*`/`updated_*`.
- Audit detenido no afecta a la API: los eventos quedan `PENDING` y el worker los entrega una sola vez al
  volver (reintentos con backoff de `libs/sio-audit`, a lo sumo `AUDIT_OUTBOX_BACKOFF_MAX_SECONDS` + 60 s
  después; sin orden de llegada garantizado: el historial se ordena por `occurred_at`).
- Las cargas por `seed` no se auditan (no hay autor autenticado).
- Variables del worker: `AUDIT_CLIENT_SECRET` = `PARTY_IDENTITY_CLIENT_SECRET` (solo en `infrastructure/.env`) y
  `AUDIT_OUTBOX_*` opcionales (ver `infrastructure/.env.example`).
- **Datos personales (DS-06)**: `identification_number`, `birth_date`, `email`, `phone`, `address_line`,
  `postal_code` y `source_document_reference` solo como marcador y en `redacted_paths`; nunca su valor.
- Perfiles de contacto (DS-11): cada versión nueva es un evento sobre la versión nueva, con la cerrada en
  `previous_values`; `application_user_id` = usuario que confirmó; empresa confirmante en los valores.

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
