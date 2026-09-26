# operational-context-service

Microservicio FastAPI de SIO, fuente de verdad del **contexto operativo**: qué empresas usan la
plataforma y en qué sucursales (sedes, tiendas, bodegas o puntos) operan. No es dueño de la
identidad legal (Party Identity) ni de la geografía (Geography): solo guarda sus `UUID`.

- Spec, plan y contratos: [`specs/004-operational-context-core/`](../../specs/004-operational-context-core/)
  (Fase A, gate `OPERATIONAL-CONTEXT-CORE READY`).
- API REST `v1` bajo `/api/v1`, protegida con `sio-auth` (Keycloak).
- Ejercicios de uso validados y guía de permisos: [`docs/ejemplo/`](docs/ejemplo/README.md).

## Entidades propias

| Entidad | Tabla | Estados |
| --- | --- | --- |
| Empresa | `companies` | `status` (uso): `ACTIVE`/`INACTIVE`; nunca se elimina |
| Sucursal | `branches` | `status` (uso): `ACTIVE`/`INACTIVE`; nunca se elimina |

Qué **no** guarda la empresa: NIT, tipo de identificación, razón social ni nombre comercial. Se
consultan en Party Identity con `organization_identity_id` (DS-01, DS-13). Tampoco guarda nombres ni
códigos geográficos, el representante legal, el sector económico ni el asesor.

Reglas principales:

- `organization_identity_id` es obligatorio, debe existir y estar `ACTIVE` en Party Identity al
  asignarlo o cambiarlo, y cada organización se vincula a una sola empresa.
- Correo, teléfono y dirección son de la **sede operativa principal** de la empresa en SIO, no el
  contacto global de la organización (DS-14).
- Ubicación opcional con coherencia estricta: si hay división o ciudad debe haber país; la división
  pertenece al país; la ciudad pertenece al país y exactamente a la división enviada. Cada nivel debe
  existir y estar `ACTIVE` en Geography al asignarlo o cambiarlo (DS-04, DS-05).
- Coordenadas en pareja, en rango y con hasta 6 decimales (se rechazan, no se redondean).
- Zona horaria IANA (empresa: `America/Bogota` por defecto; sucursal: opcional y, si falta, se usa la
  de la empresa, calculada en cada consulta como `effective_timezone`, nunca copiada). Moneda de 3
  letras (`COP` por defecto).
- Código de sucursal normalizado (recorte y mayúsculas), único por empresa (también frente a
  inactivas) y modificable; los demás servicios referencian el `id`.
- Modificaciones con la `version` leída (`409` si está desactualizada); un `PUT` sin cambios no
  escribe. Party Identity y Geography solo se consultan si cambia la referencia correspondiente.
- Inactivar una empresa no modifica sus sucursales (cada sucursal informa `company_status`); no se
  crean ni reactivan sucursales bajo una empresa inactiva, también bajo concurrencia.
- En esta fase la autorización es solo por permiso: el filtro por empresa del usuario llega en la
  Fase B (ver `docs/domain-map.md`).

## Dependencias

| Clase | Dependencia | Uso |
| --- | --- | --- |
| A | PostgreSQL 17 propio | Base `sio_operational_context` (desarrollo) y base de pruebas aislada |
| B | Keycloak | Validación de tokens (`sio-auth`) |
| C | Party Identity Service | `GET {PARTY_IDENTITY_SERVICE_BASE_URL}/organization-identities/{id}` al crear una empresa o cambiar su organización |
| C | Geography Service | `GET global-countries/{id}`, `GET global-administrative-divisions/{id}`, `GET global-cities/{id}` al asignar o cambiar la ubicación |

Se propaga el token del usuario (D5). Para escribir, el usuario necesita además de los permisos de
este servicio: `perm:party-identity:organization_identities:read`,
`perm:geography:global_countries:read`, `perm:geography:global_administrative_divisions:read` y
`perm:geography:global_cities:read` (en el realm vigente los tienen `administradores` y
`supervisores`).

### Respuestas de las dependencias

| Resultado del proveedor | Respuesta de este servicio |
| --- | --- |
| Existe y `ACTIVE` (y coherente) | Continúa |
| `404` | `422` `ORGANIZATION_IDENTITY_NOT_FOUND`, `COUNTRY_NOT_FOUND`, `ADMINISTRATIVE_DIVISION_NOT_FOUND` o `CITY_NOT_FOUND` |
| `INACTIVE` | `422` `ORGANIZATION_IDENTITY_INACTIVE` o `LOCATION_INACTIVE` |
| Incoherente | `422 GEOGRAPHY_INCOHERENT` (con el campo en `errors[]`) |
| Tiempo agotado, red, `5xx`, `401`/`403` o respuesta inesperada | `503 DEPENDENCY_UNAVAILABLE`; no se guarda nada |

