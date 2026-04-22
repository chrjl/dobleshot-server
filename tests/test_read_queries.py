import pytest
import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from db import models, queries
from bin.seed_countries_regions import generate_country_objects, generate_origin_objects
from bin.seed_sample_data import green_coffee_objects, roaster_object_and_associations


SAMPLE_DATA_PATH = "assets/sample-data.json"


@pytest.fixture(scope="module", autouse=True)
def engine():
    with open(SAMPLE_DATA_PATH) as file:
        data = json.load(file)

    engine = create_engine("sqlite:///", echo=True)
    models.Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Seed country and origin tables
        session.add_all(generate_country_objects())
        session.add_all(generate_origin_objects())
        session.commit()

    # Seed sample data
    with Session(engine) as session:
        if green_coffee_data := data.get("green_coffees"):
            session.add_all(green_coffee_objects(engine, green_coffee_data))
            session.commit()

    for roaster_data in data.get("roasters"):
        with Session(engine) as session:
            r = roaster_object_and_associations(engine, roaster_data)

            roaster_object = r.get("roaster")
            session.add(roaster_object)

            coffee_objects = r.get("coffees", [])
            session.add_all(coffee_objects)

            component_objects = r.get("component_associations", [])
            session.add_all(component_objects)
            session.commit()

    yield engine

    models.Base.metadata.drop_all(engine)
    engine.dispose()


class TestSetup:
    def test_green_coffees(self, engine):
        with Session(engine) as session:
            result = session.scalars(select(models.GreenCoffee)).all()
            assert len(result) == 5

    def test_roasters(self, engine):
        with Session(engine) as session:
            result = session.scalars(select(models.Roaster)).all()
            assert len(result) == 2

    def test_roasted_coffees(self, engine):
        with Session(engine) as session:
            result = session.scalars(select(models.RoastedCoffee)).all()
            assert len(result) == 7

    def test_roasted_coffee_components(self, engine):
        with Session(engine) as session:
            result = session.scalars(select(models.CoffeeComponent)).all()
            assert len(result) == 10


class TestCountryFilters:
    def test_select(self, engine):
        with Session(engine) as session:
            query = queries.Country().select()
            result = session.scalars(query).all()

            assert len(result) == 262
            assert type(result[0]) == models.Country
            assert "BO" in [r.id for r in result]

    def test_filter_by_ids(self, engine):
        with Session(engine) as session:
            query = queries.Country().filter_by_ids(ids=["BO", "BR", "BI"])
            result = session.scalars(query.select()).all()

            assert len(result) == 3
            assert set([country.name for country in result]) == set(
                ["Bolivia", "Brazil", "Burundi"]
            )

            query = query.filter_by_ids(ids=["BO"])
            result = session.scalars(query.select()).all()
            assert len(result) == 1

            query = query.filter_by_ids(ids=["BR"])
            result = session.scalars(query.select()).all()
            assert len(result) == 0

    def test_filter_by_name(self, engine):
        with Session(engine) as session:
            query = queries.Country().filter_by_name(filter={"starts_with": "bo"})
            result = session.scalars(query.select()).all()

            assert len(result) == 4
            assert set([country.name for country in result]) == set(
                [
                    "Bolivia",
                    "Botswana",
                    "Bosnia and Herzegovina",
                    "Bouvet Island",
                ]
            )

            query = query.filter_by_name({"contains": "ia"})
            result = session.scalars(query.select()).all()

            assert len(result) == 2
            assert set([country.name for country in result]) == set(
                [
                    "Bolivia",
                    "Bosnia and Herzegovina",
                ]
            )

    def test_filter_by_ids_and_name(self, engine):
        with Session(engine) as session:
            query = (
                queries.Country()
                .filter_by_ids(ids=["BA", "BO", "BR"])
                .filter_by_name(filter={"contains": "ia"})
            )

            result = session.scalars(query.select()).all()

            assert len(result) == 2
            assert set([country.name for country in result]) == set(
                [
                    "Bolivia",
                    "Bosnia and Herzegovina",
                ]
            )


