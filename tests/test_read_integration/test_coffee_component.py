import pytest, requests
from . import GRAPHQL_ENDPOINT


@pytest.mark.parametrize(
    "name,components",
    [
        ("Privam Estate", {"green_coffees": ["Privam Estate AA Week 23"]}),
        ("Minor Monuments", {"origins": ["Guatemala", "Honduras"]}),
    ],
)
def test_components_of_roasted_coffee(name, components):
    query = """
    query($filter: Filter) {
        roastedCoffees(filter: $filter) {
            components {
                roastedCoffee {
                    name
                }
                greenCoffee {
                    name
                }
                origin {
                    name
                }
                process
            }
        }
    }
    """
    variables = {"filter": {"name": {"starts_with": name}}}

    response = requests.post(
        GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}
    )

    assert response.status_code == 200

    result = response.json()["data"]["roastedCoffees"][0]["components"]

    assert len(result) == len(components.get("green_coffees", [])) + len(
        components.get("origins", [])
    )

    for item in result:
        assert item["roastedCoffee"]["name"].startswith(name)

        if green_coffee := item.get("greenCoffee"):
            assert green_coffee["name"] in components.get("green_coffees", [])
        elif origin := item.get("origin"):
            assert origin["name"] in components.get("origins", [])


@pytest.mark.parametrize(
    "name,roasted_coffee_names",
    [
        ("Privam Estate", ["Privam Estate AA Week 23"]),
        ("Placer de la Tarde", ["Placer de la Tarde"]),
    ],
)
def test_associations_of_green_coffee(name, roasted_coffee_names):
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
                origin {
                    name
                }
                process
            }
        }
    }
    """
    variables = {"filter": {"name": {"starts_with": name}}}

    response = requests.post(
        GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}
    )

    assert response.status_code == 200

    result = response.json()["data"]["greenCoffees"][0]["associations"]

    assert len(result) == len(roasted_coffee_names)

    for item in result:
        assert item["greenCoffee"]["name"].startswith(name)

        if roasted_coffee := item.get("roastedCoffee"):
            assert roasted_coffee["name"] in roasted_coffee_names


class TestColumns:
    def test_fraction_of_single_origin_coffees(self):
        query = """
            query($filter: Filter) {
                roastedCoffees(filter: $filter) {
                    components {
                        greenCoffee {
                            name
                        }
                        roastedCoffee {
                            name
                        }
                        fraction
                    }
                }
            }
        """

        filter = {"coffeeDetail": {"profiles": ["single origin"]}}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": query, "variables": {"filter": filter}}
        )

        assert response.status_code == 200

        result = response.json()["data"]["roastedCoffees"][0]
        assert result["components"][0]["fraction"] == 100
