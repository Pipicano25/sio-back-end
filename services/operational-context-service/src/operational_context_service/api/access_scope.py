"""Dependencia FastAPI que construye el `AccessScope` de cada solicitud (R-01).

Lee los claims ya validados por `sio-auth` y consulta las membresías `ACTIVE`
del `sub` una vez por solicitud, sin caché entre solicitudes (FR-044).
"""

from fastapi import Depends
from sio_auth import CurrentClaims
from sqlalchemy.orm import Session

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.infrastructure.database import get_db_session
from operational_context_service.infrastructure.membership_lookup import SQLAlchemyMembershipLookup


def get_access_scope(
    claims: CurrentClaims,
    session: Session = Depends(get_db_session),
) -> AccessScope:
    """Alcance del usuario autenticado para la solicitud actual."""
    lookup = SQLAlchemyMembershipLookup(session)

    return AccessScope.build(
        subject=claims.subject,
        grants=claims.permissions,
        member_company_ids=lookup.active_company_ids(claims.subject),
    )