class TestCountryProperties:
    def test_origin_ids(self, engine):
        with Session(engine) as session:
            query = queries.Country().filter_by_ids(["BO", "GT"]).select(["origin_id"])
            result = session.scalars(query).all()

            control = session.scalars(
                select(models.Origin.id).where(
                    models.Origin.name.in_(["Bolivia", "Guatemala"])
                )
            ).all()

            assert set(result) == set(control)

    def test_suborigins(self, engine):
        with Session(engine) as session:
            query = queries.Country().filter_by_ids(ids=["GT"])
            result = session.scalars(query.select()).all()[0].suborigins

            assert len(result) == 9
            assert "Nuevo Oriente" in [o.name for o in result]

    def test_roasters(self, engine):
        with Session(engine) as session:
            query = queries.Country().get("roasters")
            result = session.scalars(query).all()

            assert len(result) == 2

    @pytest.mark.parametrize(
        "country_id,coffee_name,origin_name",
        [
            ("ET", "Tariku Kare", "Sidama"),
            ("PE", "Salomon Estela", "Cajamarca"),
        ],
    )
    def test_green_coffees(self, engine, country_id, coffee_name, origin_name):
        with Session(engine) as session:
            country = queries.Country().filter_by_ids([country_id])
            result = session.scalars(country.get("green_coffees")).all()

            assert len(result) == 1
            assert result[0].name.startswith(coffee_name)
            assert result[0].origin.name == origin_name
            assert result[0].origin.country_id == country_id

    @pytest.mark.parametrize(
        "country_id,coffee_names",
        [
            ("ET", ["Tariku Kare"]),
            ("GT", ["Minor Monuments", "Humbuggle: A Holiday Blend"]),
        ],
    )
    def test_roasted_coffees(self, engine, country_id, coffee_names):
        with Session(engine) as session:
            country = queries.Country().filter_by_ids([country_id])
            result = session.scalars(country.get("roasted_coffees")).all()

            assert set([r.name for r in result]) == set(coffee_names)


class TestOriginFilters:
    def test_select(self, engine):
        with Session(engine) as session:
            query = queries.Origin().select()
            result = session.scalars(query).all()

            assert len(result) == 214
            assert type(result[0]) == models.Origin
            assert "Bolivia" in [r.name for r in result]

    def test_filter_by_ids(self, engine):
        with Session(engine) as session:
            query = queries.Origin().filter_by_ids(ids=[1, 2, 3])
            result = session.scalars(query.select()).all()
            control = [
                session.get(models.Origin, 1),
                session.get(models.Origin, 2),
                session.get(models.Origin, 3),
            ]

            assert len(result) == 3
            assert set([country.name for country in result]) == set(
                [getattr(country, "name") for country in control]
            )

            query = query.filter_by_ids(ids=[1])
            result = session.scalars(query.select()).all()
            assert len(result) == 1

            query = query.filter_by_ids(ids=[2])
            result = session.scalars(query.select()).all()
            assert len(result) == 0

    def test_filter_by_name(self, engine):
        with Session(engine) as session:
            query = queries.Origin().filter_by_name(filter={"starts_with": "bo"})
            result = session.scalars(query.select()).all()

            assert len(result) == 3
            assert set([country.name for country in result]) == set(
                ["Bolivia", "Boyacá", "Boquete"]
            )

            query = query.filter_by_name({"contains": "ia"})
            result = session.scalars(query.select()).all()

            assert len(result) == 1
            assert result[0].name == "Bolivia"

    def test_filter_by_ids_and_name(self, engine):
        with Session(engine) as session:
            query = (
                queries.Origin()
                .filter_by_ids(ids=[1, 2, 3])
                .filter_by_name(filter={"contains": "ia"})
            )

            result = session.scalars(query.select()).all()

            assert len(result) == 1
            assert result[0].name == "Bolivia"


@pytest.fixture(scope="module")
def origin_us(engine):
    with Session(engine) as session:
        return session.scalar(
            queries.Origin().filter_by_name({"starts_with": "United States"}).select()
        )


