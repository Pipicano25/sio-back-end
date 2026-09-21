"""Excepciones de aplicación de Party Identity Service."""


class PersonIdentityNotFoundError(Exception):
    """La identidad de persona solicitada no existe."""


class PersonIdentityConflictError(Exception):
    """Existe un conflicto con los datos de la identidad de persona."""


class PersonIdentityVersionConflictError(Exception):
    """Existe un conflicto de concurrencia sobre la identidad de persona."""


class InvalidIdentificationNumberError(Exception):
    """El número de identificación no cumple la regla configurada."""
