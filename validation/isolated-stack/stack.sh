#!/usr/bin/env bash
# Pila de integración aislada de SIO (spec 022, T129 y T130). Uso, desde la raíz del repositorio:
#
#   bash validation/isolated-stack/stack.sh verificar   # solo valida la configuración (no crea nada)
#   bash validation/isolated-stack/stack.sh levantar    # construye, levanta, migra y carga los datos de referencia
#   bash validation/isolated-stack/stack.sh estado      # contenedores de la pila
#   bash validation/isolated-stack/stack.sh retirar     # elimina SOLO los contenedores y la red del proyecto sio-it
#   bash validation/isolated-stack/stack.sh entorno     # imprime los export de URL (sin secretos) para las pruebas
#
# Garantías (se comprueban en "verificar", que también corre antes de "levantar" y "retirar"):
# - proyecto "sio-it"; todos los contenedores "sio-it-*" con sio.integration.isolated=true;
# - una sola red, "sio-it-network"; ningún volumen con nombre (bases y objetos en tmpfs);
# - puertos publicados solo en 127.0.0.1 y en 18000-18999;
# - imágenes construidas solo con etiquetas "sio-it/…": nunca se reemplaza una imagen "sio/…" del entorno persistente;
# - secretos propios en validation/isolated-stack/.env (no versionado); nunca se leen los de infrastructure/.env.
# Nunca ejecuta "docker volume rm", "docker system prune" ni comandos sobre contenedores fuera de la pila.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
ENV_FILE="$HERE/.env"
PROJECT=sio-it
COMPOSE=(docker compose --project-name "$PROJECT" --file "$HERE/compose.yaml" --env-file "$ENV_FILE")

APP_SERVICES=(geography-service party-identity-service operational-context-service payment-reference-service
    product-catalog-service commercial-relationship-service inventory-service purchase-service sales-service
    audit-service)

say() { printf '==> %s\n' "$*"; }
fail() { printf 'Error: %s\n' "$*" >&2; exit 1; }

random() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }

ensure_env() {
    [ -f "$ENV_FILE" ] && return
    say "Generando $ENV_FILE con secretos propios de la pila (no se versiona)"
    umask 077
    {
        echo "# Generado por stack.sh: secretos SOLO de la pila aislada sio-it (no son los del entorno persistente)."
        echo "SIO_IT_TAG=spec022"
        echo "POSTGRES_VERSION=17-alpine"
        echo "KEYCLOAK_VERSION=26.7.0"
        echo "KEYCLOAK_REALM=sio"
        echo "SIO_IT_KEYCLOAK_PUBLIC_URL=http://localhost:18081"
        echo "SIO_IT_DB_USER=sio_it"
        echo "SIO_IT_DB_PASSWORD=$(random 24)"
        echo "SIO_IT_KEYCLOAK_ADMIN_USER=sio-it-admin"
        echo "SIO_IT_KEYCLOAK_ADMIN_PASSWORD=$(random 24)"
        echo "SIO_IT_MINIO_ROOT_USER=sio-it-root"
        echo "SIO_IT_MINIO_ROOT_PASSWORD=$(random 24)"
        echo "SIO_IT_PC_STORAGE_ACCESS_KEY=sio-it-pc-reader"
        echo "SIO_IT_PC_STORAGE_SECRET_KEY=$(random 24)"
        echo "SIO_IT_WRITER_STORAGE_ACCESS_KEY=sio-it-seed-writer"
        echo "SIO_IT_WRITER_STORAGE_SECRET_KEY=$(random 24)"
        echo "SIO_IT_PRODUCT_IMAGE_REF_SECRET=$(random 48)"
        echo "SIO_IT_PIQS_CURSOR_SECRET=$(random 48)"
        echo "KEYCLOAK_TEST_USER_PASSWORD=$(random 18)"
        for name in PARTY_IDENTITY OPERATIONAL_CONTEXT COMMERCIAL_RELATIONSHIP AUDIT_TEST_EMITTER INVENTORY_SERVICE \
                    INVENTORY_TEST_OPERATOR SIO_DATA_IMPORTER PURCHASE_SERVICE SALES_SERVICE PRODUCT_CATALOG_SERVICE \
                    PRODUCT_INVENTORY_QUERY_SERVICE; do
            echo "${name}_CLIENT_SECRET=$(random 32)"
        done
    } > "$ENV_FILE"
}

