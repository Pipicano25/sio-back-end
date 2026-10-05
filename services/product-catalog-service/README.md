# product-catalog-service

Microservicio de SIO que es la **fuente de verdad única del catálogo global y compartido de
productos**. Define qué es un producto de forma independiente de la empresa que lo compra, vende o
almacena. No guarda datos de ninguna empresa: ni precios, costos, stock, SKU o códigos internos, ni
proveedores.

- Spec, plan y contratos: `specs/002-product-catalog-service/`
- Contrato REST: `specs/002-product-catalog-service/contracts/rest-api.md`
- Errores: `specs/002-product-catalog-service/contracts/errors.md`
- Mapa de dominio: `docs/domain-map.md`
- Guía de uso de la API y su lógica: `docs/api-guide.md`
- Referencia detallada de cada ruta: `docs/api/`
- Ejemplos con datos reales del Excel de productos (5 ejercicios paso a paso, con usuarios y
  permisos por URL): `docs/ejemplo/`, validados por `tests/examples/`

## Entidades propias

| Entidad                        | Tabla                              |
| ------------------------------ | ---------------------------------- |
| `GlobalUnitOfMeasure`          | `global_units_of_measure`          |
| `GlobalPackagingType`          | `global_packaging_types`           |
| `GlobalBrand`                  | `global_brands`                    |
| `GlobalCategory`               | `global_categories`                |
| `GlobalProduct`                | `global_products`                  |
| `GlobalProductCategory`        | `global_product_categories`        |
| `ProductAttributeDefinition`   | `product_attribute_definitions`    |
| `ProductAttributeOption`       | `product_attribute_options`        |
| `GlobalCategoryAttribute`      | `global_category_attributes`       |
| `GlobalProductAttributeValue`  | `global_product_attribute_values`  |
| `GlobalProductPresentation`    | `global_product_presentations`     |
| `GlobalProductIdentifier`      | `global_product_identifiers`       |
| `GlobalProductGroupType`       | `global_product_group_types`       |
| `GlobalProductGroup`           | `global_product_groups`            |
| `GlobalProductGroupAssignment` | `global_product_group_assignments` |
| `ProductAsset`                 | `product_assets`                   |

## Dependencias

| Clase | Dependencia               | Qué se consume y para qué                                                                                                                                                                                                 |
| ----- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A     | PostgreSQL 17 propio      | Persistencia del catálogo (extensión `pg_trgm` para búsqueda).                                                                                                                                                            |
| B     | Keycloak (vía `sio-auth`) | Validación de tokens y permisos `perm:product-catalog:{recurso}:{accion}`.                                                                                                                                                |
| C     | Party Identity Service    | `GET {PARTY_IDENTITY_SERVICE_BASE_URL}/organization-identities/{id}`: comprobar que existe la organización fabricante **solo** cuando se asigna o cambia `manufacturer_organization_id`. Se propaga el token del usuario. |

No publica ni consume eventos (sin RabbitMQ). Commercial Relationship Service consume este
servicio: consultas por lotes y registro del primer uso
(`specs/002-product-catalog-service/contracts/first-use.md`).

## Configuración

Copie `.env.example` a `.env` (el `.env` no se versiona).

| Variable                                                         | Uso                                                         | Ejemplo                                                      |
| ---------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------ |
| `SIO_DOCS_ENABLED`                                               | Publica `/docs` y `/openapi.json`                           | `true`                                                       |
| `DATABASE_URL`                                                   | Base del proyecto compose (credenciales en `infrastructure/.env`)                                    | `postgresql+psycopg://…@127.0.0.1:5444/product_catalog` |
| `PRODUCT_CATALOG_TEST_DATABASE_URL` | Base aislada de pruebas                                     | puerto `55438`                                               |
| `SIO_AUTH_ISSUER`, `SIO_AUTH_JWKS_URL`, `SIO_AUTH_AUDIENCE`      | Configuración de `sio-auth`                                 | `http://localhost:8081/realms/sio`, `sio-api`                |
| `PARTY_IDENTITY_SERVICE_BASE_URL`                                | URL base de Party Identity, **incluido su prefijo de ruta** | `http://localhost:8101/api/v1`                                   |
| `PARTY_IDENTITY_TIMEOUT_SECONDS`                                 | Tiempo de espera de la validación del fabricante            | `3`                                                          |

