"""Configuración propia de Product Catalog Service."""

import os
from dataclasses import dataclass

IMAGE_REF_SECRET_MIN_BYTES = 32
IMAGE_STAGE_TRANSITION = "transition"
IMAGE_STAGE_COMPLETED = "completed"
IMAGE_STAGES = (IMAGE_STAGE_TRANSITION, IMAGE_STAGE_COMPLETED)


@dataclass(frozen=True, slots=True)
class Settings:
    """Representa la configuración del microservicio.

    Attributes:
        docs_enabled: Indica si Swagger y OpenAPI están habilitados.
        database_url: URL de conexión hacia PostgreSQL.
        party_identity_service_base_url: URL base de Party Identity Service,
            incluido su prefijo de ruta.
        party_identity_timeout_seconds: Tiempo de espera de la validación del
            fabricante.
        asset_storage_*: Almacenamiento de objetos compatible con S3 del contenido
            de los activos (`ASSET_STORAGE_*`); opcional: sin él, `/content`
            responde 503.
        public_base_url: URL pública base con la que se construye `image_url`
            (`PRODUCT_CATALOG_PUBLIC_BASE_URL`, spec 022, FR-022-96).
        image_ref_secret / image_ref_secret_previous: secreto HMAC de las
            referencias de imagen y el saliente durante una rotación
            (`PRODUCT_IMAGE_REF_SECRET[_PREVIOUS]`, FR-022-97). Sin secreto o sin
            URL pública base no se entregan `image_url` ni existe la ruta pública.
        asset_upload_max_bytes / asset_upload_max_pixels: límites de la carga directa de
            imágenes (`ASSET_UPLOAD_MAX_BYTES`, `ASSET_UPLOAD_MAX_PIXELS`; spec 024, FR-024-12).
        image_migration_stage: etapa de las rutas por producto frente a las imágenes
            (`PRODUCT_IMAGE_MIGRATION_STAGE`; spec 024, research R2): `transition` (entrega 1,
            por defecto) o `completed` (entrega 2, después de verificar la migración).
    """

    docs_enabled: bool
    database_url: str
    party_identity_service_base_url: str
    party_identity_timeout_seconds: float
    asset_storage_endpoint: str | None = None
    asset_storage_bucket: str = "sio-product-assets"
    asset_storage_access_key: str | None = None
    asset_storage_secret_key: str | None = None
    asset_storage_region: str = "us-east-1"
    asset_storage_timeout_seconds: float = 5.0
    public_base_url: str | None = None
    image_ref_secret: str | None = None
    image_ref_secret_previous: str | None = None
    asset_upload_max_bytes: int = 5_242_880
    asset_upload_max_pixels: int = 40_000_000
    image_migration_stage: str = IMAGE_STAGE_TRANSITION

    def __post_init__(self) -> None:
        if self.image_migration_stage not in IMAGE_STAGES:
            raise RuntimeError("PRODUCT_IMAGE_MIGRATION_STAGE debe ser 'transition' o 'completed'.")
        if self.asset_upload_max_bytes <= 0 or self.asset_upload_max_pixels <= 0:
            raise RuntimeError("ASSET_UPLOAD_MAX_BYTES y ASSET_UPLOAD_MAX_PIXELS deben ser mayores que cero.")
        for name, value in (
            ("PRODUCT_IMAGE_REF_SECRET", self.image_ref_secret),
            ("PRODUCT_IMAGE_REF_SECRET_PREVIOUS", self.image_ref_secret_previous),
        ):
            if value is not None and len(value.encode("utf-8")) < IMAGE_REF_SECRET_MIN_BYTES:
                raise RuntimeError(f"{name} debe tener al menos {IMAGE_REF_SECRET_MIN_BYTES} bytes.")
        if self.image_ref_secret_previous is not None and self.image_ref_secret is None:
            raise RuntimeError("PRODUCT_IMAGE_REF_SECRET_PREVIOUS requiere PRODUCT_IMAGE_REF_SECRET.")

    def __repr__(self) -> str:  # nunca muestra secretos ni la URL de la base
        return f"Settings(docs_enabled={self.docs_enabled!r}, public_images={self.public_images_enabled!r})"

    @property
    def public_images_enabled(self) -> bool:
        """La URL pública de imágenes existe solo con secreto y URL base configurados (FR-022-99)."""
        return bool(self.image_ref_secret and self.public_base_url)

    @property
    def image_ref_secrets(self) -> list[str]:
        """Secretos aceptados al verificar una referencia: el actual y, en rotación, el anterior."""
        return [secret for secret in (self.image_ref_secret, self.image_ref_secret_previous) if secret]

    @property
    def image_migration_completed(self) -> bool:
        """Entrega 2: las rutas por producto ya no gestionan imágenes (FR-024-32)."""
        return self.image_migration_stage == IMAGE_STAGE_COMPLETED

    @property
    def asset_storage_configured(self) -> bool:
        return bool(self.asset_storage_endpoint and self.asset_storage_access_key and self.asset_storage_secret_key)