# Verifica la configuración renderizada antes de tocar Docker (no imprime secretos).
verify() {
    ensure_env
    say "Verificando la configuración de la pila (proyecto $PROJECT)"
    "${COMPOSE[@]}" --profile bootstrap config --format json > "$HERE/.config.json"
    python3 - "$HERE/.config.json" <<'PY'
import json, sys
config = json.load(open(sys.argv[1]))
problems = []
if config.get("name") != "sio-it":
    problems.append(f"proyecto {config.get('name')!r}")
if set(config.get("networks", {})) != {"sio-it-network"} or config["networks"]["sio-it-network"].get("name") != "sio-it-network":
    problems.append("redes distintas de sio-it-network")
if config.get("volumes"):
    problems.append(f"volúmenes con nombre: {sorted(config['volumes'])}")
for name, service in config["services"].items():
    container = service.get("container_name", "")
    if not container.startswith("sio-it-"):
        problems.append(f"{name}: contenedor {container!r}")
    if service.get("labels", {}).get("sio.integration.isolated") != "true":
        problems.append(f"{name}: sin la etiqueta de aislamiento")
    if set(service.get("networks", {})) != {"sio-it-network"}:
        problems.append(f"{name}: redes {sorted(service.get('networks', {}))}")
    for volume in service.get("volumes", []):
        if volume.get("type") != "bind" or not volume.get("read_only"):
            problems.append(f"{name}: volumen {volume.get('type')} {volume.get('target')} (solo se admiten bind de solo lectura)")
    for port in service.get("ports", []):
        published = int(port.get("published", 0))
        if port.get("host_ip") != "127.0.0.1" or not 18000 <= published <= 18999:
            problems.append(f"{name}: puerto {port.get('host_ip')}:{published}")
    if "build" in service and not service.get("image", "").startswith("sio-it/"):
        problems.append(f"{name}: construye la imagen {service.get('image')!r} (debe ser sio-it/...)")
if problems:
    print("Configuración NO aislada:\n- " + "\n- ".join(problems), file=sys.stderr)
    sys.exit(1)
print(f"Configuración aislada: {len(config['services'])} servicios, red sio-it-network, sin volúmenes, puertos 18xxx")
PY
    rm -f "$HERE/.config.json"
    # Ningún contenedor sio-it-* debe pertenecer a otro proyecto.
    local foreign
    foreign="$(docker ps -a --filter name=^sio-it- --format '{{.Names}} {{.Label "com.docker.compose.project"}}' | awk '$2 != "sio-it"')"
    [ -z "$foreign" ] || fail "hay contenedores sio-it-* de otro proyecto: $foreign"
}

isolated_container() {
    local label
    label="$(docker inspect -f '{{index .Config.Labels "sio.integration.isolated"}}' "$1")"
    [ "$label" = true ] && [[ "$1" == sio-it-* ]] || fail "$1 no es un contenedor aislado"
}

exec_in() {
    local service=$1; shift
    isolated_container "sio-it-$service"
    "${COMPOSE[@]}" exec -T "$service" "$@"
}

