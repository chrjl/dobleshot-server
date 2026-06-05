import pytest, requests
from . import GRAPHQL_ENDPOINT


class TestGreenCoffeeColumns:
    query = """
    query($ids: [ID], $filter: Filter) {
        greenCoffees(ids: $ids, filter: $filter) {
            id
            name
            source {
                name
                sourceType
                producerName
                harvestYear
            }
            details
        }
    }
    """

    def test_all_green_coffees(self):
        response = requests.post(GRAPHQL_ENDPOINT, json={"query": self.query})
        data = response.json()["data"]
        result = data["greenCoffees"]

        assert response.status_code == 200
        assert len(result) == 5

        for green_coffee in result:
            assert "id" in green_coffee
            assert type(green_coffee.get("id")) == str

            assert "name" in green_coffee
            if name := green_coffee.get("name"):
                assert type(name) == str

            assert "details" in green_coffee
            assert type(green_coffee.get("details")) == dict

            assert "source" in green_coffee
            source = green_coffee["source"]

            if source_name := source.get("name"):
                assert type(source_name) == str
            if source_type := source.get("source_type"):
                assert type(source_type) == str
            if producer_name := source.get("producer_name"):
                assert type(producer_name) == str
            if harvest_year := source.get("harvest_year"):
                assert type(harvest_year) == int


class TestGreenCoffeeFilters:
    query = """
    query($ids: [ID], $filter: Filter) {
        greenCoffees(ids: $ids, filter: $filter) {
            id
            name
        }
    }
    """

    @pytest.mark.parametrize(
        "name",
        ["Privam Estate", "Tariku Kare"],
    )
    def test_filter_by_id(self, name):
        response = requests.post(
            GRAPHQL_ENDPOINT,
            json={
                "query": self.query,
                "variables": {"filter": {"name": {"starts_with": name}}},
            },
        )

        assert response.status_code == 200

        coffee_ids = [
            coffee["id"] for coffee in response.json()["data"]["greenCoffees"]
        ]

        assert len(coffee_ids) == 1

        response = requests.post(
            GRAPHQL_ENDPOINT,
            json={"query": self.query, "variables": {"ids": coffee_ids}},
        )

        assert response.status_code == 200

        coffee_name = response.json()["data"]["greenCoffees"][0]["name"]
        assert coffee_name.startswith(name)

    @pytest.mark.parametrize(
        "name,is_valid",
        [("Privam Estate", True), ("invalid", False)],
    )
    def test_filter_by_name(self, name, is_valid):
        filter = {"name": {"contains": name[1:]}}
        variables = {"filter": filter}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": self.query, "variables": variables}
        )
        result = response.json()["data"]["greenCoffees"]

        assert response.status_code == 200
        if is_valid:
            assert result[0]["name"].startswith(name)
        else:
            assert result == []

    @pytest.mark.parametrize(
        "processes,count",
        [
            (["washed"], 3),
            (["natural"], 1),
            (["washed", "natural"], 4),
            (["washed", "anaerobic"], 3),
        ],
    )
    def test_filter_by_process(self, processes, count):
        filter = {"coffeeDetail": {"processes": processes}}
        variables = {"filter": filter}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": self.query, "variables": variables}
        )
        assert response.status_code == 200

        result = response.json()["data"]["greenCoffees"]
        assert len(result) == count

    @pytest.mark.parametrize(
        "varieties,count",
        [
            (["sl28"], 1),
            (["sl-28"], 1),
            (["sl28", "sl-28"], 1),
            (["bourbon", "heirloom", "sl28"], 3),
            (["caturra"], 0),
        ],
    )
    def test_filter_by_variety(self, varieties, count):
        filter = {"coffeeDetail": {"varieties": varieties}}
        variables = {"filter": filter}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": self.query, "variables": variables}
        )
        assert response.status_code == 200

        result = response.json()["data"]["greenCoffees"]
        assert len(result) == count

    @pytest.mark.parametrize(
        "tasting,count",
        [(["cocoa"], 2), (["lime"], 2), (["cocoa", "fudge"], 2), (["nothing"], 0)],
    )
    def test_filter_by_tasting(self, tasting, count):
        filter = {"coffeeDetail": {"tasting": tasting}}
        variables = {"filter": filter}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": self.query, "variables": variables}
        )
        assert response.status_code == 200

        result = response.json()["data"]["greenCoffees"]
        assert len(result) == count


