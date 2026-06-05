from __future__ import annotations

from sqlalchemy import select, or_, null
from db import models
from .base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy import BindParameter, Select, CompoundSelect, CTE


def suborigin_ids_cte(origin_ids: list[int] | BindParameter | Select) -> CTE:
    """Selectable CTE of all suborigin `origin_id`s of an origin (inclusive).

    Args:
        origin_ids (int):
            Either a list of `id`s from the `origins` table, or a bound
            parameter or selectable that provide it.

    Returns:
        sqlalchemy.CTE:
            Recursive CTE that, when selected, returns a single column of `id`s
            of the `origins` table.
            Either a list of `id`s from the `origins` table, or a bound parameter or
            selectable that provide it.
    Usage:
        (
            select(Origin)
            .where(
                Origin.id.in_.select(suborigin_ids_cte(bindparam("origin_id"))
            ),
            {"origin_id": 1},
        )

        suborigin_list = aliased(Origin, suborigin_ids_cte(origin_id))
        select(suborigin_list)
    """
    cte = (
        select(models.Origin.id)
        .where(models.Origin.id.in_(origin_ids))
        .cte(recursive=True)
    )
    return cte.union_all(
        select(models.Origin.id).join(cte, cte.c.id == models.Origin.parent_id)
    )


class Origin(Base[models.Origin]):
    def __init__(self, *ids: int):
        super().__init__(models.Origin, *ids)

    def suborigin_ids(self) -> Select[tuple[int]]:
        return select(suborigin_ids_cte(origin_ids=self.select(["id"])))

    def suborigins(self, cols: list[str] | None = None) -> Select[tuple[models.Origin]]:
        """List of suborigin `Origin` objects, inclusive.

        Optional args:
            cols (list[str]): list of columns of `Origin` objects to return
        """
        select_stmt = (
            select(models.Origin)
            if cols is None
            else select(*[getattr(models.Origin, col) for col in cols])
        )

        return select_stmt.where(
            models.Origin.id.in_(
                select(suborigin_ids_cte(origin_ids=self.select(["id"])))
            )
        )

    def green_coffees(
        self, cols: list[str] | None = None
    ) -> Select[tuple[models.GreenCoffee]]:
        """
        List of `GreenCoffee` objects of all of the class' origins, including
        all suborigins.

        Optional args:
            cols (list[str]): list of columns of `Origin` objects to return
        """
        select_stmt = (
            select(models.GreenCoffee)
            if cols is None
            else select(*[getattr(models.GreenCoffee, col) for col in cols])
        )

        return select_stmt.join(models.Origin).where(
            models.Origin.id.in_(self.suborigins(["id"]))
        )

    def roasted_coffees(
        self, cols: list[str] | None = None
    ) -> Select[tuple[models.RoastedCoffee]]:
        """
        List of `RoastedCoffee` objects that have components from any of the
        class' origins, including all suborigins.

        Resolves both generic origin components (unknown specific green coffee)
        and origins of known green coffee components.
        """
        select_stmt = (
            select(models.RoastedCoffee)
            if cols is None
            else select(*[getattr(models.RoastedCoffee, col) for col in cols])
        )

        return (
            select_stmt.join_from(models.RoastedCoffee, models.CoffeeComponent)
            .outerjoin_from(models.CoffeeComponent, models.GreenCoffee)
            .where(
                or_(
                    models.GreenCoffee.origin_id.in_(self.suborigins(["id"])),
                    models.CoffeeComponent.origin_id.in_(self.suborigins(["id"])),
                )
            )
        )

    def processes(self) -> CompoundSelect[tuple[str]]:
        """Green coffee processing methods of cataloged coffees."""

        # From green coffees
        green_coffee_processes = select(models.GreenCoffeeTag.value).where(
            models.GreenCoffeeTag.type == "process",
            models.GreenCoffeeTag.green_id.in_(self.green_coffees(["id"])),
        )

        # From anonymous components
        generic_component_processes = select(models.CoffeeComponent.process).where(
            models.CoffeeComponent.origin_id.in_(self.select(["id"]))
        )

        return green_coffee_processes.union(generic_component_processes)

    def varieties(self) -> CompoundSelect[tuple[str]]:
        """Varieties of cataloged coffees."""

        # From green coffees
        green_coffee_varieties = select(models.GreenCoffeeTag.value).where(
            models.GreenCoffeeTag.type == "variety",
            models.GreenCoffeeTag.green_id.in_(self.green_coffees(["id"])),
        )

        # From anonymous components
        generic_component_varieties = select(
            # func.json_query(models.CoffeeComponent.details, "$.variety")
            models.CoffeeComponent.details["variety"]
        ).where(
            models.CoffeeComponent.origin_id.in_(self.select(["id"])),
            models.CoffeeComponent.details["variety"].as_string() != "null",
        )

        return green_coffee_varieties.union(generic_component_varieties)

    def roasters(self) -> Select[tuple[models.Roaster]]:
        """Roasters of catalogued coffees."""
        return (
            select(models.Roaster)
            .join_from(models.Roaster, models.RoastedCoffee)
            .join_from(models.RoastedCoffee, models.CoffeeComponent)
            .outerjoin_from(models.CoffeeComponent, models.GreenCoffee)
            .where(
                or_(
                    models.GreenCoffee.id.in_(self.green_coffees(["id"])),
                    models.CoffeeComponent.origin_id.in_(self.suborigins(["id"])),
                )
            )
        )
