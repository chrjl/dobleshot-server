from __future__ import annotations

from sqlalchemy import select
from db import models
from .utilities.filters import name_filter_clauses

from typing import TYPE_CHECKING, TypeVar, Type, Generic, Sequence

if TYPE_CHECKING:
    from typing import Self
    from sqlalchemy import ColumnElement, Select, Join
    from .utilities.filters import NameFilter


T = TypeVar("T", bound=models.Base)


class Base(Generic[T]):
    def __init__(self, model: Type[T], *ids: str | int):
        self._model = model
        self._filters: list[ColumnElement] = []
        self._joins: list[Join] = []

        if ids:
            self.filter_by_ids(ids)

    def select(self, columns: list[str] | None = None) -> Select[tuple[T]]:
        if columns is None:
            return (
                select(self._model)
                .group_by(self._model.id)
                .select_from(self._model, *self._joins)
                .where(*self._filters)
            )

        return (
            select(*[getattr(self._model, c) for c in columns])
            .group_by(self._model.id)
            .select_from(self._model, *self._joins)
            .where(*self._filters)
        )

    def get(self, attribute: str, cols: list[str] | None = None):
        if cols is not None:
            return getattr(self, attribute)(cols)

        return getattr(self, attribute)()

    def filter_by_ids(self, ids: Sequence[str | int] | Select[tuple[T]]) -> Self:
        self._filters.append(getattr(self._model, "id").in_(ids))

        return self

    def filter_by_name(self, filter: NameFilter, name_column: str = "_name_n") -> Self:
        self._filters.extend(
            name_filter_clauses(filter, model=self._model, name_column=name_column)
        )

        return self