@pytest.fixture(scope="module")
def origin_hawaii(engine):
    with Session(engine) as session:
        return session.scalar(
            queries.Origin().filter_by_name({"starts_with": "Hawaii"}).select()
        )


@pytest.fixture(scope="module")
def origin_regions_of_hawaii(engine):
    with Session(engine) as session:
        return session.scalars(
            select(models.Origin).where(models.Origin._name_n.in_(["kona", "kau"]))
        ).all()


class TestOriginSelfRelationships:
    def test_self(self, engine, origin_hawaii, origin_regions_of_hawaii):
        assert origin_hawaii.name == "Hawaii"
        assert len(origin_regions_of_hawaii) == 2

    def test_parent(self, engine, origin_hawaii, origin_us):
        with Session(engine) as session:
            session.add(origin_hawaii)
            session.add(origin_us)
            assert origin_hawaii.parent == origin_us

    def test_children(self, engine, origin_hawaii, origin_regions_of_hawaii):
        with Session(engine) as session:
            session.add(origin_hawaii)

            assert set([region.name for region in origin_hawaii.children]) == set(
                [region.name for region in origin_regions_of_hawaii]
            )


class TestOriginQueries:
    def test_suborigins(
        self, engine, origin_us, origin_hawaii, origin_regions_of_hawaii
    ):
        with Session(engine) as session:
            session.add(origin_us)
            session.add(origin_hawaii)
            for region in origin_regions_of_hawaii:
                session.add(region)

            result = session.scalars(
                queries.Origin()
                .filter_by_name({"starts_with": "united states"})
                .get("suborigins")
            ).all()

            assert len(result) == 6

            for region in [origin_us, origin_hawaii, *origin_regions_of_hawaii]:
                assert region in result

    @pytest.mark.parametrize(
        "query_name,coffee_name,origin_name,country_id",
        [
            ("ethiopia", "Tariku Kare", "Sidama", "ET"),
            ("cajamarca", "Salomon Estela", "Cajamarca", "PE"),
        ],
    )
    def test_green_coffees(
        self, engine, query_name, coffee_name, origin_name, country_id
    ):
        with Session(engine) as session:
            origin = queries.Origin().filter_by_name({"starts_with": query_name})
            result = session.scalars(origin.get("green_coffees")).all()

            assert len(result) == 1
            assert result[0].name.startswith(coffee_name)
            assert result[0].origin.name == origin_name
            assert result[0].origin.country_id == country_id

    @pytest.mark.parametrize(
        "query_name,coffee_names",
        [
            ("ethiopia", ["Tariku Kare"]),
            ("guatemala", ["Minor Monuments", "Humbuggle: A Holiday Blend"]),
        ],
    )
    def test_roasted_coffees(self, engine, query_name, coffee_names):
        with Session(engine) as session:
            origin = queries.Origin().filter_by_name({"starts_with": query_name})
            result = session.scalars(origin.get("roasted_coffees")).all()

            assert set([r.name for r in result]) == set(coffee_names)

    @pytest.mark.parametrize(
        "origin_name,processes",
        [
            ("Peru", ["natural"]),
            ("Rwanda", ["washed", "anaerobic"]),
            ("Huila", ["decaf", "sugarcane"]),
        ],
    )
    def test_processes(self, engine, origin_name, processes):
        with Session(engine) as session:
            origin = queries.Origin().filter_by_name({"starts_with": origin_name})
            result = session.scalars(origin.get("processes")).all()

            assert set(result) == set(processes)

    @pytest.mark.parametrize(
        "origin_name,varieties",
        [
            ("Peru", ["Marshell"]),
            ("Kenya", ["Batian", "Ruiru 11", "SL28"]),
        ],
    )
    def test_varieties(self, engine, origin_name, varieties):
        with Session(engine) as session:
            origin = queries.Origin().filter_by_name({"starts_with": origin_name})
            result = session.scalars(origin.get("varieties")).all()

            assert set(result) == set(varieties)

    @pytest.mark.parametrize(
        "origin_name,roaster_name",
        [
            ("Ethiopia", "Christopher L"),
            ("Rwanda", "Christopher L"),
            ("Huila", "Go Get Em Tiger"),
            ("Guatemala", "Go Get Em Tiger"),
        ],
    )
    def test_roasters(self, engine, origin_name, roaster_name):
        with Session(engine) as session:
            origin = queries.Origin().filter_by_name({"starts_with": origin_name})
            result = session.scalars(origin.get("roasters")).all()

            assert result[0].name.startswith(roaster_name)


