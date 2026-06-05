import os
from dotenv import load_dotenv
import uvicorn


def main(options={}):
    if ("host" not in options) and (host := os.getenv("UVICORN_HOST")):
        options["host"] = host
    if ("port" not in options) and (port := os.getenv("UVICORN_PORT")):
        options["port"] = int(port)

    uvicorn.run("server:app", **options)


def serve():
    load_dotenv(f".env.{os.getenv("APP_ENV")}")
    main()


def dev():
    os.environ["APP_ENV"] = "development"

    if os.path.exists(".env.development"):
        load_dotenv(".env.development")
    else:
        load_dotenv(".env")

    options = {
        "reload": True,
        "reload_includes": "*.graphql",
        "log_level": "trace",
    }

    main(options)


def test(host="127.0.0.1", port=8001):
    os.environ["APP_ENV"] = "testing"

    options = {"host": host, "port": port}
    main(options)


if __name__ == "__main__":
    main()
