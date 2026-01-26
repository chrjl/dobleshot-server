import os
from dotenv import load_dotenv
import uvicorn


def main():
    APP_ENV = os.getenv("APP_ENV", "development")

    if APP_ENV == "development":
        return dev()
    else:
        return serve(APP_ENV)


def serve(APP_ENV):
    load_dotenv(f".env.{APP_ENV}")
    uvicorn.run("server:app")


def dev():
    if os.path.exists(".env.development"):
        load_dotenv(".env.development")
    else:
        load_dotenv(".env")

    uvicorn.run(
        "server:app", reload=True, reload_includes="*.graphql", log_level="trace"
    )


if __name__ == "__main__":
    main()
