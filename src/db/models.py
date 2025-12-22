from sqlalchemy import ForeignKey, String, ARRAY, JSON, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
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
    date_updated: Mapped[datetime | None]
    date_removed: Mapped[datetime | None]

    roaster = relationship("Roaster", back_populates="coffees")
