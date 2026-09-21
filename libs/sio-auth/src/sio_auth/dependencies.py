"""Dependencias de FastAPI que consumen el estado ya autenticado de la solicitud."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from .tokens import TokenClaims


def get_current_claims(request: Request) -> TokenClaims:
    """Devuelve los claims cargados por el middleware global de sio-auth.

    Esta función nunca decodifica un JWT. Si el middleware no fue instalado o
    una ruta pública intenta exigir identidad, el acceso se deniega con 401.
    """

    claims = getattr(request.state, "sio_claims", None)
    if not isinstance(claims, TokenClaims):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No existe un contexto de autenticación para esta solicitud",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims


CurrentClaims = Annotated[TokenClaims, Depends(get_current_claims)]


def get_current_subject(
    claims: CurrentClaims,
) -> str:
    """Devuelve el subject estable del usuario autenticado."""

    subject = claims.sub.strip()

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No fue posible identificar al usuario autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return subject


CurrentSubject = Annotated[
    str,
    Depends(get_current_subject),
]
