Aquí tienes los **comandos para desplegar los 12 microservicios de SIO en tu VPS de Hostinger**, utilizando Docker Compose.

### 1. Primero, actualiza el repositorio

Ejecuta desde la VPS:

```bash
cd /opt/proyecto_sio/sio-back-end
git pull
```
Desde la raíz del proyecto:

```bash
cd /opt/proyecto_sio/sio-back-end
```

### 1. Crear todos los `.env.vps`

```bash
for dir in services/*/; do
  if [ -f "${dir}.env.vps.example" ] && [ ! -f "${dir}.env.vps" ]; then
    cp "${dir}.env.vps.example" "${dir}.env.vps"
  fi
done
```

### 2. Abrir cada archivo con Nano

```bash
nano services/party-identity-service/.env.vps
nano services/geography-service/.env.vps
nano services/product-catalog-service/.env.vps
nano services/operational-context-service/.env.vps
nano services/payment-reference-service/.env.vps
nano services/commercial-relationship-service/.env.vps
nano services/purchase-service/.env.vps
nano services/sales-service/.env.vps
nano services/inventory-service/.env.vps
nano services/audit-service/.env.vps
nano services/product-inventory-query-service/.env.vps
nano services/business-reporting-service/.env.vps
```

Ejecuta **un comando Nano a la vez** para configurar cada servicio.

### 3. Proteger los archivos

```bash
chmod 600 services/*/.env.vps
```

**Recuerda:** cambia los valores `CHANGE_ME`, configura las credenciales PostgreSQL y establece:

```dotenv
SIO_DOCS_ENABLED=true
```

**Antes de desplegar:** cada servicio debe tener su archivo `.env.vps` configurado con las credenciales PostgreSQL, la configuración de Keycloak y `SIO_DOCS_ENABLED=true` si quieres habilitar Swagger.

### 2. Comandos de despliegue por microservicio

Puedes ejecutar cada comando de forma independiente desde la raíz del proyecto.

#### 1. Party Identity Service — Puerto 8101

```bash
docker compose -f services/party-identity-service/docker-compose.vps.yml --env-file services/party-identity-service/.env.vps up -d --build
```
```bash
nano services/party-identity-service/.env.vps
```

#### 2. Geography Service — Puerto 8102

```bash
docker compose -f services/geography-service/docker-compose.vps.yml --env-file services/geography-service/.env.vps up -d --build
```

```bash
nano services/geography-service/.env.vps
```
#### 3. Product Catalog Service — Puerto 8103

```bash
docker compose -f services/product-catalog-service/docker-compose.vps.yml --env-file services/product-catalog-service/.env.vps up -d --build
```

```bash
nano services/product-catalog-service/.env.vps
```

#### 4. Operational Context Service — Puerto 8104

```bash
docker compose -f services/operational-context-service/docker-compose.vps.yml --env-file services/operational-context-service/.env.vps up -d --build
```

```bash
nano services/operational-context-service/.env.vps
```

#### 5. Payment Reference Service — Puerto 8105

```bash
docker compose -f services/payment-reference-service/docker-compose.vps.yml --env-file services/payment-reference-service/.env.vps up -d --build
```

```bash
nano services/payment-reference-service/.env.vps
```

#### 6. Commercial Relationship Service — Puerto 8106

```bash
docker compose -f services/commercial-relationship-service/docker-compose.vps.yml --env-file services/commercial-relationship-service/.env.vps up -d --build
```

```bash
nano services/commercial-relationship-service/.env.vps
```

#### 7. Purchase Service — Puerto 8107

```bash
docker compose -f services/purchase-service/docker-compose.vps.yml --env-file services/purchase-service/.env.vps up -d --build
```

```bash
nano services/purchase-service/.env.vps
```

#### 8. Sales Service — Puerto 8108

```bash
docker compose -f services/sales-service/docker-compose.vps.yml --env-file services/sales-service/.env.vps up -d --build
```

```bash
nano services/sales-service/.env.vps
```

#### 9. Inventory Service — Puerto 8109

```bash
docker compose -f services/inventory-service/docker-compose.vps.yml --env-file services/inventory-service/.env.vps up -d --build
```

```bash
nano services/inventory-service/.env.vps
```

#### 10. Audit Service — Puerto 8110

```bash
docker compose -f services/audit-service/docker-compose.vps.yml --env-file services/audit-service/.env.vps up -d --build
```

```bash
nano services/audit-service/.env.vps
```

#### 11. Product Inventory Query Service — Puerto 8112

```bash
docker compose -f services/product-inventory-query-service/docker-compose.vps.yml --env-file services/product-inventory-query-service/.env.vps up -d --build
```

```bash
nano services/product-inventory-query-service/.env.vps
```

#### 12. Business Reporting Service — Puerto 8113

```bash
docker compose -f services/business-reporting-service/docker-compose.vps.yml --env-file services/business-reporting-service/.env.vps up -d --build
```

```bash
nano services/business-reporting-service/.env.vps
```
---

### 3. URLs HTTPS de las APIs

Una vez desplegados y configurados correctamente en Traefik:

| Microservicio | Swagger |
|---|---|
| Party Identity | https://party.2.25.76.203.sslip.io/docs |
| Geography | https://geography.2.25.76.203.sslip.io/docs |
| Product Catalog | https://products.2.25.76.203.sslip.io/docs |
| Operational Context | https://operational.2.25.76.203.sslip.io/docs |
| Payment Reference | https://payments.2.25.76.203.sslip.io/docs |
| Commercial Relationship | https://commercial.2.25.76.203.sslip.io/docs |
| Purchase | https://purchases.2.25.76.203.sslip.io/docs |
| Sales | https://sales.2.25.76.203.sslip.io/docs |
| Inventory | https://inventory.2.25.76.203.sslip.io/docs |
| Audit | https://audit.2.25.76.203.sslip.io/docs |
| Product Inventory Query | https://product-inventory.2.25.76.203.sslip.io/docs |
| Business Reporting | https://reports.2.25.76.203.sslip.io/docs |

Estas son las URL configuradas, no una confirmación de que todos los servicios ya estén disponibles.

### 4. Verificar los contenedores

Después de desplegar, ejecuta:

```bash
docker ps
```

Para revisar los logs de un servicio:

```bash
docker logs sio-geography-service --tail 50
```

Si el nombre del contenedor es diferente, consulta el nombre real mediante `docker ps`.

Para probar la salud de Geography:

```bash
curl -i https://geography.2.25.76.203.sslip.io/health/live
```

### 5. Orden recomendado de despliegue

Para SIO, recomiendo iniciar en este orden:

1. Keycloak (ya desplegado).
2. Geography.
3. Party Identity.
4. Product Catalog.
5. Operational Context.
6. Payment Reference.
7. Commercial Relationship.
8. Audit.
9. Inventory.
10. Purchase.
11. Sales.
12. Product Inventory Query.
13. Business Reporting.

Este es un orden sugerido para facilitar el diagnóstico, no una garantía de que todas las dependencias estén resueltas.

**Importante:** no ejecutes todos los despliegues simultáneamente. Es preferible iniciar cada servicio, comprobar que esté saludable y continuar con el siguiente. Así podrás identificar rápidamente cualquier problema de conexión con PostgreSQL, Keycloak u otros microservicios.