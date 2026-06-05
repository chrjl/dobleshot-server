import pytest, requests

GRAPHQL_ENDPOINT = "http://localhost:8000/api/graphql"


def test_hello():
    name = "dog"

    # graphql
    query = """
    query($name: String) { hello(name: $name) }
    """

    variables = {"name": name}

    response = requests.post(
        GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}
    )

    assert response.status_code == 200
    assert response.json()["data"]["hello"] == f"Hello {name}!"
