"""Excepciones de dominio con código estable (`contracts/errors.md`).

Cada excepción define su código `PRODUCT_CATALOG.*` y el estado HTTP que la
capa de API debe usar. La traducción a HTTP ocurre solo en `api/errors.py`.
"""

from __future__ import annotations

from typing import Any

CODE_PREFIX = "PRODUCT_CATALOG."


class DomainError(Exception):
    """Error de dominio con código estable y estado HTTP asociado."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    title: str = "Error interno"

    def __init__(
        self,
        detail: str,
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.extra = extra or {}

    @property
    def full_code(self) -> str:
        """Código completo con el prefijo del servicio."""
        return f"{CODE_PREFIX}{self.code}"


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    status_code = 404
    title = "Recurso no encontrado"


class ValidationError(DomainError):
    code = "VALIDATION_ERROR"
    status_code = 422
    title = "Solicitud inválida"

    def __init__(self, detail: str, *, field: str | None = None) -> None:
        errors = [{"field": field, "message": detail, "code": self.code}] if field else []
        super().__init__(detail, extra={"errors": errors} if errors else None)


class ImmutableFieldError(DomainError):
    code = "IMMUTABLE_FIELD"
    status_code = 422
    title = "Campo inmutable"


class ReferenceNotFoundError(DomainError):
    code = "REFERENCE_NOT_FOUND"
    status_code = 422
    title = "Referencia inexistente"


class ReferenceInactiveError(DomainError):
    code = "REFERENCE_INACTIVE"
    status_code = 422
    title = "Referencia inactiva"


class ProductInactiveError(DomainError):
    code = "PRODUCT_INACTIVE"
    status_code = 422
    title = "Producto inactivo"


class HierarchyCycleError(DomainError):
    code = "HIERARCHY_CYCLE"
    status_code = 422
    title = "Ciclo jerárquico"


class HasActiveChildrenError(DomainError):
    code = "HAS_ACTIVE_CHILDREN"
    status_code = 422
    title = "Tiene hijos activos"


class ParentInactiveError(DomainError):
    code = "PARENT_INACTIVE"
    status_code = 422
    title = "Padre inactivo"


class ParentOfOtherTypeError(DomainError):
    code = "PARENT_OF_OTHER_TYPE"
    status_code = 422
    title = "Padre de otro tipo"


class NewPrimaryRequiredError(DomainError):
    code = "NEW_PRIMARY_REQUIRED"
    status_code = 422
    title = "Se requiere una nueva principal"


class UnitNotAllowedForDataTypeError(DomainError):
    code = "UNIT_NOT_ALLOWED_FOR_DATA_TYPE"
    status_code = 422
    title = "Unidad no permitida para el tipo de dato"


class DefinitionNotOptionError(DomainError):
    code = "DEFINITION_NOT_OPTION"
    status_code = 422
    title = "La definición no es de tipo OPTION"


class AttributeNotApplicableError(DomainError):
    code = "ATTRIBUTE_NOT_APPLICABLE"
    status_code = 422
    title = "Atributo no aplicable"


class ValueOutOfClassificationError(DomainError):
    code = "VALUE_OUT_OF_CLASSIFICATION"
    status_code = 422
    title = "Valor fuera de clasificación"


class ValueTypeMismatchError(DomainError):
    code = "VALUE_TYPE_MISMATCH"
    status_code = 422
    title = "Tipo de valor inválido"


class OptionNotInDefinitionError(DomainError):
    code = "OPTION_NOT_IN_DEFINITION"
    status_code = 422
    title = "Opción no válida para la definición"


class AttributeNotFilterableError(DomainError):
    code = "ATTRIBUTE_NOT_FILTERABLE"
    status_code = 422
    title = "Atributo no filtrable"


class BaseUnitLockedByFirstUseError(DomainError):
    code = "BASE_UNIT_LOCKED_BY_FIRST_USE"
    status_code = 422
    title = "Unidad base bloqueada por primer uso"


class PresentationLockedByFirstUseError(DomainError):
    code = "PRESENTATION_LOCKED_BY_FIRST_USE"
    status_code = 422
    title = "Presentación bloqueada por primer uso"


class BasePresentationExistsError(DomainError):
    code = "BASE_PRESENTATION_EXISTS"
    status_code = 409
    title = "Ya existe una presentación base"


class BaseQuantityMustBeOneError(DomainError):
    code = "BASE_QUANTITY_MUST_BE_ONE"
    status_code = 422
    title = "La presentación base debe tener factor 1"


class InvalidGtinFormatError(DomainError):
    code = "INVALID_GTIN_FORMAT"
    status_code = 422
    title = "Formato GTIN inválido"


class InvalidCheckDigitError(DomainError):
    code = "INVALID_CHECK_DIGIT"
    status_code = 422
    title = "Dígito de control inválido"


class BarcodeIsGtinError(DomainError):
    code = "BARCODE_IS_GTIN"
    status_code = 422
    title = "El código debe registrarse con su tipo GTIN, EAN o UPC"


class InvalidIumFormatError(DomainError):
    code = "INVALID_IUM_FORMAT"
    status_code = 422
    title = "Formato IUM inválido"


class IumRequiresPresentationError(DomainError):
    code = "IUM_REQUIRES_PRESENTATION"
    status_code = 422
    title = "El IUM debe asociarse a una presentación"


class PresentationOfOtherProductError(DomainError):
    code = "PRESENTATION_OF_OTHER_PRODUCT"
    status_code = 422
    title = "La presentación no pertenece al producto"


class IdentifierCollisionError(DomainError):
    code = "IDENTIFIER_COLLISION"
    status_code = 409
    title = "Colisión de identificador"


class GroupTypeSingleValueError(DomainError):
    code = "GROUP_TYPE_SINGLE_VALUE"
    status_code = 422
    title = "El tipo de grupo no admite varios valores"


class MultipleAssignmentsExistError(DomainError):
    code = "MULTIPLE_ASSIGNMENTS_EXIST"
    status_code = 422
    title = "Existen productos con varias asignaciones del tipo"


class InvalidStorageUriError(DomainError):
    code = "INVALID_STORAGE_URI"
    status_code = 422
    title = "Referencia de almacenamiento inválida"


class DuplicateCodeError(DomainError):
    code = "DUPLICATE_CODE"
    status_code = 409
    title = "Código duplicado"


class CodeUsedByPackagingTypeError(DomainError):
    code = "CODE_USED_BY_PACKAGING_TYPE"
    status_code = 409
    title = "Código usado por un tipo de empaque"


class CodeUsedByUnitOfMeasureError(DomainError):
    code = "CODE_USED_BY_UNIT_OF_MEASURE"
    status_code = 409
    title = "Código usado por una unidad de medida"


class DuplicateAssociationError(DomainError):
    code = "DUPLICATE_ASSOCIATION"
    status_code = 409
    title = "Asociación duplicada"


class VersionConflictError(DomainError):
    code = "VERSION_CONFLICT"
    status_code = 409
    title = "Versión desactualizada"

    def __init__(self, detail: str = "El registro fue modificado por otra operación; consulte la versión vigente.") -> None:
        super().__init__(detail)


class BatchLimitExceededError(DomainError):
    code = "BATCH_LIMIT_EXCEEDED"
    status_code = 422
    title = "Límite de lote excedido"


class ManufacturerNotFoundError(DomainError):
    code = "MANUFACTURER_NOT_FOUND"
    status_code = 422
    title = "Fabricante inexistente"


class ManufacturerAccessDeniedError(DomainError):
    code = "MANUFACTURER_ACCESS_DENIED"
    status_code = 403
    title = "Sin acceso para validar el fabricante"


class NotEligibleForFirstUseError(DomainError):
    code = "NOT_ELIGIBLE_FOR_FIRST_USE"
    status_code = 422
    title = "No elegible para registrar primer uso"


class DependencyUnavailableError(DomainError):
    code = "DEPENDENCY_UNAVAILABLE"
    status_code = 503
    title = "Dependencia no disponible"


class AssetContentNotStoredError(DomainError):
    code = "ASSET_CONTENT_NOT_STORED"
    status_code = 409
    title = "El contenido del activo no está en el almacenamiento de SIO"


class AssetStorageUnavailableError(Exception):
    """El almacenamiento de objetos no respondió de forma utilizable (lo emite el adaptador)."""


class ManufacturerDirectoryUnavailableError(Exception):
    """Party Identity no respondió de forma utilizable (lo emite el adaptador)."""


class ManufacturerDirectoryAccessDeniedError(Exception):
    """Party Identity respondió 401 o 403 al token propagado (lo emite el adaptador)."""