up() {
    verify
    say "Construyendo imágenes sio-it/*:spec022 (no reemplaza las imágenes del entorno persistente)"
    "${COMPOSE[@]}" build "${APP_SERVICES[@]}" product-inventory-query-service business-reporting-service
    say "Levantando Keycloak, almacenamiento y bases"
    "${COMPOSE[@]}" up -d --wait keycloak-db keycloak object-storage geography-db party-identity-db \
        operational-context-db payment-reference-db product-catalog-db commercial-relationship-db inventory-db \
        purchase-db sales-db audit-db
    "${COMPOSE[@]}" --profile bootstrap run --rm object-storage-bootstrap
    say "Levantando los servicios"
    "${COMPOSE[@]}" up -d --wait "${APP_SERVICES[@]}" product-inventory-query-service business-reporting-service

    say "Migraciones"
    for service in geography-service product-catalog-service payment-reference-service operational-context-service \
                   commercial-relationship-service inventory-service purchase-service sales-service audit-service; do
        echo "--- $service"
        exec_in "$service" alembic upgrade head >/dev/null
    done
    exec_in geography-service python -m geography_service.seed load \
        --data-dir /app/services/geography-service/data/south_america | tail -1
    isolated_container sio-it-geography-db
    local colombia
    colombia="$("${COMPOSE[@]}" exec -T geography-db psql -U sio_it -d geography -tA \
        -c "SELECT id FROM global_countries WHERE iso2_code = 'CO'" | tr -d '[:space:]')"
    [ -n "$colombia" ] || fail "Colombia no quedó cargada en Geography"
    echo "--- party-identity-service"
    isolated_container sio-it-party-identity-service
    "${COMPOSE[@]}" exec -T -e PARTY_IDENTITY_SEED_COUNTRY_ID="$colombia" party-identity-service alembic upgrade head >/dev/null

    say "Datos de referencia (seeds de cada servicio)"
    exec_in product-catalog-service python -m product_catalog_service.seed load | tail -1
    exec_in payment-reference-service python -m payment_reference_service.seed load | tail -1
    exec_in party-identity-service python -m party_identity_service.seed load --country-id "$colombia" | tail -1
    exec_in party-identity-service python -m party_identity_service.seed load-business-sectors | tail -1

    say "Trabajadores"
    "${COMPOSE[@]}" up -d --wait
    say "Pila aislada lista (sio-it-*). Siguiente: python validation/isolated-stack/seed.py"
}

down() {
    verify
    say "Retirando SOLO el proyecto $PROJECT (contenedores y red; no hay volúmenes)"
    "${COMPOSE[@]}" --profile bootstrap down --timeout 20
}

environment() {
    cat <<EOF
export SIO_TEST_TARGET=isolated
export SIO_INTEGRATION_CONTAINER_PREFIX=sio-it-
export SIO_IT_ENV_FILE=$ENV_FILE
export KEYCLOAK_TOKEN_URL=http://127.0.0.1:18081/realms/sio/protocol/openid-connect/token
export OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL=http://127.0.0.1:18104/api/v1
export COMMERCIAL_RELATIONSHIP_INTEGRATION_BASE_URL=http://127.0.0.1:18106/api/v1
export PRODUCT_CATALOG_INTEGRATION_BASE_URL=http://127.0.0.1:18103/api/v1
export INVENTORY_INTEGRATION_BASE_URL=http://127.0.0.1:18109/api/v1
export PURCHASE_INTEGRATION_BASE_URL=http://127.0.0.1:18107/api/v1
export SALES_INTEGRATION_BASE_URL=http://127.0.0.1:18108/api/v1
export PARTY_IDENTITY_INTEGRATION_BASE_URL=http://127.0.0.1:18101/api/v1
export PAYMENT_REFERENCE_INTEGRATION_BASE_URL=http://127.0.0.1:18105
export GEOGRAPHY_INTEGRATION_BASE_URL=http://127.0.0.1:18102
export AUDIT_INTEGRATION_BASE_URL=http://127.0.0.1:18110/api/v1
export PRODUCT_INVENTORY_QUERY_INTEGRATION_BASE_URL=http://127.0.0.1:18112/api/v1
export BUSINESS_REPORTING_INTEGRATION_BASE_URL=http://127.0.0.1:18113/api/v1
EOF
}

case "${1:-}" in
    verificar) verify ;;
    levantar) up ;;
    estado) docker ps -a --filter label=com.docker.compose.project=$PROJECT --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' ;;
    retirar) down ;;
    entorno) environment ;;
    *) sed -n '2,8p' "$0"; exit 2 ;;
esac
