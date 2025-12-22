import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from .utilities import generate_url

load_dotenv()

connection_url = generate_url(
    drivername=os.getenv("DB_DRIVER", "postgresql"),
    username=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", ""),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME", "postgres"),
)

engine = create_engine(connection_url, echo=True)
