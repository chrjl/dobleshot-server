from __future__ import annotations

from sqlalchemy import join, outerjoin

from db import models
from .base import Base
from .utilities.filters import LocationFilter, location_filter_clauses


class Roaster(Base[models.Roaster]):
    def __init__(self, *ids: int):
        super().__init__(models.Roaster, *ids)

    def filter_by_location(self, filter: LocationFilter):
        if not filter:
            return self

        self._joins.append(
            join(
                models.Roaster,
                models.Country,
                models.Roaster.country == models.Country.id,
            )
        )

        self._filters.extend(location_filter_clauses(filter))

        return self
