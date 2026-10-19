#!/usr/bin/env bash
#
# SIO - Render de realm de Keycloak
#
# Genera:
#   infrastructure/keycloak/import/sio-realm.json
#
# A partir de:
#   infrastructure/keycloak/realm-template/sio-realm.template.json
#
# Sustituye los placeholders ${VAR} con los valores definidos en
# infrastructure/.env antes de que Keycloak ejecute --import-realm.
#
# La plantilla incluye:
#   - clientes sio-api y sio-web
#   - roles de negocio de SIO
#   - permisos CRUD por recurso con formato:
#       perm:{microservicio}:{tabla}:{accion}
#   - grants compactos con wildcard lógico "all", por ejemplo:
#       perm:all:all:all
#       perm:geography:all:read
#   - grupos y usuarios de prueba
#
# Importante:
#   Keycloak no interpreta el wildcard "all". Es un convenio de autorización
#   de SIO que será interpretado por libs/sio-auth. Keycloak únicamente emite
#   esos Client Roles de sio-api dentro del access token.
#
# Uso (desde infrastructure):
#   cp .env.example .env   # si todavía no existe
#   bash ./scripts/render-realm.sh
#
# Después, en un entorno de desarrollo donde quieras reconstruir el realm:
#   docker compose --env-file .env down
#   docker volume rm sio_keycloak-data   # usa el nombre real de tu volumen
#   docker compose --env-file .env up -d keycloak-db keycloak
#
# Nota:
#   --import-realm no sobrescribe un realm que ya existe. Si el realm "sio"
#   ya está almacenado en PostgreSQL, editar el JSON y reiniciar Keycloak no
#   reemplaza automáticamente su configuración.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$INFRA_DIR/.env"
TEMPLATE_FILE="$INFRA_DIR/keycloak/realm-template/sio-realm.template.json"
IMPORT_DIR="$INFRA_DIR/keycloak/import"
OUTPUT_FILE="$IMPORT_DIR/sio-realm.json"

fail() {
    echo "Error: $*" >&2
    exit 1
}

if [ ! -f "$ENV_FILE" ]; then
    fail "no existe $ENV_FILE. Crea infrastructure/.env antes de renderizar el realm."
fi

if [ ! -f "$TEMPLATE_FILE" ]; then
    fail "no existe la plantilla $TEMPLATE_FILE."
fi

mkdir -p "$IMPORT_DIR"

# Lee una variable del .env sin hacer source del archivo completo. Esto evita
# ejecutar accidentalmente contenido del .env y evita pisar variables del
# entorno actual. tr -d '\r' soporta archivos editados en Windows (CRLF).
get_env_var() {
    local var_name="$1"
    local line

    line="$(grep -E "^[[:space:]]*${var_name}=" "$ENV_FILE" | tail -1 || true)"

    if [ -z "$line" ]; then
        printf ''
        return 0
    fi

    printf '%s' "${line#*=}" | tr -d '\r'
}

