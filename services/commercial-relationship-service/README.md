# commercial-relationship-service

Microservicio de SIO que es la **fuente de verdad de la relación comercial de cada empresa** con
productos, clientes y proveedores (Fase A, núcleo). Guarda solo lo que pertenece a la empresa
(códigos internos, nombres visibles, precio simple, costo de referencia, banderas de inventario,
estado); la identidad del producto, de la persona y de la organización vive en su servicio dueño y
aquí solo se guarda su UUID.

- Spec, plan y contratos: `specs/007-commercial-relationship-core/`
- Contrato REST: `specs/007-commercial-relationship-core/contracts/rest-api.md`
- Errores: `specs/007-commercial-relationship-core/contracts/errors.md`
- Contrato Provider (consulta por UUID de las 3 entidades y por lotes de productos para Purchase,
  Sales e Inventory): `specs/007-commercial-relationship-core/contracts/commercial-relationship-provider.md`
- Mapa de dominio: `docs/domain-map.md`
- Ejemplos paso a paso con filas reales del Excel de productos, usuarios y permisos por URL:
  `docs/ejemplo/`, validados por `tests/examples/`

## Entidades propias

| Entidad           | Tabla               | Referencias externas (`UUID REF`, sin FK física)                                                  |
| ----------------- | ------------------- | ------------------------------------------------------------------------------------------------- |
| `CompanyProduct`  | `company_products`  | `company_id` (Operational Context), `global_product_id` (Product Catalog)                         |
| `CompanyCustomer` | `company_customers` | `company_id`, `person_identity_id` u `organization_identity_id`, `preferred_contact_person_id` (Party Identity) |
| `CompanySupplier` | `company_suppliers` | `company_id`, `organization_identity_id`, `preferred_contact_person_id` (Party Identity)          |

Estados: productos y clientes `ACTIVE`/`INACTIVE`; proveedores además `BLOCKED` (con
`block_reason` obligatorio). Nada se borra: no hay `DELETE`.

## Dependencias

| Clase | Dependencia                | Qué se consume, para qué y con qué autenticación                                                                                                                                                                                                                           |
| ----- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A     | PostgreSQL 17 propio       | Persistencia de las 3 entidades.                                                                                                                                                                                                                                           |
| B     | Keycloak (vía `sio-auth`)  | Validación de tokens y permisos `perm:commercial-relationship:{recurso}:{accion}`; emisión del token `client_credentials` del cliente técnico `commercial-relationship-service`.                                                                                            |
| C     | Operational Context        | `GET /operational-access?company_id=` (membresía `ACTIVE` y estado de la empresa, con el token del usuario) en toda ruta de usuario; `GET /me/operational-context` (empresas del usuario, en el resumen); `GET /companies/{id}` (solo `organization_identity_id`, para impedir que la empresa se relacione consigo misma y para mostrar la razón social en el resumen), con el token del usuario. |
| C     | Product Catalog            | `POST /products/batch-lookup` (al adoptar: existencia, estado y elegibilidad; al reactivar: solo estado) y `POST /products/{id}/first-use` (registro síncrono del primer uso, solo al adoptar), con la **identidad técnica propia** (`products:read`, `first-use:register`).                                  |
| C     | Party Identity             | `GET /person-identities/{id}`, `GET /organization-identities/{id}` y `GET /organization-contact-persons/{id}` al incorporar, modificar, reactivar o desbloquear, y la razón social (`legal_name`) de cada empresa en el resumen, con el token del usuario.                                                                                  |

Las URL base de los proveedores **incluyen** `/api/v1`. Un proveedor caído, con tiempo agotado o con
una respuesta fuera de contrato produce `503 COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` con la
extensión `dependency` (`operational-context`, `product-catalog`, `party-identity`); el log registra
la causa interna con el mismo `trace_id`. No publica ni consume eventos (sin RabbitMQ).

Un único comportamiento en todos los entornos: no hay variables de "modo" (stub, fake) para los
proveedores; las pruebas inyectan dobles por la fábrica `create_app`.

## Aislamiento por empresa

- Toda ruta de usuario exige, tras el token y el permiso, membresía `ACTIVE` del usuario en la
  empresa (por la ruta o por el recurso), consultada en Operational Context. Sin membresía o con un
  UUID ajeno → `404 NOT_FOUND`, igual que un UUID inexistente. Si Operational Context responde `403`
  → `403 OPERATIONAL_ACCESS_DENIED`; si no está disponible → `503`.
- Empresa `INACTIVE`: las lecturas y las inactivaciones continúan; las demás escrituras (incluido el
  `PUT`) → `422 COMPANY_INACTIVE`.
