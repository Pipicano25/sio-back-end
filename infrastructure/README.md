# Infraestructura de SIO

Esta carpeta contiene los recursos y la configuración necesarios para levantar los servicios externos de SIO.

## Contenido

- `compose.yaml`: proyecto compose `sio`, solo infraestructura compartida
  (Keycloak, su base, RabbitMQ) y la red `sio-network`.
- `services/<microservicio>.yaml`: un proyecto compose por microservicio
  (`sio-<microservicio>`) con su base propia y, si ya existe, su contenedor
  de aplicación. Se une a `sio-network` (externa), por eso `sio` se levanta
  primero.
- `.env.example`: plantilla de variables de entorno (una sola para todos los
  proyectos; no define `COMPOSE_PROJECT_NAME`, cada archivo declara su `name:`).
- `keycloak/`: configuración de Keycloak (Containerfile, plantilla del
  realm, realm ya renderizado, temas).
- `scripts/`: utilidades locales — `render-realm.sh` y `rebuild-all.sh`
  (regenera todos los proyectos en orden).

## Estructura de carpetas

```text
infrastructure/
├── compose.yaml                      (proyecto "sio")
├── services/
│   ├── geography-service.yaml        (proyecto "sio-geography-service")
│   ├── party-identity-service.yaml   (proyecto "sio-party-identity-service")
│   └── ...                           (uno por microservicio)
├── .env.example
├── scripts/
│   ├── rebuild-all.sh
│   └── render-realm.sh
└── keycloak/
    ├── Containerfile
    ├── realm-template/
    │   └── sio-realm.template.json   (versionado en git, con placeholders)
    ├── import/
    │   └── sio-realm.json            (generado por render-realm.sh, NO versionado)
    └── themes/
```

> Nota: no hay carpeta `postgres/` con scripts de inicialización — cada
> microservicio tiene su propia base de datos PostgreSQL independiente,
> creada directamente por su propio contenedor (variables `POSTGRES_DB` /
> `POSTGRES_USER` / `POSTGRES_PASSWORD`), sin script compartido.

## Servicios incluidos

Proyecto `sio` (`compose.yaml`):

- `keycloak`: servidor de identidad.
- `keycloak-db`: base de datos PostgreSQL de Keycloak.
- `rabbitmq`: broker de mensajería para eventos de dominio entre
  microservicios (patrón outbox/inbox).

Un proyecto `sio-<microservicio>` por microservicio (`services/`), con su
base de datos PostgreSQL **independiente** (ver `docs/port-map.md` para los
puertos) y, cuando existe, su contenedor de aplicación:

| Proyecto | Contenedores |
|---|---|
| `sio-geography-service` | `geography-db`, `geography-service` |
| `sio-party-identity-service` | `party-identity-db`, `party-identity-service` |
| `sio-product-catalog-service` | `product-catalog-db`, `product-catalog-service` |
| `sio-operational-context-service` | `operational-context-db`, `operational-context-service` |
| `sio-payment-reference-service` | `payment-reference-db` |
| `sio-commercial-relationship-service` | `commercial-relationship-db` |
| `sio-purchase-service` | `purchase-db` |
| `sio-sales-service` | `sales-db` |
| `sio-inventory-service` | `inventory-db` |
| `sio-audit-service` | `audit-db` |
| `sio-workflow-service` | `workflow-db` |

Los proyectos llevan el prefijo `sio-` para no chocar con el entorno
independiente de cada servicio (`services/<microservicio>/docker-compose.yml`),
cuyo proyecto toma el nombre de su carpeta (`geography-service`, ...).

Todos comparten la red `sio-network`, así que entre contenedores se siguen
usando los nombres de servicio (`http://keycloak:8080`,
`http://party-identity-service:8000`). `depends_on` no cruza proyectos: el
orden (primero `sio`, después los microservicios) lo garantiza
`scripts/rebuild-all.sh`.

## Requisitos previos

- Docker 24+ con Docker Compose v2.
- `python3` solo si desea formatear o validar JSON con `python3 -m json.tool`.
- Copiar la plantilla de entorno antes de ejecutar:

```bash
cp .env.example .env
```

> No se incluye la base de datos de producción ni usuarios reales. Esta infraestructura es para desarrollo/local.

Después de crear `.env`, renderiza el realm de Keycloak (obligatorio, ver
sección siguiente):

