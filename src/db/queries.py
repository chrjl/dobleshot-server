from sqlalchemy import Engine, func, select, bindparam, or_
from sqlalchemy.orm import Session, aliased
from .models import CoffeeComponent, GreenCoffee, RoastedCoffee, Origin, Country

from sqlalchemy import BindParameter, CTE, Select, Subquery
from collections.abc import Sequence


def suborigins_cte(origin_id: int | BindParameter | Select) -> CTE:
    """Selectable CTE of all suborigin `origin_id`s of an origin (inclusive).

    Args:
        origin_id (int):
            Either the `id` from the `origins` table, or a bound parameter or
            selectable that provides it.

    Returns:
        sqlalchemy.CTE:
            Recursive CTE that, when selected, returns a single column of `id`s
            of the `origins` table.

    Usage:
        (
            select(Origin)
            .where(
                Origin.id.in_.select(suborigins_cte(bindparam("origin_id"))
            ),
            {"origin_id": 1},
        )

        suborigin_list = aliased(Origin, suborigins_cte(origin_id))
        select(suborigin_list)
    """
    cte = select(Origin.id).where(Origin.id == origin_id).cte(recursive=True)
    return cte.union_all(select(Origin.id).join(cte, cte.c.id == Origin.parent_id))


def suborigins_list_subq(
    *, origin_id: int | None = None, country_id: str | None = None
) -> Subquery:
    if not origin_id and not country_id:
        raise Exception

    return (
        select(suborigins_cte(bindparam("origin_id")))
        if origin_id
        else select(
            suborigins_cte(
                select(Origin.id)
                .join(Country, Country.name == Origin.name)
                .where(Country.id == bindparam("country_id"))
            )
        )
    ).subquery()


def get_origins_of_roasted_coffee(engine: Engine, roasted_id: int) -> Sequence[Origin]:
    """List of `Origin` objects of components of a `RoastedCoffee`.

    Args:
        engine (sqlalchemy.Engine)
        roasted_id (int)

    Returns:
        list[Origin]:
            Resolves both:
            - Generic origin components (unknown specific green coffee).
            - Origins of known green coffee components.
    """
    origin_id_query = (
        select(func.coalesce(CoffeeComponent.origin_id, GreenCoffee.origin_id))
        .select_from(CoffeeComponent)
        .outerjoin(Origin, Origin.id == CoffeeComponent.origin_id)
        .outerjoin(GreenCoffee, GreenCoffee.id == CoffeeComponent.green_id)
        .where(
            CoffeeComponent.roasted_id == bindparam("roasted_id"),
        )
    )

    with Session(engine) as session:
        return session.scalars(
            select(Origin).where(Origin.id.in_(origin_id_query)),
            {"roasted_id": roasted_id},
        ).all()


def get_suborigins(
    engine: Engine,
    *,
    origin_id: int | None = None,
    country_id: str | None = None,
) -> Sequence[Origin]:
    """List of suborigin `Origin` objects of an `Origin`, inclusive.

    Args:
        engine (sqlalchemy.Engine)

    Keyword args, one of:
        origin_id (int)
        country_id (str)

    Returns:
        list[GreenCoffee]
    """

    origins_q = select(Origin).where(
        Origin.id.in_(
            select(suborigins_list_subq(origin_id=origin_id, country_id=country_id))
        )
    )

    with Session(engine) as session:
        return session.scalars(
            origins_q, {"origin_id": origin_id, "country_id": country_id}
        ).all()


def get_green_coffees_of_origin(
    engine: Engine,
    *,
    origin_id: int | None = None,
    country_id: str | None = None,
) -> Sequence[GreenCoffee]:
    """List of `GreenCoffee` objects of an `Origin`, including its suborigins.

    Args:
        engine (sqlalchemy.Engine)

    Keyword args, one of:
        origin_id (int)
        country_id (str)

    Returns:
        list[GreenCoffee]
    """

    green_coffees_q = select(GreenCoffee).where(
        GreenCoffee.origin_id.in_(
            select(suborigins_list_subq(origin_id=origin_id, country_id=country_id))
        )
    )

    with Session(engine) as session:
        return session.scalars(
            green_coffees_q, {"origin_id": origin_id, "country_id": country_id}
        ).all()


def get_roasted_coffees_of_origin(
    engine: Engine,
    *,
    origin_id: int | None = None,
    country_id: str | None = None,
) -> Sequence[RoastedCoffee]:
    """
    List of `RoastedCoffee` objects that have components from an `Origin`,
    including its subregions.

    Args:
        engine (sqlalchemy.Engine)

    Keyword args, one of:
        origin_id (int)
        country_id (str)

    Returns:
        list[RoastedCoffee]:
            Resolves both generic origin components (unknown specific green
            coffee) and origins of known green coffee components.
    """
    origins_list_q = select(
        suborigins_list_subq(origin_id=origin_id, country_id=country_id)
    )

    roasted_coffees_q = (
        select(RoastedCoffee)
        .join(CoffeeComponent)
        .outerjoin(GreenCoffee)
        .where(
            or_(
                CoffeeComponent.origin_id.in_(origins_list_q),
                GreenCoffee.origin_id.in_(origins_list_q),
            )
        )
    )

    with Session(engine) as session:
        return session.scalars(
            roasted_coffees_q, {"origin_id": origin_id, "country_id": country_id}
        ).all()
