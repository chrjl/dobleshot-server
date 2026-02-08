import csv
from os import path, getenv
from typing import Any
from sqlalchemy.orm import Session, class_mapper

from db.main import engine
from db.models import Country, Origin
from db.utilities import is_in_model

import logging

logger = logging.getLogger(__name__)

if getenv("DEBUG") and getenv("DEBUG") != "False":
    logger.setLevel(logging.DEBUG)

BASEDIR = "assets"
COUNTRY_LIST_FILENAME = "independent-states-in-the-world.csv"
REGION_LIST_FILENAME = "region-list-cafe-imports.csv"
REGION_DATA_FILENAME = "region-data-cafe-imports.csv"


def generate_country_data():
    countries: dict[str, dict] = {}

    with open(path.join(BASEDIR, COUNTRY_LIST_FILENAME), encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            id = row["GENC_2A_CODE"]
            name = row["SHORT_FORM_NAME"]
            long_name = row["LONG_FORM_NAME"]

            countries[id] = {
                "name": name,
                "long_name": long_name,
            }

    return countries


def generate_country_objects() -> list[Country]:
    return [
        Country(id=id, **country_data)
        for id, country_data in generate_country_data().items()
    ]


def generate_origin_objects() -> list[Origin]:
    # Import region data
    with open(path.join(BASEDIR, REGION_DATA_FILENAME)) as file:
        reader = csv.DictReader(file)
        region_data: dict[tuple[str, str | None], dict[str, Any]] = {}

        for row in reader:
            country_id = row["country_id"]
            region = row["region"]

            region_data[(row["country_id"], row["region"].lower() or None)] = {
                **{k: v for k, v in row.items() if is_in_model(Origin, k) and v != ""},
                "processes": row["processes"].split(";") if row["processes"] else [],
                "varieties": row["varieties"].split(";") if row["varieties"] else [],
            }

    country_data = generate_country_data()
    country_objs: dict[str, Origin] = {}
    region_objs: list[Origin] = []

    # Generate region list
    with open(path.join(BASEDIR, REGION_LIST_FILENAME)) as file:
        reader = csv.DictReader(file)
        row: dict[str, str]

        for row in reader:
            country_id = row["country_id"]
            region_name = row["region"]
            subregion_list = row["subregions"].split(";") if row["subregions"] else []

            # Create country object, if necessary
            if country_id not in country_objs:
                data = region_data.get((country_id, None), {"country_id": country_id})

                country_objs[country_id] = Origin(
                    name=country_data[country_id]["name"],
                    type="country",
                    **data,
                )

                logger.info(f"CREATED REGION OBJECT: {country_id}")

            # Create region object
            if region_name:
                data = region_data.get(
                    (country_id, region_name.lower()), {"country_id": country_id}
                )
                logger.debug(
                    {
                        "country_id": country_id,
                        "region_name": region_name,
                        **data,
                    }
                )

                region = Origin(
                    name=region_name,
                    type="region",
                    parent=country_objs[country_id],
                    **data,
                )

                region_objs.append(region)

                logger.info(f"CREATED REGION OBJECT: {region_name}")

                # Create subregion objects
                for subregion_name in subregion_list:
                    data = region_data.get(
                        (country_id, subregion_name.lower()), {"country_id": country_id}
                    )

                    region_objs.append(
                        Origin(
                            name=subregion_name,
                            type="region",
                            parent=region,
                            **data,
                        )
                    )

                    logger.info(f"CREATED SUBREGION OBJECT: {subregion_name}")

    return [*country_objs.values(), *region_objs]


def main():
    country_objs = generate_country_objects()
    origin_objs = generate_origin_objects()

    with Session(engine) as session:
        session.add_all(country_objs)
        session.add_all(origin_objs)
        session.commit()


if __name__ == "__main__":
    main()