## Arranque local

Desde `services/product-catalog-service/`:

```bash
cp .env.example .env
python -m venv .venv
.venv/Scripts/activate            # Linux/macOS: source .venv/bin/activate
pip install -e ".[test]"
docker compose --file ../../infrastructure/services/product-catalog-service.yaml --env-file ../../infrastructure/.env up -d product-catalog-db
alembic upgrade head
python -m product_catalog_service.seed load
uvicorn product_catalog_service.main:app --port 8003
```

Con contenedor: `docker compose --file ../../infrastructure/services/product-catalog-service.yaml --env-file ../../infrastructure/.env up -d --build`
(aplicación `sio-product-catalog-service` en `http://localhost:8103`). Es el mismo proyecto compose
`product-catalog-service` que levanta `infrastructure/scripts/rebuild-all.sh`: requiere el proyecto `sio`
arriba (red `sio-network` y Keycloak). `uvicorn` fuera de Docker usa el puerto local `8003` y la
misma base del proyecto (`DATABASE_URL` del `.env`).
`GET /health/live` y `GET /health/ready` son públicos.

## Migraciones

Alembic en `alembic/versions/`. La migración `0001` crea la extensión `pg_trgm` y las 16 tablas con
restricciones nombradas (`uq_`, `ck_`, `ix_`, `fk_`). Una migración ya aplicada en un entorno
compartido no se edita: las correcciones van en una migración nueva.

## Datos iniciales

```bash
python -m product_catalog_service.seed load
```

Carga de forma idempotente 8 unidades de medida (`UND`, `KG`, `G`, `LT`, `ML`, `M`, `CM`, `M2`), 10
tipos de empaque (`BOX`, `BOTTLE`, …) y los tipos de grupo `GROUP_1` a `GROUP_15`. Usa
`INSERT … ON CONFLICT (code) DO NOTHING`: no duplica, no sobrescribe y no reactiva registros
modificados por un administrador. Audita con la identidad técnica
**`system:product-catalog-seed`** (`created_by`/`updated_by`).

## Pruebas

```bash
docker compose --file ../../infrastructure/services/product-catalog-service.yaml --env-file ../../infrastructure/.env --profile test up -d product-catalog-test-db
pytest                                  # unitarias, contrato, API y salud
pytest -m performance -o addopts=""     # volumen: 500 000 productos (SC-002, SC-003)
```

- Las pruebas ordinarias no necesitan Keycloak ni Party Identity: los tokens se firman con una clave
  RSA temporal y el fabricante se valida contra un doble (`tests/conftest.py`).
- `tests/contract/test_migrations.py` aplica y revierte las migraciones desde cero.
- `tests/api/test_security_matrix.py` exige `401` y `403` en todas las rutas bajo `/api/v1`.
- `tests/api/test_openapi_contract.py` compara el OpenAPI con el contrato.
- `tests/examples/` ejecuta los ejercicios de `docs/ejemplo/` (Principio XXII, puerta de calidad 11):
  cada ejercicio en una base nueva y los cinco en la misma base; verifica el permiso de cada URL
  contra la plantilla del realm, que cada usuario de prueba sin permiso reciba `403` y que los de
  lectura puedan consultar; exige que `docs/ejemplo/` coincida con lo generado y que no haya
  secretos. Tras cambiar un ejercicio, un contrato o el realm, regenere la documentación con
  `PRODUCT_CATALOG_EXAMPLES_WRITE=1 pytest tests/examples` y revise el diff.
