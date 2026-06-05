from __future__ import annotations

from sqlalchemy import select, join, and_, func
from .base import Base
from db import models
from db.queries.component_associations import CoffeeComponent
from db.utilities import normalized_text

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self
    from sqlalchemy import Select


class GreenCoffee(Base[models.GreenCoffee]):
    def __init__(self, *ids: int):
        super().__init__(models.GreenCoffee, *ids)

    def filter_by_tag(self, tag_name: str, values: list[str] = []) -> Self:
        self._joins.append(
            join(
                models.GreenCoffee,
                models.GreenCoffeeTag,
                models.GreenCoffee.id == models.GreenCoffeeTag.green_id,
            )
        )

        self._filters.append(
            and_(
                func.lower(models.GreenCoffeeTag.value).in_(
                    [normalized_text(value) for value in values]
                ),
                models.GreenCoffeeTag.type == tag_name,
            )
        )

        return self

    def filter_by_process(self, processes: list[str] = []) -> Self:
        self.filter_by_tag("process", processes)
        return self

    def filter_by_variety(self, varieties: list[str] = []) -> Self:
        self.filter_by_tag("variety", varieties)
        return self

    def filter_by_tasting(self, tasting_notes: list[str] = []) -> Self:
        self.filter_by_tag("tasting", tasting_notes)
        return self

    def origins(self) -> Select[tuple[models.Origin]]:
        return (
            select(models.Origin)
            .join(models.GreenCoffee)
            .where(models.GreenCoffee.id.in_(self.select(["id"])))
        )

    def processes(self) -> Select[tuple[str]]:
        return select(models.GreenCoffeeTag.value).where(
            models.GreenCoffeeTag.type == "process",
            models.GreenCoffeeTag.green_id.in_(self.select(["id"])),
        )

    def varieties(self) -> Select[tuple[str]]:
        return select(models.GreenCoffeeTag.value).where(
            models.GreenCoffeeTag.type == "variety",
            models.GreenCoffeeTag.green_id.in_(self.select(["id"])),
        )

    def tasting(self) -> Select[tuple[str]]:
        return select(models.GreenCoffeeTag.value).where(
            models.GreenCoffeeTag.type == "tasting",
            models.GreenCoffeeTag.green_id.in_(self.select(["id"])),
        )

    def roasters(self) -> Select[tuple[models.Roaster]]:
        return (
            select(models.Roaster)
            .group_by(models.Roaster.id)
            .join_from(models.Roaster, models.RoastedCoffee)
            .join_from(models.RoastedCoffee, models.CoffeeComponent)
            .join_from(models.CoffeeComponent, models.GreenCoffee)
            .where(models.GreenCoffee.id.in_(self.select(["id"])))
        )

    def associations(self) -> Select[tuple[models.CoffeeComponent]]:
        return select(models.CoffeeComponent).where(
            models.CoffeeComponent.green_id.in_(self.select(["id"]))
        )
        return CoffeeComponent().filter_by_green_coffee(self.select(["id"])).select()
