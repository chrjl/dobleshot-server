import pytest, requests
from . import GRAPHQL_ENDPOINT


class TestCountryColumns:
    query = """
        query($ids: [ID], $filter: Filter) {
            countries(ids: $ids, filter: $filter) {
                id
                name
                longName
            }
        }
    """

    def test_all_countries(self):
        response = requests.post(GRAPHQL_ENDPOINT, json={"query": self.query})
        result = response.json()["data"]["countries"]

        assert response.status_code == 200
        assert len(result) == 262

    @pytest.mark.parametrize(
        "ids,expected_result",
        [
            (
                ["BO"],
                [
                    {
                        "id": "BO",
                        "name": "Bolivia",
                        "longName": "Plurinational State of Bolivia",
                    }
                ],
            ),
            (
                ["BO", "BR"],
                [
                    {
                        "id": "BO",
                        "name": "Bolivia",
                        "longName": "Plurinational State of Bolivia",
                    },
                    {
                        "id": "BR",
                        "name": "Brazil",
                        "longName": "Federative Republic of Brazil",
                    },
                ],
            ),
            (["ZZ"], []),
        ],
    )
    def test_filter_by_id(self, ids, expected_result):
        variables = {"ids": ids}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": self.query, "variables": variables}
        )
        result = response.json()["data"]["countries"]

        assert response.status_code == 200
        assert len(result) == len(expected_result)
        assert result == expected_result

    @pytest.mark.parametrize(
        "filter,count",
        [
            ({"name": {"starts_with": "Bo"}}, 4),
            ({"name": {"starts_with": "bO"}}, 4),
            ({"name": {"contains": "ia"}}, 48),
            ({"name": {"starts_with": "bo", "contains": "ia"}}, 2),
        ],
    )
    def test_filter_by_name(self, filter, count):
        variables = {"filter": filter}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": self.query, "variables": variables}
        )
        result = response.json()["data"]["countries"]

        assert response.status_code == 200
        assert len(result) == count

        assert "id" in result[0]
        assert "name" in result[0]
        assert "longName" in result[0]
        assert "Bolivia" in [row["name"] for row in result]

    @pytest.mark.parametrize(
        "ids,filter,expected_result",
        [
            (
                ["BO", "BR"],
                {"name": {"starts_with": "B"}},
                [
                    {
                        "id": "BO",
                        "name": "Bolivia",
                        "longName": "Plurinational State of Bolivia",
                    },
                    {
                        "id": "BR",
                        "name": "Brazil",
                        "longName": "Federative Republic of Brazil",
                    },
                ],
            ),
        ],
    )
    def test_multiple_filters(self, ids, filter, expected_result):
        variables = {"ids": ids, "filter": filter}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": self.query, "variables": variables}
        )
        result = response.json()["data"]["countries"]

        assert response.status_code == 200
        assert len(result) == len(expected_result)
        assert result == expected_result


class TestCountryRelationships:
    @pytest.mark.parametrize(
        "country_id,origin_name",
        [("US", "United States")],
    )
    def test_origin(self, country_id, origin_name):
        query = """
        query($country_id: ID, $origin_name: String) {
            countries(ids: [$country_id]) {
                origin {
                    name
                }
            }

            origins(filter: {name: {starts_with: $origin_name}}) {
                name
            }
        }
    """

        variables = {"country_id": country_id, "origin_name": origin_name}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}
        )

        assert response.status_code == 200

        result = response.json()["data"]
        country_query_result = result["countries"][0]["origin"]["name"]
        origin_query_result = result["origins"][0]["name"]

        assert country_query_result == origin_query_result

    @pytest.mark.parametrize(
        "country_id,expected_suborigin_count",
        [("US", 6), ("GT", 9)],
    )
    def test_suborigins(self, country_id, expected_suborigin_count):
        query = """
        query($country_id: ID) {
            countries(ids: [$country_id]) {
                origin {
                    suborigins {
                        name
                    }
                }
            }
        }
    """

        variables = {"country_id": country_id}

        response = requests.post(
            GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}
        )

        assert response.status_code == 200

        result = response.json()["data"]
        suborigin_count = len(result["countries"][0]["origin"]["suborigins"])
        assert suborigin_count == expected_suborigin_count

    def test_roasters(self):
        """TODO"""
        pass

    def test_roasted_coffees(self):
        """TODO"""
        pass

    def test_green_coffees(self):
        """TODO"""
        pass
