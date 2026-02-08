"""refactor origin to country and regions

Revision ID: e3ff81cf0bba
Revises: 052eae0af0e0
Create Date: 2026-02-02 06:55:30.440360

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm
import sqlalchemy.sql as sql

from bin.seed_countries_regions import (
    generate_country_data,
    generate_origin_objects,
)


# revision identifiers, used by Alembic.
revision: str = "e3ff81cf0bba"
down_revision: Union[str, Sequence[str], None] = "052eae0af0e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    components_table = sql.table(
        "roasted_coffee_components",
        sql.column("roasted_id", sa.Integer),
        sql.column("green_id", sa.Integer),
        sql.column("origin_id", sa.Integer),
        sql.column("process", sa.String),
    )
    prev_origins_table = sql.table(
        "origins_previous",
        sql.column("id", sa.Integer),
        sql.column("country", sa.String(2)),
        sql.column("region", sa.String),
    )
    green_coffees_table = sql.table(
        "green_coffees",
        sql.column("id", sa.Integer),
        sql.column("name", sa.String),
        sql.column("region_id", sa.Integer),
        sql.column("origin_id", sa.Integer),
        sql.column("process", sa.String),
    )

    connection = op.get_bind()

    """Upgrade schema."""
    # Create and seed countries table
    countries_table = op.create_table(
        "countries",
        sa.Column("id", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("long_name", sa.String, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        comment="List of countries attributed to US Dept. of State; coffee data attributed to Cafe Imports.",
    )

    country_data = generate_country_data()

    op.bulk_insert(
        countries_table,
        [{"id": id, **country_data} for id, country_data in country_data.items()],
        multiinsert=False,
    )

    # Create and seed new origins table
    op.rename_table("origins", "origins_previous")

    origins_table = op.create_table(
        "origins",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("origins.id")),
        sa.Column(
            "country_id", sa.String(2), sa.ForeignKey("countries.id"), nullable=False
        ),
        sa.Column("processes", sa.JSON, server_default="[]"),
        sa.Column("varieties", sa.JSON, server_default="[]"),
        sa.Column("harvest_start", sa.Integer, nullable=True),
        sa.Column("harvest_end", sa.Integer, nullable=True),
        sa.Column("details", sa.JSON, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
        comment="Data attributed to Cafe Imports.",
    )

    origin_objs = generate_origin_objects()

    with orm.Session(connection) as session:
        session.add_all(origin_objs)
        session.commit()

    # Add the new origin model to green_coffees
    op.add_column(
        "green_coffees",
        sa.Column("origin_id", sa.Integer, sa.ForeignKey("origins.id"), nullable=True),
    )

    country_name_subq = (
        sa.select(countries_table.c.name)
        .where(countries_table.c.id == origins_table.c.country_id)
        .scalar_subquery()
    )

    origin_id_subq = (
        sa.select(origins_table.c.id)
        .select_from(origins_table)
        .join(
            prev_origins_table,
            sa.and_(
                prev_origins_table.c.country == origins_table.c.country_id,
                sa.func.lower(origins_table.c.name)
                == sa.case(
                    (
                        prev_origins_table.c.region == None,
                        sa.func.lower(country_name_subq),
                    ),
                    else_=sa.func.lower(prev_origins_table.c.region),
                ),
            ),
        )
        .where(prev_origins_table.c.id == green_coffees_table.c.region_id)
    ).scalar_subquery()

    connection.execute(
        sa.update(green_coffees_table).values(
            {"origin_id": origin_id_subq},
        )
    )

    # Refactor green_coffees × roasted_coffee_components
    # Refactor anonymous green coffees into origin_id × process in components table
    # Remove anonymous green coffees from green_coffees table
    op.drop_constraint("roasted_coffee_components_pkey", "roasted_coffee_components")
    op.add_column(
        "roasted_coffee_components",
        sa.Column(
            "id",
            sa.Integer,
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
    )
    op.add_column(
        "roasted_coffee_components",
        sa.Column("origin_id", sa.Integer, sa.ForeignKey("origins.id"), nullable=True),
    )
    op.add_column(
        "roasted_coffee_components",
        sa.Column("process", sa.String, nullable=True),
    )
    op.add_column(
        "roasted_coffee_components",
        sa.Column("details", sa.JSON, nullable=True, server_default="{}"),
    )
    op.alter_column(
        "roasted_coffee_components", "green_id", existing_nullable=False, nullable=True
    )
    op.create_check_constraint(
        "ck_component_or_origin",
        "roasted_coffee_components",
        ~(
            sa.and_(
                components_table.c.green_id != None,
                components_table.c.origin_id != None,
            )
        ),
    )

    connection.execute(
        sa.update(components_table)
        .where(components_table.c.green_id == green_coffees_table.c.id)
        .where(green_coffees_table.c.name == None)
        .values(
            {
                "green_id": None,
                "origin_id": green_coffees_table.c.origin_id,
                "process": green_coffees_table.c.process,
            }
        )
    )

    connection.execute(
        sa.delete(green_coffees_table).where(green_coffees_table.c.name == None)
    )

    op.alter_column(
        "green_coffees", "origin_id", existing_nullable=True, nullable=False
    )

    # Drop previous origins table
    op.drop_column("green_coffees", "region_id")
    op.drop_table("origins_previous")


def downgrade() -> None:
    green_coffees_table = sql.table(
        "green_coffees",
        sql.column("id", sa.Integer),
        sql.column("name", sa.String),
        sql.column("region_id", sa.Integer),
        sql.column("origin_id", sa.Integer),
        sql.column("process", sa.String),
    )
    components_table = sql.table(
        "roasted_coffee_components",
        sql.column("roasted_id", sa.Integer),
        sql.column("green_id", sa.Integer),
        sql.column("origin_id", sa.Integer),
        sql.column("process", sa.String),
    )
    prev_origins_table = sql.table(
        "origins_previous",
        sql.column("id", sa.Integer),
        sql.column("country", sa.String(2)),
        sql.column("region", sa.String),
    )
    origins_table = sql.table(
        "origins",
        sa.Column("id", sa.Integer),
        sa.Column("parent_id", sa.Integer),
        sa.Column("name", sa.String),
        sa.Column("country_id", sa.String),
    )
    countries_table = sql.table(
        "countries",
        sa.Column("id", sa.String, nullable=False),
        sa.Column("name", sa.String, nullable=False),
    )

    connection = op.get_bind()

    """Downgrade schema."""
    # Re-create and populate old origins table
    prev_origins_table = op.create_table(
        "origins_previous",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("country", sa.String(2)),
        sa.Column("region", sa.String),
    )

    connection.execute(
        sa.insert(prev_origins_table).from_select(
            ["country", "region"],
            sa.union(
                sa.select(origins_table.c.country_id, origins_table.c.name)
                .select_from(green_coffees_table)
                .join(
                    origins_table, origins_table.c.id == green_coffees_table.c.origin_id
                ),
                sa.select(
                    origins_table.c.country_id,
                    sa.case(
                        (origins_table.c.parent_id != None, origins_table.c.name),
                        else_=None,
                    ),
                )
                .select_from(components_table)
                .join(
                    origins_table, origins_table.c.id == components_table.c.origin_id
                ),
            ),
        )
    )

    op.add_column("green_coffees", sa.Column("region_id", sa.Integer))

    # Undo refactoring of anonymous (region-generic) green coffees
    op.drop_constraint("ck_component_or_origin", "roasted_coffee_components")

    connection.execute(
        sa.insert(green_coffees_table).from_select(
            ["origin_id", "process"],
            sa.select(components_table.c.origin_id, components_table.c.process)
            .distinct()
            .where(components_table.c.green_id == None),
        )
    )

    country_name_subq = (
        sa.select(countries_table.c.name)
        .where(countries_table.c.id == origins_table.c.country_id)
        .scalar_subquery()
    )

    region_id_subq = (
        sa.select(prev_origins_table.c.id)
        .select_from(prev_origins_table)
        .join(
            origins_table,
            sa.and_(
                origins_table.c.country_id == prev_origins_table.c.country,
                sa.func.lower(origins_table.c.name)
                == sa.case(
                    (
                        prev_origins_table.c.region == None,
                        sa.func.lower(country_name_subq),
                    ),
                    else_=sa.func.lower(prev_origins_table.c.region),
                ),
            ),
        )
        .where(origins_table.c.id == green_coffees_table.c.origin_id)
    ).scalar_subquery()

    connection.execute(
        sa.update(green_coffees_table)
        .where(green_coffees_table.c.region_id == None)
        .values({"region_id": region_id_subq})
    )

    connection.execute(
        sa.update(components_table)
        .where(components_table.c.green_id == None)
        .where(green_coffees_table.c.origin_id == components_table.c.origin_id)
        .values({"green_id": green_coffees_table.c.id})
    )

    op.alter_column(
        "roasted_coffee_components", "green_id", existing_nullable=True, nullable=False
    )
    op.create_primary_key(
        "roasted_coffee_components_pkey",
        "roasted_coffee_components",
        ["roasted_id", "green_id"],
    )
    op.drop_column("roasted_coffee_components", "id")
    op.drop_column("roasted_coffee_components", "process")
    op.drop_column("roasted_coffee_components", "origin_id")
    op.drop_column("roasted_coffee_components", "details")

    # Remove the new origin model from green_coffees
    op.drop_column("green_coffees", "origin_id")
    op.create_foreign_key(
        None, "green_coffees", "origins_previous", ["region_id"], ["id"]
    )
    op.alter_column(
        "green_coffees", "region_id", existing_nullable=True, nullable=False
    )

    # Drop tables
    op.drop_table("origins")
    op.rename_table("origins_previous", "origins")
    op.drop_table("countries")
