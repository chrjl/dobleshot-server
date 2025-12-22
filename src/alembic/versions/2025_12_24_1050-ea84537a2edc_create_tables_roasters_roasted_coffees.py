"""create tables: roasters, roasted coffees

Revision ID: ea84537a2edc
Revises:
Create Date: 2025-12-24 10:50:57.898108

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ea84537a2edc"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "roasters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("equipment_brand", sa.String(), nullable=True),
        sa.Column("equipment_model", sa.String(), nullable=True),
        sa.Column("equipment_capacity", sa.Float(), nullable=True),
        sa.Column(
            "details",
            sa.JSON(),
            nullable=True,
            comment="Can include contact information, website, socials profiles, location details, etc.",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "roasted_coffees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_blend", sa.Boolean(), nullable=False),
        sa.Column("roaster_id", sa.Integer(), nullable=False),
        sa.Column(
            "profile",
            sa.ARRAY(sa.String()),
            nullable=True,
            comment="A list of the roaster's intended roast attributes, e.g. dark roast, espresso, cold brew.",
        ),
        sa.Column(
            "notes",
            sa.ARRAY(sa.String()),
            nullable=True,
            comment="A list of the roaster's tasting notes.",
        ),
        sa.Column("prices", sa.JSON(), nullable=True),
        sa.Column("date_added", sa.DateTime(), nullable=False),
        sa.Column("date_updated", sa.DateTime(), nullable=True),
        sa.Column("date_removed", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["roaster_id"],
            ["roasters.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Roasted coffee products for sale or use in preparation of drinks.",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("roasted_coffees")
    op.drop_table("roasters")
