from os import getenv
from sqlalchemy.orm import sessionmaker
from ariadne import gql, load_schema_from_path, make_executable_schema, QueryType
from ariadne.asgi import GraphQL
from ariadne.types import ContextValue

from db.main import engine

environment = getenv("APP_ENV")
type_defs = gql(load_schema_from_path("src/schema/"))


def get_context_value(request, _) -> ContextValue:
    Session = sessionmaker(engine, autoflush=True)

    return {
        "request": request,
        "Session": Session,
    }


query = QueryType()


@query.field("hello")
def resolve_hello(*_):
    return "Hello world!"


schema = make_executable_schema(type_defs, query)

app = GraphQL(
    schema,
    context_value=get_context_value,
    debug=(environment == "development"),
)