class TestGreenCoffeeFilters:
    model = models.GreenCoffee

    @pytest.fixture(scope="function")
    def base_query(self):
        return queries.GreenCoffee()

    def test_select(self, engine, base_query):
        with Session(engine) as session:
            result = session.scalars(base_query.select()).all()

            assert len(result) == 5
            assert type(result[0]) == self.model
            assert "Placer de la Tarde" in [r.name for r in result]

    def test_filter_by_ids(self, engine, base_query):
        with Session(engine) as session:
            query = base_query.filter_by_ids(ids=[1, 2, 3])
            result = session.scalars(query.select()).all()
            control = [
                session.get(self.model, 1),
                session.get(self.model, 2),
                session.get(self.model, 3),
            ]

            assert len(result) == 3
            assert set([coffee.name for coffee in result]) == set(
                [getattr(coffee, "name") for coffee in control]
            )

            query = query.filter_by_ids(ids=[1])
            result = session.scalars(query.select()).all()
            assert len(result) == 1

            query = query.filter_by_ids(ids=[2])
            result = session.scalars(query.select()).all()
            assert len(result) == 0

    @pytest.mark.parametrize(
        "filter,expected_result_count,expected_results",
        [
            (
                {"starts_with": "P"},
                2,
                ["Privam Estate AA Week 23", "Placer de la Tarde"],
            ),
            (
                {"contains": "la"},
                2,
                ["Salomon Estela Marshell Natural K56", "Placer de la Tarde"],
            ),
            ({"starts_with": "P", "contains": "la"}, 1, ["Placer de la Tarde"]),
        ],
    )
    def test_filter_by_name(
        self, engine, base_query, filter, expected_result_count, expected_results
    ):
        with Session(engine) as session:
            query = base_query.filter_by_name(filter)
            result = session.scalars(query.select(["name"])).all()

            assert len(result) == expected_result_count
            for name in expected_results:
                assert name in result

    @pytest.mark.parametrize(
        "processes,count",
        [
            (["washed"], 3),
            (["natural"], 1),
            (["decaf"], 1),
            (["honey"], 0),
            (["anaerobic", "sugarcane"], 2),
        ],
    )
    def test_filter_by_process(self, engine, base_query, processes, count):
        with Session(engine) as session:
            query = base_query.filter_by_process(processes=processes)
            result = session.scalars(query.select()).all()

            assert len(result) == count

    @pytest.mark.parametrize(
        "varieties,count,coffee_names",
        [
            (["bourbon"], 1, ["Dukorere Kawa Anaerobic Lot 10"]),
            (
                ["bourbon, sl28"],
                2,
                ["Dukorere Kawa Anaerobic Lot 10", "Privam Estate AA Week 23"],
            ),
        ],
    )
    def test_filter_by_variety(
        self, engine, base_query, varieties, count, coffee_names
    ):
        with Session(engine) as session:
            query = base_query.filter_by_variety(varieties=varieties)
            result = session.scalars(query.select()).all()

            assert len(result) == count


