# audit-service

Registro **oficial e inmutable** de las acciones importantes de SIO (feature `011-audit-core`, gate
`AUDIT-CORE READY`). Los microservicios **emisores** registran eventos con su identidad técnica y los
usuarios autorizados los **consultan** por empresa o, con un permiso propio, los de plataforma.

No es un log técnico (errores, depuración, métricas), no decide ni bloquea operaciones de otros
servicios y no es fuente de verdad de las entidades que menciona: solo del **evento**.

Especificación y diseño: `specs/011-audit-core/` (Spec, plan, contratos, modelo de datos).

## Entidades propias

| Entidad | Tabla | Notas |
| --- | --- | --- |
| `AuditEvent` | `audit_events` | Inmutable. Atributos de §11.1 de `docs/SIO Database V1.1.0.md` más `redacted_paths` y las columnas de auditoría (`created_at` = `recorded_at`, `created_by` = `sub` de la cuenta emisora; `updated_*` iguales y nunca modificados). Sin `version`. |

`username_snapshot`, `previous_values` y `new_values` son **instantáneas históricas** autorizadas por
la excepción **E-01** (aprobada el 2026-10-05): evidencia del estado observado al momento del evento,
nunca fuente del estado actual; solo lo que admite el contrato del evento; siempre redactadas; con las
mismas reglas de autorización e inmutabilidad que el evento.

## Dependencias

| Clase | Dependencia | Para qué |
| --- | --- | --- |
| A | PostgreSQL propia `audit` (`5449`; pruebas `55451`) | Persistencia |
| B | Keycloak (validación de tokens con `sio-auth`) | Autenticación y permisos |
| C | Operational Context — `GET /operational-access?company_id=` (vía propia) | Solo la consulta de eventos **de empresa**: membresía `ACTIVE` del usuario, con **su propio token** |

El **registro** de eventos no depende de ningún otro servicio. Audit no tiene cliente técnico propio
y nunca sustituye la identidad del usuario por una técnica. Librerías: `libs/sio-auth` (≥ 0.4.0) y
`libs/sio-audit` (≥ 0.1.0; contrato del evento y política de redacción).

## Permisos

| Permiso | Operación | Quién |
| --- | --- | --- |
| `perm:audit:audit-events:create` | Registrar uno o varios eventos | Solo **cuentas de servicio**: un usuario humano recibe `403` aunque tenga el permiso por comodín |
| `perm:audit:audit-events:read` | Consultar eventos **de empresa** (lista, `id`, historial) | Hoy `administradores` y `supervisores` (comodines) |
| `perm:audit:platform-events:read` | Consultar eventos **de plataforma** (sin empresa) | Hoy `administradores` y `supervisores` (comodines) |

**Dependencia de permisos (FR-037, FR-050)**: consultar la auditoría de una empresa exige
`perm:audit:audit-events:read` **más** `perm:operational-context:application_users:read` (lo exige
Operational Context al resolver el acceso) **más** la membresía `ACTIVE` en la empresa, validada con el
token del usuario. Ser miembro no da acceso a la auditoría. Ningún grupo recibe permisos de auditoría
explícitos; otro grupo se habilita asignándolos en Keycloak, sin cambios de código. Los alcances están
separados: el permiso de empresa nunca muestra eventos de plataforma y viceversa.

## Inmutabilidad

- La API no publica `PUT`, `PATCH` ni `DELETE` sobre eventos (`405`).
- La base rechaza `UPDATE`, `DELETE` y `TRUNCATE` sobre `audit_events` con triggers
  (`tr_audit_events_no_update`, `tr_audit_events_no_delete`, `tr_audit_events_no_truncate`), también
  en sesiones manuales. Solo las migraciones cambian la estructura.
- Retención indefinida; no hay purga ni eliminación (D7).

## Redacción de valores sensibles

Audit aplica la política única de `libs/sio-audit` (fuente normativa: su
[`README.md`](../../libs/sio-audit/README.md)) al recibir cada evento, como defensa en profundidad:
reemplaza los valores sensibles por `"***"`, registra sus rutas en `redacted_paths` y nunca rechaza el
evento por ello. Validación, idempotencia y persistencia usan el contenido redactado. Ningún valor
original se guarda, se devuelve ni se escribe en logs.

## Integración de servicios emisores

