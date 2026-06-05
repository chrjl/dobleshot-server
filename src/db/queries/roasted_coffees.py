from __future__ import annotations

from sqlalchemy import select, join, func, and_, or_
from .base import Base
from db import models
from db.queries.component_associations import CoffeeComponent
from db.utilities import normalized_text

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self
    from sqlalchemy import Select, CompoundSelect


class RoastedCoffee(Base[models.RoastedCoffee]):
    def __init__(self, *ids: int):
        super().__init__(models.RoastedCoffee, *ids)

    def filter_by_tag(self, tag_name: str, values: list[str] = []) -> Self:
        self._joins.append(
            join(
                models.RoastedCoffee,
                models.RoastedCoffeeTag,
                models.RoastedCoffee.id == models.RoastedCoffeeTag.roasted_id,
            )
        )

        self._filters.append(
            and_(
                func.lower(models.RoastedCoffeeTag.value).in_(
                    [normalized_text(value) for value in values]
                ),
                models.RoastedCoffeeTag.type == tag_name,
            )
        )

        return self

    def filter_by_profile(self, profiles: list[str] = []) -> Self:
        self.filter_by_tag("profile", profiles)
        return self

    def filter_by_tasting(self, tasting_notes: list[str] = []) -> Self:
        self.filter_by_tag("tasting", tasting_notes)
        return self

    def filter_by_process(self, processes: list[str] = []) -> Self:
        processes = [normalized_text(process) for process in processes]

        self._joins.append(
            join(
                models.RoastedCoffee,
                models.CoffeeComponent,
                models.RoastedCoffee.id == models.CoffeeComponent.roasted_id,
            )
            .outerjoin(
                models.GreenCoffee,
                models.CoffeeComponent.green_id == models.GreenCoffee.id,
            )
            .join(
                models.GreenCoffeeTag,
                models.GreenCoffee.id == models.GreenCoffeeTag.green_id,
            ),
        )

        self._filters.append(
            or_(
                models.CoffeeComponent.process.in_(processes),
                and_(
                    models.GreenCoffeeTag.value.in_(processes),
                    models.GreenCoffeeTag.type == "process",
                ),
            )
        )

        return self

    def filter_by_variety(self, varieties: list[str] = []) -> Self:
        varieties = [normalized_text(variety) for variety in varieties]

        self._joins.append(
            join(
                models.RoastedCoffee,
                models.CoffeeComponent,
                models.RoastedCoffee.id == models.CoffeeComponent.roasted_id,
            )
            .outerjoin(
                models.GreenCoffee,
                models.CoffeeComponent.green_id == models.GreenCoffee.id,
            )
            .join(
                models.GreenCoffeeTag,
                models.GreenCoffee.id == models.GreenCoffeeTag.green_id,
            ),
        )

        self._filters.append(
            or_(
                func.lower(models.CoffeeComponent.details["variety"].as_string()).in_(
                    varieties
                ),
                and_(
                    func.lower(models.GreenCoffeeTag.value).in_(varieties),
                    models.GreenCoffeeTag.type == "variety",
                ),
            )
        )

        return self

    def origins(self) -> Select[tuple[models.Origin]]:
        """List of `Origin` objects of components of a `RoastedCoffee`.

        Resolves both:
        - Generic origin components (unknown specific green coffee).
        - Origins of known green coffee components.
        """

        origin_ids_q = (
            select(
                func.coalesce(
                    models.CoffeeComponent.origin_id, models.GreenCoffee.origin_id
                )
            )
            .distinct()
            .select_from(models.CoffeeComponent)
            .outerjoin_from(models.CoffeeComponent, models.GreenCoffee)
            .where(
                models.CoffeeComponent.roasted_id.in_(self.select(["id"])),
            )
        )

        return select(models.Origin).where(models.Origin.id.in_(origin_ids_q))

    def processes(self) -> CompoundSelect[tuple[str]]:
        """Return all green coffee processing methods of component coffees."""

        green_coffee_query = (
            select(models.GreenCoffeeTag.value)
            .distinct()
            .select_from(models.RoastedCoffee)
            .join_from(models.RoastedCoffee, models.CoffeeComponent)
            .join_from(models.CoffeeComponent, models.GreenCoffee)
            .join_from(models.GreenCoffee, models.GreenCoffeeTag)
            .where(
                models.GreenCoffeeTag.type == "process",
                models.RoastedCoffee.id.in_(self.select(["id"])),
            )
        )

        generic_component_query = (
            select(models.CoffeeComponent.process)
            .distinct()
            .select_from(models.RoastedCoffee)
            .join_from(models.RoastedCoffee, models.CoffeeComponent)
            .where(
                models.RoastedCoffee.id.in_(self.select(["id"])),
                models.CoffeeComponent.process.is_not(None),
            )
        )

        return green_coffee_query.union(generic_component_query)

    def varieties(self) -> Select[tuple[str]]:
        """Return all varieties of component coffees."""

        return (
            select(models.GreenCoffeeTag.value)
            .select_from(models.RoastedCoffee)
            .join_from(models.RoastedCoffee, models.CoffeeComponent)
            .join_from(models.CoffeeComponent, models.GreenCoffee)
            .join_from(models.GreenCoffee, models.GreenCoffeeTag)
            .where(
                models.GreenCoffeeTag.type == "variety",
                models.RoastedCoffee.id.in_(self.select(["id"])),
            )
        )

    def tasting(self) -> Select[tuple[str]]:
        """Return the roaster's provided tasting notes."""

        return select(models.RoastedCoffeeTag.value).where(
            models.RoastedCoffeeTag.type == "tasting",
            models.RoastedCoffeeTag.roasted_id.in_(self.select(["id"])),
        )

    def profiles(self) -> Select[tuple[str]]:
        """Return the roaster's intended roast profiles."""

        return select(models.RoastedCoffeeTag.value).where(
            models.RoastedCoffeeTag.type == "profile",
            models.RoastedCoffeeTag.roasted_id.in_(self.select(["id"])),
        )

    def associations(self) -> Select[tuple[models.CoffeeComponent]]:
        return select(models.CoffeeComponent).where(
            models.CoffeeComponent.roasted_id.in_(self.select(["id"]))
        )
        return CoffeeComponent().filter_by_roasted_coffee(self.select(["id"])).select()

