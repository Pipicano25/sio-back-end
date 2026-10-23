#!/bin/sh
# Bootstrap idempotente del almacenamiento de objetos de SIO (se puede ejecutar N veces).
#   1. bucket privado (sin acceso anónimo);
#   2. políticas de mínimo privilegio sobre el prefijo assets/;
#   3. cuentas de aplicación (Product Catalog y migración: lectura y escritura de assets/*, sin borrado;
#      spec 024: Product Catalog escribe las imágenes que se cargan por la API).
# root solo se usa aquí. No imprime credenciales. Solo usa sh + mc (la imagen es mínima).
set -eu

: "${OBJECT_STORAGE_URL:?}" "${OBJECT_STORAGE_BUCKET:?}" "${MINIO_ROOT_USER:?}" "${MINIO_ROOT_PASSWORD:?}"
: "${PRODUCT_CATALOG_ASSET_STORAGE_ACCESS_KEY:?}" "${PRODUCT_CATALOG_ASSET_STORAGE_SECRET_KEY:?}"
: "${MIGRATION_ASSET_STORAGE_ACCESS_KEY:?}" "${MIGRATION_ASSET_STORAGE_SECRET_KEY:?}"

BUCKET="$OBJECT_STORAGE_BUCKET"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mc alias set sio "$OBJECT_STORAGE_URL" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
echo "Almacenamiento alcanzable en $OBJECT_STORAGE_URL"

mc mb --ignore-existing "sio/$BUCKET" >/dev/null
mc anonymous set none "sio/$BUCKET" >/dev/null
anonymous="$(mc anonymous get "sio/$BUCKET")"
echo "Bucket $BUCKET: existe y es privado (acceso anónimo: ${anonymous##* })"

# ListBucket limitado al prefijo assets/: permite distinguir "no existe" (404) de "sin permiso" (403).
cat > "$WORK/read.json" <<JSON
{"Version": "2012-10-17", "Statement": [
  {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": ["arn:aws:s3:::$BUCKET/assets/*"]},
  {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": ["arn:aws:s3:::$BUCKET"], "Condition": {"StringLike": {"s3:prefix": ["assets/*"]}}}
]}
JSON
cat > "$WORK/write.json" <<JSON
{"Version": "2012-10-17", "Statement": [
  {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"], "Resource": ["arn:aws:s3:::$BUCKET/assets/*"]},
  {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": ["arn:aws:s3:::$BUCKET"], "Condition": {"StringLike": {"s3:prefix": ["assets/*"]}}}
]}
JSON
mc admin policy create sio sio-assets-read "$WORK/read.json" >/dev/null
mc admin policy create sio sio-assets-write "$WORK/write.json" >/dev/null
echo "Políticas: sio-assets-read (GetObject), sio-assets-write (GetObject + PutObject; sin DeleteObject)"

ensure_user() {
    access="$1"; secret="$2"; policy="$3"; label="$4"; replaced="${5:-}"
    # add actualiza la clave si la cuenta ya existe (idempotente).
    mc admin user add sio "$access" "$secret" >/dev/null
    # La imagen mínima no trae grep/awk: solo builtins de sh.
    case "$(mc admin user info sio "$access")" in
        *"$policy"*) ;;
        *) mc admin policy attach sio "$policy" --user "$access" >/dev/null ;;
    esac
    # Política anterior de la cuenta (p. ej. solo lectura antes de la spec 024): se retira para que quede una sola.
    if [ -n "$replaced" ]; then
        case "$(mc admin user info sio "$access")" in
            *"$replaced"*) mc admin policy detach sio "$replaced" --user "$access" >/dev/null ;;
        esac
    fi
    echo "Cuenta de $label: política $policy"
}
# Spec 024: Product Catalog recibe la carga multipart y escribe el objeto (PutObject condicional, sin borrado).
ensure_user "$PRODUCT_CATALOG_ASSET_STORAGE_ACCESS_KEY" "$PRODUCT_CATALOG_ASSET_STORAGE_SECRET_KEY" sio-assets-write "Product Catalog" sio-assets-read
ensure_user "$MIGRATION_ASSET_STORAGE_ACCESS_KEY" "$MIGRATION_ASSET_STORAGE_SECRET_KEY" sio-assets-write "migración"
echo "Bootstrap del almacenamiento de objetos completo."
