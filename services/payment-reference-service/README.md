# payment-reference-service

Microservicio de SIO que administra los **catálogos maestros globales de pago**: tipos de condición de
pago (`CASH`, `CREDIT`, `FINANCING`) y métodos de pago (`CASH`, `BANK_TRANSFER`, `DEBIT_CARD`,
`CREDIT_CARD`, `DIGITAL_WALLET`, `CHECK`, `OTHER`). No guarda datos de ninguna empresa.

Spec 020: Purchase y Sales guardan el método declarado, así que los métodos **no se borran
físicamente** (sin `DELETE`; trigger `tr_global_payment_methods_no_delete`); se inactivan con `PUT`
(`status = INACTIVE`). GAP-PR-18 queda parcialmente resuelto (`version` sigue diferida). El catálogo no
registra pagos ni administra cartera.

- Corrección acotada y contrato vigente: `specs/008-payment-reference-condition-type-contract/`
- Contrato Provider (consulta de `GlobalPaymentConditionType` por UUID):
  `specs/008-payment-reference-condition-type-contract/contracts/payment-condition-type-provider.md`
- Línea base AS-IS y brechas abiertas:
  `specs/008-payment-reference-condition-type-contract/as-is/spec-as-is.md` y `as-is/gap-backlog.md`
- Mapa de dominio: `docs/domain-map.md`

## Entidades propias

| Entidad | Tabla |
| --- | --- |
| `GlobalPaymentConditionType` | `global_payment_condition_types` |
| `GlobalPaymentMethod` | `global_payment_methods` |

## Dependencias

| Clase | Dependencia | Uso |
| --- | --- | --- |
| A | PostgreSQL 17 propio | Persistencia de los dos catálogos |
| B | Keycloak (vía `sio-auth`) | Validación de tokens y permisos `perm:payment-reference:{recurso}:{accion}` |

No consume otros servicios ni publica eventos.

## Configuración

Copie `.env.example` a `.env` (el `.env` no se versiona). El servicio **no** lee el `.env` por sí mismo
al ejecutarse fuera de Docker: exporte las variables o use el contenedor del proyecto compose (GAP-PR-25).

| Variable | Uso | Ejemplo |
| --- | --- | --- |
| `DATABASE_URL` | Base del proyecto compose (credenciales en `infrastructure/.env`) (obligatoria) | `postgresql+psycopg://…@127.0.0.1:5443/payment_reference` |
| `SIO_DOCS_ENABLED` | Publica `/docs` y `/openapi.json` | `true` |
| `PAYMENT_REFERENCE_TEST_DATABASE_URL` | Base aislada de pruebas | puerto `55441` |
| `SIO_AUTH_ISSUER`, `SIO_AUTH_JWKS_URL`, `SIO_AUTH_AUDIENCE` | Configuración de `sio-auth` | `http://localhost:8081/realms/sio`, `sio-api` |

Si Windows reserva el puerto de alguna base (`netsh int ipv4 show excludedportrange protocol=tcp`),
cámbielo solo en su `.env` local.

## Arranque

Desde `services/payment-reference-service/` (con el proyecto `sio` levantado):

```bash
cp .env.example .env
python -m venv .venv
.venv/Scripts/activate            # Linux/macOS: source .venv/bin/activate
pip install -e ".[test]"
docker compose --file ../../infrastructure/services/payment-reference-service.yaml --env-file ../../infrastructure/.env up -d payment-reference-db
alembic upgrade head
python -m payment_reference_service.seed load
uvicorn payment_reference_service.main:app_factory --factory --port 8001
```

Con contenedor: `docker compose --file ../../infrastructure/services/payment-reference-service.yaml --env-file ../../infrastructure/.env up -d --build`
(aplicación `sio-payment-reference-service` en `http://localhost:8105`). Es el mismo proyecto compose
`payment-reference-service` que levanta `infrastructure/scripts/rebuild-all.sh`: requiere el proyecto `sio`
arriba (red `sio-network` y Keycloak). `uvicorn` fuera de Docker usa el puerto local `8001` y la
misma base del proyecto (`DATABASE_URL` del `.env`).
`GET /health/live` y `GET /health/ready` son públicos.
`rebuild-all.sh` aplica las migraciones y el `seed`.

## Migraciones

