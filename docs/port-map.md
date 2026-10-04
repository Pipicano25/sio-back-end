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
3. Cada entorno tiene su propio rango, de modo que el entorno integrado y los
   entornos independientes de cada servicio pueden estar levantados a la vez.
4. Los nombres de contenedor son únicos por entorno: el integrado usa
   `sio-<servicio>` / `sio-<servicio>-db`; el independiente usa
   `sio-<servicio>-service-dev` / `sio-<servicio>-dev-db` /
   `sio-<servicio>-test-db`. Así `rebuild-all.sh` nunca encuentra un
   contenedor ajeno con su mismo nombre.
5. Las bases se publican solo en `127.0.0.1`.

## Entornos

| Entorno | Archivo compose | Archivo de variables | Rango API | Rango BD | Rango BD pruebas |
|---|---|---|---|---|---|
| Integrado | `infrastructure/compose.yaml` (proyecto `sio`: Keycloak, RabbitMQ) + `infrastructure/services/<servicio>.yaml` (proyecto `sio-<servicio>`: su base y su API) — `rebuild-all.sh` | `infrastructure/.env` | `8101–8111` | `5440–5450` | — (no tiene) |
| Independiente por servicio | `services/<servicio>/docker-compose.yml` | `services/<servicio>/.env` | `8000–8010` | `55432–55452` (pares con su prueba) | idem |

El entorno independiente no levanta Keycloak: usa el del entorno integrado a
través del host (`host.docker.internal:${KEYCLOAK_HTTP_PORT}`).

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

## Microservicios — entorno integrado (`infrastructure/.env`)

| Servicio | Contenedor API | Variable API | API | Contenedor BD | Variable BD | BD |
|---|---|---|---|---|---|---|
| party-identity-service | `sio-party-identity-service` | `PARTY_IDENTITY_SERVICE_PORT` | `8101` | `sio-party-identity-db` | `PARTY_IDENTITY_DB_PORT` | `5441` |
| geography-service | `sio-geography-service` | `GEOGRAPHY_SERVICE_PORT` | `8102` | `sio-geography-db` | `GEOGRAPHY_DB_PORT` | `5442` |
| product-catalog-service | `sio-product-catalog-service` | `PRODUCT_CATALOG_SERVICE_PORT` | `8103` | `sio-product-catalog-db` | `PRODUCT_CATALOG_DB_PORT` | `5444` |
| operational-context-service | `sio-operational-context-service` | `OPERATIONAL_CONTEXT_SERVICE_PORT` | `8104` | `sio-operational-context-db` | `OPERATIONAL_CONTEXT_DB_PORT` | `5440` |
| payment-reference-service | `sio-payment-reference-service` *(reservado)* | `PAYMENT_REFERENCE_SERVICE_PORT` | `8105` | `sio-payment-reference-db` | `PAYMENT_REFERENCE_DB_PORT` | `5443` |
| commercial-relationship-service | `sio-commercial-relationship-service` | `COMMERCIAL_RELATIONSHIP_SERVICE_PORT` | `8106` | `sio-commercial-relationship-db` | `COMMERCIAL_RELATIONSHIP_DB_PORT` | `5445` |
| purchase-service | *(reservado)* | `PURCHASE_SERVICE_PORT` | `8107` | `sio-purchase-db` | `PURCHASE_DB_PORT` | `5446` |
| sales-service | *(reservado)* | `SALES_SERVICE_PORT` | `8108` | `sio-sales-db` | `SALES_DB_PORT` | `5447` |
| inventory-service | *(reservado)* | `INVENTORY_SERVICE_PORT` | `8109` | `sio-inventory-db` | `INVENTORY_DB_PORT` | `5448` |
| audit-service | *(reservado)* | `AUDIT_SERVICE_PORT` | `8110` | `sio-audit-db` | `AUDIT_DB_PORT` | `5449` |
| workflow-service | *(reservado)* | `WORKFLOW_SERVICE_PORT` | `8111` | `sio-workflow-db` | `WORKFLOW_DB_PORT` | `5450` |

*(reservado)*: el servicio aún no tiene contenedor de aplicación en
`infrastructure/services/<servicio>.yaml`; el puerto queda apartado para cuando se agregue.

## Microservicios — entorno independiente (`services/<servicio>/.env`)

