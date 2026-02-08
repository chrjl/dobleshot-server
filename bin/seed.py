#!/usr/bin/env python3
import os, argparse, json
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from db.main import engine
from db.models import (
    Country,
    Origin,
    Roaster,
    RoastedCoffee,
    GreenCoffee,
    CoffeeComponent,
)
from db.utilities import is_in_model


def main():
    parser = argparse.ArgumentParser(
        description="Seeds the database defined in db/main.py with user-provided sample data."
    )

    parser.add_argument("--json", help="path to json file")
    args = parser.parse_args()

    if (not args.json) or (not os.path.exists(args.json)):
        raise FileNotFoundError()

    with open(args.json) as file:
        text = file.read()
        data = json.loads(text)

    with Session(engine) as session:
        for green_data in data.get("green_coffees", []):
            origin_data = green_data.get("origin")
            country_id = origin_data.get("country")
            region_name = origin_data.get("region")
            community = origin_data.get("community")
            details = green_data.get("details")

            country = session.get(Country, country_id)

            if not country:
                raise ValueError

            if region_name:
                origin = session.scalar(
                    select(Origin).where(
                        func.lower(Origin.name) == func.lower(region_name)
                    )
                )

                if not origin:
                    details["region"] = region_name
            else:
                origin = next(o for o in country.origins if o.name == country.name)

            green_coffee = GreenCoffee(
                **{
                    **{
                        k: v
                        for k, v in green_data.items()
                        if is_in_model(GreenCoffee, k)
                    },
                    "origin": origin,
                    "community": community,
                    "details": details or {},
                }
            )

            session.add(green_coffee)

        for roaster_data in data["roasters"]:
            roaster = Roaster(
                **{k: v for k, v in roaster_data.items() if is_in_model(Roaster, k)}
            )

            session.add(roaster)

            for coffee_data in roaster_data.get("roasted_coffees", []):
                coffee = RoastedCoffee(
                    **{
                        k: v
                        for k, v in coffee_data.items()
                        if (is_in_model(RoastedCoffee, k) and k not in ["component"])
                    }
                )

                for component_data in coffee_data.get("components", []):
                    # Find or create the `GreenCoffee` object corresponding to
                    # the component, and associate it to the `RoastedCoffee`.

                    name = component_data.get("name")
                    fraction = (
                        100
                        if not coffee_data.get("is_blend")
                        else component_data.get("fraction")
                    )

                    # If component name is known, try to find and assign the
                    # respective `GreenCoffee` object.
                    component = (
                        session.scalar(
                            select(GreenCoffee).where(GreenCoffee.name == name)
                        )
                        if name
                        else None
                    )

                    if component:
                        coffee.component_associations.append(
                            CoffeeComponent(
                                roasted_coffee=coffee,
                                green_coffee=component,
                                fraction=fraction,
                            )
                        )

                    else:
                        # Create a component association with the origin.

                        country_id = component_data.get("country")
                        region_name = component_data.get("region")
                        process = component_data.get("process")
                        details = {}

                        if name:
                            details["name"] = name

                        # Try to find `Origin` object for the region.
                        origin = session.scalar(
                            select(Origin).where(Origin.name == region_name)
                        )

                        if not origin:
                            # Try to find `Origin` object for the country.
                            origin = session.scalar(
                                select(Origin)
                                .join(Origin.country)
                                .where(
                                    Origin.country_id == country_id,
                                    Origin.name == Country.name,
                                )
                            )

                            if region_name:
                                details["region"] = region_name

                        coffee.component_associations.append(
                            CoffeeComponent(
                                roasted_coffee=coffee,
                                process=process,
                                origin=origin,
                                fraction=fraction,
                            )
                        )

                # Associate the `RoastedCoffee` object to the `Roaster`.
                roaster.coffees.append(coffee)

        session.flush()

        if input("Commit changes? [y|n]: ") == "y":
            session.commit()


if __name__ == "__main__":
    main()
