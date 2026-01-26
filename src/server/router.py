from starlette.applications import Starlette
from starlette.routing import Route

from api.main import app as api


routes = [
    Route("/api/graphql", api),
]

app = Starlette(routes=routes)
