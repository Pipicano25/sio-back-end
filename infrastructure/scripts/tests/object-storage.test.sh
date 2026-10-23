#!/usr/bin/env bash
#
# Pruebas del almacenamiento de objetos (infrastructure/services/object-storage.yaml).
#
#   bash infrastructure/scripts/tests/object-storage.test.sh          # estáticas (configuración)
#   bash infrastructure/scripts/tests/object-storage.test.sh --live   # + MinIO efímero aislado
#
# --live levanta un MinIO EFÍMERO (contenedor sio-objstore-test-*, red propia, datos en tmpfs,
# credenciales aleatorias que no se imprimen) con la misma imagen y el mismo bootstrap; no toca
# el contenedor ni el volumen reales y lo elimina al terminar.

set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$TEST_DIR/../.." && pwd)"
COMPOSE_FILE="$INFRA_DIR/services/object-storage.yaml"
BOOTSTRAP="$INFRA_DIR/object-storage/bootstrap.sh"
FAILURES=0

pass() { printf 'OK     %s\n' "$1"; }
failed() { printf 'FALLA  %s\n' "$1"; FAILURES=$((FAILURES + 1)); }
expect() { if eval "$2"; then pass "$1"; else failed "$1"; fi; }

random() { head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c "${1:-24}"; }