- **Exención técnica** (solo lecturas por UUID y la consulta por lotes de productos): una identidad
  técnica (claims `client_id` y `preferred_username = service-account-{client_id}`) **con**
  `perm:commercial-relationship:platform:lookup` lee sin membresía. Un usuario humano nunca la
  obtiene, aunque tenga el permiso.

## Configuración

Copie `.env.example` a `.env` (el `.env` no se versiona).

| Variable                                                                   | Uso                                                              | Ejemplo                                       |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------- | --------------------------------------------- |
| `SIO_DOCS_ENABLED`                                                         | Publica `/docs` y `/openapi.json`                                | `true`                                        |
| `COMMERCIAL_RELATIONSHIP_SERVICE_PORT`                                     | Puerto del contenedor de la aplicación del entorno independiente | `8005`                                        |
| `DATABASE_URL`, `COMMERCIAL_RELATIONSHIP_DB_*`                             | PostgreSQL de desarrollo                                         | puerto `55442`                                |
| `COMMERCIAL_RELATIONSHIP_TEST_DB_*`, `COMMERCIAL_RELATIONSHIP_TEST_DATABASE_URL` | Base aislada de pruebas                                    | puerto `55443`                                |
| `SIO_AUTH_ISSUER`, `SIO_AUTH_JWKS_URL`, `SIO_AUTH_AUDIENCE`                | Configuración de `sio-auth`                                      | `http://localhost:8081/realms/sio`, `sio-api` |
| `OPERATIONAL_CONTEXT_SERVICE_BASE_URL`, `OPERATIONAL_CONTEXT_TIMEOUT_SECONDS` | Operational Context (con `/api/v1`)                           | `http://localhost:8004/api/v1`, `5`           |
| `PRODUCT_CATALOG_SERVICE_BASE_URL`, `PRODUCT_CATALOG_TIMEOUT_SECONDS`      | Product Catalog (con `/api/v1`)                                  | `http://localhost:8003/api/v1`, `5`           |
| `PARTY_IDENTITY_SERVICE_BASE_URL`, `PARTY_IDENTITY_TIMEOUT_SECONDS`        | Party Identity (con `/api/v1`)                                   | `http://localhost:8002/api/v1`, `5`           |
| `KEYCLOAK_BASE_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_TIMEOUT_SECONDS`          | Emisión del token técnico                                        | `http://localhost:8081`, `sio`                |
| `COMMERCIAL_RELATIONSHIP_CLIENT_ID`, `COMMERCIAL_RELATIONSHIP_CLIENT_SECRET` | Cliente técnico; el secreto solo en `.env` y debe coincidir con el realm | `commercial-relationship-service`   |

Si Windows reserva el rango de puertos de la base (`netsh int ipv4 show excludedportrange
protocol=tcp`), cambie `COMMERCIAL_RELATIONSHIP_DB_PORT`/`_TEST_DB_PORT` y las URL en su `.env`
local.

## Arranque local

Desde `services/commercial-relationship-service/`:

```bash
cp .env.example .env
python -m venv .venv
.venv/Scripts/activate            # Linux/macOS: source .venv/bin/activate
pip install -e ".[test]"
docker compose up -d commercial-relationship-dev-db
alembic upgrade head
uvicorn commercial_relationship_service.main:app --port 8005
```

Con contenedor: `docker compose up -d --build` (aplicación `sio-commercial-relationship-service-dev`
en `http://localhost:8005`). En el entorno integrado (`infrastructure/scripts/rebuild-all.sh`) el
contenedor es `sio-commercial-relationship-service` en `http://localhost:8106`.
`GET /health/live` y `GET /health/ready` son públicos; `ready` solo comprueba la base de datos.

## Migraciones

Alembic en `alembic/versions/`. La migración `0001` crea las 3 tablas con restricciones nombradas
(`pk_`, `uq_`, `ck_`, `ix_`), importes `NUMERIC` y unicidad de `internal_code` sin distinguir
mayúsculas por empresa, en cualquier estado. Una migración ya aplicada en un entorno compartido no
se edita: las correcciones van en una migración nueva.

## Datos iniciales

No hay `seed`: los productos, clientes y proveedores los registra cada empresa.

## Pruebas

```bash
docker compose --profile test up -d commercial-relationship-test-db
pytest                                     # unitarias, contrato, API, salud y ejemplos
pytest -m performance -o addopts=""        # 50 000 productos por empresa, p95 < 1 s (SC-009)
pytest -m integration -o addopts=""        # proveedores y Keycloak reales (entorno integrado)
```

- Las pruebas ordinarias no necesitan Keycloak ni los proveedores: los tokens se firman con una clave
  RSA temporal y Operational Context, Product Catalog y Party Identity son dobles inyectados
  (`tests/fakes.py`). Los adaptadores HTTP se prueban con `httpx.MockTransport`
  (`tests/contract/`).
