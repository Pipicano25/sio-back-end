"""reset colombia identification types

Revision ID: 0006_reset_co_id_types
Revises: 0005_co_age_rules
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006_reset_co_id_types"
down_revision: Union[str, Sequence[str], None] = "0005_co_age_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLOMBIA_COUNTRY_ID = "cf160c2d-b6de-4ef5-9257-a0a8539058d9"
SYSTEM_ACTOR_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "identification_type_rules",
        sa.Column(
            "sigla",
            sa.String(length=10),
            nullable=True,
        ),
    )
    op.alter_column(
        "identification_type_rules",
        "identification_type",
        existing_type=sa.String(length=20),
        type_=sa.String(length=40),
        existing_nullable=False,
    )

    op.drop_constraint(
        "ck_person_identities_identification_type",
        "person_identities",
        type_="check",
    )
    op.execute(
        sa.text(
            """
            UPDATE person_identities
            SET identification_type = CASE
                WHEN identification_type IN (
                    'CIVIL_REGISTRY'
                ) THEN 'RC'
                WHEN identification_type IN (
                    'IDENTITY_CARD',
                    'IDENTITY_CARD_MODERN',
                    'IDENTITY_CARD_OLD'
                ) THEN 'TI'
                WHEN identification_type IN (
                    'CITIZEN_ID',
                    'CITIZEN_ID_MODERN',
                    'CITIZEN_ID_OLD',
                    'NATIONAL_ID'
                ) THEN 'CC'
                WHEN identification_type IN (
                    'FOREIGN_CARD',
                    'FOREIGN_ID'
                ) THEN 'CE'
                WHEN identification_type = 'TAX_ID' THEN 'NIT'
                ELSE identification_type
            END
            """
        )
    )
    op.create_check_constraint(
        "ck_person_identities_identification_type",
        "person_identities",
        "identification_type IN ('RC', 'TI', 'CC', 'CE', 'NIT')",
    )

    op.drop_constraint(
        "ck_identification_type_rules_identification_type",
        "identification_type_rules",
        type_="check",
    )

    # El usuario solicitó limpiar todos los tipos previos y dejar solo
    # el catálogo colombiano indicado. Se hace antes del nuevo CHECK
    # porque las filas antiguas ya no cumplen el catálogo final.
    op.execute(
        sa.text(
            "DELETE FROM identification_type_rules"
        )
    )

    op.create_check_constraint(
        "ck_identification_type_rules_identification_type",
        "identification_type_rules",
        (
            "identification_type IN ("
            "'CIVIL_REGISTRY', "
            "'IDENTITY_CARD_MODERN', "
            "'CITIZEN_ID_MODERN', "
            "'CITIZEN_ID_OLD', "
            "'FOREIGN_CARD', "
            "'TAX_ID', "
            "'IDENTITY_CARD_OLD'"
            ")"
        ),
    )
    op.create_check_constraint(
        "ck_identification_type_rules_sigla",
        "identification_type_rules",
        "sigla IN ('RC', 'TI', 'CC', 'CE', 'NIT')",
    )

    rules = [
        {
            "id": "f1d6549f-7fbb-58bf-8573-b2c629f3d6ae",
            "identification_type": "CIVIL_REGISTRY",
            "sigla": "RC",
            "number_pattern": "^[0-9]{10}$",
            "number_pattern_description": (
                "Registro Civil de Nacimiento: NUIP numerico de 10 "
                "digitos, permitido de 0 a 6 anos."
            ),
            "example_value": "1000000000",
            "min_age_years": 0,
            "max_age_years": 6,
        },
        {
            "id": "09eb08a5-50fc-51bd-a163-9a8493138f02",
            "identification_type": "IDENTITY_CARD_MODERN",
            "sigla": "TI",
            "number_pattern": "^[0-9]{10}$",
            "number_pattern_description": (
                "Tarjeta de Identidad moderna: NUIP numerico de 10 "
                "digitos, permitido de 7 a 17 anos."
            ),
            "example_value": "1000000000",
            "min_age_years": 7,
            "max_age_years": 17,
        },
        {
            "id": "b645336b-b71e-5006-8990-e791a57014d0",
            "identification_type": "CITIZEN_ID_MODERN",
            "sigla": "CC",
            "number_pattern": "^[0-9]{10}$",
            "number_pattern_description": (
                "Cedula de Ciudadania moderna o digital: NUIP numerico "
                "de 10 digitos, permitido desde los 18 anos."
            ),
            "example_value": "1000000000",
            "min_age_years": 18,
            "max_age_years": None,
        },
        {
            "id": "8628a6ba-2d1c-59fc-a6c9-e8b66452effa",
            "identification_type": "CITIZEN_ID_OLD",
            "sigla": "CC",
            "number_pattern": "^[0-9]{3,8}$",
            "number_pattern_description": (
                "Cedula de Ciudadania antigua: numero numerico de 3 a 8 "
                "digitos, permitido desde los 18 anos."
            ),
            "example_value": "12345678",
            "min_age_years": 18,
            "max_age_years": None,
        },
        {
            "id": "a3e75773-1168-5e38-9a21-7354fe7cf38f",
            "identification_type": "FOREIGN_CARD",
            "sigla": "CE",
            "number_pattern": "^[0-9]{3,7}$",
            "number_pattern_description": (
                "Cedula de Extranjeria: numero numerico de 3 a 7 "
                "digitos, permitido desde los 7 anos."
            ),
            "example_value": "1234567",
            "min_age_years": 7,
            "max_age_years": None,
        },
        {
            "id": "48f7382b-7443-5130-b96e-c19f8f819cc2",
            "identification_type": "TAX_ID",
            "sigla": "NIT",
            "number_pattern": "^[A-Z0-9]{4,11}-[0-9]$",
            "number_pattern_description": (
                "Numero de Identificacion Tributaria: base "
                "alfanumerica de 4 a 11 caracteres, guion y digito "
                "de verificacion."
            ),
            "example_value": "900123456-7",
            "min_age_years": None,
            "max_age_years": None,
        },
        {
            "id": "475acf19-dde0-560d-817f-eec73217fed8",
            "identification_type": "IDENTITY_CARD_OLD",
            "sigla": "TI",
            "number_pattern": "^[0-9]{11}$",
            "number_pattern_description": (
                "Tarjeta de Identidad antigua o NIP: numero numerico "
                "de 11 digitos, permitido de 7 a 17 anos."
            ),
            "example_value": "19991234567",
            "min_age_years": 7,
            "max_age_years": 17,
        },
    ]

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
                'PERSON',
                CAST(:country_id AS uuid),
                :identification_type,
                :sigla,
                :number_pattern,
                :number_pattern_description,
                :example_value,
                :min_age_years,
                :max_age_years,
                true,
                CAST(:actor_id AS uuid),
                CAST(:actor_id AS uuid)
            )
            """
        ),
        [
            {
                **rule,
                "country_id": COLOMBIA_COUNTRY_ID,
                "actor_id": SYSTEM_ACTOR_ID,
            }
            for rule in rules
        ],
    )

    op.alter_column(
        "identification_type_rules",
        "sigla",
        existing_type=sa.String(length=10),
        nullable=False,
    )
    op.create_index(
        "ix_identification_type_rules_sigla",
        "identification_type_rules",
        ["sigla"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_identification_type_rules_sigla",
        table_name="identification_type_rules",
    )
    op.drop_constraint(
        "ck_identification_type_rules_sigla",
        "identification_type_rules",
        type_="check",
    )
    op.drop_column(
        "identification_type_rules",
        "sigla",
    )
