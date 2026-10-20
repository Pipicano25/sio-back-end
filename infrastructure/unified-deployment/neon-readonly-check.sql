-- Revisión de SOLO LECTURA del trabajo pendiente en Neon antes de activar los workers del
-- despliegue unificado (README.md, "Publicar en Render"). No modifica nada:
--
-- - cada bloque corre dentro de `BEGIN TRANSACTION READ ONLY` y termina en `ROLLBACK`;
--   PostgreSQL rechaza cualquier escritura dentro de esa transacción;
-- - `statement_timeout` corta cualquier consulta que tarde más de 10 s;
-- - no lee `payload` (puede contener datos de negocio): solo estados, cantidades y fechas.
--
-- Uso: con un rol de solo lectura si existe, una sesión por base, ejecutando SOLO el bloque de
-- esa base. Por ejemplo, para la base de Purchase:
--
--   sed -n '/^-- >>> purchase/,/^-- <<< purchase/p' neon-readonly-check.sql \
--     | psql "<URL de la base de purchase en Neon>" -v ON_ERROR_STOP=1
--
-- o copiando el bloque en la consola SQL de Neon. No incluya la URL ni la contraseña en archivos
-- versionados ni en el historial del shell (use PGPASSWORD en una sesión que luego se cierra).


-- >>> emisores de auditoría: party-identity, product-catalog, operational-context,
--     commercial-relationship, purchase, sales, inventory (ejecutar en CADA una de las 7 bases)
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT current_database() AS base;
-- Qué enviará el worker al arrancar: PENDING vencidos (next_attempt_at <= now()) salen en el primer ciclo.
SELECT status,
       count(*)                                          AS eventos,
       count(*) FILTER (WHERE next_attempt_at <= now())  AS vencidos_ahora,
       min(created_at)                                   AS mas_antiguo,
       max(created_at)                                   AS mas_reciente,
       max(attempts)                                     AS max_intentos
FROM audit_outbox
GROUP BY status
ORDER BY status;
-- Por qué siguen pendientes (último código HTTP y de error). 401/403 o 409/422 repetidos indican un
-- problema de identidad o de contenido que el worker reintentará con la espera máxima, no un atraso.
SELECT last_status_code, last_error_code, count(*) AS eventos, max(attempts) AS max_intentos
FROM audit_outbox
WHERE status = 'PENDING'
GROUP BY last_status_code, last_error_code
ORDER BY eventos DESC;
ROLLBACK;
-- <<< emisores de auditoría


-- >>> purchase (base de Purchase): solicitudes automáticas de precio y conciliación
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT current_database() AS base;
-- Solicitudes que purchase-price-update-worker entregará a Commercial Relationship. Cada una puede
-- producir un PRECIO NUEVO en una lista de precios real cuando CR la aplique.
SELECT status,
       count(*)                                          AS solicitudes,
       count(DISTINCT company_id)                        AS empresas,
       count(DISTINCT company_product_presentation_id)   AS presentaciones,
       min(created_at)                                   AS mas_antigua,
       max(created_at)                                   AS mas_reciente,
       max(attempts)                                     AS max_intentos
FROM purchase_price_update_outbox
GROUP BY status
ORDER BY status;
-- Pendientes por motivo del último fallo (NULL = nunca intentada).
SELECT last_error_code, count(*) AS solicitudes, max(attempts) AS max_intentos, max(last_error_at) AS ultimo_fallo
FROM purchase_price_update_outbox
WHERE status = 'PENDING'
GROUP BY last_error_code
ORDER BY solicitudes DESC;
-- Pendientes antiguas (más de 1 día): conviene confirmar con negocio antes de que se apliquen.
SELECT company_id, company_product_presentation_id, sequence, created_at, attempts, last_error_code
FROM purchase_price_update_outbox
WHERE status = 'PENDING' AND created_at < now() - interval '1 day'
ORDER BY created_at
LIMIT 50;
-- Operaciones que purchase-reconciler tomará: PENDING sin cambios hace más de 300 s
-- (PURCHASE_RECONCILER_THRESHOLD_SECONDS). Consultará Inventory por la clave y las cerrará como
-- SUCCEEDED (si Inventory la aplicó) o FAILED (si no existe allí).
SELECT operation_type,
       count(*)                                                          AS pendientes,
       count(*) FILTER (WHERE updated_at < now() - interval '300 seconds') AS las_tomara_ya,
       min(started_at)                                                   AS mas_antigua
FROM purchase_operations
WHERE status = 'PENDING'
GROUP BY operation_type
ORDER BY operation_type;
ROLLBACK;
-- <<< purchase


-- >>> sales (base de Sales): conciliación de operaciones de venta
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT current_database() AS base;
-- Operaciones que sales-reconciler tomará (umbral SALES_RECONCILER_THRESHOLD_SECONDS = 300 s).
-- Puede completarlas, marcarlas FAILED o compensarlas (revertir en Inventory una salida aplicada
-- cuya venta no se confirmó).
SELECT operation_type,
       count(*)                                                          AS pendientes,
       count(*) FILTER (WHERE updated_at < now() - interval '300 seconds') AS las_tomara_ya,
       min(started_at)                                                   AS mas_antigua
FROM sale_operations
WHERE status = 'PENDING'
GROUP BY operation_type
ORDER BY operation_type;
ROLLBACK;
-- <<< sales


-- >>> commercial-relationship (base de CR): aplicación de políticas de precio
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '10s';
SELECT current_database() AS base;
-- Aplicaciones que commercial-relationship-price-worker procesará (PENDING y FAILED vencidas).
-- Un APPLIED crea un precio nuevo y cierra el anterior en la lista.
SELECT status,
       count(*)                                          AS aplicaciones,
       count(*) FILTER (WHERE next_attempt_at <= now())  AS vencidas_ahora,
       count(DISTINCT price_list_id)                     AS listas,
       min(created_at)                                   AS mas_antigua,
       max(attempts)                                     AS max_intentos
FROM automatic_price_applications
WHERE status IN ('PENDING', 'FAILED')
GROUP BY status
ORDER BY status;
SELECT last_error_code, count(*) AS aplicaciones, max(attempts) AS max_intentos
FROM automatic_price_applications
WHERE status IN ('PENDING', 'FAILED')
GROUP BY last_error_code
ORDER BY aplicaciones DESC;
-- Solicitudes recibidas de Purchase en las últimas 24 h (contraste con el outbox de Purchase).
SELECT count(*) AS solicitudes_24h FROM automatic_price_update_requests WHERE created_at > now() - interval '1 day';
ROLLBACK;
-- <<< commercial-relationship


-- >>> conexiones (en cualquier base; repetir por proyecto de Neon)
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '10s';
SHOW max_connections;
-- Conexiones abiertas por base y estado. Con el despliegue unificado se suman, mientras está
-- despierto, hasta 11 conexiones de workers (una por worker) a las de la API.
SELECT datname, state, count(*) AS conexiones
FROM pg_stat_activity
WHERE datname IS NOT NULL
GROUP BY datname, state
ORDER BY datname, state;
ROLLBACK;
-- <<< conexiones
