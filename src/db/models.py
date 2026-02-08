from sqlalchemy import ForeignKey, JSON, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.ext.mutable import MutableList, MutableDict
from datetime import datetime
from typing import Any


def getdeepattr(obj: Any, attr: str, default: Any = None):
    result = obj

    for a in attr.split("."):
        try:
            if not hasattr(result, a):
                return default

            result = getattr(result, a)
        except DetachedInstanceError:
            return default

    return result


def representation(title: str, fields: dict[str, Any]) -> str:
    items = []

    for field, value in fields.items():
        try:
            if type(value) == str:
                items.append(f'{field}="{value}"')
            elif value is not None:
                items.append(f"{field}={str(value)}")
        except AttributeError or KeyError:
            pass

    return f"{title}({", ".join(items)})"


class Base(DeclarativeBase):
    type_annotation_map = {
        list[str]: MutableList.as_mutable(JSON),
        list[dict]: MutableList.as_mutable(JSON),
        dict: MutableDict.as_mutable(JSON),
    }


class Roaster(Base):
    """Objects from the `roasters` table.

    Required attributes:
        name(str): name of the roaster
        country(str): 2-letter country code

    Relationships:
        coffees(list[RoastedCoffee])

    Optional attributes:
        city(str)
        state(str)
        equipment_brand(str)
        equipment_model(str)
        equipment_capacity(float): in kg

    JSON attributes:
        details: additional contact details (see contact.schema.json)

            {
                "website": "https://gget.com",
                "profiles": [
                    {
                        "network": "facebook",
                        "handle": "ggetla",
                        "url": "https://facebook.com/ggetla"
                    }
                ],
                "locations": [
                    {
                        "name": "Grand Central Market",
                        "type": "coffeebar",
                        "address": "317 S Broadway",
                        "city": "Los Angeles",
                        "state": "CA",
                        "zipcode": 90013
                    }
                ],
                "contacts": [
                    {
                        "name": "John Doe",
                        "title": "Head roaster",
                        "location": "Roastery",
                        "address": "123 Unknown",
                        "city": "Los Angeles",
                        "state": "CA",
                        "zipcode": 99999
                    }
                ]
            }
    """

    __tablename__ = "roasters"
    __table_args__ = {
        "comment": "Identity information of companies, people, or users that roast coffees."
    }

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
    equipment_capacity: Mapped[float | None] = mapped_column(
        comment="Size of the roasting machine in kg."
    )

    coffees: Mapped[list["RoastedCoffee"]] = relationship(back_populates="roaster")

    def __repr__(self):
        fields = {"id": getattr(self, "id", None), "name": getattr(self, "name", None)}

        return representation("Roaster", fields)


class RoastedCoffee(Base):
    """Objects from the `roasted_coffees` table.

    Required attributes:
        name(str): name of the roasted coffee
        [ roaster_id(int) | roaster(Roaster) ]
        is_blend(bool): set `False` for single origin products

    Relationships:
        roaster(Roaster)
        component_associations(list[CoffeeComponent])
        components(list[GreenCoffee]): association proxy through `component_associations`

    Optional attributes:
        profile(list[str]): roast profile/attributes
        notes(list[str]): tasting notes
        date_added(datetime, server default)
        date_updated(datetime, server default)
        date_removed(datetime): coffee removed from the `Roaster`'s menu

    JSON attributes:
        prices: list of prices based on quantity, sale type (see prices.schema.json)

            [
                {
                "description": "retail",
                "price": 20,
                "quantity": 10.5,
                "unit": "oz"
                }
            ]
    """

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
    green_coffee_components: AssociationProxy[list["GreenCoffee"]] = association_proxy(
        "component_associations",
        "green_coffee",
        creator=lambda g: CoffeeComponent(green_coffee=g),
    )
    origin_components: AssociationProxy[list["Origin"]] = association_proxy(
        "component_associations",
        "origin",
        creator=lambda o: CoffeeComponent(origin=o),
    )

    def __repr__(self):
        roaster = getdeepattr(self, "roaster.name", None)

        common_fields = {
            "id": getattr(self, "id", None),
            "name": getattr(self, "name", None),
        }

        relationship_fields = {
            "roaster": roaster,
            "roaster_id": getattr(self, "roaster_id", None) if not roaster else None,
        }

        return representation("RoastedCoffee", {**common_fields, **relationship_fields})


