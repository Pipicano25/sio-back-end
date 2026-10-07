# SIO — Mapa de puertos y nombres de contenedor

Fuente única de verdad de los puertos del host que usa cada microservicio y la
infraestructura compartida. Cualquier puerto nuevo se registra aquí **antes**
de usarse en un `compose`, un `.env.example` o una documentación.

Reglas:

1. Todo puerto publicado en el host sale de una **variable de entorno** del
   `.env` correspondiente; ningún `compose` lleva un puerto de host fijo
   (los valores `:-NNNN` de los compose son solo respaldo y deben coincidir
   con esta tabla).
2. El puerto **interno** del contenedor no cambia nunca: API `8000`,
   PostgreSQL `5432`, Keycloak `8080`/`9000`, RabbitMQ `5672`/`15672`.
   Entre contenedores de `sio-network` se usa siempre el interno
   (`http://party-identity-service:8000`, `geography-db:5432`).
3. Cada microservicio tiene **una sola definición Compose**:
   `infrastructure/services/<servicio>.yaml`, proyecto compose `<servicio>`
   (sin prefijo). Ahí viven su API, su base y su base de pruebas (perfil
   `test`). No existe un `docker-compose.yml` dentro de `services/<servicio>/`:
   un segundo archivo crearía un segundo proyecto (otro grupo en Docker
   Desktop) con contenedores y volúmenes propios.
4. Los nombres de contenedor son únicos: `sio-<nombre>-service` (API),
   `sio-<nombre>-db` (base) y `sio-<nombre>-test-db` (base de pruebas), donde
   `<nombre>` es el servicio sin el sufijo `-service` (p. ej. `sio-geography-db`).
5. Las bases se publican solo en `127.0.0.1`.

## Proyectos compose

| Proyecto | Archivo compose | Archivo de variables | Contenido |
|---|---|---|---|
| `sio` | `infrastructure/compose.yaml` | `infrastructure/.env` | Keycloak, su base, RabbitMQ y la red `sio-network` |
| `<servicio>` | `infrastructure/services/<servicio>.yaml` | `infrastructure/.env` | API (`8101–8111`), base (`5440–5450`) y base de pruebas (perfil `test`, `55433–55453`) |

`infrastructure/scripts/rebuild-all.sh` levanta todos los proyectos (sin el
perfil `test`). La base de pruebas se levanta a pedido, desde la raíz:

```bash
docker compose --file infrastructure/services/<servicio>.yaml --env-file infrastructure/.env --profile test up -d <servicio-sin-sufijo>-test-db
```

Antes (hasta 2026-10-05) cada servicio tenía además un entorno independiente
(`services/<servicio>/docker-compose.yml`, API `8000–8010`, base `554xx`,
contenedores `*-service-dev` / `*-dev-db`). Se retiró porque generaba un
segundo proyecto por microservicio (`geography-service` junto a
`sio-geography-service`). Las bases `554xx` de desarrollo quedan libres; los
puertos `8000–8010` se conservan solo para ejecutar la aplicación con `uvicorn`
fuera de Docker (mismo número por servicio que antes: geography `8000`,
payment-reference `8001`, party-identity `8002`, product-catalog `8003`,
operational-context `8004`, commercial-relationship `8005`), sin compose.

## Infraestructura compartida (entorno integrado)

| Componente | Contenedor | Variable | Puerto host | Interno |
|---|---|---|---|---|
| Keycloak HTTP | `sio-keycloak` | `KEYCLOAK_HTTP_PORT` | `8081` | `8080` |
| Keycloak management (health/metrics) | `sio-keycloak` | `KEYCLOAK_MANAGEMENT_PORT` | `9000` | `9000` |
| Base de Keycloak | `sio-keycloak-db` | `KEYCLOAK_DB_PORT` | `5433` | `5432` |
| RabbitMQ AMQP | `sio-rabbitmq` | `RABBITMQ_AMQP_PORT` | `5672` | `5672` |
| RabbitMQ management | `sio-rabbitmq` | `RABBITMQ_MANAGEMENT_PORT` | `15672` | `15672` |
| Frontend (origen permitido) | — | `SIO_WEB_ORIGIN` | `3000` | — |

`KEYCLOAK_PUBLIC_URL` debe usar el mismo puerto que `KEYCLOAK_HTTP_PORT`: es el
`iss` de todos los tokens.

## Microservicios (`infrastructure/.env`)

