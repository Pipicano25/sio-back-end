# operational-context-service

Microservicio FastAPI de SIO, fuente de verdad del **contexto operativo**: qué empresas usan la
plataforma, en qué sucursales (sedes, tiendas, bodegas o puntos) operan, **qué personas operan en
ellas** (usuarios operativos y sus sucursales) y quién las asesora. No es dueño de la identidad
legal ni de las personas (Party Identity), de la geografía (Geography) ni de las cuentas y permisos
(Keycloak): solo guarda sus `UUID` o el `sub`.

- Fase A (empresas y sucursales): [`specs/004-operational-context-core/`](../../specs/004-operational-context-core/),
  gate `OPERATIONAL-CONTEXT-CORE READY`.
- Fase B (usuarios, asignaciones, asesores y aislamiento por empresa):
  [`specs/005-operational-context-users/`](../../specs/005-operational-context-users/), gate
  `OPERATIONAL-CONTEXT COMPLETE`.
- API REST `v1` bajo `/api/v1`, protegida con `sio-auth` (Keycloak).
- Ejercicios de uso validados y guía de permisos: [`docs/ejemplo/`](docs/ejemplo/README.md).

## Entidades propias

| Entidad | Tabla | Estados |
| --- | --- | --- |
| Empresa | `companies` | `ACTIVE`/`INACTIVE`; nunca se elimina |
| Sucursal | `branches` | `ACTIVE`/`INACTIVE`; nunca se elimina |
| Usuario operativo (membresía) | `application_users` | `ACTIVE`/`INACTIVE`; nunca se elimina |
| Asignación usuario–sucursal | `user_branches` | `ACTIVE`/`INACTIVE`; nunca se elimina |
| Asesor de la empresa | `company_advisor_assignments` | `ACTIVE` (vigente) → `INACTIVE` (cerrada, sin retorno) |

Qué **no** se guarda:

- En la empresa: NIT, tipo de identificación, razón social ni nombre comercial (Party Identity,
  DS-01, DS-13), ni nombres o códigos geográficos, representante legal o sector económico.
- En usuarios y asesores: nombres, documentos ni contacto de la persona (Party Identity, DS-16); de
  Keycloak solo el `sub` (ni el `username`, ni roles, ni credenciales).

### Reglas de la Fase A

- `organization_identity_id` obligatorio, existente y `ACTIVE` en Party Identity al asignarlo o
  cambiarlo; una organización se vincula a una sola empresa.
- Correo, teléfono y dirección son de la **sede operativa principal** en SIO (DS-14).
- Ubicación opcional con coherencia estricta país → división → ciudad, cada nivel existente y
  `ACTIVE` en Geography al asignarlo o cambiarlo (DS-04, DS-05). Coordenadas en pareja y en rango.
- Zona horaria IANA (la sucursal hereda la de la empresa en `effective_timezone`) y moneda de 3 letras.
- Código de sucursal normalizado, único por empresa y modificable.
- Modificaciones con `version` (`409` si está desactualizada); un `PUT` sin cambios no escribe.
- Inactivar una empresa no modifica sus sucursales; no se crean ni reactivan sucursales bajo una
  empresa inactiva.

### Reglas de la Fase B

- **Usuario operativo = membresía** de una persona humana (cuenta de Keycloak + `PersonIdentity`)
  en una empresa. Alta por `username` **o** `keycloak_user_id` (`sub`): el servicio verifica en
  Keycloak que la cuenta exista, esté habilitada y no sea una cuenta técnica, y guarda solo el `sub`.
  La `PersonIdentity` es obligatoria y debe estar `ACTIVE` en Party Identity (DS-03, DS-16, FR-019).
- Como máximo **una membresía `ACTIVE`** por empresa y persona y por empresa y cuenta; las históricas
  se conservan. La misma persona puede estar en varias empresas (DS-01).
- Inactivar una membresía solo afecta esa empresa; reactivarla vuelve a validar cuenta y persona.
- Asignaciones usuario–sucursal solo dentro de la misma empresa (garantizado también por FK
  compuestas); autor `assigned_by` obligatorio (el `sub`; `system:<proceso>` en procesos técnicos).
- Asesores con vigencia: un solo principal vigente, varios no principales; el cambio de principal
  (`change-primary`) cierra la vigente y crea la nueva en una transacción; una asignación cerrada es
  inmutable (DS-13, DS-15).
- Sin cascadas: inactivar empresa, sucursal o membresía no modifica relaciones hijas; el efecto se
  refleja en el **acceso operativo efectivo**, que se calcula en cada consulta (DS-07, DS-11).