Guía normativa: [`docs/integracion-emisores.md`](docs/integracion-emisores.md) (Transactional Outbox,
`audit-outbox-worker`, variables, pruebas mínimas). Party Identity, Product Catalog, Operational
Context y Commercial Relationship **no** están auditados hasta completar la feature transversal
"Auditoría de servicios existentes" del roadmap.

## Configuración

Variables en [`.env.example`](.env.example): `DATABASE_URL`, `SIO_AUTH_*`, `SIO_DOCS_ENABLED`,
`OPERATIONAL_CONTEXT_SERVICE_BASE_URL` (con `/api/v1`), `OPERATIONAL_CONTEXT_TIMEOUT_SECONDS`,
`AUDIT_MAX_CLOCK_SKEW_SECONDS` (tolerancia de `occurred_at` hacia el futuro, `300`) y las de pruebas.
Sin modos por entorno: siempre el adaptador real; las pruebas inyectan dobles por DI.

## Arranque local

El servicio vive en el proyecto Compose único `infrastructure/services/audit-service.yaml` (proyecto
`audit-service`), que se une a `sio-network` (Keycloak en el proyecto `sio`). Sigue la práctica vigente
del repositorio de un único proyecto Compose por servicio; la reconciliación del Principio IV
("`docker-compose.yml` propio") está pendiente por separado.

```bash
# desde la raíz del repositorio
docker compose -p audit-service -f infrastructure/services/audit-service.yaml --env-file infrastructure/.env up -d --build
docker exec sio-audit-service alembic upgrade head
curl -s localhost:8110/health/ready     # {"status":"ready"}
```

Entorno independiente (desde `services/audit-service/`):

```bash
cp .env.example .env
python -m venv .venv && .venv/Scripts/python -m pip install -e ../../libs/sio-auth -e ../../libs/sio-audit -e ".[test]"
alembic upgrade head
uvicorn audit_service.main:app --reload --port 8110
```

## Migraciones

`alembic/versions/0001_audit_events.py`: tabla, restricciones nombradas, índices por alcance, función
y triggers de inmutabilidad. `downgrade` elimina triggers, función y tabla. No requiere extensiones
(`gen_random_uuid()` es del núcleo de PostgreSQL 17).

## Datos iniciales

No hay: el dominio no requiere datos base (Principio XIV).

## Pruebas

```bash
docker compose --file ../../infrastructure/services/audit-service.yaml --env-file ../../infrastructure/.env --profile test up -d audit-test-db
pytest                       # unitarias, contrato, API, salud, ejemplos (base de pruebas aislada)
pytest -m performance        # 1 000 000 de eventos (SC-006)
pytest -m integration        # Keycloak, Operational Context y base reales; detiene y reinicia
                             # sio-operational-context-service y sio-audit-db
AUDIT_EXAMPLES_WRITE=1 pytest tests/examples   # regenera docs/ejemplo/
```

Las pruebas de integración leen `KEYCLOAK_TEST_USER_PASSWORD` y `AUDIT_TEST_EMITTER_CLIENT_SECRET` del
entorno o de `infrastructure/.env` (nunca del código).

## Disponibilidad de la base

Conexión con tiempo de espera de 5 s y `pool_pre_ping`. Con la base caída: `/health/live` `200`,
`/health/ready` `503` y toda ruta que la usa `503 AUDIT.DEPENDENCY_UNAVAILABLE` con
`dependency: database` (nunca `500`); al volver la base, el servicio se recupera sin reinicio.

## Consumo de la API

`{BASE}` = `http://localhost:8110/api/v1`. Errores RFC 9457 con `code` `AUDIT.<CAUSA>` y `trace_id`.

| Método y ruta | Uso |
| --- | --- |
| `POST /audit-events` | Registrar un evento (`201`, o `200` si ya existía igual; `409` si el `event_id` existe con otro contenido) |
| `POST /audit-events/batch` | Registrar 1–100 eventos, atómico (`200` con `CREATED`/`ALREADY_EXISTS` por evento) |
| `GET /companies/{company_id}/audit-events` | Listar eventos de una empresa con filtros |
| `GET /companies/{company_id}/audit-events/{id}` | Un evento de la empresa |
| `GET /companies/{company_id}/entity-history/{entity_type}/{entity_id}` | Historial de una entidad (cronológico) |
| `GET /platform-audit-events`, `/platform-audit-events/{id}`, `/platform-entity-history/{entity_type}/{entity_id}` | Lo mismo para eventos de plataforma |

Ejercicios validados: [`docs/ejemplo/`](docs/ejemplo/README.md).