```bash
./scripts/render-realm.sh
```

## Configuración de Keycloak

El realm inicial de Keycloak se define en una **plantilla**:

- `keycloak/realm-template/sio-realm.template.json`

Keycloak no sustituye variables de entorno custom de forma confiable en su
import nativo, así que esta plantilla se renderiza a
`keycloak/import/sio-realm.json` (sin placeholders, no versionado) con
`./scripts/render-realm.sh` — ese es el archivo que Keycloak realmente
importa. Ver `keycloak/import/README.md` para el detalle completo.

El realm incluye:

- Realm `sio`
- Cliente público `sio-web`
- Recurso protegido `sio-api`
- Roles generales
- Grupos generales
- Audience mapper
- Configuración PKCE S256

No contiene datos de empresas, sucursales ni usuarios productivos.

## Comandos principales

### Levantar todo el entorno

Lo más simple es el script, que levanta `sio` y luego cada microservicio,
aplica migraciones y (en modo completo) carga los datos iniciales:

```bash
bash scripts/rebuild-all.sh --rebuild   # conserva la información
bash scripts/rebuild-all.sh --status    # estado por proyecto
```

### Levantar la infraestructura

```bash
cp .env.example .env   # si aún no existe
./scripts/render-realm.sh
docker compose --file compose.yaml --env-file .env up --build -d
```

Luego, cada microservicio en su propio proyecto (requiere `sio` arriba, por
la red `sio-network` y Keycloak):

```bash
docker compose --file services/geography-service.yaml --env-file .env up --build -d
```

Los comandos de las secciones siguientes aplican igual a cualquier
`services/<microservicio>.yaml`.

Para levantar solo Keycloak (y su base de datos, por dependencia):

```bash
docker compose --file compose.yaml --env-file .env up --build -d keycloak
```

### Listar servicios en ejecución

```bash
docker compose --file compose.yaml --env-file .env ps
```

## Detener servicios

### Parar servicios (mantener contenedores)

```bash
docker compose --file compose.yaml --env-file .env stop
```

### Iniciar servicios detenidos

```bash
docker compose --file compose.yaml --env-file .env start
```

### Detener y eliminar contenedores sin eliminar datos

```bash
docker compose --file compose.yaml --env-file .env down
```

### Forzar recreación del contenedor de Keycloak DB

```bash
docker compose --file compose.yaml --env-file .env up -d --force-recreate keycloak-db
```

## Validación de configuración

Verificar que el archivo `docker compose` sea válido:

```bash
docker compose --file compose.yaml --env-file .env config
```

### Verificar OpenID Connect

```bash
curl http://localhost:8081/realms/sio/.well-known/openid-configuration
```

Formatear la respuesta JSON (requiere Python):

```bash
curl -s http://localhost:8081/realms/sio/.well-known/openid-configuration | python3 -m json.tool
```

### Verificar el health check de Keycloak

```bash
curl http://localhost:9000/health/ready
```

## Gestión de volúmenes

Cada base de datos tiene su propio volumen nombrado
`sio-<microservicio>-db-data` (ver `services/<microservicio>.yaml`), más
`sio-keycloak-db-data` y `sio-rabbitmq-data`.

Para eliminar únicamente el volumen de Keycloak:

```bash
docker volume rm sio-keycloak-db-data
```

Para eliminar el volumen de un microservicio en particular (ejemplo con
`operational-context`):

```bash
docker volume rm sio-operational-context-db-data
```

Después, levanta de nuevo los servicios:

```bash
docker compose --file services/operational-context-service.yaml --env-file .env up --build -d
```

## URLs de administración

- Keycloak Admin: `http://localhost:8081/admin/master/console/`
- Keycloak Account: `http://localhost:8081/realms/sio/account/`

### Usuarios de ejemplo

| Usuario           |
| ----------------- |
| `admin.test`      |
| `supervisor.test` |
| `compras.test`    |
| `ventas.test`     |
| `inventario.test` |
| `reportes.test`   |
| `consulta.test`   |

## Notas adicionales

- El servicio `keycloak` se construye desde `keycloak/Containerfile`.
- El servicio `keycloak` importa automáticamente el realm definido en `keycloak/import/`.
- Las contraseñas de ejemplo deben cambiarse antes de usar la infraestructura en un entorno compartido.