| Servicio | Variable API | API | Variable BD | BD | Variable BD pruebas | BD pruebas |
|---|---|---|---|---|---|---|
| geography-service | `GEOGRAPHY_SERVICE_PORT` | `8000` | `GEOGRAPHY_DB_PORT` | `55432` | `GEOGRAPHY_TEST_DB_PORT` | `55433` |
| payment-reference-service | `PAYMENT_REFERENCE_SERVICE_PORT` | `8001` | `PAYMENT_REFERENCE_DB_PORT` | `55434` | `PAYMENT_REFERENCE_TEST_DB_PORT` | `55441` *(reservado)* |
| party-identity-service | `PARTY_IDENTITY_SERVICE_PORT` | `8002` | `PARTY_IDENTITY_DB_PORT` | `55435` | `PARTY_IDENTITY_TEST_DB_PORT` | `55436` |
| product-catalog-service | `PRODUCT_CATALOG_SERVICE_PORT` | `8003` | `PRODUCT_CATALOG_DB_PORT` | `55437` | `PRODUCT_CATALOG_TEST_DB_PORT` | `55438` |
| operational-context-service | `OPERATIONAL_CONTEXT_SERVICE_PORT` | `8004` | `OPERATIONAL_CONTEXT_DB_PORT` | `55439` | `OPERATIONAL_CONTEXT_TEST_DB_PORT` | `55440` |
| commercial-relationship-service | `COMMERCIAL_RELATIONSHIP_SERVICE_PORT` | `8005` | `COMMERCIAL_RELATIONSHIP_DB_PORT` | `55442` | `COMMERCIAL_RELATIONSHIP_TEST_DB_PORT` | `55443` |
| purchase-service | `PURCHASE_SERVICE_PORT` | `8006` | `PURCHASE_DB_PORT` | `55444` | `PURCHASE_TEST_DB_PORT` | `55445` |
| sales-service | `SALES_SERVICE_PORT` | `8007` | `SALES_DB_PORT` | `55446` | `SALES_TEST_DB_PORT` | `55447` |
| inventory-service | `INVENTORY_SERVICE_PORT` | `8008` | `INVENTORY_DB_PORT` | `55448` | `INVENTORY_TEST_DB_PORT` | `55449` |
| audit-service | `AUDIT_SERVICE_PORT` | `8009` | `AUDIT_DB_PORT` | `55450` | `AUDIT_TEST_DB_PORT` | `55451` |
| workflow-service | `WORKFLOW_SERVICE_PORT` | `8010` | `WORKFLOW_DB_PORT` | `55452` | `WORKFLOW_TEST_DB_PORT` | `55453` |

Los valores de geography a operational-context son los que ya usaban el código,
las pruebas y los ejemplos (`docs/ejemplo/`); no se renumeraron para no romper
esas referencias. Los demás son asignaciones nuevas.

Nombres de contenedor del entorno independiente:

| Servicio | API | BD | BD pruebas (perfil `test`) |
|---|---|---|---|
| geography-service | `sio-geography-service-dev` | `sio-geography-dev-db` | `sio-geography-test-db` |
| payment-reference-service | `sio-payment-reference-service-dev` | `sio-payment-reference-dev-db` | — |
| party-identity-service | `sio-party-identity-service-dev` | `sio-party-identity-dev-db` | `sio-party-identity-test-db` |
| product-catalog-service | `sio-product-catalog-service-dev` | `sio-product-catalog-dev-db` | `sio-product-catalog-test-db` |
| operational-context-service | `sio-operational-context-service-dev` | `sio-operational-context-dev-db` | `sio-operational-context-test-db` |
| commercial-relationship-service | `sio-commercial-relationship-service-dev` | `sio-commercial-relationship-dev-db` | `sio-commercial-relationship-test-db` |

### Dependencias entre servicios en el entorno independiente

Un servicio independiente alcanza a sus proveedores por el host, con el puerto
**independiente** del proveedor. Para que no quede fijo en el compose, el
`.env` del consumidor declara la variable de puerto del proveedor con el mismo
nombre que usa el proveedor en su propio `.env`:

| Consumidor | Variables de proveedor en su `.env` |
|---|---|
| todos | `KEYCLOAK_HTTP_PORT=8081` |
| party-identity-service | `GEOGRAPHY_SERVICE_PORT=8000`, `OPERATIONAL_CONTEXT_SERVICE_PORT=8004` |
| product-catalog-service | `PARTY_IDENTITY_SERVICE_PORT=8002` |
| operational-context-service | `GEOGRAPHY_SERVICE_PORT=8000`, `PARTY_IDENTITY_SERVICE_PORT=8002` |
| commercial-relationship-service | `OPERATIONAL_CONTEXT_SERVICE_PORT=8004`, `PRODUCT_CATALOG_SERVICE_PORT=8003`, `PARTY_IDENTITY_SERVICE_PORT=8002` |

Si se cambia el puerto de un proveedor, se cambia en su `.env` y en el `.env`
de cada consumidor de esta tabla (y en las `*_BASE_URL` con `localhost` que se
usan al correr el servicio fuera de Docker).

## Puertos que no se deben usar

| Puerto | Motivo |
|---|---|
| `5432` | PostgreSQL instalado localmente |
| `8080` | Servidores de desarrollo genéricos; Keycloak lo usa solo dentro del contenedor |
| `3000` | Frontend |

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