class TestGreenCoffeeRelationships:
    @pytest.mark.parametrize(
        "name,origin_name,country_id",
        [("Privam Estate", "Embu", "KE"), ("Tariku Kare", "Sidama", "ET")],
    )
    def test_origin(self, name, origin_name, country_id):
        query = """
        query($filter: Filter) {
            greenCoffees(filter: $filter) {
                source {
                    origin {
                        name
                        country {
                            id
                            name
                        }
                    }
                    community
                }
            }
        }
        """
        variables = {"filter": {"name": {"starts_with": name}}}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}
        )

        result = response.json()["data"]["greenCoffees"]
        origin = result[0]["source"]["origin"]
        assert origin["name"] == origin_name
        assert origin["country"]["id"] == country_id

    @pytest.mark.parametrize(
        "name,processes",
        [("Privam Estate", ["washed"]), ("Placer de la Tarde", ["decaf", "sugarcane"])],
    )
    def test_processes(self, name, processes):
        query = """
        query($filter: Filter) {
            greenCoffees(filter: $filter) {
                processes
            }
        }
        """
        variables = {"filter": {"name": {"starts_with": name}}}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}
        )

        assert response.status_code == 200

        result = response.json()["data"]["greenCoffees"]

        assert len(result) == 1
        assert set(result[0]["processes"]) == set(processes)

    @pytest.mark.parametrize(
        "name,varieties",
        [
            ("Privam Estate", ["Batian", "Ruiru 11", "SL28"]),
            ("Tariku Kare", ["heirloom"]),
        ],
    )
    def test_varieties(self, name, varieties):
        query = """
        query($filter: Filter) {
            greenCoffees(filter: $filter) {
                varieties
            }
        }
        """
        variables = {"filter": {"name": {"starts_with": name}}}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}
        )

        assert response.status_code == 200

        result = response.json()["data"]["greenCoffees"]

        assert len(result) == 1
        assert set(result[0]["varieties"]) == set(varieties)

    @pytest.mark.parametrize(
        "name,tasting",
        [
            ("Privam Estate", ["brown sugar", "green apple", "lime", "nougat", "pear"]),
            (
                "Tariku Kare",
                ["caramel", "honeydew", "key lime", "peach tea", "pink lemonade"],
            ),
        ],
    )
    def test_tasting(self, name, tasting):
        query = """
        query($filter: Filter) {
            greenCoffees(filter: $filter) {
                tasting
            }
        }
        """
        variables = {"filter": {"name": {"starts_with": name}}}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}
        )

        assert response.status_code == 200

        result = response.json()["data"]["greenCoffees"]

        assert len(result) == 1
        assert set(result[0]["tasting"]) == set(tasting)

    @pytest.mark.parametrize(
        "name,roaster_names",
        [
            ("Privam Estate", ["Christopher L"]),
            ("Placer de la Tarde", ["Go Get Em Tiger"]),
        ],
    )
    def test_roasters(self, name, roaster_names):
        query = """
        query($filter: Filter) {
            greenCoffees(filter: $filter) {
                roasters {
                    name
                }
            }
        }
        """
        variables = {"filter": {"name": {"starts_with": name}}}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}
        )

        assert response.status_code == 200

        result = response.json()["data"]["greenCoffees"][0]

        assert set([roaster["name"] for roaster in result["roasters"]]) == set(
            roaster_names
        )

    @pytest.mark.parametrize(
        "name",
        ["Privam Estate", "Placer de la Tarde"],
    )
    def test_associations(self, name):
        query = """
        query($filter: Filter) {
            greenCoffees(filter: $filter) {
                associations {
                    roastedCoffee {
                        name
                    }
                    greenCoffee {
                        name
                    }
                }
            }
        }
        """
        variables = {"filter": {"name": {"starts_with": name}}}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}
        )

        assert response.status_code == 200

        result = response.json()["data"]["greenCoffees"][0]

        assert result["associations"][0]["roastedCoffee"]["name"].startswith(name)
        assert result["associations"][0]["greenCoffee"]["name"].startswith(name)