- **Aislamiento por empresa** en todas las rutas (DS-06): el permiso dice *qué* puede hacer el
  usuario y la membresía *dónde*. Sin `perm:operational-context:platform:administer`, un usuario
  solo ve y opera las empresas donde tiene membresía `ACTIVE`; el resto responde `404`, igual que un
  `id` inexistente. Registrar, inactivar y reactivar empresas exige `platform:administer`.
- `perm:operational-context:platform:lookup` permite a identidades técnicas leer por UUID sin
  membresía y consultar el acceso de otro usuario; nunca escribir (FR-045).

## Dependencias

| Clase | Dependencia | Uso |
| --- | --- | --- |
| A | PostgreSQL 17 propio | Base `sio_operational_context` (desarrollo) y base de pruebas aislada |
| B | Keycloak (tokens) | Validación de tokens (`sio-auth`) |
| B | Keycloak (Admin API, solo lectura) | Cliente técnico propio `operational-context-service` (`client_credentials`, `view-users` y `query-clients`): verificar cuentas al registrar o reactivar usuarios operativos y leer los roles efectivos de un usuario en la comprobación técnica de acceso |
| C | Party Identity Service | `GET {PARTY_IDENTITY_SERVICE_BASE_URL}/organization-identities/{id}` (empresa) y `/person-identities/{id}` (usuarios operativos y asesores) |
| C | Geography Service | `GET global-countries/{id}`, `GET global-administrative-divisions/{id}`, `GET global-cities/{id}` al asignar o cambiar la ubicación |

Hacia Party Identity y Geography se propaga el token del usuario (D5). Para escribir, el usuario
necesita además la lectura correspondiente en esos servicios
(`perm:party-identity:organization_identities:read`, `perm:party-identity:person_identities:read`,
`perm:geography:*:read`); en el realm vigente la tienen `administradores` y `supervisores`. Hacia
Keycloak Admin se usa **solo** la identidad técnica propia; su secreto se lee del entorno.

### Respuestas de las dependencias

| Resultado del proveedor | Respuesta de este servicio |
| --- | --- |
| Existe y `ACTIVE` (y coherente) | Continúa |
| `404` / cuenta inexistente | `422` `ORGANIZATION_IDENTITY_NOT_FOUND`, `PERSON_IDENTITY_NOT_FOUND`, `KEYCLOAK_USER_NOT_FOUND`, `COUNTRY_NOT_FOUND`, … |
| `INACTIVE` / cuenta deshabilitada o técnica | `422` `ORGANIZATION_IDENTITY_INACTIVE`, `PERSON_IDENTITY_INACTIVE`, `LOCATION_INACTIVE`, `KEYCLOAK_USER_DISABLED`, `TECHNICAL_ACCOUNT_NOT_ALLOWED` |
| Incoherente | `422 GEOGRAPHY_INCOHERENT` (con el campo en `errors[]`) |
| Tiempo agotado, red, `5xx`, `401`/`403` o respuesta inesperada | `503 DEPENDENCY_UNAVAILABLE` con la extensión `dependency` (`party-identity`, `geography` o `keycloak`); no se guarda nada |

**Observabilidad**: cada solicitud tiene un `trace_id` que se devuelve en `X-Trace-Id`, en todo
Problem Details y en cada línea de log, y se envía a los proveedores en `traceparent`. Las causas
internas de un `503` solo aparecen en el log: `ORGANIZATION_VALIDATION_DENIED`,
`PERSON_VALIDATION_DENIED`, `GEOGRAPHY_VALIDATION_DENIED`, `PARTY_IDENTITY_UNAVAILABLE`,
`GEOGRAPHY_UNAVAILABLE`, `KEYCLOAK_TOKEN_REJECTED`, `KEYCLOAK_ADMIN_DENIED`, `KEYCLOAK_UNREACHABLE`,
`KEYCLOAK_AMBIGUOUS_USERNAME`; nunca el token, el secreto ni el cuerpo. Tiempos de espera por
llamada: `PARTY_IDENTITY_TIMEOUT_SECONDS`, `GEOGRAPHY_TIMEOUT_SECONDS` y `KEYCLOAK_TIMEOUT_SECONDS`
(5 s), sin reintentos funcionales. La única repetición es una renovación de credencial: ante un
`401` de la Admin API se pide un token técnico nuevo y se repite una sola vez la misma lectura.

### Desarrollo local sin proveedores

Operational Context conserva **exactamente los mismos contratos y comportamiento funcional** en todos
los entornos. Para desarrollar sin levantar Party Identity, Geography o Keycloak Admin se puede usar
un **mock HTTP externo** que implemente esos contratos, apuntando la URL base correspondiente a él.
No existen modos `stub`, datos falsos en el código productivo ni caminos distintos por entorno; los
dobles de pruebas viven solo en `tests/`.