KEYCLOAK_REALM_VALUE="$(get_env_var "KEYCLOAK_REALM")"
SIO_WEB_ORIGIN_VALUE="$(get_env_var "SIO_WEB_ORIGIN")"
SIO_WEB_REDIRECT_URI_VALUE="$(get_env_var "SIO_WEB_REDIRECT_URI")"
# Igual que compose.yaml: en desarrollo, true si .env no la define.
SIO_WEB_DIRECT_ACCESS_GRANTS_VALUE="$(get_env_var "SIO_WEB_DIRECT_ACCESS_GRANTS_ENABLED")"
SIO_WEB_DIRECT_ACCESS_GRANTS_VALUE="${SIO_WEB_DIRECT_ACCESS_GRANTS_VALUE:-true}"
KEYCLOAK_TEST_USER_PASSWORD_VALUE="$(get_env_var "KEYCLOAK_TEST_USER_PASSWORD")"
PARTY_IDENTITY_CLIENT_SECRET_VALUE="$(get_env_var "PARTY_IDENTITY_CLIENT_SECRET")"
OPERATIONAL_CONTEXT_CLIENT_SECRET_VALUE="$(get_env_var "OPERATIONAL_CONTEXT_CLIENT_SECRET")"
COMMERCIAL_RELATIONSHIP_CLIENT_SECRET_VALUE="$(get_env_var "COMMERCIAL_RELATIONSHIP_CLIENT_SECRET")"
AUDIT_TEST_EMITTER_CLIENT_SECRET_VALUE="$(get_env_var "AUDIT_TEST_EMITTER_CLIENT_SECRET")"
INVENTORY_SERVICE_CLIENT_SECRET_VALUE="$(get_env_var "INVENTORY_SERVICE_CLIENT_SECRET")"
INVENTORY_TEST_OPERATOR_CLIENT_SECRET_VALUE="$(get_env_var "INVENTORY_TEST_OPERATOR_CLIENT_SECRET")"
PURCHASE_SERVICE_CLIENT_SECRET_VALUE="$(get_env_var "PURCHASE_SERVICE_CLIENT_SECRET")"
SIO_DATA_IMPORTER_CLIENT_SECRET_VALUE="$(get_env_var "SIO_DATA_IMPORTER_CLIENT_SECRET")"
SALES_SERVICE_CLIENT_SECRET_VALUE="$(get_env_var "SALES_SERVICE_CLIENT_SECRET")"
PRODUCT_CATALOG_SERVICE_CLIENT_SECRET_VALUE="$(get_env_var "PRODUCT_CATALOG_SERVICE_CLIENT_SECRET")"
PRODUCT_INVENTORY_QUERY_SERVICE_CLIENT_SECRET_VALUE="$(get_env_var "PRODUCT_INVENTORY_QUERY_SERVICE_CLIENT_SECRET")"

require_value() {
    local name="$1"
    local value="$2"

    if [ -z "$value" ]; then
        fail "$name no está definida o está vacía en $ENV_FILE."
    fi
}

require_value "KEYCLOAK_REALM" "$KEYCLOAK_REALM_VALUE"
require_value "SIO_WEB_ORIGIN" "$SIO_WEB_ORIGIN_VALUE"
require_value "SIO_WEB_REDIRECT_URI" "$SIO_WEB_REDIRECT_URI_VALUE"
require_value "KEYCLOAK_TEST_USER_PASSWORD" "$KEYCLOAK_TEST_USER_PASSWORD_VALUE"
require_value "PARTY_IDENTITY_CLIENT_SECRET" "$PARTY_IDENTITY_CLIENT_SECRET_VALUE"
require_value "OPERATIONAL_CONTEXT_CLIENT_SECRET" "$OPERATIONAL_CONTEXT_CLIENT_SECRET_VALUE"
require_value "COMMERCIAL_RELATIONSHIP_CLIENT_SECRET" "$COMMERCIAL_RELATIONSHIP_CLIENT_SECRET_VALUE"
require_value "AUDIT_TEST_EMITTER_CLIENT_SECRET" "$AUDIT_TEST_EMITTER_CLIENT_SECRET_VALUE"
require_value "INVENTORY_SERVICE_CLIENT_SECRET" "$INVENTORY_SERVICE_CLIENT_SECRET_VALUE"
require_value "INVENTORY_TEST_OPERATOR_CLIENT_SECRET" "$INVENTORY_TEST_OPERATOR_CLIENT_SECRET_VALUE"
require_value "PURCHASE_SERVICE_CLIENT_SECRET" "$PURCHASE_SERVICE_CLIENT_SECRET_VALUE"
require_value "SIO_DATA_IMPORTER_CLIENT_SECRET" "$SIO_DATA_IMPORTER_CLIENT_SECRET_VALUE"
require_value "SALES_SERVICE_CLIENT_SECRET" "$SALES_SERVICE_CLIENT_SECRET_VALUE"
require_value "PRODUCT_CATALOG_SERVICE_CLIENT_SECRET" "$PRODUCT_CATALOG_SERVICE_CLIENT_SECRET_VALUE"
require_value "PRODUCT_INVENTORY_QUERY_SERVICE_CLIENT_SECRET" "$PRODUCT_INVENTORY_QUERY_SERVICE_CLIENT_SECRET_VALUE"

# Debe coincidir con passwordPolicy de sio-realm.template.json:
# length(12) and upperCase(1) and lowerCase(1) and digits(1)
PASSWORD_ERRORS=()