class TestGreenCoffeeQueries:
    model = models.GreenCoffee

    @pytest.fixture(scope="function")
    def base_query(self):
        return queries.GreenCoffee()

    @pytest.mark.parametrize(
        "coffee_name,origin_name",
        [
            ("privam estate", "embu"),
            ("tariku kare", "sidama"),
            ("placer de la tarde", "huila"),
        ],
    )
    def test_origins(self, engine, base_query, coffee_name, origin_name):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            origin_q = queries.Origin().filter_by_name({"starts_with": origin_name})

            control = session.scalar(origin_q.select())
            origin = session.scalars(coffee_q.get("origins")).all()

            assert len(origin) == 1
            assert origin[0] == control

    @pytest.mark.parametrize(
        "coffee_name,processes",
        [
            ("privam estate", ["washed"]),
            ("tariku kare", ["washed"]),
            ("placer de la tarde", ["decaf", "sugarcane"]),
        ],
    )
    def test_processes(self, engine, base_query, coffee_name, processes):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            result = session.scalars(coffee_q.get("processes")).all()

            assert set(result) == set(processes)

    @pytest.mark.parametrize(
        "coffee_name,varieties",
        [
            ("privam estate", ["Batian", "Ruiru 11", "SL28"]),
            ("tariku kare", ["heirloom"]),
            ("placer de la tarde", []),
        ],
    )
    def test_varieties(self, engine, base_query, coffee_name, varieties):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            result = session.scalars(coffee_q.get("varieties")).all()

            assert set(result) == set(varieties)

    @pytest.mark.parametrize(
        "coffee_name,tasting",
        [
            ("privam estate", ["brown sugar", "green apple", "lime", "nougat", "pear"]),
            (
                "tariku kare",
                ["caramel", "honeydew", "key lime", "peach tea", "pink lemonade"],
            ),
            ("placer de la tarde", []),
        ],
    )
    def test_tasting(self, engine, base_query, coffee_name, tasting):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            result = session.scalars(coffee_q.get("tasting")).all()

            assert set(result) == set(tasting)

    @pytest.mark.parametrize(
        "coffee_name,roaster_name",
        [("Privam Estate", "Christopher L"), ("Placer de la Tarde", "Go Get Em Tiger")],
    )
    def test_roasters(self, engine, base_query, coffee_name, roaster_name):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            result = session.scalars(coffee_q.get("roasters")).all()

            assert result[0].name == roaster_name

    @pytest.mark.parametrize(
        "coffee_name,count",
        [
            ("privam estate", 1),
            ("minor monuments", 0),
        ],
    )
    def test_associations(self, engine, base_query, coffee_name, count):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            result = session.scalars(coffee_q.get("associations")).all()

            assert len(result) == count


class TestRoastedCoffeeFilters:
    model = models.RoastedCoffee

    @pytest.fixture(scope="function")
    def base_query(self):
        return queries.RoastedCoffee()

    def test_select(self, engine, base_query):
        with Session(engine) as session:
            result = session.scalars(base_query.select()).all()

            assert len(result) == 7
            assert type(result[0]) == self.model
            assert "Placer de la Tarde" in [r.name for r in result]

    def test_filter_by_ids(self, engine, base_query):
        with Session(engine) as session:
            query = base_query.filter_by_ids(ids=[1, 2, 3])
            result = session.scalars(query.select()).all()
            control = [
                session.get(self.model, 1),
                session.get(self.model, 2),
                session.get(self.model, 3),
            ]

            assert len(result) == 3
            assert set([coffee.name for coffee in result]) == set(
                [getattr(coffee, "name") for coffee in control]
            )

            query = query.filter_by_ids(ids=[1])
            result = session.scalars(query.select()).all()
            assert len(result) == 1

            query = query.filter_by_ids(ids=[2])
            result = session.scalars(query.select()).all()
            assert len(result) == 0

    @pytest.mark.parametrize(
        "filter,expected_result_count,expected_results",
        [
            (
                {"starts_with": "P"},
                2,
                ["Privam Estate AA Week 23", "Placer de la Tarde"],
            ),
            (
                {"contains": "la"},
                2,
                ["Salomon Estela Marshell Natural K56", "Placer de la Tarde"],
            ),
            ({"starts_with": "P", "contains": "la"}, 1, ["Placer de la Tarde"]),
        ],
    )
    def test_filter_by_name(
        self, engine, base_query, filter, expected_result_count, expected_results
    ):
        with Session(engine) as session:
            query = base_query.filter_by_name(filter)
            result = session.scalars(query.select(["name"])).all()

            assert len(result) == expected_result_count
            for name in expected_results:
                assert name in result

    @pytest.mark.parametrize(
        "processes,count",
        [
            (["washed"], 3),
            (["natural"], 1),
            (["decaf"], 1),
            (["honey"], 0),
            (["anaerobic", "sugarcane"], 2),
        ],
    )
    def test_filter_by_process(self, engine, base_query, processes, count):
        with Session(engine) as session:
            query = base_query.filter_by_process(processes=processes)
            result = session.scalars(query.select()).all()

            assert len(result) == count

    @pytest.mark.parametrize(
        "varieties,coffee_names",
        [
            (["SL28"], ["Privam Estate AA Week 23"]),
            (
                ["Bourbon", "Marshell"],
                [
                    "Dukorere Kawa Anaerobic Lot 10",
                    "Salomon Estela Marshell Natural K56",
                ],
            ),
        ],
    )
    def test_filter_by_variety(self, engine, base_query, varieties, coffee_names):
        with Session(engine) as session:
            query = base_query.filter_by_variety(varieties=varieties)
            result = session.scalars(query.select(["name"])).all()

            assert set(result) == set(coffee_names)

    @pytest.mark.parametrize(
        "profiles,count",
        [
            (["single origin"], 5),
            (["blend"], 2),
            (["espresso"], 2),
            (["decaf"], 1),
            (["single origin", "decaf"], 6),
        ],
    )
    def test_filter_by_profile(self, engine, base_query, profiles, count):
        with Session(engine) as session:
            query = base_query.filter_by_profile(profiles=profiles)
            result = session.scalars(query.select(["name"])).all()

            assert len(result) == count