class Country(Base):
    """List of countries of the world, with coffee growing data (if available)

    Required attributes:
        id(str, PK): GENC 2A code + optional region identifier
        name(str): short-form name

    Optional attributes:
        long_name(str): long-form name

    Attributes:
        processes(list[str])
        varieties(list[str])
        harvest_start(int)
        harvest_end(int)

    Relationships:
        origins(list[Origin])
        green_coffees(list[GreenCoffee])
        coffees(list[RoastedCoffee])
    """

    __tablename__ = "countries"
    __table_args__ = {
        "comment": "List of countries attributed to US Dept. of State; coffee data attributed to Cafe Imports."
    }

    id: Mapped[str] = mapped_column(String(length=2), primary_key=True)
    name: Mapped[str]
    long_name: Mapped[str | None]

    origins: Mapped[list["Origin"]] = relationship(back_populates="country")

    def __repr__(self):
        return f"Country(id={self.id}, name={self.name})"


class Origin(Base):
    """List of coffee growing origins

    Required attributes:
        name(str)
        [country_id(str, FK) | country ]
        [parent_id(int, self-referential FK) | parent ]: null means the row is a country

    Relationships:
        parent(Origin)
        children(list[Origin])
        country(Country)
        green_coffees(list[GreenCoffee])
        coffees(list[RoastedCoffee])

    JSON attributes:
        details: region-specific growing/harvest details

            {
                "processes": ["washed", "natural"],
                "varieties": ["s795", "timor hybrid"],
                "harvest_start": 5,
                "harvest_end": 10
            }
    """

    __tablename__ = "origins"
    __table_args__ = {"comment": "Data attributed to Cafe Imports."}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("origins.id"))
    country_id: Mapped[str] = mapped_column(ForeignKey("countries.id"))
    processes: Mapped[list[str] | None] = mapped_column(server_default="[]")
    varieties: Mapped[list[str] | None] = mapped_column(server_default="[]")
    harvest_start: Mapped[int | None]
    harvest_end: Mapped[int | None]
    details: Mapped[dict | None] = mapped_column(server_default="{}")
    type: Mapped[str]

    parent: Mapped["Origin"] = relationship(back_populates="children", remote_side=[id])
    children: Mapped[list["Origin"]] = relationship(back_populates="parent")
    country: Mapped["Country"] = relationship(back_populates="origins")
    green_coffees: Mapped[list["GreenCoffee"]] = relationship(back_populates="origin")

    def __repr__(self):
        fields = {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "country_id": self.country_id,
        }

        return representation("Origin", fields)


class GreenCoffee(Base):
    """Objects from the `green_coffees` table.

    Required attributes:
        name(str|None): leave null for region-generic coffees
        [ origin_id(int) | origin ]

    Relationships:
        origin(Origin)
        country(Country)

    Optional attributes:
        [ region_id(int) | region ]
        process(str)
        source(str): the lowest level of traceability
        source_type(str): e.g. microlot, single estate, coop
        community(str): more fine-grained region detail
        varieties(list[str])

    JSON attributes:
        details: more fine-grained sourcing information

            {
                "harvest_year": 2024,
                "harvest_season": null,
                "supplier": "Showroom Coffee",
                "processing": "Cherries are handpicked and floated to separate by color and density, then pulped and sorted through washing channels into fermentation tanks, where they sit overnight before more washing and 10-14 days of drying on raised beds.",
                "references": [
                    {
                        "type": "website",
                        "url": "https://www.croptocup.com/community/privam-estate/"
                    }
                ]
            }
    """

    __tablename__ = "green_coffees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(
        comment="Green coffees without an assigned name refer to generic/unknown coffee of the specified region."
    )
    origin_id: Mapped[int] = mapped_column(ForeignKey("origins.id"))

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

    origin: Mapped["Origin"] = relationship(back_populates="green_coffees")
    country: Mapped["Country"] = relationship(secondary="origins", viewonly=True)

    def __repr__(self):
        origin_obj = getdeepattr(self, "origin")

        common_fields = {
            "id": getattr(self, "id"),
            "name": getattr(self, "name", None),
        }

        relationship_fields = (
            {"origin": origin_obj.name, "country": origin_obj.country_id}
            if origin_obj
            else {"origin_id": getattr(self, "origin_id", None)}
        )

        return representation("GreenCoffee", {**common_fields, **relationship_fields})