| Operación | Con proveedores reales | Pruebas automáticas |
| --- | --- | --- |
| Arranque, `/health/*`, consultas, `me`, `operational-access` propio, `PUT` de usuarios, inactivaciones, asignaciones, cierre de asesor | No los usa | No los usa |
| Alta de empresa; cambio de organización o ubicación | Party Identity / Geography | Dobles inyectados en `create_app` |
| Alta y reactivación de usuario operativo | Keycloak Admin + Party Identity | Dobles inyectados |
| Alta y cambio de asesor | Party Identity | Doble inyectado |
| `operational-access` técnico con `permission` | Keycloak Admin | Doble inyectado |

## Configuración

Copie `.env.example` a `.env`. Variables:

| Variable | Uso | Ejemplo |
| --- | --- | --- |
| `SIO_DOCS_ENABLED` | Publica `/docs` y `/openapi.json` | `true` |
| `DATABASE_URL` | Base del proyecto compose (credenciales en `infrastructure/.env`) | `postgresql+psycopg://…@127.0.0.1:5440/operational_context` |
| `OPERATIONAL_CONTEXT_TEST_DATABASE_URL` | Base de pruebas (perfil `test`) | puerto `55440` |
| `SIO_AUTH_ISSUER`, `SIO_AUTH_JWKS_URL`, `SIO_AUTH_AUDIENCE` | `sio-auth` | `http://localhost:8081/realms/sio`, …, `sio-api` |
| `PARTY_IDENTITY_SERVICE_BASE_URL`, `PARTY_IDENTITY_TIMEOUT_SECONDS` | Party Identity **con** `/api/v1` | `http://localhost:8101/api/v1`, `5` |
| `GEOGRAPHY_SERVICE_BASE_URL`, `GEOGRAPHY_TIMEOUT_SECONDS` | Geography con su prefijo vigente (hoy sin `/api/v1`) | `http://localhost:8102`, `5` |
| `KEYCLOAK_BASE_URL` (obligatoria) | Keycloak para el token técnico y la Admin API | `http://localhost:8081` (integrado `http://keycloak:8080`) |
| `KEYCLOAK_REALM` | Realm | `sio` |
| `OPERATIONAL_CONTEXT_CLIENT_ID` (obligatoria) | Cliente técnico propio | `operational-context-service` |
| `OPERATIONAL_CONTEXT_CLIENT_SECRET` (obligatoria) | Secreto del cliente técnico; **solo** en `.env`, igual al de `infrastructure/.env` | — |
| `KEYCLOAK_TIMEOUT_SECONDS` | Tiempo de espera por llamada a Keycloak | `5` |
| `SIO_API_CLIENT_ID` | Cliente cuyos roles son los permisos SIO | `sio-api` |
| `OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL`, `KEYCLOAK_TOKEN_URL` | Solo `pytest -m integration` | `http://localhost:8104`, `…/openid-connect/token` |

El servicio no llama a Keycloak Admin al arrancar: arranque, salud y consultas funcionan sin él.

### Versión de `sio-auth`

`pyproject.toml` declara `sio-auth @ file:../../libs/sio-auth`: una referencia directa no admite
`>=0.3.0`. La versión es la de `libs/sio-auth/pyproject.toml` (`0.3.0`, con la función pública
`evaluate_permission`). Si se instala una versión anterior, el servicio no arranca y las pruebas
fallan al importar (`ImportError`). Tras cambiar la librería, reinstálela en el entorno del
servicio: `pip install ../../libs/sio-auth`.

## Arranque local

```bash
cd services/operational-context-service
docker compose --file ../../infrastructure/services/operational-context-service.yaml --env-file ../../infrastructure/.env up -d operational-context-db               # sio-operational-context-db
python -m venv .venv && .venv/Scripts/pip install -e ".[test]"
alembic upgrade head
uvicorn operational_context_service.main:app --port 8004 --env-file .env
```

Con contenedor: `docker compose --file ../../infrastructure/services/operational-context-service.yaml --env-file ../../infrastructure/.env up -d --build`
(aplicación `sio-operational-context-service` en `http://localhost:8104`). Es el mismo proyecto compose
`operational-context-service` que levanta `infrastructure/scripts/rebuild-all.sh`: requiere el proyecto `sio`
arriba (red `sio-network` y Keycloak). `uvicorn` fuera de Docker usa el puerto local `8004` y la
misma base del proyecto (`DATABASE_URL` del `.env`).
Aplique las migraciones del contenedor con `docker exec sio-operational-context-service alembic upgrade head`.

