#!/usr/bin/env python3
import os, argparse, json
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.main import engine
from db.models import Origin, Roaster, RoastedCoffee, GreenCoffee, CoffeeComponent
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
        for country, regions in data["origins"].items():
            for region in regions:
                session.add(Origin(country=country, region=region))

        for green_data in data["green_coffees"]:
            origin_data = green_data.get("origin")
            country = origin_data.get("country")
            region = origin_data.get("region")
            community = origin_data.get("community")

            origin = (
                (
                    session.scalar(
                        select(Origin).where(
                            Origin.country == country, Origin.region == region
                        )
                    )
                    or Origin(country=country, region=region)
                )
                if country
                else None
            )

            green_coffee = GreenCoffee(
                **{
                    **{
                        k: v
                        for k, v in green_data.items()
                        if is_in_model(GreenCoffee, k)
                    },
                    "origin": origin,
                    "community": community,
                }
            )

            session.add(green_coffee)

        for roaster_data in data["roasters"]:
            roaster = Roaster(
                **{k: v for k, v in roaster_data.items() if is_in_model(Roaster, k)}
            )

            session.add(roaster)

            for coffee_data in roaster_data["roasted_coffees"]:
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

                    component = None

                    if name := component_data.get("name"):
                        # If component name is known, get the `GreenCoffee`
                        # object. If it doesn't exist, set the component to a
                        # generic `GreenCoffee` for the region.

                        component = session.scalar(
                            select(GreenCoffee).where(GreenCoffee.name == name)
                        )

                    if not component and (country := component_data.get("country")):
                        # If the country and/or region are known, try to get the
                        # generic `GreenCoffee` object for the region and process.

                        region = component_data.get("region")
                        process = component_data.get("process")

                        # Try to get the `Origin` object for the region.
                        origin = session.scalar(
                            select(Origin).where(
                                Origin.country == country, Origin.region == region
                            )
                        )

                        if not origin:
                            # If the `Origin` entry does not exist, create both
                            # the `Origin` and region-generic `GreenCoffee`
                            # objects.

                            origin = Origin(country=country, region=region)
                            component = GreenCoffee(
                                process=process,
                                origin=origin,
                            )

                        else:
                            # Try to get the generic `GreenCoffee` object for
                            # the region and process. If it does not exist, create it.

                            component = session.scalar(
                                select(GreenCoffee).where(
                                    GreenCoffee.name == None,
                                    GreenCoffee.process == process,
                                    GreenCoffee.origin == origin,
                                )
                            ) or GreenCoffee(
                                process=process,
                                origin=origin,
                            )

                    # Associate the `GreenCoffee` object to the `RoastedCoffee`.
                    fraction = (
                        100
                        if not coffee_data.get("is_blend")
                        else component_data.get("fraction")
                    )
                    coffee.component_associations.append(
                        CoffeeComponent(
                            roasted_coffee=coffee,
                            green_coffee=component,
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