- `tests/contract/test_migrations.py` aplica y revierte las migraciones desde cero.
- `tests/api/test_auth.py` y `tests/api/test_isolation.py` recorren las 22 rutas (el aislamiento del resumen se prueba en `tests/api/test_company_summaries.py`): `401`, `403`,
  `404` fuera de alcance, `403 OPERATIONAL_ACCESS_DENIED`, `503` y la exención técnica.
- `tests/api/test_openapi_contract.py` compara el OpenAPI con el contrato.
- `tests/examples/` ejecuta los ejercicios de `docs/ejemplo/` (Principio XXII): cada uno en una base
  nueva y los tres en la misma base; verifica el permiso de cada URL contra la plantilla del realm y
  exige que `docs/ejemplo/` coincida con lo generado. Tras cambiar un ejercicio, un contrato o el
  realm, regenere con `COMMERCIAL_RELATIONSHIP_EXAMPLES_WRITE=1 pytest tests/examples` y revise el
  diff.
- Marcador `integration`: `tests/integration/test_real_dependencies.py` adopta un producto completo y
  verifica el primer uso en Product Catalog, incorpora un cliente y un proveedor contra Party
  Identity, comprueba el `404` sin membresía y el predicado de identidad técnica con tokens reales.
  Usa el entorno integrado (CR `8106`, Product Catalog `8103`, Operational Context `8104`, Party
  Identity `8101`, Geography `8102`, Keycloak `8081`; variables `*_INTEGRATION_BASE_URL`). La
  contraseña de `admin.test` y el secreto del cliente técnico se leen del entorno o de
  `infrastructure/.env`. Es repetible: cada ejecución crea datos ficticios de validación. La caída
  de un proveedor (`503`) se verifica a mano deteniendo su contenedor.

## Consumo de la API

- Prefijo `/api/v1`; errores RFC 9457 (`application/problem+json`) con `code`
  (`COMMERCIAL_RELATIONSHIP.*`), `trace_id` y `errors[]`; cabecera `X-Trace-Id` en toda respuesta.
- Concurrencia optimista: `version` en el cuerpo de `PUT` y de las acciones; desactualizada →
  `409 VERSION_CONFLICT`. Un `PUT` sin cambios devuelve `200` sin incrementar `version`.
- El `PUT` se acepta en cualquier estado y nunca cambia `status`; los cambios de estado son acciones
  `POST …/deactivate`, `…/reactivate`, `…/block`, `…/unblock`.
- Importes: entrada como número o cadena; salida siempre como cadena decimal (`sale_price` con 2
  decimales, `reference_cost` con 4). `currency_code` ISO 4217 de la lista soportada; en las monedas sin
  decimales (`CLP`, `PYG`, `JPY`, `KRW`) un `sale_price` con fracción → `422 PRICE_SCALE_NOT_ALLOWED`.
- Adopción: el producto global debe existir, estar `ACTIVE` y ser elegible; el primer uso se registra
  en Product Catalog antes de guardar. Un producto se adopta una sola vez por empresa (en cualquier
  estado: si está inactivo, se reactiva).
- Resumen de mis empresas: `GET /api/v1/company-summaries` devuelve, **una empresa por página** por
  defecto (`?page=2`, `?page_size=` hasta 100), las empresas donde el usuario tiene membresía `ACTIVE`,
  con `company_status`, razón social (`legal_name`, `null` si no es visible) y el total y el conteo por
  estado de productos, clientes y proveedores (`null` sin el permiso de lectura correspondiente). Exige
  `company_products:read`; no da alcance de plataforma.
- Consulta por lotes: `POST /api/v1/company-products/batch-lookup` con hasta 100 UUID; los ausentes o
  fuera de alcance se devuelven con solo `id` y `found: false`.

## Permisos

Roles de cliente `sio-api` (plantilla `infrastructure/keycloak/realm-template/sio-realm.template.json`):

| Recurso             | `read`                  | `create`    | `update`                          | `delete`             |
| ------------------- | ----------------------- | ----------- | --------------------------------- | -------------------- |
| `company_products`  | Listar, obtener, lotes, resumen | Adoptar     | Modificar, reactivar              | Inactivar            |
| `company_customers` | Listar, obtener         | Incorporar  | Modificar, reactivar              | Inactivar            |
| `company_suppliers` | Listar, obtener         | Seleccionar | Modificar, reactivar, desbloquear | Inactivar, bloquear  |

`perm:commercial-relationship:platform:lookup` es la capacidad de consulta técnica sin membresía;
solo tiene efecto en identidades técnicas. El cliente técnico `commercial-relationship-service`
tiene `perm:product-catalog:products:read` y `perm:product-catalog:first-use:register`.
