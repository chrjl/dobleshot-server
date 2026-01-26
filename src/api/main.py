from ariadne import gql, load_schema_from_path, make_executable_schema, QueryType
from ariadne.asgi import GraphQL

type_defs = gql(load_schema_from_path("src/schema/"))


query = QueryType()


@query.field("hello")
def resolve_hello(*_):
    return "Hello world!"


schema = make_executable_schema(type_defs, query)

app = GraphQL(schema)