def load_settings() -> Settings:
    """Carga la configuración del servicio desde variables de entorno.

    Returns:
        Configuración obtenida desde el entorno.

    Raises:
        RuntimeError: Si una variable obligatoria falta o tiene un valor inválido.
    """
    return Settings(
        docs_enabled=_read_bool(
            name="SIO_DOCS_ENABLED",
            default=False,
        ),
        database_url=_required_text("DATABASE_URL"),
        party_identity_service_base_url=_read_text(
            name="PARTY_IDENTITY_SERVICE_BASE_URL",
            default="http://localhost:8002",
        ),
        party_identity_timeout_seconds=_read_float(
            name="PARTY_IDENTITY_TIMEOUT_SECONDS",
            default=3.0,
        ),
        asset_storage_endpoint=_optional_text("ASSET_STORAGE_ENDPOINT"),
        asset_storage_bucket=_read_text(name="ASSET_STORAGE_BUCKET", default="sio-product-assets"),
        asset_storage_access_key=_optional_text("ASSET_STORAGE_ACCESS_KEY"),
        asset_storage_secret_key=_optional_text("ASSET_STORAGE_SECRET_KEY"),
        asset_storage_region=_read_text(name="ASSET_STORAGE_REGION", default="us-east-1"),
        asset_storage_timeout_seconds=_read_float(name="ASSET_STORAGE_TIMEOUT_SECONDS", default=5.0),
        public_base_url=(_optional_text("PRODUCT_CATALOG_PUBLIC_BASE_URL") or "").rstrip("/") or None,
        image_ref_secret=_optional_text("PRODUCT_IMAGE_REF_SECRET"),
        image_ref_secret_previous=_optional_text("PRODUCT_IMAGE_REF_SECRET_PREVIOUS"),
        asset_upload_max_bytes=_read_int(name="ASSET_UPLOAD_MAX_BYTES", default=5_242_880),
        asset_upload_max_pixels=_read_int(name="ASSET_UPLOAD_MAX_PIXELS", default=40_000_000),
        image_migration_stage=_read_text(name="PRODUCT_IMAGE_MIGRATION_STAGE", default=IMAGE_STAGE_TRANSITION).lower(),
    )


def _optional_text(name: str) -> str | None:
    """Variable opcional; vacía equivale a no definida (nunca se registra su valor)."""
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


def _required_text(name: str) -> str:
    """Obtiene una variable de entorno de texto obligatoria."""
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(
            f"La variable de entorno {name} es obligatoria y no puede estar vacía."
        )

    return value.strip()


def _read_text(
    name: str,
    default: str,
) -> str:
    """Obtiene una variable opcional de texto sin barra final."""
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    return value.strip().rstrip("/")


def _read_float(
    name: str,
    default: float,
) -> float:
    """Obtiene una variable opcional numérica mayor que cero."""
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        number = float(value.strip())
    except ValueError as exc:
        raise RuntimeError(
            f"La variable de entorno {name} debe ser un número."
        ) from exc

    if number <= 0:
        raise RuntimeError(
            f"La variable de entorno {name} debe ser mayor que cero."
        )

    return number


def _read_int(name: str, default: int) -> int:
    """Obtiene una variable opcional entera mayor que cero."""
    value = os.getenv(name)

    if value is None or not value.strip():
        return default

    try:
        number = int(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"La variable de entorno {name} debe ser un número entero.") from exc

    if number <= 0:
        raise RuntimeError(f"La variable de entorno {name} debe ser mayor que cero.")

    return number


def _read_bool(name: str, default: bool) -> bool:
    """Obtiene una variable de entorno booleana."""
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    normalized_value = raw_value.strip().lower()

    if normalized_value in {"true", "1", "yes", "on"}:
        return True

    if normalized_value in {"false", "0", "no", "off"}:
        return False

    raise RuntimeError(
        f"La variable de entorno {name} debe contener un valor booleano válido."
    )
