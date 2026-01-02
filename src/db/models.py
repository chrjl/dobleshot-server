from sqlalchemy import ForeignKey, String, ARRAY, JSON, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.associationproxy import association_proxy
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Roaster(Base):
    __tablename__ = "roasters"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    city: Mapped[str | None]
    state: Mapped[str | None]
    country: Mapped[str | None]
    details = mapped_column(
        JSON,
        nullable=True,
        comment="Can include contact information, website, socials profiles, location details, etc.",
    )
    equipment_brand: Mapped[str | None]
    equipment_model: Mapped[str | None]
    equipment_capacity: Mapped[float | None]

    coffees = relationship("RoastedCoffee", back_populates="roaster")


class RoastedCoffee(Base):
    __tablename__ = "roasted_coffees"
    __table_args__ = {
        "comment": "Roasted coffee products for sale or use in preparation of drinks.",
    }

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    roaster_id = mapped_column(ForeignKey("roasters.id"), nullable=False)
    is_blend: Mapped[bool]
    profile = mapped_column(
        ARRAY(String),
        comment="A list of the roaster's intended roast attributes, e.g. dark roast, espresso, cold brew.",
    )
    notes = mapped_column(
        ARRAY(String), comment="A list of the roaster's tasting notes."
    )
    prices = mapped_column(JSON)
    date_added: Mapped[datetime] = mapped_column(default=func.now())
    date_updated: Mapped[datetime | None] = mapped_column(default=func.now())
    date_removed: Mapped[datetime | None]

    roaster = relationship("Roaster", back_populates="coffees")
    component_associations = relationship(
        "CoffeeComponent",
        back_populates="roasted_coffee",
        cascade="all, delete-orphan",
    )
    components = association_proxy(
        "component_associations",
        "green_coffee",
        creator=lambda g: CoffeeComponent(green_coffee=g),
    )


class Origin(Base):
    __tablename__ = "origins"
    __tableargs__ = {"comment": "Geographical origins of green coffees."}

    id: Mapped[int] = mapped_column(primary_key=True)
    region: Mapped[str | None]
    country: Mapped[str]

    coffees = relationship("GreenCoffee", back_populates="origin")


class GreenCoffee(Base):
    __tablename__ = "green_coffees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    process: Mapped[str | None]
    source: Mapped[str | None] = mapped_column(
        comment="The lowest level of traceability of the coffee, e.g. a farm name, cooperative, wet mill."
    )
    source_type: Mapped[str | None] = mapped_column(
        comment="e.g. single estate, microlot, smallholder, cooperative, wet mill, purchasing station"
    )
    community: Mapped[str | None]
    region_id = mapped_column(ForeignKey("origins.id"))
    varieties = mapped_column(ARRAY(String))
    details = mapped_column(JSON)

    origin = relationship("Origin", back_populates="coffees")


class CoffeeComponent(Base):
    __tablename__ = "roasted_coffee_components"
    __tableargs__ = {
        "comment": "Association table linking roasted coffees and green coffees."
    }

    roasted_id = mapped_column(ForeignKey("roasted_coffees.id"), primary_key=True)
    green_id = mapped_column(ForeignKey("green_coffees.id"), primary_key=True)
    fraction: Mapped[int | None] = mapped_column(
        comment="Percentage of blend constituted by green coffee."
    )
    date_added: Mapped[datetime] = mapped_column(default=func.now())
    date_updated: Mapped[datetime | None] = mapped_column(default=func.now())
    date_removed: Mapped[datetime | None]

    green_coffee = relationship("GreenCoffee")
    roasted_coffee = relationship(
        "RoastedCoffee", back_populates="component_associations"
    )
