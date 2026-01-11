from sqlalchemy import ForeignKey, JSON, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.ext.mutable import MutableList, MutableDict
from datetime import datetime
from typing import Any


class Base(DeclarativeBase):
    type_annotation_map = {
        list[str]: MutableList.as_mutable(JSON),
        list[dict]: MutableList.as_mutable(JSON),
        dict: MutableDict.as_mutable(JSON),
    }


class Roaster(Base):
    __tablename__ = "roasters"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    city: Mapped[str | None]
    state: Mapped[str | None]
    country: Mapped[str] = mapped_column(
        String(length=2), comment="Two letter country code (ISO 3166-1 alpha-2)"
    )
    details: Mapped[dict] = mapped_column(
        nullable=True,
        server_default="{}",
        comment="Can include contact information, website, socials profiles, location details, etc.",
    )
    equipment_brand: Mapped[str | None]
    equipment_model: Mapped[str | None]
    equipment_capacity: Mapped[float | None]

    coffees: Mapped[list["RoastedCoffee"]] = relationship(back_populates="roaster")


class RoastedCoffee(Base):
    __tablename__ = "roasted_coffees"
    __table_args__ = {
        "comment": "Roasted coffee products for sale or use in preparation of drinks.",
    }

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    roaster_id: Mapped[int] = mapped_column(ForeignKey("roasters.id"))
    is_blend: Mapped[bool]

    profile: Mapped[list[str]] = mapped_column(
        server_default="[]",
        comment="A list of the roaster's intended roast attributes, e.g. dark roast, espresso, cold brew.",
    )
    notes: Mapped[list[str]] = mapped_column(
        server_default="[]",
        comment="A list of the roaster's tasting notes.",
    )
    prices: Mapped[list[dict]] = mapped_column(server_default="[]")
    date_added: Mapped[datetime] = mapped_column(server_default=func.now())
    date_updated: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    date_removed: Mapped[datetime | None]

    roaster: Mapped["Roaster"] = relationship(back_populates="coffees")
    component_associations: Mapped[list["CoffeeComponent"]] = relationship(
        back_populates="roasted_coffee",
        cascade="all, delete-orphan",
    )
    components: AssociationProxy[list["GreenCoffee"]] = association_proxy(
        "component_associations",
        "green_coffee",
        creator=lambda g: CoffeeComponent(green_coffee=g),
    )


class Origin(Base):
    __tablename__ = "origins"
    __tableargs__ = {"comment": "Geographical origins of green coffees."}

    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(
        String(length=2), comment="Two letter country code (ISO 3166-1 alpha-2)"
    )
    region: Mapped[str | None]

    coffees: Mapped[list["GreenCoffee"]] = relationship(back_populates="origin")


class GreenCoffee(Base):
    __tablename__ = "green_coffees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(
        comment="Green coffees without an assigned name refer to generic/unknown coffee of the specified region."
    )
    region_id: Mapped[int | None] = mapped_column(ForeignKey("origins.id"))

    process: Mapped[str | None]
    source: Mapped[str | None] = mapped_column(
        comment="The lowest level of traceability of the coffee, e.g. a farm name, cooperative, wet mill."
    )
    source_type: Mapped[str | None] = mapped_column(
        comment="e.g. single estate, microlot, smallholder, cooperative, wet mill, purchasing station"
    )
    community: Mapped[str | None]
    varieties: Mapped[list[str]] = mapped_column(server_default="[]")
    details: Mapped[dict] = mapped_column(server_default="{}")

    origin: Mapped["Origin"] = relationship(back_populates="coffees")


class CoffeeComponent(Base):
    __tablename__ = "roasted_coffee_components"
    __tableargs__ = {
        "comment": "Association table linking roasted coffees and green coffees."
    }

    roasted_id: Mapped[int] = mapped_column(
        ForeignKey("roasted_coffees.id"), primary_key=True
    )
    green_id: Mapped[int] = mapped_column(
        ForeignKey("green_coffees.id"), primary_key=True
    )
    fraction: Mapped[int | None] = mapped_column(
        comment="Percentage of blend constituted by green coffee."
    )
    date_added: Mapped[datetime] = mapped_column(server_default=func.now())
    date_updated: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    date_removed: Mapped[datetime | None]

    green_coffee: Mapped["GreenCoffee"] = relationship()
    roasted_coffee: Mapped["RoastedCoffee"] = relationship(
        back_populates="component_associations"
    )