# --- Estáticas: configuración renderizada con valores ficticios --------------------------
ENV_TMP="$(mktemp)"
trap 'rm -f "$ENV_TMP"' EXIT
cat > "$ENV_TMP" <<EOF
MINIO_ROOT_USER=u$(random 10)
MINIO_ROOT_PASSWORD=p$(random 30)
PRODUCT_CATALOG_ASSET_STORAGE_ACCESS_KEY=pc$(random 10)
PRODUCT_CATALOG_ASSET_STORAGE_SECRET_KEY=s$(random 30)
MIGRATION_ASSET_STORAGE_ACCESS_KEY=mg$(random 10)
MIGRATION_ASSET_STORAGE_SECRET_KEY=s$(random 30)
EOF
CONFIG="$(docker compose --project-name object-storage --file "$COMPOSE_FILE" --env-file "$ENV_TMP" --profile bootstrap config --format json 2>/dev/null)"
expect "compose válido" '[ -n "$CONFIG" ]'
q() { python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(eval(sys.argv[2]))" "$CONFIG" "$1"; }
IMAGE="$(q "d['services']['object-storage']['image']")"
expect "imagen fijada por digest" '[[ "$IMAGE" == *@sha256:* ]]'
expect "API solo en 127.0.0.1:9002" '[ "$(q "[p for p in d[\"services\"][\"object-storage\"][\"ports\"] if p[\"target\"]==9000][0][\"host_ip\"]")" = 127.0.0.1 ] && [ "$(q "[p for p in d[\"services\"][\"object-storage\"][\"ports\"] if p[\"target\"]==9000][0][\"published\"]")" = 9002 ]'
expect "consola solo en 127.0.0.1:9003" '[ "$(q "[p for p in d[\"services\"][\"object-storage\"][\"ports\"] if p[\"target\"]==9001][0][\"host_ip\"]")" = 127.0.0.1 ] && [ "$(q "[p for p in d[\"services\"][\"object-storage\"][\"ports\"] if p[\"target\"]==9001][0][\"published\"]")" = 9003 ]'
expect "volumen persistente con nombre fijo" '[ "$(q "d[\"volumes\"][\"object_storage_data\"][\"name\"]")" = sio-object-storage-data ]'
expect "healthcheck definido" '[ "$(q "d[\"services\"][\"object-storage\"][\"healthcheck\"][\"test\"]")" != None ]'
expect "bootstrap solo con perfil explícito" '[ "$(q "d[\"services\"][\"object-storage-bootstrap\"][\"profiles\"]")" = "['"'"'bootstrap'"'"']" ]'
expect "sin credenciales en el archivo versionado" '! grep -qE "(ROOT_USER|ROOT_PASSWORD|ACCESS_KEY|SECRET_KEY):[[:space:]]+[A-Za-z0-9]" "$COMPOSE_FILE"'
expect "credenciales obligatorias (falla clara sin .env)" '! docker compose --project-name object-storage --file "$COMPOSE_FILE" --env-file /dev/null config >/dev/null 2>&1'
expect "rebuild-all no borra el volumen (--full)" 'grep -q "PRESERVED_VOLUME_PROJECTS=(object-storage)" "$INFRA_DIR/scripts/rebuild-all.sh"'
expect "reset-business-data no toca el almacenamiento" '! grep -qiE "object-storage|minio" "$INFRA_DIR/scripts/reset-business-data.sh"'
expect "bootstrap: bucket privado y sin DeleteObject" 'grep -q "anonymous set none" "$BOOTSTRAP" && ! grep -q "DeleteObject\"" "$BOOTSTRAP"'

# --- Live: MinIO efímero ----------------------------------------------------------------
if [ "${1:-}" = --live ]; then
    SUFFIX="$(random 6 | tr 'A-Z' 'a-z')"
    NET="sio-objstore-test-$SUFFIX"
    SERVER="sio-objstore-test-$SUFFIX"
    ROOT_USER="r$(random 12)"; ROOT_PASS="$(random 32)"
    PC_KEY="pc$(random 10)"; PC_SECRET="$(random 32)"
    MG_KEY="mg$(random 10)"; MG_SECRET="$(random 32)"
    BUCKET=sio-product-assets
    cleanup() { docker rm -f "$SERVER" >/dev/null 2>&1; docker network rm "$NET" >/dev/null 2>&1; rm -f "$ENV_TMP"; }
    trap cleanup EXIT
    docker network create "$NET" >/dev/null
    docker run -d --name "$SERVER" --network "$NET" --network-alias object-storage --tmpfs /data \
        -e MINIO_ROOT_USER="$ROOT_USER" -e MINIO_ROOT_PASSWORD="$ROOT_PASS" -e MC_CONFIG_DIR=/tmp/.mc \
        "$IMAGE" server /data --address :9000 >/dev/null
    for _ in $(seq 1 30); do docker exec "$SERVER" mc ready local >/dev/null 2>&1 && break; sleep 1; done
    expect "servidor saludable (healthcheck mc ready)" 'docker exec "$SERVER" mc ready local >/dev/null 2>&1'

    bootstrap() {
        docker run --rm --network "$NET" -v "$INFRA_DIR/object-storage:/bootstrap:ro" --entrypoint /bin/sh \
            -e OBJECT_STORAGE_URL=http://object-storage:9000 -e OBJECT_STORAGE_BUCKET="$BUCKET" -e MC_CONFIG_DIR=/tmp/.mc \
            -e MINIO_ROOT_USER="$ROOT_USER" -e MINIO_ROOT_PASSWORD="$ROOT_PASS" \
            -e PRODUCT_CATALOG_ASSET_STORAGE_ACCESS_KEY="$PC_KEY" -e PRODUCT_CATALOG_ASSET_STORAGE_SECRET_KEY="$PC_SECRET" \
            -e MIGRATION_ASSET_STORAGE_ACCESS_KEY="$MG_KEY" -e MIGRATION_ASSET_STORAGE_SECRET_KEY="$MG_SECRET" \
            "$IMAGE" /bootstrap/bootstrap.sh
    }
    out1="$(bootstrap 2>&1)"; rc1=$?
    out2="$(bootstrap 2>&1)"; rc2=$?
    expect "bootstrap correcto" '[ $rc1 -eq 0 ] && grep -q "Bootstrap del almacenamiento de objetos completo" <<< "$out1"'
    expect "bootstrap idempotente (segunda ejecución)" '[ $rc2 -eq 0 ]'
    expect "bootstrap sin errores de herramientas faltantes" '! grep -q "command not found" <<< "$out1$out2"'
    expect "la segunda ejecución no vuelve a asociar políticas" '[ "$(grep -c "política" <<< "$out2")" -ge 2 ]'
    expect "bootstrap no imprime credenciales" '! grep -qE "$ROOT_PASS|$PC_SECRET|$MG_SECRET" <<< "$out1$out2"'

    as() {  # as <access> <secret> <comando mc...>
        local access=$1 secret=$2; shift 2
        docker exec -e MC_HOST_t="http://$access:$secret@localhost:9000" "$SERVER" mc "$@"
    }
    docker exec "$SERVER" sh -c 'printf "contenido-de-prueba" > /tmp/obj.png'
    expect "migración puede escribir en assets/" 'as "$MG_KEY" "$MG_SECRET" cp /tmp/obj.png "t/$BUCKET/assets/abc.png" >/dev/null 2>&1'
    expect "subida repetida de la misma clave no duplica objetos" 'as "$MG_KEY" "$MG_SECRET" cp /tmp/obj.png "t/$BUCKET/assets/abc.png" >/dev/null 2>&1 && [ "$(as "$MG_KEY" "$MG_SECRET" ls "t/$BUCKET/assets/" | wc -l)" = 1 ]'
    expect "migración no puede borrar" '! as "$MG_KEY" "$MG_SECRET" rm "t/$BUCKET/assets/abc.png" >/dev/null 2>&1'
    expect "migración no puede escribir fuera de assets/" '! as "$MG_KEY" "$MG_SECRET" cp /tmp/obj.png "t/$BUCKET/otro/abc.png" >/dev/null 2>&1'
    expect "Product Catalog puede leer assets/" '[ "$(as "$PC_KEY" "$PC_SECRET" cat "t/$BUCKET/assets/abc.png")" = contenido-de-prueba ]'
    # Spec 024: Product Catalog escribe las imágenes cargadas por la API, pero nunca borra ni sale de assets/.
    expect "Product Catalog puede escribir en assets/" 'as "$PC_KEY" "$PC_SECRET" cp /tmp/obj.png "t/$BUCKET/assets/x.png" >/dev/null 2>&1'
    expect "Product Catalog no puede borrar" '! as "$PC_KEY" "$PC_SECRET" rm "t/$BUCKET/assets/x.png" >/dev/null 2>&1'
    expect "Product Catalog no puede escribir fuera de assets/" '! as "$PC_KEY" "$PC_SECRET" cp /tmp/obj.png "t/$BUCKET/otro/x.png" >/dev/null 2>&1'
    expect "Product Catalog queda solo con sio-assets-write" '[[ "$(docker exec -e MC_HOST_r="http://$ROOT_USER:$ROOT_PASS@localhost:9000" "$SERVER" mc admin user info r "$PC_KEY")" != *sio-assets-read* ]]'
    status="$(docker run --rm --network "$NET" python:3.13-slim python -c "
import urllib.request, urllib.error
try:
    print(urllib.request.urlopen('http://object-storage:9000/$BUCKET/assets/abc.png', timeout=10).status)
except urllib.error.HTTPError as e:
    print(e.code)" 2>/dev/null)"
    anon_policy="$(MC_HOST_r="http://$ROOT_USER:$ROOT_PASS@localhost:9000" docker exec -e MC_HOST_r="http://$ROOT_USER:$ROOT_PASS@localhost:9000" "$SERVER" mc anonymous get "r/$BUCKET" 2>/dev/null | awk '{print $NF}')"
    expect "bucket sin acceso anónimo" '[[ "$anon_policy" == *private* || "$anon_policy" == *none* ]]'
    expect "lectura anónima rechazada (HTTP 403)" '[ "$status" = 403 ]'
fi

echo
[ "$FAILURES" -eq 0 ] && echo "Resultado: todas las pruebas pasaron." || { echo "Resultado: $FAILURES fallidas."; exit 1; }
