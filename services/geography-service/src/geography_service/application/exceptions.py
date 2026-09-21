class GlobalCountryNotFoundError(Exception):
    """El país global solicitado no existe."""


class GlobalCountryConflictError(Exception):
    """Existe un conflicto con los datos del país global."""


class GlobalCountryVersionConflictError(Exception):
    """Existe un conflicto de concurrencia sobre el país global."""

class GlobalAdministrativeDivisionNotFoundError(Exception):
    """La división administrativa solicitada no existe."""


class GlobalAdministrativeDivisionConflictError(Exception):
    """Existe un conflicto con la división administrativa."""


class GlobalAdministrativeDivisionVersionConflictError(Exception):
    """Existe un conflicto de concurrencia."""


class GlobalAdministrativeDivisionInvalidParentError(Exception):
    """La división superior indicada no es válida."""

class GlobalCityNotFoundError(Exception):
    """Indica que la ciudad global solicitada no existe."""


class GlobalCityConflictError(Exception):
    """Indica un conflicto de integridad relacionado con una ciudad global."""


class GlobalCityVersionConflictError(Exception):
    """Indica un conflicto de concurrencia sobre una ciudad global."""


class GlobalCityInvalidAdministrativeDivisionError(Exception):
    """Indica que la división administrativa indicada no es válida."""