[ "${#KEYCLOAK_TEST_USER_PASSWORD_VALUE}" -ge 12 ] \
    || PASSWORD_ERRORS+=("al menos 12 caracteres")
[[ "$KEYCLOAK_TEST_USER_PASSWORD_VALUE" =~ [A-Z] ]] \
    || PASSWORD_ERRORS+=("al menos una mayúscula")
[[ "$KEYCLOAK_TEST_USER_PASSWORD_VALUE" =~ [a-z] ]] \
    || PASSWORD_ERRORS+=("al menos una minúscula")
[[ "$KEYCLOAK_TEST_USER_PASSWORD_VALUE" =~ [0-9] ]] \
    || PASSWORD_ERRORS+=("al menos un dígito")

if [ "${#PASSWORD_ERRORS[@]}" -gt 0 ]; then
    echo "Error: KEYCLOAK_TEST_USER_PASSWORD no cumple la política del realm." >&2
    echo "Debe incluir:" >&2
    for err in "${PASSWORD_ERRORS[@]}"; do
        echo "  - $err" >&2
    done
    exit 1
fi

# Escapa los caracteres con significado especial para sed. Usamos | como
# delimitador para no tener que escapar las barras de URLs http://...
escape_for_sed() {
    printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'
}

REALM_ESCAPED="$(escape_for_sed "$KEYCLOAK_REALM_VALUE")"
ORIGIN_ESCAPED="$(escape_for_sed "$SIO_WEB_ORIGIN_VALUE")"
REDIRECT_ESCAPED="$(escape_for_sed "$SIO_WEB_REDIRECT_URI_VALUE")"
PASSWORD_ESCAPED="$(escape_for_sed "$KEYCLOAK_TEST_USER_PASSWORD_VALUE")"
PARTY_IDENTITY_SECRET_ESCAPED="$(escape_for_sed "$PARTY_IDENTITY_CLIENT_SECRET_VALUE")"
OPERATIONAL_CONTEXT_SECRET_ESCAPED="$(escape_for_sed "$OPERATIONAL_CONTEXT_CLIENT_SECRET_VALUE")"
COMMERCIAL_RELATIONSHIP_SECRET_ESCAPED="$(escape_for_sed "$COMMERCIAL_RELATIONSHIP_CLIENT_SECRET_VALUE")"
AUDIT_TEST_EMITTER_SECRET_ESCAPED="$(escape_for_sed "$AUDIT_TEST_EMITTER_CLIENT_SECRET_VALUE")"
INVENTORY_SERVICE_SECRET_ESCAPED="$(escape_for_sed "$INVENTORY_SERVICE_CLIENT_SECRET_VALUE")"
INVENTORY_TEST_OPERATOR_SECRET_ESCAPED="$(escape_for_sed "$INVENTORY_TEST_OPERATOR_CLIENT_SECRET_VALUE")"
PURCHASE_SERVICE_SECRET_ESCAPED="$(escape_for_sed "$PURCHASE_SERVICE_CLIENT_SECRET_VALUE")"
SIO_DATA_IMPORTER_SECRET_ESCAPED="$(escape_for_sed "$SIO_DATA_IMPORTER_CLIENT_SECRET_VALUE")"
SALES_SERVICE_SECRET_ESCAPED="$(escape_for_sed "$SALES_SERVICE_CLIENT_SECRET_VALUE")"
PRODUCT_CATALOG_SERVICE_SECRET_ESCAPED="$(escape_for_sed "$PRODUCT_CATALOG_SERVICE_CLIENT_SECRET_VALUE")"
PRODUCT_INVENTORY_QUERY_SERVICE_SECRET_ESCAPED="$(escape_for_sed "$PRODUCT_INVENTORY_QUERY_SERVICE_CLIENT_SECRET_VALUE")"

TEMP_FILE="${OUTPUT_FILE}.tmp"
trap 'rm -f "$TEMP_FILE"' EXIT