**Observabilidad**: cada solicitud tiene un `trace_id` (tomado de `traceparent` o generado) que se
devuelve en `X-Trace-Id`, en todo Problem Details, en cada línea de log (`trace_id=<id>`) y se envía a
los proveedores en `traceparent` (mismo trace-id, `span-id` nuevo). Las causas internas de un `503`
solo aparecen en el log: `ORGANIZATION_VALIDATION_DENIED` / `GEOGRAPHY_VALIDATION_DENIED` (`WARNING`,
el proveedor respondió `401`/`403`) y `PARTY_IDENTITY_UNAVAILABLE` / `GEOGRAPHY_UNAVAILABLE`
(`ERROR`), con proveedor, operación, resultado y duración; nunca el token ni el cuerpo. Los rechazos
`422` de referencias externas se registran en `INFO` con el código, el campo y el UUID rechazado.
Tiempo de espera por llamada: `PARTY_IDENTITY_TIMEOUT_SECONDS` y `GEOGRAPHY_TIMEOUT_SECONDS` (5 s),
sin reintentos automáticos.

### Desarrollo local sin proveedores

Operational Context conserva **exactamente los mismos contratos y comportamiento funcional** en todos
los entornos. Para desarrollar sin levantar Party Identity o Geography se puede usar un **mock HTTP
externo** que implemente esos mismos contratos (ver
[`contracts/`](../../specs/004-operational-context-core/contracts/)), apuntando
`PARTY_IDENTITY_SERVICE_BASE_URL` o `GEOGRAPHY_SERVICE_BASE_URL` a él.

No existen `PARTY_IDENTITY_MODE=stub`, `GEOGRAPHY_MODE=stub`, datos falsos en el código productivo ni
caminos distintos para desarrollo, pruebas y producción. Los dobles de pruebas viven solo en
`tests/`.

| Operación | Con proveedores reales | Pruebas automáticas | Desarrollo sin proveedores |
| --- | --- | --- | --- |
| Arranque, `/health/*`, consultas, inactivar/reactivar | No los usa | No los usa | No los usa |
| Alta de empresa; cambio de organización | Party Identity real | Doble inyectado desde `tests/conftest.py` | Mock HTTP externo |
| Alta o cambio de ubicación | Geography real | Doble inyectado | Mock HTTP externo |

## Configuración

Copie `.env.example` a `.env`. Variables:

| Variable | Uso | Ejemplo |
| --- | --- | --- |
| `SIO_DOCS_ENABLED` | Publica `/docs` y `/openapi.json` | `true` |
| `OPERATIONAL_CONTEXT_SERVICE_PORT` | Puerto local del servicio | `8004` |
| `DATABASE_URL` | Base de desarrollo | `postgresql+psycopg://…@127.0.0.1:55439/sio_operational_context` |
| `OPERATIONAL_CONTEXT_DB_*` | Contenedor de la base de desarrollo | puerto `55439` |
| `OPERATIONAL_CONTEXT_TEST_DB_*`, `OPERATIONAL_CONTEXT_TEST_DATABASE_URL` | Base de pruebas (perfil `test`) | puerto `55440` |
| `SIO_AUTH_ISSUER`, `SIO_AUTH_JWKS_URL`, `SIO_AUTH_AUDIENCE` | `sio-auth` | `http://localhost:8081/realms/sio`, …, `sio-api` |
| `PARTY_IDENTITY_SERVICE_BASE_URL` | URL de Party Identity **con** `/api/v1` | `http://localhost:8002/api/v1` |
| `PARTY_IDENTITY_TIMEOUT_SECONDS` | Tiempo de espera por llamada | `5` |
| `GEOGRAPHY_SERVICE_BASE_URL` | URL de Geography con su prefijo vigente (hoy sin `/api/v1`) | `http://localhost:8000` |
| `GEOGRAPHY_TIMEOUT_SECONDS` | Tiempo de espera por llamada | `5` |
| `OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL`, `KEYCLOAK_TOKEN_URL` | Solo `pytest -m integration` | `http://localhost:8004`, `…/openid-connect/token` |

## Arranque local