class TestRoastedCoffeeQueries:
    model = models.RoastedCoffee

    @pytest.fixture(scope="function")
    def base_query(self):
        return queries.RoastedCoffee()

    @pytest.mark.parametrize(
        "coffee_name,origin_names",
        [
            ("privam estate", ["embu"]),
            ("minor monuments", ["honduras", "guatemala"]),
        ],
    )
    def test_origins(self, engine, base_query, coffee_name, origin_names):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            origins = session.scalars(coffee_q.get("origins")).all()

            control = [
                session.scalar(
                    queries.Origin().filter_by_name({"starts_with": name}).select()
                )
                for name in origin_names
            ]

            assert set(origins) == set(control)

    @pytest.mark.parametrize(
        "coffee_name,processes",
        [
            ("privam estate", ["washed"]),
            ("tariku kare", ["washed"]),
            ("placer de la tarde", ["decaf", "sugarcane"]),
        ],
    )
    def test_processes(self, engine, base_query, coffee_name, processes):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            result = session.scalars(coffee_q.get("processes")).all()

            assert set(result) == set(processes)

    @pytest.mark.parametrize(
        "coffee_name,varieties",
        [
            ("privam estate", ["Batian", "Ruiru 11", "SL28"]),
            ("tariku kare", ["heirloom"]),
            ("placer de la tarde", []),
        ],
    )
    def test_varieties(self, engine, base_query, coffee_name, varieties):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            result = session.scalars(coffee_q.get("varieties")).all()

            assert set(result) == set(varieties)

    @pytest.mark.parametrize(
        "coffee_name,tasting",
        [
            ("privam estate", []),
            ("minor monuments", ["brown sugar", "dark chocolate", "plum"]),
            ("placer de la tarde", ["black forest cake", "brownie", "cherry"]),
        ],
    )
    def test_tasting(self, engine, base_query, coffee_name, tasting):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            result = session.scalars(coffee_q.get("tasting")).all()

            assert set(result) == set(tasting)

    @pytest.mark.parametrize(
        "coffee_name,profiles",
        [
            ("privam estate", ["single origin"]),
            ("minor monuments", ["blend", "espresso"]),
            ("placer de la tarde", ["single origin", "espresso", "decaf"]),
        ],
    )
    def test_profile(self, engine, base_query, coffee_name, profiles):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            result = session.scalars(coffee_q.get("profiles")).all()

            assert set(result) == set(profiles)

    @pytest.mark.parametrize(
        "coffee_name,counts",
        [
            ("privam estate", {"green_coffees": 1, "origins": 0}),
            ("minor monuments", {"green_coffees": 0, "origins": 2}),
            ("placer de la tarde", {"green_coffees": 1, "origins": 0}),
        ],
    )
    def test_associations(self, engine, base_query, coffee_name, counts):
        with Session(engine) as session:
            coffee_q = base_query.filter_by_name({"starts_with": coffee_name})
            result = session.scalars(coffee_q.get("associations")).all()

            origins = [row.origin for row in result if row.origin is not None]
            green_coffees = [
                row.green_coffee for row in result if row.green_coffee is not None
            ]

            assert len(origins) == counts["origins"]
            assert len(green_coffees) == counts["green_coffees"]