Para la Fase B, el realm debe incluir el cliente técnico `operational-context-service` y los permisos
`platform:*`: defina `OPERATIONAL_CONTEXT_CLIENT_SECRET` en `infrastructure/.env`, vuelva a
renderizar la plantilla con `infrastructure/scripts/render-realm.sh` e importe el realm.

## Migraciones

`alembic upgrade head`:

- `0001`: `companies` y `branches`.
- `0002`: `application_users`, `user_branches`, `company_advisor_assignments` y la restricción
  `uq_branches_id_company_id` (destino de la FK compuesta). Unicidades `ACTIVE` con índices únicos
  parciales. `downgrade 0001` las elimina sin tocar la Fase A.

Todas las FK son internas (`ON DELETE RESTRICT`); no hay FK hacia otros servicios.

## Datos iniciales

No hay: el dominio no requiere datos base (Principio XIV).

## Pruebas

```bash
docker compose --file ../../infrastructure/services/operational-context-service.yaml --env-file ../../infrastructure/.env --profile test up -d operational-context-test-db
pytest                                   # toda la suite, sin Party Identity, Geography ni Keycloak reales
pytest tests/examples                    # ejercicios de docs/ejemplo/
OPERATIONAL_CONTEXT_EXAMPLES_WRITE=1 pytest tests/examples   # regenerar docs/ejemplo/
pytest -m integration                    # contra servicios reales (ver abajo)
```

- `tests/unit`: reglas de dominio (acceso operativo, vigencias, alcance), servicios con dobles.
- `tests/contract`: migraciones, restricciones (incluidos índices parciales y FK compuestas),
  repositorios y adaptadores HTTP (Party Identity, Geography, Keycloak Admin) con `httpx.MockTransport`.
- `tests/api`: rutas, errores, `401`/`403` por operación, **aislamiento por empresa en todas las rutas**
  (`test_isolation.py`, que falla si una ruta nueva no figura en su tabla), contratos Provider,
  OpenAPI, concurrencia (unicidades y cambio de asesor) y carreras deterministas.
- `tests/health`, `tests/examples`.

### Pruebas de integración (`pytest -m integration`)

Exigen en ejecución este servicio, Party Identity (reglas `NIT` y `CC` de Colombia), Geography con los
datos de Colombia y Keycloak con el realm renderizado (incluido el cliente técnico de la Fase B). La
contraseña de `admin.test` se lee de `KEYCLOAK_TEST_USER_PASSWORD` o de `infrastructure/.env`. Si falta
algo, las pruebas se omiten con un mensaje.

Cada ejecución crea datos **ficticios de validación** que permanecen en el entorno: una organización
(`PRUEBA SIO OC <id>`), una empresa, una sucursal, una persona (`PRUEBA<id>`) y la membresía de
`compras.test` en esa empresa. Para comprobar un `503`, detenga el contenedor del proveedor y repita
la operación.

## Auditoría (feature 016)

Eventos de empresa (`company_id`; `branch_id` en sucursales y asignaciones a sucursal). 18 operaciones de escritura auditadas.

Cada escritura de la API registra **un** evento de auditoría en la tabla `audit_outbox` de este
servicio, en la misma transacción que el cambio (si el cambio se revierte, el evento no existe), y el
proceso `operational-context-audit-outbox-worker` (misma imagen y base; `python -m sio_audit.worker`) lo entrega a
Audit con el cliente técnico `operational-context-service` (`perm:audit:audit-events:create`; `source_service =
operational-context-service`). Detalle por operación en
[`specs/016-existing-services-audit/contracts/audit-actions.md`](../../specs/016-existing-services-audit/contracts/audit-actions.md).

- Solo eventos `SUCCESS`: un rechazo sin efecto (`401`, `403`, `404`, `409`, `422`, `503`) no registra
  nada; una escritura que no cambia ningún campo tampoco (DS-02, DS-05).
- Valores: en la creación, los campos de la entidad; en la edición, solo los campos que cambiaron (antes y
  después); sin `id`, `version` ni columnas `created_*`/`updated_*`.
- Audit detenido no afecta a la API: los eventos quedan `PENDING` y el worker los entrega una sola vez al
  volver (reintentos con backoff de `libs/sio-audit`, a lo sumo `AUDIT_OUTBOX_BACKOFF_MAX_SECONDS` + 60 s
  después; sin orden de llegada garantizado: el historial se ordena por `occurred_at`).
