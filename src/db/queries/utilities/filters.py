from typing import TypedDict, Literal
from sqlalchemy import ColumnElement, func, or_, and_, select
from db.utilities import normalized_text
from db import models
from .suborigins_cte import suborigins_cte


class NameFilter(TypedDict, total=False):
    starts_with: str | None
    contains: str | None


class CoffeeFilter(TypedDict, total=False):
    origins: list[int]
    categories: list[Literal["BLEND", "SINGLE", "DECAF"]]
    profiles: list[str]
    processes: list[str]
    varieties: list[str]


class LocationFilter(TypedDict, total=False):
    city: str
    state: str
    country_code: str
    country_name: str


class Filter(NameFilter, CoffeeFilter):
    pass


def name_filter_clauses(
    filter: NameFilter | None, model, name_column: str = "_name_n"
) -> list[ColumnElement]:
    if filter is None:
        return []

    filter_clauses: list[ColumnElement] = []

    if starts_with := filter.get("starts_with", None):
        filter_clauses.append(
            func.lower(getattr(model, name_column)).like(
                (f"{normalized_text(starts_with)}%")
            )
        )

    if contains := filter.get("contains", None):
        filter_clauses.append(
            func.lower(getattr(model, name_column)).like(
                (f"%{normalized_text(contains)}%")
            )
        )

    return filter_clauses


def coffee_filter_clauses(filter: CoffeeFilter) -> list[ColumnElement]:
    filter_clauses: list[ColumnElement] = []

    if origins := filter.get("origins"):
        filter_clauses.append(
            or_(
                models.GreenCoffee.origin_id.in_(select(suborigins_cte(origins))),
                models.CoffeeComponent.origin_id.in_(select(suborigins_cte(origins))),
            )
        )

    if categories := filter.get("categories", []):
        filter_clauses.append(
            and_(
                models.RoastedCoffeeTag.type == "profile",
                func.lower(models.RoastedCoffeeTag.value).in_(
                    [normalized_text(c) for c in categories]
                ),
            )
        )

    if profiles := filter.get("profiles", []):
        filter_clauses.append(
            and_(
                models.RoastedCoffeeTag.type == "profile",
                func.lower(models.RoastedCoffeeTag.value).in_(
                    [normalized_text(p) for p in profiles]
                ),
            )
        )

    if processes := filter.get("processes", []):
        filter_clauses.append(
            or_(
                and_(
                    models.GreenCoffeeTag.type == "process",
                    func.lower(models.GreenCoffeeTag.value).in_(
                        [normalized_text(p) for p in processes]
                    ),
                ),
                models.CoffeeComponent.process.in_(processes),
            )
        )

    if varieties := filter.get("varieties", []):
        filter_clauses.append(
            and_(
                models.GreenCoffeeTag.type == "variety",
                func.lower(models.GreenCoffeeTag.value).in_(
                    [normalized_text(v) for v in varieties]
                ),
            ),
        )

    return filter_clauses


def location_filter_clauses(filter: LocationFilter) -> list[ColumnElement]:
    filter_clauses: list[ColumnElement] = []

    if city := filter.get("city"):
        filter_clauses.append(
            func.lower(models.Roaster.city).like(city.lower() + "%"),
        )

    if state := filter.get("state"):
        filter_clauses.append(
            func.lower(models.Roaster.state).like(state.lower() + "%"),
        )

    if country_code := filter.get("country_code"):
        filter_clauses.append(
            func.lower(models.Roaster.country).like(country_code.lower() + "%"),
        )

    if country_name := filter.get("country_name"):
        filter_clauses.append(
            func.lower(models.Country.name).like(country_name.lower() + "%"),
        )

    return filter_clauses