class TestCoffeeComponentFilters:
    model = models.CoffeeComponent

    @pytest.mark.parametrize(
        "roasted_coffee_name,green_coffee_names,origin_names",
        [
            ("minor monuments", [], ["honduras", "guatemala"]),
            ("placer de la tarde", ["placer de la tarde"], []),
        ],
    )
    def test_filter_by_roasted_coffee(
        self, engine, roasted_coffee_name, green_coffee_names, origin_names
    ):
        with Session(engine) as session:
            roasted_coffees = session.scalars(
                queries.RoastedCoffee()
                .filter_by_name({"starts_with": roasted_coffee_name})
                .select()
            ).all()

            green_coffees = [
                session.scalar(
                    queries.GreenCoffee().filter_by_name({"starts_with": name}).select()
                )
                for name in green_coffee_names
            ]

            origins = [
                session.scalar(
                    queries.Origin().filter_by_name({"starts_with": name}).select()
                )
                for name in origin_names
            ]

            associations = session.scalars(
                queries.CoffeeComponent()
                .filter_by_roasted_coffee(roasted_ids=[r.id for r in roasted_coffees])
                .select()
            ).all()

            assert len(associations) == len(green_coffees) + len(origins)
            assert set(
                [c.roasted_coffee for c in associations if c.roasted_coffee is not None]
            ) == set(roasted_coffees)
            assert set(
                [c.green_coffee for c in associations if c.green_coffee is not None]
            ) == set(green_coffees)
            assert set([c.origin for c in associations if c.origin is not None]) == set(
                origins
            )

    @pytest.mark.parametrize(
        "green_coffee_name,roasted_coffee_names",
        [
            ("placer de la tarde", ["placer de la tarde"]),
            ("tariku kare", ["tariku kare"]),
        ],
    )
    def test_filter_by_green_coffee(
        self, engine, green_coffee_name, roasted_coffee_names
    ):
        with Session(engine) as session:
            green_coffees = session.scalars(
                queries.GreenCoffee()
                .filter_by_name({"starts_with": green_coffee_name})
                .select()
            ).all()

            roasted_coffees = [
                session.scalar(
                    queries.RoastedCoffee()
                    .filter_by_name({"starts_with": name})
                    .select()
                )
                for name in roasted_coffee_names
            ]

            associations = session.scalars(
                queries.CoffeeComponent()
                .filter_by_green_coffee(green_ids=[r.id for r in green_coffees])
                .select()
            ).all()

            assert len(associations) == len(green_coffees)
            assert set(
                [c.roasted_coffee for c in associations if c.roasted_coffee is not None]
            ) == set(roasted_coffees)
            assert set(
                [c.green_coffee for c in associations if c.green_coffee is not None]
            ) == set(green_coffees)

    @pytest.mark.parametrize(
        "origin_name,include_suborigins,count",
        [("guatemala", False, 2), ("colombia", False, 1), ("colombia", True, 2)],
    )
    def test_filter_by_origin(self, engine, origin_name, include_suborigins, count):
        with Session(engine) as session:
            origin_ids_q = (
                queries.Origin()
                .filter_by_name({"starts_with": origin_name})
                .select(["id"])
            )

            associations = session.scalars(
                queries.CoffeeComponent()
                .filter_by_origin(origin_ids_q, include_suborigins=include_suborigins)
                .select()
            ).all()

            assert len(associations) == count
