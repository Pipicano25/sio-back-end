"""Excepciones definidas por sio-auth."""


class SIOAuthError(Exception):
    """Excepción base para los errores generados por sio-auth."""


class AuthConfigurationError(SIOAuthError, ValueError):
    """Se genera cuando la configuración de sio-auth está ausente o es inválida."""


class AuthenticationError(SIOAuthError):
    """Se genera cuando una solicitud no puede autenticarse."""

    def __init__(self, message: str = "Token de acceso ausente o inválido") -> None:
        super().__init__(message)
        self.message = message