- Marcador `integration`: `tests/integration/test_party_identity_integration.py` valida el
  fabricante contra Party Identity y Keycloak reales (alta y cambio con organización existente,
  `422 MANUFACTURER_NOT_FOUND` en alta y modificación sin alterar el producto, `X-Trace-Id`
  propagado). Se ejecuta con `pytest -m integration` contra el entorno integrado
  (`infrastructure/`): Product Catalog `8103`, Party Identity `8101`, Geography `8102`, Keycloak
  `8081`; se cambian con `PRODUCT_CATALOG_INTEGRATION_BASE_URL`,
  `PARTY_IDENTITY_INTEGRATION_BASE_URL` (con `/api/v1`), `GEOGRAPHY_INTEGRATION_BASE_URL` y
  `KEYCLOAK_TOKEN_URL`. La contraseña de `admin.test` se lee de `KEYCLOAK_TEST_USER_PASSWORD` o de
  `infrastructure/.env`. Es repetible: cada ejecución crea organizaciones y un producto ficticios
  de validación. La caída del proveedor (`503 DEPENDENCY_UNAVAILABLE`) se verifica a mano
  deteniendo `sio-party-identity-service`.

## Disponibilidad de la base

Regla de la Constitución 2.4.0 (Principio X), feature 009:

- La conexión a PostgreSQL tiene un tiempo de espera de 5 s y el pool descarta las conexiones rotas
  antes de usarlas (`pool_pre_ping`).
- Si la base no está disponible: `/health/live` sigue en `200`, `/health/ready` responde `503` y los
  endpoints que usan la base responden `503` `PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE` con `dependency:
  "database"`, `trace_id` y sin detalles internos (la causa queda en el log).
- Solo la pérdida o indisponibilidad de la conexión produce ese `503` (conexión rechazada o perdida,
  tiempo agotado, SQLSTATE `08xxx`, `57P01`, `57P02`, `57P03`). Un *deadlock*, un fallo de
  serialización, una sentencia cancelada o un bloqueo no disponible conservan su respuesta
  (`500 PRODUCT_CATALOG.INTERNAL_ERROR`); integridad, validación y versión conservan `409`/`422`.
- Cuando la base vuelve, el servicio se recupera solo, sin reiniciarse.
- En Docker la base `sio-product-catalog-db` tiene `healthcheck` y `restart: unless-stopped`, y la aplicación
  arranca cuando la base está sana (`infrastructure/services/product-catalog-service.yaml`).

Validación en el entorno integrado (detiene la base temporalmente; solo lecturas con `admin.test` y
`KEYCLOAK_TEST_USER_PASSWORD` del entorno o de `infrastructure/.env`):

```bash
pytest -m integration -o addopts="" tests/integration/test_database_outage_recovery.py
```

Cubre una caída prolongada (`docker stop`) y una caída inesperada de PostgreSQL (reinicio por Docker),
contra `http://localhost:8103` (`PRODUCT_CATALOG_INTEGRATION_BASE_URL`). Si se interrumpe con la
base detenida: `docker start sio-product-catalog-db`.

## Consumo de la API

- Prefijo `/api/v1`; errores RFC 9457 (`application/problem+json`) con `code` y `trace_id`; cabecera
  `X-Trace-Id` en toda respuesta.
- Concurrencia optimista: `version` en el cuerpo de `PUT` y de las acciones; `?version=` en el único
  `DELETE` (retiro de un valor de atributo). Una versión desactualizada devuelve `409`.
- Nada se borra salvo los valores de atributo: se inactiva y reactiva con `POST …/deactivate`, que
  exige el permiso `deactivate` del recurso dueño.
- Completitud y elegibilidad: se calculan en cada consulta (`completeness`, `eligible_for_adoption`)
  y nunca se guardan. Solo un producto `ACTIVE` y completo puede adoptarse.
- Primer uso: `POST /api/v1/products/{id}/first-use` (permiso `first-use:register`, servicios que
  adoptan) y `…/first-use/manual` (permiso `first-use:register-manual`). La marca es irreversible y
  bloquea la unidad base y la equivalencia física de la presentación.

## Permisos

Roles de cliente `sio-api` (plantilla `infrastructure/keycloak/realm-template/sio-realm.template.json`):

| Recurso                                                                                                  | Acciones                                           |
| -------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `units-of-measure`, `packaging-types`, `brands`, `categories`, `attribute-definitions`, `group-types`    | `read`, `create`, `update`, `deactivate`           |
| `products` (incluye categorías, valores, presentaciones, identificadores, grupos y activos del producto) | `read`, `create`, `update`, `deactivate`, `delete` |
| `first-use`                                                                                              | `register`, `register-manual`                      |
