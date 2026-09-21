"""Excepciones de aplicación de Party Identity Service."""


class PersonIdentityNotFoundError(Exception):
    """La identidad de persona solicitada no existe."""


class PersonIdentityConflictError(Exception):
    """Existe un conflicto con los datos de la identidad de persona."""


class PersonIdentityVersionConflictError(Exception):
    """Existe un conflicto de concurrencia sobre la identidad de persona."""


class InvalidIdentificationNumberError(Exception):
    """El número de identificación no cumple la regla configurada."""


class InvalidIdentificationAgeError(Exception):
    """La edad no cumple la regla del tipo de identificación."""


class CountryNotFoundError(Exception):
    """El país referenciado no existe en Geography Service."""


class CountryValidationUnavailableError(Exception):
    """No fue posible validar el país contra Geography Service."""


class IdentificationTypeRuleNotFoundError(Exception):
    """La regla de identificación solicitada no existe."""


class IdentificationTypeRuleConflictError(Exception):
    """Existe un conflicto con los datos de la regla."""


class IdentificationTypeRuleVersionConflictError(Exception):
    """Existe un conflicto de concurrencia sobre la regla."""
