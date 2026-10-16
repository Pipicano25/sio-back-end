# commercial-relationship-service

Microservicio de SIO que es la **fuente de verdad de la relación comercial de cada empresa** con
productos, clientes y proveedores (Fase A, núcleo) y de su configuración comercial: presentaciones,
productos de proveedor, condiciones de pago y listas de precios (Fase B, producto comercial). Guarda solo
lo que pertenece a la empresa (códigos internos, nombres visibles, precios por presentación, banderas, vigencias,
estado); la identidad del producto, de la presentación, de la persona, de la organización y del tipo de
condición de pago vive en su servicio dueño y aquí solo se guarda su UUID.

- Spec, plan y contratos: `specs/007-commercial-relationship-core/` (Fase A) y
  `specs/010-commercial-relationship-commercial-product/` (Fase B); precios automáticos por recepción de compras en
  `specs/021-automatic-purchase-pricing/` (ver [Precios automáticos](#precios-automáticos-spec-021))
- Contrato REST: `contracts/rest-api.md` de ambas features (la 010 amplía la 007 sin cambiarla)
- Errores: `contracts/errors.md` de ambas features
- Contrato Provider (consulta por UUID de las 8 entidades, por lotes de productos y presentaciones y
  precio aplicable para Purchase, Sales e Inventory): `contracts/commercial-relationship-provider.md` de
  ambas features
- Mapa de dominio: `docs/domain-map.md`
- Ejemplos paso a paso con filas reales del Excel de productos, usuarios y permisos por URL:
  `docs/ejemplo/`, validados por `tests/examples/`

## Entidades propias

| Entidad           | Tabla               | Referencias externas (`UUID REF`, sin FK física)                                                  |
| ----------------- | ------------------- | ------------------------------------------------------------------------------------------------- |
| `CompanyProduct`  | `company_products`  | `company_id` (Operational Context), `global_product_id` (Product Catalog)                         |
| `CompanyCustomer` | `company_customers` | `company_id`, `person_identity_id` u `organization_identity_id`, `preferred_contact_person_id` (Party Identity) |
| `CompanySupplier` | `company_suppliers` | `company_id`, `organization_identity_id`, `preferred_contact_person_id` (Party Identity)          |
| `CompanyProductPresentation` | `company_product_presentations` | `company_id`, `global_product_presentation_id` (Product Catalog) |
| `SupplierProduct` | `supplier_products` | `company_id`, `purchase_unit_id` (Product Catalog; siempre la unidad base) |
| `SupplierPaymentCondition` | `supplier_payment_conditions` | `company_id`, `payment_condition_type_id` (Payment Reference) |
| `PriceList` | `price_lists` | `company_id` |
| `PriceListItem` | `price_list_items` | `company_id` |
| `PriceListPricingPolicy` (spec 021) | `price_list_pricing_policies` | `company_id` |
| `PriceListPricingPolicyTerm` (spec 021) | `price_list_pricing_policy_terms` | — |
| `PriceListPricingPolicyPresentation` (spec 021) | `price_list_pricing_policy_presentations` | `company_id` |
| `AutomaticPriceUpdateRequest` (spec 021) | `automatic_price_update_requests` | `company_id`, `purchase_id`, `purchase_detail_id`, `branch_id`, `received_by_user_id` (Purchase, Operational Context) |
| `AutomaticPriceApplication` (spec 021) | `automatic_price_applications` | `company_id` |

Las entidades de la Fase B se relacionan entre sí y con las de la Fase A con **FK internas compuestas
con `company_id`**: la base garantiza que todo pertenece a la misma empresa (y la presentación al mismo
producto). Estados: todas `ACTIVE`/`INACTIVE`; proveedores además `BLOCKED` (con `block_reason`
obligatorio). Nada se borra: no hay `DELETE`.

## Dependencias

| Clase | Dependencia                | Qué se consume, para qué y con qué autenticación                                                                                                                                                                                                                           |
| ----- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A     | PostgreSQL 17 propio       | Persistencia de las 8 entidades (extensión `btree_gist` para la restricción que impide precios solapados).                                                                                                                                                                  |
| B     | Keycloak (vía `sio-auth`)  | Validación de tokens y permisos `perm:commercial-relationship:{recurso}:{accion}`; emisión del token `client_credentials` del cliente técnico `commercial-relationship-service`.                                                                                            |
| C     | Operational Context        | `GET /operational-access?company_id=` (membresía `ACTIVE` y estado de la empresa, con el token del usuario) en toda ruta de usuario; `GET /me/operational-context` (empresas del usuario, en el resumen); `GET /companies/{id}` (solo `organization_identity_id`, para impedir que la empresa se relacione consigo misma y para mostrar la razón social en el resumen), con el token del usuario. |
| C     | Product Catalog            | `POST /products/batch-lookup` (al adoptar: existencia, estado y elegibilidad; al reactivar: solo estado), `POST /presentations/batch-lookup` (al adoptar o reactivar una presentación), `GET /products/{id}` (unidad base, al registrar o cambiar la unidad de un producto de proveedor) y `POST /products/{id}/first-use` (primer uso síncrono del producto o de la presentación, solo al adoptar), con la **identidad técnica propia** (`products:read`, `first-use:register`). |
| C     | Party Identity             | `GET /person-identities/{id}`, `GET /organization-identities/{id}` y `GET /organization-contact-persons/{id}` al incorporar, modificar, reactivar o desbloquear, y la razón social (`legal_name`) de cada empresa en el resumen, con el token del usuario.                                                                                  |
| C     | Payment Reference          | `GET /global-payment-condition-types/{id}` (existencia, estado y código del tipo, para validar el plazo) al registrar una condición de pago, al cambiar su tipo o su plazo y al reactivarla, con la **identidad técnica propia** (`global_payment_condition_types:read`). El código no se guarda. |

Las URL base de los proveedores **incluyen** `/api/v1`, salvo la de Payment Reference, que aún no publica el
prefijo (GAP-PR-14; al corregirse solo cambia la variable). Un proveedor caído, con tiempo agotado o con
una respuesta fuera de contrato produce `503 COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` con la
extensión `dependency` (`operational-context`, `product-catalog`, `party-identity`, `payment-reference`);
el log registra la causa interna con el mismo `trace_id`. No publica ni consume eventos (sin RabbitMQ).

**Spec 021:** CR no agrega dependencias salientes. Recibe de Purchase (clase C, consumidor) la solicitud de
actualización de precio de cada recepción por HTTP con el token `client_credentials` de `purchase-service`, validado
por Keycloak (clase B); es la excepción EXC-001 a D6, aprobada solo para esta spec. El worker de precios no hace
llamadas HTTP: solo usa la base propia (clase A). No hay dependencias de clase D.

Un único comportamiento en todos los entornos: no hay variables de "modo" (stub, fake) para los
proveedores; las pruebas inyectan dobles por la fábrica `create_app`.

## Aislamiento por empresa

- Toda ruta de usuario exige, tras el token y el permiso, membresía `ACTIVE` del usuario en la
  empresa (por la ruta o por el recurso), consultada en Operational Context. Sin membresía o con un
  UUID ajeno → `404 NOT_FOUND`, igual que un UUID inexistente. Si Operational Context responde `403`
  → `403 OPERATIONAL_ACCESS_DENIED`; si no está disponible → `503`.
- Empresa `INACTIVE`: las lecturas y las inactivaciones continúan; las demás escrituras (incluido el
  `PUT`) → `422 COMPANY_INACTIVE`.
- **Exención técnica** (solo lecturas por UUID, las consultas por lotes de productos y presentaciones y
  el precio aplicable): una identidad
  técnica (claims `client_id` y `preferred_username = service-account-{client_id}`) **con**
  `perm:commercial-relationship:platform:lookup` lee sin membresía. Un usuario humano nunca la
  obtiene, aunque tenga el permiso.

## Configuración

Copie `.env.example` a `.env` (el `.env` no se versiona).

| Variable                                                                   | Uso                                                              | Ejemplo                                       |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------- | --------------------------------------------- |
| `SIO_DOCS_ENABLED`                                                         | Publica `/docs` y `/openapi.json`                                | `true`                                        |
| `DATABASE_URL`                             | Base del proyecto compose (credenciales en `infrastructure/.env`)                                         | puerto `5445`                                |
| `COMMERCIAL_RELATIONSHIP_TEST_DATABASE_URL` | Base aislada de pruebas                                    | puerto `55443`                                |
| `SIO_AUTH_ISSUER`, `SIO_AUTH_JWKS_URL`, `SIO_AUTH_AUDIENCE`                | Configuración de `sio-auth`                                      | `http://localhost:8081/realms/sio`, `sio-api` |
| `OPERATIONAL_CONTEXT_SERVICE_BASE_URL`, `OPERATIONAL_CONTEXT_TIMEOUT_SECONDS` | Operational Context (con `/api/v1`)                           | `http://localhost:8104/api/v1`, `5`           |
| `PRODUCT_CATALOG_SERVICE_BASE_URL`, `PRODUCT_CATALOG_TIMEOUT_SECONDS`      | Product Catalog (con `/api/v1`)                                  | `http://localhost:8103/api/v1`, `5`           |
| `PARTY_IDENTITY_SERVICE_BASE_URL`, `PARTY_IDENTITY_TIMEOUT_SECONDS`        | Party Identity (con `/api/v1`)                                   | `http://localhost:8101/api/v1`, `5`           |
| `PAYMENT_REFERENCE_SERVICE_BASE_URL`, `PAYMENT_REFERENCE_TIMEOUT_SECONDS`  | Payment Reference (**sin** `/api/v1`, GAP-PR-14)                 | `http://localhost:8105`, `5`                  |
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
docker compose --file ../../infrastructure/services/commercial-relationship-service.yaml --env-file ../../infrastructure/.env up -d commercial-relationship-db
alembic upgrade head
uvicorn commercial_relationship_service.main:app --port 8005
```

Con contenedor: `docker compose --file ../../infrastructure/services/commercial-relationship-service.yaml --env-file ../../infrastructure/.env up -d --build`
(aplicación `sio-commercial-relationship-service` en `http://localhost:8106`). Es el mismo proyecto compose
`commercial-relationship-service` que levanta `infrastructure/scripts/rebuild-all.sh`: requiere el proyecto `sio`
arriba (red `sio-network` y Keycloak). `uvicorn` fuera de Docker usa el puerto local `8005` y la
misma base del proyecto (`DATABASE_URL` del `.env`).
`GET /health/live` y `GET /health/ready` son públicos; `ready` solo comprueba la base de datos.

## Migraciones

Alembic en `alembic/versions/`. La migración `0001` crea las 3 tablas de la Fase A con restricciones
nombradas (`pk_`, `uq_`, `ck_`, `ix_`), importes `NUMERIC` y unicidad de `internal_code` sin distinguir
mayúsculas por empresa, en cualquier estado. La `0002` crea las 5 tablas de la Fase B con FK internas
compuestas (`fk_`), predeterminadas como índices únicos parciales y la exclusión
`ex_price_list_items_no_overlap` (crea la extensión `btree_gist`; el rol de la base debe poder crearla),
y agrega `UNIQUE (id, company_id)` a `company_products` y `company_suppliers` sin cambio funcional. Una migración ya aplicada en un entorno compartido no
se edita: las correcciones van en una migración nueva. La `0005` (spec 021) crea las 5 tablas de precios automáticos
con exclusiones GiST y triggers de inmutabilidad, y agrega `purchase_tax_percentage` a `company_products` y `origin`,
`closure_reason` y `automatic_application_id` a `price_list_items` (anulables: las filas existentes no cambian). Su
`downgrade` se detiene si ya hay datos de la spec 021.

## Datos iniciales

No hay `seed`: productos, clientes, proveedores, presentaciones, condiciones y precios los registra cada
empresa.

## Pruebas

```bash
docker compose --file ../../infrastructure/services/commercial-relationship-service.yaml --env-file ../../infrastructure/.env --profile test up -d commercial-relationship-test-db
pytest                                     # unitarias, contrato, API, salud y ejemplos
pytest -m performance -o addopts=""        # 50 000 productos por empresa: búsqueda y precio aplicable, p95 < 1 s
pytest -m integration -o addopts=""        # proveedores y Keycloak reales (entorno integrado)
```

- Las pruebas ordinarias no necesitan Keycloak ni los proveedores: los tokens se firman con una clave
  RSA temporal y Operational Context, Product Catalog, Party Identity y Payment Reference son dobles inyectados
  (`tests/fakes.py`). Los adaptadores HTTP se prueban con `httpx.MockTransport`
  (`tests/contract/`).
- `tests/contract/test_migrations.py` aplica y revierte las migraciones desde cero.
- `tests/api/test_auth.py` y `tests/api/test_isolation.py` recorren las 55 rutas (`tests/api/routes.py`; el aislamiento del resumen se prueba en `tests/api/test_company_summaries.py`): `401`, `403`,
  `404` fuera de alcance, `403 OPERATIONAL_ACCESS_DENIED`, `503` y la exención técnica.
- `tests/api/test_openapi_contract.py` compara el OpenAPI con los contratos de la 007 y la 010.
- `tests/api/*_concurrency.py` comprueban contra la base real que nunca quedan dos predeterminadas ni dos
  precios solapados con solicitudes simultáneas.
- `tests/examples/` ejecuta los ejercicios de `docs/ejemplo/` (Principio XXII): cada uno en una base
  nueva y los seis en la misma base; verifica el permiso de cada URL contra la plantilla del realm y
  exige que `docs/ejemplo/` coincida con lo generado. Tras cambiar un ejercicio, un contrato o el
  realm, regenere con `COMMERCIAL_RELATIONSHIP_EXAMPLES_WRITE=1 pytest tests/examples` y revise el
  diff.
- Marcador `integration`: `tests/integration/test_real_dependencies.py` adopta un producto completo y
  verifica el primer uso en Product Catalog, incorpora un cliente y un proveedor contra Party
  Identity, comprueba el `404` sin membresía y el predicado de identidad técnica con tokens reales; en
  la Fase B adopta una presentación (primer uso real), registra un producto de proveedor con la unidad
  base real, condiciones de pago contra Payment Reference, una lista con `change-price` y el precio
  aplicable. Usa el entorno integrado (CR `8106`, Product Catalog `8103`, Operational Context `8104`,
  Party Identity `8101`, Geography `8102`, Payment Reference `8105`, Keycloak `8081`; variables
  `*_INTEGRATION_BASE_URL`). Requiere el realm importado con la plantilla vigente (permisos de la Fase B). La
  contraseña de `admin.test` y el secreto del cliente técnico se leen del entorno o de
  `infrastructure/.env`. Es repetible: cada ejecución crea datos ficticios de validación. La caída
  de un proveedor (`503`) se verifica a mano deteniendo su contenedor.

## Auditoría (feature 016)

Eventos de empresa (`company_id`). 35 operaciones de escritura auditadas.

Cada escritura de la API registra **un** evento de auditoría en la tabla `audit_outbox` de este
servicio, en la misma transacción que el cambio (si el cambio se revierte, el evento no existe), y el
proceso `commercial-relationship-audit-outbox-worker` (misma imagen y base; `python -m sio_audit.worker`) lo entrega a
Audit con el cliente técnico `commercial-relationship-service` (`perm:audit:audit-events:create`; `source_service =
commercial-relationship-service`). Detalle por operación en
[`specs/016-existing-services-audit/contracts/audit-actions.md`](../../specs/016-existing-services-audit/contracts/audit-actions.md).

- Solo eventos `SUCCESS`: un rechazo sin efecto (`401`, `403`, `404`, `409`, `422`, `503`) no registra
  nada; una escritura que no cambia ningún campo tampoco (DS-02, DS-05).
- Valores: en la creación, los campos de la entidad; en la edición, solo los campos que cambiaron (antes y
  después); sin `id`, `version` ni columnas `created_*`/`updated_*`.
- Audit detenido no afecta a la API: los eventos quedan `PENDING` y el worker los entrega una sola vez al
  volver (reintentos con backoff de `libs/sio-audit`, a lo sumo `AUDIT_OUTBOX_BACKOFF_MAX_SECONDS` + 60 s
  después; sin orden de llegada garantizado: el historial se ordena por `occurred_at`).
- Las cargas por `seed` no se auditan (no hay autor autenticado).
- Variables del worker: `AUDIT_CLIENT_SECRET` = `COMMERCIAL_RELATIONSHIP_CLIENT_SECRET` (solo en `infrastructure/.env`) y
  `AUDIT_OUTBOX_*` opcionales (ver `infrastructure/.env.example`).
- `change-price` registra `CHANGE_PRICE_LIST_ITEM_PRICE` sobre el ítem nuevo, con el ítem y el precio
  anteriores en `previous_values`; el bloqueo registra su motivo como `reason`. Las consultas por
  `POST` (`batch-lookup`, `applicable-prices/resolve`) no se auditan.

## Disponibilidad de la base

Regla de la Constitución 2.4.0 (Principio X), feature 009:

- La conexión a PostgreSQL tiene un tiempo de espera de 5 s y el pool descarta las conexiones rotas
  antes de usarlas (`pool_pre_ping`).
- Si la base no está disponible: `/health/live` sigue en `200`, `/health/ready` responde `503` y los
  endpoints que usan la base responden `503` `COMMERCIAL_RELATIONSHIP.DEPENDENCY_UNAVAILABLE` con `dependency:
  "database"`, `trace_id` y sin detalles internos (la causa queda en el log).
- Solo la pérdida o indisponibilidad de la conexión produce ese `503` (conexión rechazada o perdida,
  tiempo agotado, SQLSTATE `08xxx`, `57P01`, `57P02`, `57P03`). Un *deadlock*, un fallo de
  serialización, una sentencia cancelada o un bloqueo no disponible conservan su respuesta
  (`500 COMMERCIAL_RELATIONSHIP.INTERNAL_ERROR`); integridad, validación y versión conservan `409`/`422`.
- Cuando la base vuelve, el servicio se recupera solo, sin reiniciarse.
- En Docker la base `sio-commercial-relationship-db` tiene `healthcheck` y `restart: unless-stopped`, y la aplicación
  arranca cuando la base está sana (`infrastructure/services/commercial-relationship-service.yaml`).

Validación en el entorno integrado (detiene la base temporalmente; solo lecturas con `admin.test` y
`KEYCLOAK_TEST_USER_PASSWORD` del entorno o de `infrastructure/.env`):

```bash
pytest -m integration -o addopts="" tests/integration/test_database_outage_recovery.py
```

Cubre una caída prolongada (`docker stop`) y una caída inesperada de PostgreSQL (reinicio por Docker),
contra `http://localhost:8106` (`COMMERCIAL_RELATIONSHIP_INTEGRATION_BASE_URL`). Si se interrumpe con la
base detenida: `docker start sio-commercial-relationship-db`.

## Consumo de la API

- Prefijo `/api/v1`; errores RFC 9457 (`application/problem+json`) con `code`
  (`COMMERCIAL_RELATIONSHIP.*`), `trace_id` y `errors[]`; cabecera `X-Trace-Id` en toda respuesta.
- Concurrencia optimista: `version` en el cuerpo de `PUT` y de las acciones; desactualizada →
  `409 VERSION_CONFLICT`. Un `PUT` sin cambios devuelve `200` sin incrementar `version`.
- El `PUT` se acepta en cualquier estado y nunca cambia `status`; los cambios de estado son acciones
  `POST …/deactivate`, `…/reactivate`, `…/block`, `…/unblock`.
- Predeterminadas (presentación de compra y de venta, proveedor preferido, condición por moneda, lista
  por moneda): marcar una nueva retira la anterior en la misma operación (sube su `version`); inactivar
  retira la marca.
- Precios: sin solapamiento de vigencias por lista, producto y presentación (`409 PRICE_PERIOD_OVERLAP`).
  Un precio en vigencia no se reescribe: solo se cierra o pospone su fin, se inactiva o se cambia con
  `POST /api/v1/price-list-items/{id}/change-price`, que cierra el vigente y crea el nuevo en una operación.
- Precio aplicable: `POST /api/v1/companies/{company_id}/applicable-prices/resolve` con hasta 100 líneas;
  cada línea indica su presentación (spec 019) y se usa **solo** el precio explícito de esa presentación en
  la lista indicada o en la predeterminada vigente de la moneda del producto. Sin él: `NO_PRICE_IN_LIST`
  (o `NO_APPLICABLE_PRICE_LIST` si no hay lista predeterminada vigente). No hay precios generales por
  producto, respaldos ni conversiones entre presentaciones.
- Producto empresarial sin precio ni costo (spec 019, migración `0004`): `sale_price` y `reference_cost`
  no existen; enviarlos responde `422 VALIDATION_ERROR`. Los costos vienen de las compras e Inventory.
- Precios de lista: `company_product_presentation_id` obligatorio; un precio anterior sin presentación se
  conserva y se puede consultar o inactivar, pero `change-price` responde `422 PRICE_ITEM_WITHOUT_PRESENTATION`.
- Importes: entrada como número o cadena; salida siempre como cadena decimal. `currency_code` ISO 4217 de
  la lista soportada; en las monedas sin decimales (`CLP`, `PYG`, `JPY`, `KRW`) un `unit_price` con
  fracción → `422 PRICE_SCALE_NOT_ALLOWED`.
- Adopción: el producto global debe existir, estar `ACTIVE` y ser elegible; el primer uso se registra
  en Product Catalog antes de guardar. Un producto se adopta una sola vez por empresa (en cualquier
  estado: si está inactivo, se reactiva).
- Resumen de mis empresas: `GET /api/v1/company-summaries` devuelve, **una empresa por página** por
  defecto (`?page=2`, `?page_size=` hasta 100), las empresas donde el usuario tiene membresía `ACTIVE`,
  con `company_status`, razón social (`legal_name`, `null` si no es visible) y el total y el conteo por
  estado de productos, clientes y proveedores (`null` sin el permiso de lectura correspondiente). Exige
  `company_products:read`; no da alcance de plataforma.
- Consulta por lotes: `POST /api/v1/company-products/batch-lookup` y
  `POST /api/v1/company-product-presentations/batch-lookup` con hasta 100 UUID; los ausentes o fuera de
  alcance se devuelven con solo `id` y `found: false`.

## Permisos

Roles de cliente `sio-api` (plantilla `infrastructure/keycloak/realm-template/sio-realm.template.json`):

| Recurso             | `read`                  | `create`    | `update`                          | `delete`             |
| ------------------- | ----------------------- | ----------- | --------------------------------- | -------------------- |
| `company_products`  | Listar, obtener, lotes, resumen | Adoptar     | Modificar, reactivar              | Inactivar            |
| `company_customers` | Listar, obtener         | Incorporar  | Modificar, reactivar              | Inactivar            |
| `company_suppliers` | Listar, obtener         | Seleccionar | Modificar, reactivar, desbloquear | Inactivar, bloquear  |
| `company_product_presentations` | Listar, obtener, lotes | Adoptar | Modificar, reactivar | Inactivar |
| `supplier_products` | Listar, obtener | Registrar | Modificar, reactivar | Inactivar |
| `supplier_payment_conditions` | Listar, obtener | Registrar | Modificar, reactivar | Inactivar |
| `price_lists` | Listar, obtener | Crear | Modificar, reactivar | Inactivar |
| `price_list_items` | Listar, obtener, precio aplicable | Registrar | Modificar, cambiar precio, reactivar | Inactivar |
| `pricing_policies` (spec 021) | Listar, obtener, historial | Crear | Renombrar, porcentaje, presentaciones | Inactivar |
| `company_product_purchase_taxes` (spec 021) | — | — | Tasa de compra (individual y en lote) | — |
| `automatic_price_applications` (spec 021) | Listar, obtener | — | `resolve`: resolución administrativa | — |
| `automatic_price_update_requests` (spec 021) | — | `submit`: solo la identidad técnica de Purchase | — | — |

Los permisos de la spec 021 solo los tienen `administradores` y `supervisores` (los de `compras` y `ventas` se
listan explícitamente, sin comodines, para no recibirlos), salvo `automatic_price_update_requests:submit`, que es del
cliente técnico `purchase-service`.

`perm:commercial-relationship:platform:lookup` es la capacidad de consulta técnica sin membresía;
solo tiene efecto en identidades técnicas. El cliente técnico `commercial-relationship-service`
tiene `perm:product-catalog:products:read`, `perm:product-catalog:first-use:register` y
`perm:payment-reference:global_payment_condition_types:read`. Ningún usuario necesita permisos de
Payment Reference para registrar condiciones de pago.

## Precios automáticos (spec 021)

- **Políticas por lista:** una lista con al menos una política `ACTIVE` en el momento de la recepción recibe precios
  automáticos; una lista sin políticas conserva sus precios manuales. Una presentación está a lo sumo en una política
  por lista. Cambiar una política no cambia precios: rige desde la siguiente recepción.
- **Cálculo:** costo real unitario = `(subtotal − descuento + impuesto) / cantidad` de la presentación (sin volver a
  sumar el impuesto). Si baja frente a la recepción anterior, el costo de referencia es el promedio simple; si sube o
  se mantiene, el actual. Precio = costo de referencia × (1 + porcentaje/100), con los decimales de la moneda.
- **Proceso:** la ruta técnica `POST /companies/{company_id}/automatic-price-update-requests` guarda la solicitud y
  crea una aplicación por lista; el contenedor `commercial-relationship-price-worker` (misma imagen,
  `python -m commercial_relationship_service.price_worker`, `--once` y `--check`) las procesa en orden de secuencia
  por lista y presentación, cada una en su transacción, con reintentos de espera creciente y auditoría
  (`system:commercial-relationship-price-worker`). Variables: `CR_PRICE_WORKER_INTERVAL_SECONDS` (5),
  `CR_PRICE_WORKER_BATCH_SIZE` (50) y `CR_PRICE_WORKER_MAX_BACKOFF_SECONDS` (300).
- **Consulta y resolución:** `GET /companies/{company_id}/automatic-price-applications[/{id}]` y
  `POST …/{id}/resolution` (solo administradores y supervisores; exponen costos). Ejemplo: `docs/ejemplo/9-actualizaciones-automaticas/`.
- **Tasa de compra:** `PUT /company-products/{id}/purchase-tax` y `POST /companies/{company_id}/company-products/purchase-taxes/batch`;
  `null` = sin configurar, `0` = exento. Ninguna tasa se asigna automáticamente.
- **Limitación (R-12):** el precio de la lista es el importe final que paga el cliente; Sales no agrega impuesto
  (provisional, **no es una solución fiscal**). El porcentaje de la política es un recargo comercial sobre el costo
  real de compra: no es el costo contable FIFO de Inventory ni el margen que calcula Sales.