sed \
    -e "s|\${KEYCLOAK_REALM}|${REALM_ESCAPED}|g" \
    -e "s|\${SIO_WEB_ORIGIN}|${ORIGIN_ESCAPED}|g" \
    -e "s|\${SIO_WEB_REDIRECT_URI}|${REDIRECT_ESCAPED}|g" \
    -e "s|\${SIO_WEB_DIRECT_ACCESS_GRANTS_ENABLED:false}|${SIO_WEB_DIRECT_ACCESS_GRANTS_VALUE}|g" \
    -e "s|\${KEYCLOAK_TEST_USER_PASSWORD}|${PASSWORD_ESCAPED}|g" \
    -e "s|\${PARTY_IDENTITY_CLIENT_SECRET}|${PARTY_IDENTITY_SECRET_ESCAPED}|g" \
    -e "s|\${OPERATIONAL_CONTEXT_CLIENT_SECRET}|${OPERATIONAL_CONTEXT_SECRET_ESCAPED}|g" \
    -e "s|\${COMMERCIAL_RELATIONSHIP_CLIENT_SECRET}|${COMMERCIAL_RELATIONSHIP_SECRET_ESCAPED}|g" \
    -e "s|\${AUDIT_TEST_EMITTER_CLIENT_SECRET}|${AUDIT_TEST_EMITTER_SECRET_ESCAPED}|g" \
    -e "s|\${INVENTORY_SERVICE_CLIENT_SECRET}|${INVENTORY_SERVICE_SECRET_ESCAPED}|g" \
    -e "s|\${INVENTORY_TEST_OPERATOR_CLIENT_SECRET}|${INVENTORY_TEST_OPERATOR_SECRET_ESCAPED}|g" \
    -e "s|\${PURCHASE_SERVICE_CLIENT_SECRET}|${PURCHASE_SERVICE_SECRET_ESCAPED}|g" \
    -e "s|\${SIO_DATA_IMPORTER_CLIENT_SECRET}|${SIO_DATA_IMPORTER_SECRET_ESCAPED}|g" \
    -e "s|\${SALES_SERVICE_CLIENT_SECRET}|${SALES_SERVICE_SECRET_ESCAPED}|g" \
    -e "s|\${PRODUCT_CATALOG_SERVICE_CLIENT_SECRET}|${PRODUCT_CATALOG_SERVICE_SECRET_ESCAPED}|g" \
    -e "s|\${PRODUCT_INVENTORY_QUERY_SERVICE_CLIENT_SECRET}|${PRODUCT_INVENTORY_QUERY_SERVICE_SECRET_ESCAPED}|g" \
    "$TEMPLATE_FILE" > "$TEMP_FILE"

# Ningún placeholder puede llegar sin resolver al import de Keycloak.
if grep -q '\${' "$TEMP_FILE"; then
    echo "Error: quedaron placeholders sin resolver:" >&2
    grep -o '\${[A-Za-z_][A-Za-z0-9_]*}' "$TEMP_FILE" | sort -u >&2 || true
    exit 1
fi

# Validación JSON opcional. No introducimos una dependencia obligatoria nueva:
# usamos Python solo si ya está disponible en la máquina.
if command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool "$TEMP_FILE" >/dev/null \
        || fail "el JSON renderizado no es válido."
elif command -v python >/dev/null 2>&1; then
    python -m json.tool "$TEMP_FILE" >/dev/null \
        || fail "el JSON renderizado no es válido."
fi

mv "$TEMP_FILE" "$OUTPUT_FILE"
trap - EXIT

# Resumen útil sin mostrar credenciales.
PERMISSION_COUNT="$(grep -o '"name": "perm:[^"]*"' "$OUTPUT_FILE" | wc -l | tr -d ' ')"
USER_COUNT="$(grep -o '"username": "[^"]*"' "$OUTPUT_FILE" | wc -l | tr -d ' ')"

echo "OK: realm renderizado correctamente."
echo "  Realm:       $KEYCLOAK_REALM_VALUE"
echo "  Archivo:     $OUTPUT_FILE"
echo "  Usuarios:    $USER_COUNT"
echo "  Roles perm:* $PERMISSION_COUNT"
echo ""
echo "Nota: si el realm '$KEYCLOAK_REALM_VALUE' ya existe en Keycloak, --import-realm no lo sobrescribirá."
