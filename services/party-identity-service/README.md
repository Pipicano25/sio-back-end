# party-identity-service

Microservicio FastAPI de SIO, fuente de verdad de la **identidad global** de personas naturales y
organizaciones: responde **quién es** una persona u organización, independientemente del rol que
tenga para cada empresa (cliente, proveedor, fabricante, asesor…).

- Spec, plan y contratos: [`specs/003-party-identity-core/`](../../specs/003-party-identity-core/)
  (Fase A, gate `PARTY-IDENTITY-CORE READY`).
- API REST `v1` bajo `/api/v1`, protegida con `sio-auth` (Keycloak).
- Ejercicios de uso validados y guía de permisos: [`docs/ejemplo/`](docs/ejemplo/README.md).

## Entidades propias

| Entidad | Tabla | Estados |
| --- | --- | --- |
| Regla de identificación | `identification_type_rules` | Activa / histórica (`is_active`, `valid_to`); nunca se elimina |
| Persona | `person_identities` | `status` (uso): `ACTIVE`/`INACTIVE` · `verification_status`: `UNVERIFIED`/`VERIFIED`/`SUSPENDED` |
| Organización | `organization_identities` | `status` (uso): `ACTIVE`/`INACTIVE` · `registration_status`: estado legal informativo |

Terminología: **`status` es el estado de uso** (controla si la identidad aparece por defecto en las
listas y si los consumidores aceptan nuevas referencias). `verification_status` y
`registration_status` son independientes y no controlan el uso.

Reglas principales:

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

## Dependencias

| Clase | Dependencia | Uso |
| --- | --- | --- |
| A | PostgreSQL 17 propio | Base `sio_party_identity` (desarrollo) y base de pruebas aislada |
| B | Keycloak | Validación de tokens (`sio-auth`); token técnico del `seed` en modo Geography |
| C | Geography Service | Validar el país (`GET {GEOGRAPHY_SERVICE_BASE_URL}/global-countries/{id}`) al crear o al cambiar país/tipo/número; resolver `COL` en el `seed` (modo Geography). Se propaga el token del usuario. |

### Integración con Geography e independencia local

Party Identity tiene **un único contrato de integración con Geography** y el mismo comportamiento
en todos los entornos (FR-044): no existen modos ni variables que cambien la lógica por entorno.

| Operación | Producción e integración | Pruebas | Desarrollo local sin Geography (opcional) |
| --- | --- | --- | --- |
| Arranque, `/health/*`, consultas | No usa Geography | No usa Geography | No usa Geography |
| Altas y cambios de país/tipo/número | Geography real | Doble inyectado desde `tests/conftest.py` | Mock HTTP externo que implemente el mismo contrato, apuntando `GEOGRAPHY_SERVICE_BASE_URL` a él |
| Modificaciones sin cambio de identificación, inactivar/reactivar | No usa Geography | No usa Geography | No usa Geography |

- País existente → continúa; inexistente → `422 PARTY_IDENTITY.COUNTRY_NOT_FOUND`; Geography no
  disponible, tiempo agotado o `401`/`403` → `503 PARTY_IDENTITY.DEPENDENCY_UNAVAILABLE` (la causa
  real queda en el log: `COUNTRY_VALIDATION_DENIED` o `GEOGRAPHY_UNAVAILABLE`).
- Con Geography detenido el servicio arranca y responde consultas; las altas responden `503`.
- Nunca se copian tablas ni datos de Geography.

## Configuración

Copie `.env.example` a `.env`. Variables:

| Variable | Uso | Ejemplo |
| --- | --- | --- |
| `SIO_DOCS_ENABLED` | Publica `/docs` y `/openapi.json` | `true` |
| `PARTY_IDENTITY_SERVICE_PORT` | Puerto local del servicio | `8002` |
| `DATABASE_URL` | Base de desarrollo | `postgresql+psycopg://…@127.0.0.1:55435/sio_party_identity` |
| `PARTY_IDENTITY_DB_*` | Contenedor de la base de desarrollo | puerto `55435` |
| `PARTY_IDENTITY_TEST_DB_*`, `PARTY_IDENTITY_TEST_DATABASE_URL` | Base de pruebas (perfil `test`) | puerto `55436` |
| `SIO_AUTH_ISSUER`, `SIO_AUTH_JWKS_URL`, `SIO_AUTH_AUDIENCE` | `sio-auth` | `http://localhost:8081/realms/sio`, …, `sio-api` |
| `GEOGRAPHY_SERVICE_BASE_URL` | URL de Geography **incluido su prefijo de ruta** (hoy sin `/api/v1`) | `http://localhost:8000` |
| `GEOGRAPHY_TIMEOUT_SECONDS` | Tiempo de espera de Geography | `5` |
| `PARTY_IDENTITY_SEED_COUNTRY_ID` | País explícito del `seed` (vacío = modo Geography) | UUID de Colombia en su Geography |
| `KEYCLOAK_TOKEN_URL`, `KEYCLOAK_TIMEOUT_SECONDS` | Token técnico del `seed` en modo Geography | `…/protocol/openid-connect/token`, `5` |
| `PARTY_IDENTITY_CLIENT_ID`, `PARTY_IDENTITY_CLIENT_SECRET` | Cliente técnico `party-identity-service` (`client_credentials`) | secreto real solo en `.env`, nunca en el repositorio |