| Servicio | Contenedor API | Variable API | API | Contenedor BD | Variable BD | BD | Variable BD pruebas | BD pruebas |
|---|---|---|---|---|---|---|---|---|
| party-identity-service | `sio-party-identity-service` | `PARTY_IDENTITY_SERVICE_PORT` | `8101` | `sio-party-identity-db` | `PARTY_IDENTITY_DB_PORT` | `5441` | `PARTY_IDENTITY_TEST_DB_PORT` | `55436` |
| geography-service | `sio-geography-service` | `GEOGRAPHY_SERVICE_PORT` | `8102` | `sio-geography-db` | `GEOGRAPHY_DB_PORT` | `5442` | `GEOGRAPHY_TEST_DB_PORT` | `55433` |
| product-catalog-service | `sio-product-catalog-service` | `PRODUCT_CATALOG_SERVICE_PORT` | `8103` | `sio-product-catalog-db` | `PRODUCT_CATALOG_DB_PORT` | `5444` | `PRODUCT_CATALOG_TEST_DB_PORT` | `55438` |
| operational-context-service | `sio-operational-context-service` | `OPERATIONAL_CONTEXT_SERVICE_PORT` | `8104` | `sio-operational-context-db` | `OPERATIONAL_CONTEXT_DB_PORT` | `5440` | `OPERATIONAL_CONTEXT_TEST_DB_PORT` | `55440` |
| payment-reference-service | `sio-payment-reference-service` | `PAYMENT_REFERENCE_SERVICE_PORT` | `8105` | `sio-payment-reference-db` | `PAYMENT_REFERENCE_DB_PORT` | `5443` | `PAYMENT_REFERENCE_TEST_DB_PORT` | `55441` |
| commercial-relationship-service | `sio-commercial-relationship-service` | `COMMERCIAL_RELATIONSHIP_SERVICE_PORT` | `8106` | `sio-commercial-relationship-db` | `COMMERCIAL_RELATIONSHIP_DB_PORT` | `5445` | `COMMERCIAL_RELATIONSHIP_TEST_DB_PORT` | `55443` |
| purchase-service | `sio-purchase-service` | `PURCHASE_SERVICE_PORT` | `8107` | `sio-purchase-db` | `PURCHASE_DB_PORT` | `5446` | `PURCHASE_TEST_DB_PORT` | `55445` |
| sales-service | *(reservado)* | `SALES_SERVICE_PORT` | `8108` | `sio-sales-db` | `SALES_DB_PORT` | `5447` | `SALES_TEST_DB_PORT` | `55447` |
| inventory-service | `sio-inventory-service` | `INVENTORY_SERVICE_PORT` | `8109` | `sio-inventory-db` | `INVENTORY_DB_PORT` | `5448` | `INVENTORY_TEST_DB_PORT` | `55449` |
| audit-service | `sio-audit-service` | `AUDIT_SERVICE_PORT` | `8110` | `sio-audit-db` | `AUDIT_DB_PORT` | `5449` | `AUDIT_TEST_DB_PORT` | `55451` |
| workflow-service | *(reservado)* | `WORKFLOW_SERVICE_PORT` | `8111` | `sio-workflow-db` | `WORKFLOW_DB_PORT` | `5450` | `WORKFLOW_TEST_DB_PORT` | `55453` |

*(reservado)*: el servicio aún no tiene contenedor de aplicación en
`infrastructure/services/<servicio>.yaml`; el puerto queda apartado para cuando se agregue.
Lo mismo aplica a la base de pruebas de esos servicios.

Contenedores de la base de pruebas: `sio-<servicio-sin-sufijo>-test-db`
(p. ej. `sio-geography-test-db`), con datos en `tmpfs`.

## Puertos que no se deben usar

| Puerto | Motivo |
|---|---|
| `5432` | PostgreSQL instalado localmente |
| `8080` | Servidores de desarrollo genéricos; Keycloak lo usa solo dentro del contenedor |
| `3000` | Frontend |
| `55363–55462` (variable) | En algunos equipos Windows, Hyper-V/WinNAT excluye rangos dinámicos (`netsh interface ipv4 show excludedportrange protocol=tcp`). Si un puerto `554xx` de pruebas cae en uno, se sobrescribe su variable `*_TEST_DB_PORT` en `infrastructure/.env` local y en `*_TEST_DATABASE_URL` del `.env` del servicio |

## Diagnóstico de conflictos

```bash
# ¿Quién publica un puerto? (Docker)
docker ps -a --format '{{.Names}}\t{{.Ports}}' | grep ':8081->'

# ¿Qué proceso escucha en un puerto? (Windows / Git Bash)
netstat -ano | grep LISTENING | grep ':9000 '
```

`infrastructure/scripts/rebuild-all.sh` revisa, antes de levantar el entorno
integrado, que ningún contenedor ajeno ni otro proceso ocupe sus puertos, e
indica la variable de `infrastructure/.env` que hay que cambiar. Si se cambia
un puerto, se actualiza también esta tabla.