class CoffeeComponent(Base):
    """Objects from the `roasted_coffee_components` association table.

    Required attributes:
        [ roasted_id(int) | roasted_coffee(RoastedCoffee) ]: PK

    Requires one of:
        [ green_id(int) | green_coffee(GreenCoffee) ]: null for origin-generic coffee
        origin_id(int): only required for origin-generic coffee

    Relationships:
        roasted_coffee(RoastedCoffee)
        green_coffee(GreenCoffee)
        origin(Origin)

    Optional attributes:
        process(str)
        fraction(int): percentage
        date_added(datetime, server default)
        date_updated(datetime, server default)
        date_removed(datetime)

    JSON attributes:
        details

            {
                "name": green coffee name, if it is not included in the `green_coffees` table
                "region": region name, if it is not included in the `origins` table
            }
    """

    __tablename__ = "roasted_coffee_components"
    __tableargs__ = {
        "comment": "Association table linking roasted coffees and green coffees."
    }

    id: Mapped[int] = mapped_column(primary_key=True)
    roasted_id: Mapped[int] = mapped_column(ForeignKey("roasted_coffees.id"))
    green_id: Mapped[int | None] = mapped_column(ForeignKey("green_coffees.id"))
    origin_id: Mapped[int | None] = mapped_column(ForeignKey("origins.id"))
    process: Mapped[str | None]

    fraction: Mapped[int | None] = mapped_column(
        comment="Percentage of blend constituted by green coffee."
    )
    date_added: Mapped[datetime] = mapped_column(server_default=func.now())
    date_updated: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    date_removed: Mapped[datetime | None]

    details: Mapped[dict | None] = mapped_column(server_default="{}")

    origin: Mapped["Origin"] = relationship()
    green_coffee: Mapped["GreenCoffee"] = relationship()
    roasted_coffee: Mapped["RoastedCoffee"] = relationship(
        back_populates="component_associations"
    )

    def __repr__(self):
        roasted_coffee_name = getdeepattr(self, "roasted_coffee.name", None)
        green_coffee_name = getdeepattr(self, "green_coffee.name", None)
        green_coffee_origin = getdeepattr(self, "green_coffee.origin.name", None)
        country_id = getdeepattr(
            self,
            "green_coffee.origin.country_id",
            getdeepattr(self, "origin.country_id", None),
        )
        origin_name = getdeepattr(self, "origin.name", None)

        relationship_fields = {
            "roasted_coffee": roasted_coffee_name,
            "roasted_id": (
                getattr(self, "roasted_id") if roasted_coffee_name is None else None
            ),
            "green_coffee": green_coffee_name,
            "green_id": (
                getattr(self, "green_id") if green_coffee_name is None else None
            ),
            "origin": green_coffee_origin or origin_name,
            "origin_id": (getattr(self, "origin_id") if not origin_name else None),
            "country_id": country_id,
        }

        common_fields = {
            "fraction": getattr(self, "fraction"),
        }

        return representation(
            "CoffeeComponent", {"id": self.id, **relationship_fields, **common_fields}
        )