Alembic en `alembic/versions/`: `c935f548c708` (tipos de condición), `1e2923297584` (métodos) y
`4a30e958088d` (columna `version` de `global_payment_condition_types`, feature 008). Una migración ya
aplicada no se edita: las correcciones van en una migración nueva.

## Datos iniciales

`python -m payment_reference_service.seed load` carga de forma idempotente (por `code`) los 3 tipos de
condición y los 7 métodos de pago; `seed prepare` solo comprueba que existan las tablas. Audita con
`system:payment-reference-seed`.

## Pruebas

```bash
docker compose --file ../../infrastructure/services/payment-reference-service.yaml --env-file ../../infrastructure/.env --profile test up -d payment-reference-test-db
pytest
```

Las pruebas no necesitan Keycloak: firman tokens con una clave RSA temporal e inyectan ese doble con
`create_app(auth=...)`. Sin doble, la aplicación usa siempre la autenticación real (lo verifica
`tests/api/test_default_auth.py`). Cubren permisos (`401`, `403`, mínimo privilegio), ciclo de vida,
concurrencia optimista, cuerpos estrictos, contrato Provider, base caída (`503`), migraciones y `seed`.
`pytest -m integration -o addopts=""` valida contra el entorno integrado la caída y recuperación de la base
(usa Docker y `KEYCLOAK_TEST_USER_PASSWORD`).

## Consumo de la API

- Sin prefijo `/api/v1` (GAP-PR-14). Errores con el cuerpo `{"detail": …}` (RFC 9457 pendiente,
  GAP-PR-15); el `403` nunca revela el permiso exigido.
- **`/global-payment-condition-types`** (feature 008):
  - `GET` (listado y por UUID), `POST` (alta, siempre `ACTIVE`, versión 1), `PUT` (reemplazo completo con
    `version`, `code`, `name`, `description?`; no cambia `status`), `POST /{id}/deactivate` y
    `POST /{id}/reactivate` (cuerpo `{"version": n}`). **No existe `DELETE`** (`405`).
  - Cuerpos estrictos: un campo no definido (incluido `status` en el alta o el `PUT`) → `422`.
  - Versión desactualizada → `409 {"detail": …, "code": "PAYMENT_REFERENCE.VERSION_CONFLICT"}`; transición
    inválida → `409 {"detail": …, "code": "PAYMENT_REFERENCE.INVALID_STATUS_TRANSITION"}`; código duplicado →
    `409 {"detail": …}`.
- **`/global-payment-methods`**: `GET`, `POST` y `PUT` (spec 020: sin `DELETE`, `405`) (su ciclo de vida sigue pendiente,
  GAP-PR-18).
- Disponibilidad: si PostgreSQL no está disponible, `/health/live` sigue en `200`, `/health/ready` responde
  `503` y los endpoints con base responden `503 {"detail": …}` en tiempo acotado (conexión con tiempo de
  espera de 5 s); al volver la base el servicio se recupera solo. En Docker la base tiene `healthcheck` y
  reinicio automático, y la aplicación arranca cuando la base está sana.
  Solo la pérdida o indisponibilidad de la conexión produce ese `503` (conexión rechazada o perdida,
  tiempo agotado, SQLSTATE `08xxx`, `57P01`, `57P02`, `57P03`; mismo criterio que los demás servicios,
  feature 009); un *deadlock*, un fallo de serialización, una sentencia cancelada o un bloqueo no
  disponible responden `500`.
- Los consumidores del contrato Provider DEBEN usar su propio tiempo de espera finito.

## Permisos

| Operación | Permiso |
| --- | --- |
| Consultar tipos de condición | `perm:payment-reference:global_payment_condition_types:read` |
| Crear / modificar y reactivar / inactivar | `…:create` / `…:update` / `…:delete` |
| Métodos de pago | `perm:payment-reference:global_payment_methods:{read,create,update}` (spec 020: sin `delete`) |

## Brechas abiertas

Las brechas no corregidas por la feature 008 (prefijo `/api/v1`, RFC 9457 y `trace_id`, ejemplos de uso,
ciclo de vida de `GlobalPaymentMethod`, normalización de `code`, comportamiento con la base caída, entre
otras) están registradas como trabajo pendiente en
`specs/008-payment-reference-condition-type-contract/as-is/gap-backlog.md`.
