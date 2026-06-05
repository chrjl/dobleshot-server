from __future__ import annotations

from sqlalchemy import select, outerjoin, or_
from db import models
from .base import Base
from .utilities import suborigins_cte

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self
    from sqlalchemy import Select


class CoffeeComponent(Base[models.CoffeeComponent]):
    def __init__(self, *ids: int):
        super().__init__(models.CoffeeComponent, *ids)

    def filter_by_roasted_coffee(
        self,
        roasted_ids: list[int] | Select[tuple[models.RoastedCoffee]] = [],
    ) -> Self:
        self._filters.append(models.CoffeeComponent.roasted_id.in_(roasted_ids))

        return self

    def filter_by_green_coffee(
        self,
        green_ids: list[int] | Select[tuple[models.GreenCoffee]] = [],
    ) -> Self:
        self._filters.append(models.CoffeeComponent.green_id.in_(green_ids))

        return self

    def filter_by_origin(
        self,
        origin_ids: list[int] | Select[tuple[models.Origin]] = [],
        include_suborigins: bool = False,
    ) -> Self:

        if include_suborigins:
            self._filters.append(
                or_(
                    models.CoffeeComponent.origin_id.in_(
                        select(suborigins_cte(origin_ids))
                    ),
                    models.GreenCoffee.origin_id.in_(
                        select(suborigins_cte(origin_ids))
                    ),
                )
            )
        else:
            self._filters.append(
                or_(
                    models.CoffeeComponent.origin_id.in_(origin_ids),
                    models.GreenCoffee.origin_id.in_(origin_ids),
                )
            )

        self._joins.append(
            outerjoin(
                models.CoffeeComponent,
                models.GreenCoffee,
                models.CoffeeComponent.green_id == models.GreenCoffee.id,
            )
        )

        return self