```bash
cd services/operational-context-service
docker compose up -d operational-context-dev-db               # sio-operational-context-dev-db
python -m venv .venv && .venv/Scripts/pip install -e ".[test]"
alembic upgrade head
uvicorn operational_context_service.main:app --port 8004 --env-file .env
```

O con Docker: `docker compose up -d --build` (contenedor `sio-operational-context-service-dev`,
puerto `8004`, que apunta a Party Identity en `8002` y Geography en `8000` del host). En el entorno
integrado de `infrastructure/` el servicio es `sio-operational-context-service` en el puerto `8104`
sobre la base `operational-context-db`.
Tras el primer arranque aplique las migraciones dentro del contenedor:
`docker exec sio-operational-context-service alembic upgrade head`. Sus escrituras necesitan
`party-identity-service` y `geography-service` del mismo proyecto; si no están en ejecución responden
`503 DEPENDENCY_UNAVAILABLE`.

## Migraciones

`alembic upgrade head`. La migración `0001` crea `companies` y `branches` con todas sus
restricciones con nombre (`uq_`, `ck_`, `fk_`, `ix_`). La única FK es interna
(`branches.company_id → companies.id`, `ON DELETE RESTRICT`); no hay FK hacia otros servicios.

## Datos iniciales

No hay: el dominio no requiere datos base (Principio XIV).

## Pruebas

```bash
docker compose --profile test up -d operational-context-test-db
pytest                                   # toda la suite, sin Party Identity, Geography ni Keycloak reales
pytest tests/examples                    # ejercicios de docs/ejemplo/
OPERATIONAL_CONTEXT_EXAMPLES_WRITE=1 pytest tests/examples   # regenerar docs/ejemplo/
pytest -m integration                    # contra servicios reales (ver abajo)
```

- `tests/unit`: reglas de dominio, validación de ubicación y servicios con dobles instrumentados.
- `tests/contract`: migraciones desde cero, restricciones, repositorios y adaptadores HTTP con
  `httpx.MockTransport` (incluidos logs con causa interna y `trace_id`).
- `tests/api`: rutas, errores RFC 9457, `401`/`403` por operación, contrato Provider, OpenAPI,
  propagación del trace-id, unicidad concurrente y la carrera determinista entre inactivar la empresa
  y crear o reactivar sucursales.
- `tests/health`, `tests/examples`.

### Pruebas de integración (`pytest -m integration`)

Exigen en ejecución: este servicio (`OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL`, por defecto
`http://localhost:8004`), Party Identity con la regla `NIT` de Colombia, Geography con los datos de
Colombia y Keycloak. La contraseña de `admin.test` se lee de `KEYCLOAK_TEST_USER_PASSWORD` o de
`infrastructure/.env`. Si falta algo, las pruebas se omiten con un mensaje.

Cada ejecución crea en Party Identity una organización nueva con datos **ficticios de validación**
(razón social `PRUEBA SIO OC <id>` y un NIT generado que cumple la regla vigente), y con ella una
empresa y una sucursal. Esos registros **permanecen** en el entorno como datos de validación; por
eso la prueba se puede repetir sin `409`. Para comprobar el `503`, detenga el contenedor del proveedor
y repita un alta (instrucciones en el propio archivo de prueba).

## Consumo de la API

- Prefijo `/api/v1`; errores `application/problem+json` con `code` (`OPERATIONAL_CONTEXT.<CAUSA>`) y
  `trace_id`; cabecera `X-Trace-Id` en toda respuesta.
- Contrato completo: [`contracts/rest-api.md`](../../specs/004-operational-context-core/contracts/rest-api.md);
  errores: [`contracts/errors.md`](../../specs/004-operational-context-core/contracts/errors.md).
- **Contrato Provider** para Commercial Relationship, Inventory, Purchase y Sales:
  [`operational-context-provider.md`](../../specs/004-operational-context-core/contracts/operational-context-provider.md).
  `GET /api/v1/companies/{id}` y `GET /api/v1/branches/{id}` devuelven la entidad en cualquier estado;
  una sucursal es apta para nuevas referencias solo si `status` y `company_status` son `ACTIVE`, y el
  consumidor debe comprobar que su `company_id` coincide con la empresa que recibió.
- Permisos: `perm:operational-context:{companies|branches}:{read|create|update|delete}`; inactivar
  exige `delete` y reactivar `update`. Detalle por usuario en
  [`docs/ejemplo/usuarios-y-permisos.md`](docs/ejemplo/usuarios-y-permisos.md).
