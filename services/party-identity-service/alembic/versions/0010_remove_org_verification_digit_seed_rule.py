"""remove org verification digit and seed organization rule

Revision ID: 0010_org_nit_rule_no_dv
Revises: 0009_align_ident_metadata
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0010_org_nit_rule_no_dv"
down_revision: Union[str, Sequence[str], None] = "0009_align_ident_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLOMBIA_COUNTRY_ID = "cf160c2d-b6de-4ef5-9257-a0a8539058d9"
SYSTEM_ACTOR_ID = "00000000-0000-0000-0000-000000000001"
ORGANIZATION_NIT_RULE_ID = "9c4f89ac-3a77-56e4-9f10-d765c1236df2"


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column(
        "organization_identities",
        "verification_digit",
    )

    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO identification_type_rules (
                id,
                party_kind,
                country_id,
                identification_type,
                sigla,
                number_pattern,
                number_pattern_description,
                example_value,
                min_age_years,
                max_age_years,
                is_active,
                created_by,
                updated_by
            )
            VALUES (
                CAST(:id AS uuid),
                'ORGANIZATION',
                CAST(:country_id AS uuid),
                'TAX_ID',
                'NIT',
                '^[A-Z0-9]{4,11}-[0-9]$',
                'Numero de Identificacion Tributaria de organizacion: base alfanumerica de 4 a 11 caracteres, guion y digito de verificacion.',
                '900123456-7',
                NULL,
                NULL,
                true,
                CAST(:actor_id AS uuid),
                CAST(:actor_id AS uuid)
            )
            ON CONFLICT (
                party_kind,
                country_id,
                identification_type
            )
            WHERE is_active = true
            DO UPDATE SET
                sigla = EXCLUDED.sigla,
                number_pattern = EXCLUDED.number_pattern,
                number_pattern_description =
                    EXCLUDED.number_pattern_description,
                example_value = EXCLUDED.example_value,
                min_age_years = EXCLUDED.min_age_years,
                max_age_years = EXCLUDED.max_age_years,
                updated_by = EXCLUDED.updated_by,
                updated_at = now()
            """
        ),
        {
            "id": ORGANIZATION_NIT_RULE_ID,
            "country_id": COLOMBIA_COUNTRY_ID,
            "actor_id": SYSTEM_ACTOR_ID,
        },
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            """
            DELETE FROM identification_type_rules
            WHERE id = CAST(:id AS uuid)
            """
        ).bindparams(
            id=ORGANIZATION_NIT_RULE_ID,
        )
    )
    op.add_column(
        "organization_identities",
        sa.Column(
            "verification_digit",
            sa.String(length=5),
            nullable=True,
        ),
    )
