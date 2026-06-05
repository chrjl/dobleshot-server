from __future__ import annotations

from sqlalchemy import select
from db import models, queries
from db.queries.origins import suborigin_ids_cte
from .base import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy import Select
    from .utilities.filters import NameFilter


class Country(Base[models.Country]):
    def __init__(self, *ids: str):
        super().__init__(models.Country, *ids)

    def filter_by_name(self, filter: NameFilter, name_column="name"):
        return super().filter_by_name(filter, name_column)

    def origin(self):
        """List of `Origin` objects directly corresponding to `Country`.

        See also: `suborigins`
        """

        return select(models.Origin).where(
            models.Origin.id.in_(self.select(["origin_id"]))
        )

    def suborigins(self):
        """List of suborigin `Origin` objects of a `Country`, inclusive."""
        pass

    def roasters(self) -> Select[tuple[models.Roaster]]:
        return (
            select(models.Roaster)
            .join_from(
                models.Country,
                models.Roaster,
                models.Roaster.country == models.Country.id,
            )
            .where(models.Country.id.in_(self.select(["id"])))
        )

    def roasted_coffees(self) -> Select[tuple[models.RoastedCoffee]]:
        """
        List of `RoastedCoffee` objects that have components from a `Country`,
        including its subregions.

        Resolves both generic origin components (unknown specific green coffee)
        and origins of known green coffee components.
        """

        return (
            queries.Origin()
            .filter_by_ids(select(suborigin_ids_cte(self.select(["origin_id"]))))
            .get("roasted_coffees")
        )

    def green_coffees(self) -> Select[tuple[models.GreenCoffee]]:
        """List of `GreenCoffee` objects of a `Country`, including its suborigins."""

        return (
            queries.Origin()
            .filter_by_ids(select(suborigin_ids_cte(self.select(["origin_id"]))))
            .get("green_coffees")
        )