## Arranque local

```bash
cd services/party-identity-service
docker compose up -d party-identity-db                       # sio-party-identity-dev-db
python -m venv .venv && .venv/Scripts/pip install -e ".[test]"
alembic upgrade head
python -m party_identity_service.seed load --country-id <uuid>   # ver "Datos iniciales"
uvicorn party_identity_service.main:app --port 8002
```

O con Docker: `docker compose up -d --build` (contenedor `sio-party-identity-service-dev`). Los
nombres de contenedor no chocan con el entorno integrado de `infrastructure/`, donde el servicio es
`sio-party-identity-service` en el puerto `8101`.

## Migraciones

`alembic upgrade head`. Las migraciones `0001`–`0010` son históricas y no se editan. `0011` añade
`status` a personas y organizaciones; `0012` convierte `created_by`/`updated_by` a texto
(`VARCHAR(255)`, el `sub` de Keycloak). El `downgrade` de `0012` falla de forma explícita si hay
identidades de auditoría que no son UUID (por ejemplo `system:party-identity-seed`).

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
`docker compose exec party-identity-service python -m party_identity_service.seed load`.

Las migraciones históricas `0003`–`0010` también insertan reglas con un `id` de Colombia fijo; si en
su entorno Colombia tiene otro `id`, el `seed` crea las reglas correctas y lista las anteriores como
advertencia (no se eliminan).

## Pruebas

```bash
docker compose --profile test up -d party-identity-test-db
pytest                                   # toda la suite, sin Geography ni Keycloak reales
pytest tests/examples                    # ejercicios de docs/ejemplo/
PARTY_IDENTITY_EXAMPLES_WRITE=1 pytest tests/examples   # regenerar docs/ejemplo/
pytest -m integration                    # opcionales contra servicios reales (si existen)
```

- `tests/unit`: reglas, edad, enmascaramiento, servicios con dobles, adaptadores HTTP con
  `httpx.MockTransport`.
- `tests/contract`: migraciones desde cero, restricciones, repositorios, concurrencia y `seed`.
- `tests/api`: rutas, errores RFC 9457, `401`/`403` por operación, contrato Provider, OpenAPI.
- `tests/health`, `tests/examples`.

Geography se sustituye por `FakeCountryDirectory` (solo en `tests/`) y `sio-auth` usa un JWKS local
con tokens RS256 firmados en la prueba.

## Consumo de la API

- Prefijo `/api/v1`; errores `application/problem+json` con `code` (`PARTY_IDENTITY.<CAUSA>`) y
  `trace_id`; cabecera `X-Trace-Id` en toda respuesta (se respeta `traceparent`).
- Contrato completo: [`contracts/rest-api.md`](../../specs/003-party-identity-core/contracts/rest-api.md);
  errores: [`contracts/errors.md`](../../specs/003-party-identity-core/contracts/errors.md).
- **Consumidores** (Product Catalog, Operational Context, Commercial Relationship): consultan
  `GET /api/v1/organization-identities/{id}` o `GET /api/v1/person-identities/{id}` según
  [`identity-lookup-provider.md`](../../specs/003-party-identity-core/contracts/identity-lookup-provider.md).
  Su `PARTY_IDENTITY_SERVICE_BASE_URL` **debe incluir `/api/v1`** (las rutas sin prefijo ya no
  existen). `200` devuelve `status`: `INACTIVE` significa que existe pero no debería aceptarse en
  referencias nuevas.

## Permisos

`perm:party-identity:{recurso}:{accion}` con recursos `identification_type_rules`,
`person_identities` y `organization_identities`:

| Operación | Acción |
| --- | --- |
| Consultar | `read` |
| Crear; crear una nueva versión de regla | `create` |
| Modificar; reactivar | `update` |
| Inactivar identidad; retirar regla | `delete` |

Usuarios de prueba: `admin.test` todo; `supervisor.test` todo menos `delete` (reactiva pero no
inactiva); `compras`, `ventas`, `reportes`, `consulta` solo lectura; `inventario.test` sin acceso.
Detalle y ejemplos en [`docs/ejemplo/usuarios-y-permisos.md`](docs/ejemplo/usuarios-y-permisos.md).