- Las cargas por `seed` no se auditan (no hay autor autenticado).
- Variables del worker: `AUDIT_CLIENT_SECRET` = `OPERATIONAL_CONTEXT_CLIENT_SECRET` (solo en `infrastructure/.env`) y
  `AUDIT_OUTBOX_*` opcionales (ver `infrastructure/.env.example`).
- **Datos protegidos (DS-09)**: `email`, `phone`, `address_line`, `postal_code`, `latitude` y `longitude`
  de empresas y sucursales, y `reference_email` de usuarios de aplicación, se registran solo como
  `"<registrado>"`, `"<modificado>"` o `"<eliminado>"` y se declaran en `redacted_paths`; nunca su valor.
- Tras reconstruir Keycloak, reinicie el contenedor de este servicio: guarda en memoria el UUID interno
  del cliente `sio-api` para la comprobación técnica de acceso.

## Disponibilidad de la base

Regla de la Constitución 2.4.0 (Principio X), feature 009:

- La conexión a PostgreSQL tiene un tiempo de espera de 5 s y el pool descarta las conexiones rotas
  antes de usarlas (`pool_pre_ping`).
- Si la base no está disponible: `/health/live` sigue en `200`, `/health/ready` responde `503` y los
  endpoints que usan la base responden `503` `OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE` con `dependency:
  "database"`, `trace_id` y sin detalles internos (la causa queda en el log).
- Solo la pérdida o indisponibilidad de la conexión produce ese `503` (conexión rechazada o perdida,
  tiempo agotado, SQLSTATE `08xxx`, `57P01`, `57P02`, `57P03`). Un *deadlock*, un fallo de
  serialización, una sentencia cancelada o un bloqueo no disponible conservan su respuesta
  (`500 OPERATIONAL_CONTEXT.INTERNAL_ERROR`); integridad, validación y versión conservan `409`/`422`.
- Cuando la base vuelve, el servicio se recupera solo, sin reiniciarse.
- En Docker la base `sio-operational-context-db` tiene `healthcheck` y `restart: unless-stopped`, y la aplicación
  arranca cuando la base está sana (`infrastructure/services/operational-context-service.yaml`).

Validación en el entorno integrado (detiene la base temporalmente; solo lecturas con `admin.test` y
`KEYCLOAK_TEST_USER_PASSWORD` del entorno o de `infrastructure/.env`):

```bash
pytest -m integration -o addopts="" tests/integration/test_database_outage_recovery.py
```

Cubre una caída prolongada (`docker stop`) y una caída inesperada de PostgreSQL (reinicio por Docker),
contra `http://localhost:8104` (`OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL`). Si se interrumpe con la
base detenida: `docker start sio-operational-context-db`.

## Consumo de la API

- Prefijo `/api/v1`; errores `application/problem+json` con `code` (`OPERATIONAL_CONTEXT.<CAUSA>`) y
  `trace_id`; cabecera `X-Trace-Id` en toda respuesta.
- Contratos: Fase A en [`specs/004-operational-context-core/contracts/`](../../specs/004-operational-context-core/contracts/)
  y Fase B en [`specs/005-operational-context-users/contracts/`](../../specs/005-operational-context-users/contracts/)
  (`rest-api.md`, `errors.md`).
- **Contratos Provider**:
  - Empresa y sucursal por UUID ([`operational-context-provider.md`](../../specs/004-operational-context-core/contracts/operational-context-provider.md));
    con aislamiento, o sin él con `platform:lookup`.
  - Contexto y acceso operativo ([`operational-access-provider.md`](../../specs/005-operational-context-users/contracts/operational-access-provider.md)):
    `GET /api/v1/me/operational-context` y `GET /api/v1/operational-access`, que responde siempre
    `200` con `allowed` y una causa estable (`USER_NOT_MEMBER`, `USER_MEMBERSHIP_INACTIVE`,
    `COMPANY_INACTIVE`, `BRANCH_INACTIVE`, `BRANCH_NOT_ASSIGNED`, `USER_BRANCH_INACTIVE`,
    `PERMISSION_DENIED`). La vía técnica (`keycloak_user_id` + `platform:lookup`) evalúa el permiso con
    los roles del usuario objetivo leídos de Keycloak (`sio_auth.evaluate_permission`), nunca con los
    del token técnico.
  - Usuario operativo por UUID: `GET /api/v1/application-users/{id}`; los consumidores guardan solo
    su `id` en sus documentos.
- Permisos: `perm:operational-context:{companies|branches|application_users|user_branches|company_advisor_assignments}:{read|create|update|delete}`
  y las capacidades `perm:operational-context:platform:{administer|lookup}`. Detalle por usuario en
  [`docs/ejemplo/usuarios-y-permisos.md`](docs/ejemplo/usuarios-y-permisos.md).
